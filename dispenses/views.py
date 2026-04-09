import logging

from django.contrib.auth.decorators import login_required
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .forms import DispenseSearchForm
from .services.monitoring import build_monitoring_payload
from .services.oracle import (
    build_oracle_insert_sql_literal,
    build_oracle_update_sql_literal,
    fetch_dispense_rows_by_pairs,
    fetch_dispenses,
    fetch_short_webservice_internal_error_without_next,
    fetch_short_webservice_logs_undo_without_next,
    fetch_webservice_internal_error_without_next,
    fetch_webservice_logs,
    fetch_webservice_logs_undo_without_next,
    fetch_webservice_ssin_not_integrated_without_next,
    fetch_webservice_unknown_code_without_next,
    identify_person,
    resolve_person,
)
from .services.page_contexts import (
    MONITORING_EXPORT_FIELDS,
    build_monitoring_view_context,
    build_search_results_context,
    build_ws_issue_context,
    resolve_monitoring_period,
)
from .services.page_responses import build_csv_download_response, build_text_download_response

logger = logging.getLogger(__name__)


def _record_pair(record: dict[str, object]) -> tuple[str, str]:
    return str(record["id_dispense"]), str(record["decisionsituationnbr"])


def _render_ws_issue_page(
    request: WSGIRequest,
    *,
    ws_logs: list[dict[str, object]],
    issue_title: str,
    issue_description: str,
    issue_badge: str,
    sql_download_url: str | None = None,
    sql_button_label: str = "Telecharger le SQL",
) -> HttpResponse:
    context = build_ws_issue_context(
        ws_logs=ws_logs,
        issue_title=issue_title,
        issue_description=issue_description,
        issue_badge=issue_badge,
        sql_download_url=sql_download_url,
        sql_button_label=sql_button_label,
    )
    return render(request, "dispenses/ws_issue.html", context)


def _internal_error_sql_from_row(row: dict[str, object] | None) -> str:
    if not row:
        return ""
    return build_oracle_update_sql_literal(
        table="ib_dispenses",
        row=row,
        key_fields={"id_dispense", "no_avenant"},
        set_fields={"flg_envoye_onem": "N"},
    )


def _undo_sql_from_row(row: dict[str, object] | None) -> str:
    if not row:
        return ""
    return build_oracle_insert_sql_literal(
        table="ib_dispenses",
        row=row,
        exclude={"id_dispense", "dt_creation", "user_creation", "dt_modification", "user_modification"},
        increment_fields={"no_avenant"},
        set_fields={"flg_envoye_onem": "N"},
        nullify_fields={"dt_envoi_onem"},
    )


@login_required
@require_http_methods(["GET"])
def monitoring_dispenses(request: WSGIRequest):
    month, year, current_month, current_year, date_start, date_end_excl = resolve_monitoring_period(request)
    refresh = request.GET.get("refresh") == "1"
    payload = build_monitoring_payload(
        request,
        year=year,
        month=month,
        date_start=date_start,
        date_end_excl=date_end_excl,
        refresh=refresh,
    )
    return render(
        request,
        "dispenses/monitoring.html",
        build_monitoring_view_context(
            month=month,
            year=year,
            current_month=current_month,
            current_year=current_year,
            payload=payload,
        ),
    )


@login_required
@require_http_methods(["GET"])
def export_monitoring_abnormal_csv(request: WSGIRequest) -> HttpResponse:
    month, year, _current_month, _current_year, date_start, date_end_excl = resolve_monitoring_period(request)
    payload = build_monitoring_payload(
        request,
        year=year,
        month=month,
        date_start=date_start,
        date_end_excl=date_end_excl,
        refresh=request.GET.get("refresh") == "1",
    )
    rows = payload["abnormal_records"]
    return build_csv_download_response(
        rows=rows,
        fieldnames=list(rows[0].keys()) if rows else MONITORING_EXPORT_FIELDS,
        filename=f"monitoring_abnormal_{year:04d}_{month:02d}.csv",
    )


@login_required
@require_http_methods(["GET"])
def search_dispenses(request: WSGIRequest):
    form = DispenseSearchForm(request.GET or None)
    if not (form.is_valid() and any(form.cleaned_data.values())):
        return render(request, "dispenses/search.html", {"form": form})

    key = form.cleaned_data["search_key"]
    value = form.cleaned_data["search_value"]
    if key in ("id_dispense", "no_dispense"):
        key, value = identify_person(request, key, value)

    person = resolve_person(request, key, value)
    if not person:
        return render(request, "dispenses/search.html", {"form": form, "not_found": True})

    dispenses = fetch_dispenses(request, person.id_demandeur)
    ws_logs = fetch_webservice_logs(request, person.id_demandeur)
    return render(
        request,
        "dispenses/result.html",
        build_search_results_context(
            form=form,
            person=person,
            dispenses=dispenses,
            ws_logs=ws_logs,
        ),
    )


@login_required
@require_http_methods(["GET"])
def internal_error(request: WSGIRequest):
    logger.info("Rendering internal error dispense view")
    ws_logs = fetch_webservice_internal_error_without_next(request)
    logger.debug("Fetched %s internal error webservice logs", len(ws_logs))
    return _render_ws_issue_page(
        request,
        ws_logs=ws_logs,
        issue_title="Erreurs internes",
        issue_description="Repere les reponses ONEM en erreur interne et prepare un SQL de remise en file.",
        issue_badge="ERR",
        sql_download_url="solve_dispenses_internal_error",
        sql_button_label="Generer le SQL de correction",
    )


@login_required
@require_http_methods(["GET", "POST"])
def undo_dispense(request: WSGIRequest):
    ws_logs = fetch_webservice_logs_undo_without_next(request)
    logger.debug("Fetched %s undo webservice logs", len(ws_logs))
    return _render_ws_issue_page(
        request,
        ws_logs=ws_logs,
        issue_title="Annulations a rejouer",
        issue_description="Liste les messages UND00003 et genere un nouveau script d'insertion.",
        issue_badge="UNDO",
        sql_download_url="solve_dispenses_undo",
        sql_button_label="Generer le SQL d'annulation",
    )


@login_required
@require_http_methods(["GET"])
def get_new_sql_create_for_internal_error(request: WSGIRequest):
    logger.info("Generating SQL file for internal error dispenses")
    records = fetch_short_webservice_internal_error_without_next(request)
    rows_by_pair = fetch_dispense_rows_by_pairs(
        request,
        (_record_pair(record) for record in records),
    )
    statements = []
    for index, record in enumerate(records):
        sql = _internal_error_sql_from_row(rows_by_pair.get(_record_pair(record)))
        if sql:
            statements.append(sql)
            logger.debug("Generated internal error SQL statement %s with length %s", index, len(sql))
    return build_text_download_response("\n".join(statements) + ("\n" if statements else ""), "internal_error")


@login_required
@require_http_methods(["GET"])
def get_new_sql_create_for_undo(request: WSGIRequest):
    records = fetch_short_webservice_logs_undo_without_next(request)
    rows_by_pair = fetch_dispense_rows_by_pairs(
        request,
        (_record_pair(record) for record in records),
    )
    statements = [sql for record in records if (sql := _undo_sql_from_row(rows_by_pair.get(_record_pair(record))))]
    return build_text_download_response("\n".join(statements) + ("\n" if statements else ""), "undo")


@login_required
@require_http_methods(["GET"])
def unknown_code(request: WSGIRequest):
    return _render_ws_issue_page(
        request,
        ws_logs=fetch_webservice_unknown_code_without_next(request),
        issue_title="Codes inconnus",
        issue_description="Controle les statuts de retour non reconnus pour investigation metier.",
        issue_badge="CODE",
    )


@login_required
@require_http_methods(["GET"])
def ssin_not_integrated(request: WSGIRequest):
    return _render_ws_issue_page(
        request,
        ws_logs=fetch_webservice_ssin_not_integrated_without_next(request),
        issue_title="NISS non integres",
        issue_description="Isole les flux rejetes parce que le NISS n'est pas encore integre cote ONEM.",
        issue_badge="NISS",
    )
