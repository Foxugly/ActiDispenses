from __future__ import annotations

from dataclasses import dataclass

from django.core.cache import cache

METRIC_CACHE_PREFIX = "metrics"


def _metric_key(name: str) -> str:
    return f"{METRIC_CACHE_PREFIX}:{name}"


def increment_metric(name: str, amount: int = 1) -> int:
    key = _metric_key(name)
    if cache.add(key, amount):
        return amount
    try:
        return int(cache.incr(key, amount))
    except ValueError:
        cache.set(key, amount)
        return amount


def set_metric(name: str, value: int | float) -> int | float:
    cache.set(_metric_key(name), value)
    return value


def get_metric(name: str, default: int | float = 0) -> int | float:
    value = cache.get(_metric_key(name))
    return default if value is None else value


@dataclass(frozen=True)
class AppMetricsSnapshot:
    query_requests: int
    query_successes: int
    query_failures: int
    healthz_requests: int
    oracle_checks: int
    oracle_check_failures: int
    credential_tests: int
    credential_test_failures: int
    last_database_duration_ms: float
    last_oracle_duration_ms: float


def get_app_metrics_snapshot() -> AppMetricsSnapshot:
    return AppMetricsSnapshot(
        query_requests=int(get_metric("query.requests")),
        query_successes=int(get_metric("query.success")),
        query_failures=int(get_metric("query.failure")),
        healthz_requests=int(get_metric("healthz.requests")),
        oracle_checks=int(get_metric("healthz.oracle.requests")),
        oracle_check_failures=int(get_metric("healthz.oracle.failure")),
        credential_tests=int(get_metric("oracle.credential_test.requests")),
        credential_test_failures=int(get_metric("oracle.credential_test.failure")),
        last_database_duration_ms=float(get_metric("healthz.last_database_duration_ms", 0.0)),
        last_oracle_duration_ms=float(get_metric("healthz.last_oracle_duration_ms", 0.0)),
    )
