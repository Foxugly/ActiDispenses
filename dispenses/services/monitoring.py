from __future__ import annotations

import json
from datetime import date
from typing import TypedDict, cast

from django.conf import settings
from django.core.cache import cache
from django.core.handlers.wsgi import WSGIRequest

from dispenses.services.constants import OK_STATUS
from dispenses.services.oracle import (
    add_month,
    fetch_webservice_abnormal,
    fetch_webservice_daily,
    fetch_webservice_status,
    fill_missing_days,
)


class DailyCount(TypedDict):
    day: date
    count: int


class StatusCount(TypedDict):
    status: str
    count: int
    pct: float


class AbnormalRecord(TypedDict, total=False):
    id_dispense: object
    id_demandeur: object
    nom: object
    prenom: object
    niss: object
    decisionidentification: object
    decisionsituationnbr: object
    detail_statut_reponse: object
    dt_creation: object
    user_creation: object
    dt_modification: object
    user_modification: object


class MonitoringPayload(TypedDict):
    ok_status: str
    daily_counts: list[DailyCount]
    status_counts: list[StatusCount]
    abnormal_records: list[AbnormalRecord]
    total_status: int
    daily_counts_json: str
    prev_year: int
    prev_month: int
    next_year: int
    next_month: int
    cache_ttl_seconds: int
    refresh_used: bool


class MonitoringCachePayload(TypedDict):
    daily_counts: list[DailyCount]
    status_counts: list[dict[str, object]]
    abnormal_records: list[AbnormalRecord]


class MonitoringQueryParams(TypedDict):
    date_start: date
    date_end: date


def monitoring_cache_key(user_id: int, year: int, month: int) -> str:
    return f"dispenses:monitoring:{user_id}:{year:04d}:{month:02d}"


def invalidate_monitoring_cache(user_id: int, year: int, month: int) -> None:
    cache.delete(monitoring_cache_key(user_id, year, month))


def build_monitoring_payload(
    request: WSGIRequest,
    *,
    year: int,
    month: int,
    date_start: date,
    date_end_excl: date,
    refresh: bool = False,
) -> MonitoringPayload:
    params_common: MonitoringQueryParams = {"date_start": date_start, "date_end": date_end_excl}
    cache_key = monitoring_cache_key(request.user.id, year, month)

    if refresh:
        cache.delete(cache_key)

    payload = cast(MonitoringCachePayload | None, cache.get(cache_key))
    if payload is None:
        fresh_payload: MonitoringCachePayload = {
            "daily_counts": fill_missing_days(
                fetch_webservice_daily(request, params_common),
                date_start,
                date_end_excl,
            ),
            "status_counts": fetch_webservice_status(request, params_common),
            "abnormal_records": cast(
                list[AbnormalRecord],
                fetch_webservice_abnormal(request, {**params_common, "ok_status": OK_STATUS}),
            ),
        }
        cache.set(cache_key, fresh_payload, settings.MONITORING_CACHE_TTL_SECONDS)
        payload = fresh_payload
    payload = cast(MonitoringCachePayload, payload)

    total_status = sum(int(cast(int | str, item["count"])) for item in payload["status_counts"])
    status_counts: list[StatusCount] = [
        StatusCount(
            status=str(item["status"]),
            count=int(cast(int | str, item["count"])),
            pct=0.0,
        )
        for item in payload["status_counts"]
    ]
    for item in status_counts:
        item["pct"] = (item["count"] / total_status * 100.0) if total_status > 0 else 0.0

    prev_year, prev_month = add_month(year, month, -1)
    next_year, next_month = add_month(year, month, 1)

    return {
        "ok_status": OK_STATUS,
        "daily_counts": payload["daily_counts"],
        "status_counts": status_counts,
        "abnormal_records": payload["abnormal_records"],
        "total_status": total_status,
        "daily_counts_json": json.dumps(
            [{"day": item["day"].strftime("%Y-%m-%d"), "count": item["count"]} for item in payload["daily_counts"]]
        ),
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "cache_ttl_seconds": settings.MONITORING_CACHE_TTL_SECONDS,
        "refresh_used": refresh,
    }
