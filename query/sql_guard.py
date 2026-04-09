from __future__ import annotations

import re

from django.conf import settings
from django.core.exceptions import ValidationError

IDENTIFIER_PATTERN = r"[A-Za-z_][\w$#]*(?:\.[A-Za-z_][\w$#]*)?"
SOURCE_PATTERN = re.compile(rf"\b(?:from|join)\s+({IDENTIFIER_PATTERN})", re.IGNORECASE)
WITH_CTE_PATTERN = re.compile(r"\bwith\s+([A-Za-z_][\w$#]*)\s+as\s*\(", re.IGNORECASE)
ADDITIONAL_CTE_PATTERN = re.compile(r",\s*([A-Za-z_][\w$#]*)\s+as\s*\(", re.IGNORECASE)


def _configured_allowed_tables() -> set[str]:
    return {table.upper() for table in settings.QUERY_ALLOWED_TABLES}


def _configured_allowed_schemas() -> set[str]:
    return {schema.upper() for schema in settings.QUERY_ALLOWED_SCHEMAS}


def _extract_cte_names(query: str) -> set[str]:
    return {
        match.group(1).upper() for match in [*WITH_CTE_PATTERN.finditer(query), *ADDITIONAL_CTE_PATTERN.finditer(query)]
    }


def _normalize_source(identifier: str) -> tuple[str | None, str]:
    parts = [part.upper() for part in identifier.split(".") if part]
    if len(parts) == 1:
        return None, parts[0]
    return parts[-2], parts[-1]


def extract_query_sources(query: str) -> list[tuple[str | None, str]]:
    cte_names = _extract_cte_names(query)
    sources: list[tuple[str | None, str]] = []
    for match in SOURCE_PATTERN.finditer(query):
        schema, table = _normalize_source(match.group(1))
        if table in cte_names:
            continue
        sources.append((schema, table))
    return sources


def validate_allowed_query_sources(query: str) -> None:
    allowed_tables = _configured_allowed_tables()
    allowed_schemas = _configured_allowed_schemas()
    disallowed_sources: list[str] = []

    for schema, table in extract_query_sources(query):
        if allowed_tables and table not in allowed_tables:
            disallowed_sources.append(f"{schema}.{table}" if schema else table)
            continue
        if schema and allowed_schemas and schema not in allowed_schemas:
            disallowed_sources.append(f"{schema}.{table}")

    if disallowed_sources:
        allowed_tables_display = ", ".join(sorted(allowed_tables)) or "aucune restriction"
        raise ValidationError(
            f"Sources SQL non autorisees: {', '.join(disallowed_sources)}. Tables autorisees: {allowed_tables_display}."
        )
