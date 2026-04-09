from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any


def oracle_literal(value: Any, engine: str = "oracle") -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, datetime):
        if engine == "oracle":
            return "TO_TIMESTAMP('{:%Y-%m-%d %H:%M:%S}','YYYY-MM-DD HH24:MI:SS')".format(value)
        return f"'{value:%Y-%m-%d %H:%M:%S}'"
    if isinstance(value, date):
        return "TO_DATE('{:%Y-%m-%d}', 'YYYY-MM-DD')".format(value)

    text = re.sub(r"\s+", " ", str(value)).strip().replace("'", "''")
    return f"'{text}'"


def build_oracle_update_sql_literal(
    table: str,
    row: dict[str, Any],
    *,
    key_fields: set[str],
    increment_fields: set[str] | None = None,
    set_fields: dict[str, Any] | None = None,
    nullify_fields: set[str] | None = None,
) -> str:
    key_fields = {column.lower() for column in key_fields}
    increment_fields = {column.lower() for column in (increment_fields or set())}
    nullify_fields = {column.lower() for column in (nullify_fields or set())}
    set_fields_lc = {column.lower(): value for column, value in (set_fields or {}).items()}

    set_clauses: list[str] = []
    where_clauses: list[str] = []

    for key in key_fields:
        if key not in row:
            raise ValueError(f"Cle {key} absente de la ligne")
        where_clauses.append(f"{key} = {oracle_literal(row[key])}")

    for column, value in set_fields_lc.items():
        set_clauses.append(f"{column} = {oracle_literal(value)}")

    for column in nullify_fields:
        set_clauses.append(f"{column} = NULL")

    for column in increment_fields:
        if column not in row:
            raise ValueError(f"Impossible d'incrementer {column}: absent de la ligne")
        value = row[column]
        if value is None:
            raise ValueError(f"Impossible d'incrementer {column}: valeur None")
        set_clauses.append(f"{column} = {int(value) + 1}")

    if not set_clauses:
        raise ValueError("Aucun champ a mettre a jour")

    return f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)};"


def build_oracle_insert_sql_literal(
    table: str,
    row: dict[str, Any],
    *,
    exclude: set[str] | None = None,
    increment_fields: set[str] | None = None,
    set_fields: dict[str, Any] | None = None,
    nullify_fields: set[str] | None = None,
    pk_expr: dict[str, str] | None = None,
) -> str:
    exclude = {column.lower() for column in (exclude or set())}
    increment_fields = {column.lower() for column in (increment_fields or set())}
    nullify_fields = {column.lower() for column in (nullify_fields or set())}
    set_fields_lc = {column.lower(): value for column, value in (set_fields or {}).items()}
    pk_expr = {column.lower(): value for column, value in (pk_expr or {}).items()}

    columns: list[str] = []
    values: list[str] = []

    for column, expr in pk_expr.items():
        columns.append(column)
        values.append(expr)

    for column, value in row.items():
        column_lc = column.lower()
        if column_lc in exclude or column_lc in pk_expr:
            continue

        columns.append(column_lc)

        if column_lc in nullify_fields:
            values.append("NULL")
            continue
        if column_lc in set_fields_lc:
            values.append(oracle_literal(set_fields_lc[column_lc]))
            continue
        if column_lc in increment_fields:
            if value is None:
                raise ValueError(f"Impossible d'incrementer {column_lc}: valeur None")
            values.append(str(int(value) + 1))
            continue

        values.append(oracle_literal(value))

    return f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(values)});"
