from __future__ import annotations

import json
from datetime import date
from typing import Mapping, TypedDict

from django.core.handlers.wsgi import WSGIRequest
from django.utils import timezone

from dispenses.forms import DispenseSearchForm
from dispenses.services.oracle import parse_int
from dispenses.services.page_tables import build_table_payload

WS_WANTED = [
    "id_unempl_decision_dispense",
    "id_dispense",
    "id_demandeur",
    "decisionidentification",
    "decisionsituationnbr",
    "decisionstatus",
    "detail_statut_reponse",
    "user_creation",
    "dt_creation",
    "user_modification",
    "dt_modification",
]

DISPENSES_WANTED = [
    "id_dispense",
    "id_demandeur",
    "no_dispense",
    "no_avenant",
    "flg_envoye_onem",
    "dt_envoi_onem",
    "user_creation",
    "dt_creation",
    "user_modification",
    "dt_modification",
]

MONITORING_EXPORT_FIELDS = [
    "id_dispense",
    "id_demandeur",
    "nom",
    "prenom",
    "niss",
    "decisionidentification",
    "decisionsituationnbr",
    "detail_statut_reponse",
    "dt_creation",
    "user_creation",
    "dt_modification",
    "user_modification",
]


class WsIssueContext(TypedDict):
    ws_logs: list[dict[str, object]]
    ws_cols: list[str]
    ws_cols_json: str
    ws_default_visible_json: str
    ws_table_config_json: str
    issue_title: str
    issue_description: str
    issue_badge: str
    sql_download_url: str | None
    sql_button_label: str


def resolve_monitoring_period(request: WSGIRequest) -> tuple[int, int, int, int, date, date]:
    today = timezone.localdate()
    current_month, current_year = today.month, today.year
    month = parse_int(request.GET.get("month"), today.month, 1, 12)
    year = parse_int(request.GET.get("year"), today.year, 2000, 2100)
    if (year, month) > (current_year, current_month):
        year, month = current_year, current_month

    date_start = date(year, month, 1)
    date_end_excl = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return month, year, current_month, current_year, date_start, date_end_excl


def build_monitoring_view_context(
    *,
    month: int,
    year: int,
    current_month: int,
    current_year: int,
    payload: Mapping[str, object],
) -> dict[str, object]:
    return {
        "month": month,
        "year": year,
        "can_go_next": (payload["next_year"], payload["next_month"]) <= (current_year, current_month),
        **payload,
    }


def build_search_results_context(
    *,
    form: DispenseSearchForm,
    person: object,
    dispenses: list[dict[str, object]],
    ws_logs: list[dict[str, object]],
) -> dict[str, object]:
    dispenses_payload = build_table_payload(
        rows=dispenses,
        wanted_columns=DISPENSES_WANTED,
        table_id="tblDispenses",
        filename="dispenses",
        toggle_button_id="btnColsDispenses",
        panel_id="panelColsDispenses",
        checklist_id="colsChecklistDispenses",
        reset_button_id="colsResetDispenses",
        close_button_id="colsCloseDispenses",
    )
    ws_payload = build_table_payload(
        rows=ws_logs,
        wanted_columns=WS_WANTED,
        table_id="tblWs",
        filename="historique_onem",
        toggle_button_id="btnColsWs",
        panel_id="panelColsWs",
        checklist_id="colsChecklistWs",
        reset_button_id="colsResetWs",
        close_button_id="colsCloseWs",
    )
    return {
        "form": form,
        "person": person,
        "dispenses": dispenses,
        "ws_logs": ws_logs,
        "dispenses_cols": dispenses_payload["columns"],
        "ws_cols": ws_payload["columns"],
        "dispenses_cols_json": dispenses_payload["columns_json"],
        "ws_cols_json": ws_payload["columns_json"],
        "dispenses_default_visible_json": dispenses_payload["default_visible_json"],
        "ws_default_visible_json": ws_payload["default_visible_json"],
        "result_tables_config_json": json.dumps([dispenses_payload["table_config"], ws_payload["table_config"]]),
    }


def build_ws_issue_context(
    *,
    ws_logs: list[dict[str, object]],
    issue_title: str,
    issue_description: str,
    issue_badge: str,
    sql_download_url: str | None = None,
    sql_button_label: str = "Telecharger le SQL",
) -> WsIssueContext:
    ws_payload = build_table_payload(
        rows=ws_logs,
        wanted_columns=WS_WANTED,
        table_id="tblWs",
        filename="dispenses_issue",
        toggle_button_id="btnColsWs",
        panel_id="panelColsWs",
        checklist_id="colsChecklistWs",
        reset_button_id="colsResetWs",
        close_button_id="colsCloseWs",
    )
    return {
        "ws_logs": ws_logs,
        "ws_cols": ws_payload["columns"],
        "ws_cols_json": ws_payload["columns_json"],
        "ws_default_visible_json": ws_payload["default_visible_json"],
        "ws_table_config_json": json.dumps(ws_payload["table_config"]),
        "issue_title": issue_title,
        "issue_description": issue_description,
        "issue_badge": issue_badge,
        "sql_download_url": sql_download_url,
        "sql_button_label": sql_button_label,
    }
