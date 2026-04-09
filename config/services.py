from __future__ import annotations

from dataclasses import dataclass

from django.core.cache import cache

from config.metrics import AppMetricsSnapshot, get_app_metrics_snapshot
from query.models import QueryAudit
from query.services import latest_successful_audit


@dataclass(frozen=True)
class OpsDashboardData:
    total_audits: int
    successful_audits: int
    failed_audits: int
    latest_audits: list[QueryAudit]
    latest_successful_audit: QueryAudit | None
    last_oracle_success: dict[str, str] | None
    metrics: AppMetricsSnapshot


def build_ops_dashboard_data() -> OpsDashboardData:
    audits = QueryAudit.objects.select_related("user").order_by("-created_at")
    return OpsDashboardData(
        total_audits=audits.count(),
        successful_audits=audits.filter(success=True).count(),
        failed_audits=audits.filter(success=False).count(),
        latest_audits=list(audits[:10]),
        latest_successful_audit=latest_successful_audit(),
        last_oracle_success=cache.get("healthz:last_oracle_success"),
        metrics=get_app_metrics_snapshot(),
    )
