from __future__ import annotations

import csv
import json
from datetime import timedelta
from io import StringIO
from typing import TypedDict, cast

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.core.paginator import Page
from django.db.models import QuerySet
from django.http import HttpResponse
from django.utils.dateparse import parse_date

from dispenses.services.oracle import infer_columns
from query.sql_guard import extract_query_sources

from .forms import QueryForm
from .models import QueryAudit


class QueryAuditFilters(TypedDict):
    username: str
    success: str
    date_from: str
    date_to: str


class QueryResultTableConfig(TypedDict):
    tableId: str
    filename: str
    columns: list[str]
    defaultVisible: list[bool]
    toggleButtonId: str
    panelId: str
    checklistId: str
    resetButtonId: str
    closeButtonId: str


class QueryResultContext(TypedDict):
    form: QueryForm
    results: list[dict[str, object]]
    cols: list[str]
    cols_json: str
    max_rows: int
    query_table_config_json: str


class QuerySearchContext(TypedDict):
    form: QueryForm
    max_rows: int
    allowed_tables: list[str]


class QueryAuditListContext(TypedDict):
    page_obj: Page[QueryAudit]
    audits: list[QueryAudit]
    filters: QueryAuditFilters


class QueryExecutionSummary(TypedDict):
    source_count: int
    sources: list[str]


def filter_query_audits(
    queryset: QuerySet[QueryAudit],
    *,
    username: str,
    success: str,
    date_from: str,
    date_to: str,
) -> QuerySet[QueryAudit]:
    parsed_date_from = parse_date(date_from.strip()) if date_from else None
    parsed_date_to = parse_date(date_to.strip()) if date_to else None

    if username:
        queryset = queryset.filter(user__username__icontains=username)
    if success in {"true", "false"}:
        queryset = queryset.filter(success=(success == "true"))
    if parsed_date_from:
        queryset = queryset.filter(created_at__date__gte=parsed_date_from)
    if parsed_date_to:
        queryset = queryset.filter(created_at__date__lt=parsed_date_to + timedelta(days=1))
    return queryset


def audit_filters_from_request(request: WSGIRequest) -> QueryAuditFilters:
    return {
        "username": (request.GET.get("username") or "").strip(),
        "success": (request.GET.get("success") or "").strip(),
        "date_from": request.GET.get("date_from", ""),
        "date_to": request.GET.get("date_to", ""),
    }


def build_query_audit_csv(queryset: QuerySet[QueryAudit]) -> HttpResponse:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["created_at", "username", "success", "row_count", "query_text", "error_message"])

    for audit in queryset:
        writer.writerow(
            [
                audit.created_at.isoformat(),
                audit.user.username if audit.user else "",
                "true" if audit.success else "false",
                audit.row_count,
                audit.query_text,
                audit.error_message,
            ]
        )

    response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="query_audit.csv"'
    return response


def create_query_audit(
    *,
    user,
    query_text: str,
    row_count: int,
    success: bool,
    error_message: str = "",
) -> QueryAudit:
    created = QueryAudit.objects.create(
        user=user,
        query_text=query_text,
        row_count=row_count,
        success=success,
        error_message=error_message,
    )
    return cast(QueryAudit, created)


def build_query_result_context(form: QueryForm, results: list[dict[str, object]]) -> QueryResultContext:
    cols = infer_columns(results)
    table_config: QueryResultTableConfig = {
        "tableId": "tblResults",
        "filename": "resultats_requete",
        "columns": cols,
        "defaultVisible": [True for _ in cols],
        "toggleButtonId": "btnCols",
        "panelId": "panelCols",
        "checklistId": "colsChecklist",
        "resetButtonId": "colsReset",
        "closeButtonId": "colsClose",
    }
    return {
        "form": form,
        "results": results,
        "cols": cols,
        "cols_json": json.dumps(cols),
        "max_rows": settings.QUERY_PREVIEW_MAX_ROWS,
        "query_table_config_json": json.dumps(table_config),
    }


def build_query_search_context(form: QueryForm) -> QuerySearchContext:
    return {
        "form": form,
        "max_rows": settings.QUERY_PREVIEW_MAX_ROWS,
        "allowed_tables": list(settings.QUERY_ALLOWED_TABLES),
    }


def build_query_execution_summary(query: str) -> QueryExecutionSummary:
    sources = [f"{schema}.{table}" if schema else table for schema, table in extract_query_sources(query)]
    unique_sources = list(dict.fromkeys(sources))
    return {
        "source_count": len(unique_sources),
        "sources": unique_sources,
    }


def build_query_audit_list_context(page: Page[QueryAudit], filters: QueryAuditFilters) -> QueryAuditListContext:
    return {
        "page_obj": page,
        "audits": list(cast(list[QueryAudit], page.object_list)),
        "filters": filters,
    }


def latest_successful_audit() -> QueryAudit | None:
    return cast(QueryAudit | None, QueryAudit.objects.filter(success=True).select_related("user").first())
