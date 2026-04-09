import logging
from time import perf_counter

from django.contrib.auth.decorators import login_required
from django.core.handlers.wsgi import WSGIRequest
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from config.metrics import increment_metric
from dispenses.services.oracle import fetch_query

from .forms import QueryForm
from .models import QueryAudit
from .permissions import ensure_can_run_sql_console, ensure_can_view_query_audit
from .services import (
    audit_filters_from_request,
    build_query_audit_csv,
    build_query_audit_list_context,
    build_query_execution_summary,
    build_query_result_context,
    build_query_search_context,
    create_query_audit,
    filter_query_audits,
)

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET", "POST"])
def run_query(request: WSGIRequest):
    ensure_can_run_sql_console(request)

    form = QueryForm(request.POST or None)
    if form.is_valid():
        sql = form.cleaned_data["query"]
        query_summary = build_query_execution_summary(sql)
        increment_metric("query.requests")
        logger.info(
            "Running read-only Oracle query for user_id=%s with max_rows=%s source_count=%s sources=%s",
            request.user.id,
            build_query_search_context(form)["max_rows"],
            query_summary["source_count"],
            ",".join(query_summary["sources"]) or "-",
        )
        started = perf_counter()
        try:
            results = fetch_query(request, sql)
        except Exception as exc:
            increment_metric("query.failure")
            create_query_audit(
                user=request.user,
                query_text=sql,
                row_count=0,
                success=False,
                error_message=str(exc),
            )
            raise

        increment_metric("query.success")
        create_query_audit(
            user=request.user,
            query_text=sql,
            row_count=len(results),
            success=True,
        )
        logger.info(
            "Oracle query succeeded for user_id=%s row_count=%s duration_ms=%.2f",
            request.user.id,
            len(results),
            round((perf_counter() - started) * 1000, 2),
        )
        return render(request, "query/result.html", build_query_result_context(form, results))

    return render(request, "query/search.html", build_query_search_context(form))


@login_required
@require_http_methods(["GET"])
def query_audit_list(request: WSGIRequest):
    ensure_can_view_query_audit(request)

    audits = QueryAudit.objects.select_related("user").order_by("-created_at")
    filters = audit_filters_from_request(request)
    audits = filter_query_audits(audits, **filters)

    paginator = Paginator(audits, 25)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "query/audit_list.html", build_query_audit_list_context(page, filters))


@login_required
@require_http_methods(["GET"])
def query_audit_detail(request: WSGIRequest, audit_id: int):
    ensure_can_view_query_audit(request)
    audit = get_object_or_404(QueryAudit.objects.select_related("user"), pk=audit_id)
    return render(request, "query/audit_detail.html", {"audit": audit})


@login_required
@require_http_methods(["GET"])
def query_audit_export(request: WSGIRequest):
    ensure_can_view_query_audit(request)
    audits = QueryAudit.objects.select_related("user").order_by("-created_at")
    audits = filter_query_audits(audits, **audit_filters_from_request(request))
    return build_query_audit_csv(audits)
