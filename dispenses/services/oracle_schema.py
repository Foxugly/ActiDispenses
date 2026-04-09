from __future__ import annotations

from typing import cast

from django.conf import settings
from django.core.cache import cache
from django.core.handlers.wsgi import WSGIRequest

from dispenses.services.oracle_gateway import OracleGateway, OracleQueryError
from oracle_accounts.services import get_current_oracle_credential

TABLE_COLUMNS_CACHE_PREFIX = "oracle:table_columns"
TABLE_COLUMNS_CACHE_TTL = 3600


def _table_columns_cache_key(request: WSGIRequest, table_name: str) -> str:
    credential = get_current_oracle_credential(request)
    return f"{TABLE_COLUMNS_CACHE_PREFIX}:{credential.username}@{credential.makedsn()}:{table_name.upper()}"


def get_table_columns(request: WSGIRequest, table_name: str) -> list[str]:
    cache_key = _table_columns_cache_key(request, table_name)
    cached_columns = cache.get(cache_key)
    if cached_columns:
        return cast(list[str], cached_columns)

    gateway = OracleGateway(request, call_timeout_ms=settings.ORACLE_CALL_TIMEOUT_MS)
    with gateway.connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {table_name} WHERE 1 = 0")
            columns = [column[0] for column in cursor.description or []]

    if not columns:
        raise OracleQueryError(f"Aucune colonne n'a pu etre resolue pour la table {table_name}.")

    cache.set(cache_key, columns, TABLE_COLUMNS_CACHE_TTL)
    return columns


def select_columns_sql(
    request: WSGIRequest,
    table_name: str,
    *,
    alias: str | None = None,
    columns: list[str] | None = None,
) -> str:
    selected_columns = columns or get_table_columns(request, table_name)
    prefix = f"{alias}." if alias else ""
    return ", ".join(f"{prefix}{column}" for column in selected_columns)
