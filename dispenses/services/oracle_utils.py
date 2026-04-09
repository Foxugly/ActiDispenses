from __future__ import annotations

from datetime import date, datetime, timedelta


def infer_columns(rows: list[dict]) -> list[str]:
    return list(rows[0].keys()) if rows else []


def reorder_columns(columns: list[str], wanted_order: list[str]) -> list[str]:
    positions = {name.lower(): index for index, name in enumerate(wanted_order)}
    return sorted(
        columns,
        key=lambda column: (0, positions[column.lower()]) if column.lower() in positions else (1, column.lower()),
    )


def default_visible_map(columns: list[str], wanted: list[str]) -> list[bool]:
    wanted_set = {column.lower() for column in wanted}
    return [column.lower() in wanted_set for column in columns]


def parse_int(value: str | None, default: int, min_v: int, max_v: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return max(min_v, min(max_v, parsed))


def to_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return value


def fill_missing_days(daily_counts, date_start, date_end_excl):
    by_day = {to_date(item["day"]): item["count"] for item in daily_counts}
    output = []
    current = date_start
    while current < date_end_excl:
        output.append({"day": current, "count": by_day.get(current, 0)})
        current += timedelta(days=1)
    return output


def add_month(year: int, month: int, delta: int) -> tuple[int, int]:
    shifted_month = month + delta
    shifted_year = year + (shifted_month - 1) // 12
    shifted_month = (shifted_month - 1) % 12 + 1
    return shifted_year, shifted_month


def expect_one(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    if len(rows) != 1:
        raise ValueError(f"Attendu 1 enregistrement, recu {len(rows)}.")
    return rows[0]
