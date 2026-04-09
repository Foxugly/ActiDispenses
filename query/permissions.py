from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.core.handlers.wsgi import WSGIRequest

RUN_SQL_CONSOLE_PERMISSION = "query.run_sql_console"
VIEW_QUERY_AUDIT_PERMISSION = "query.view_queryaudit"
VIEW_OPS_DASHBOARD_PERMISSION = "query.view_ops_dashboard"


def _user_has_access(request: WSGIRequest, permission: str) -> bool:
    user = request.user
    return bool(user.is_staff or user.is_superuser or user.has_perm(permission))


def ensure_can_run_sql_console(request: WSGIRequest) -> None:
    if not _user_has_access(request, RUN_SQL_CONSOLE_PERMISSION):
        raise PermissionDenied("Acces interdit.")


def ensure_can_view_query_audit(request: WSGIRequest) -> None:
    if not _user_has_access(request, VIEW_QUERY_AUDIT_PERMISSION):
        raise PermissionDenied("Acces interdit.")


def ensure_can_view_ops_dashboard(request: WSGIRequest) -> None:
    if not _user_has_access(request, VIEW_OPS_DASHBOARD_PERMISSION):
        raise PermissionDenied("Acces interdit.")
