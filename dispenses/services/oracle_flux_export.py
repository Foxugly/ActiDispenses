from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

FLUX_TABLE_PATTERN = re.compile(r"^IB_FLUX_[A-Z0-9_]+$")
SHEET_NAME_LIMIT = 31
SUMMARY_SHEET_NAME = "global"


@dataclass(frozen=True)
class MonthlyCount:
    annee_mois: str
    nb_records: int


@dataclass(frozen=True)
class TableMonthlyCounts:
    table_name: str
    rows: list[MonthlyCount]


def normalize_output_path(output: str) -> Path:
    path = Path(output)
    if path.suffix.lower() != ".xlsx":
        path = path.with_suffix(".xlsx")
    return path


def list_flux_tables(connection) -> list[str]:
    sql = """
        SELECT DISTINCT table_name
        FROM all_tables
        WHERE table_name LIKE 'IB_FLUX_%'
        ORDER BY table_name ASC
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        tables = [row[0] for row in cursor.fetchall()]
    return [table for table in tables if is_allowed_flux_table_name(table)]


def fetch_monthly_counts(connection, table_name: str) -> list[MonthlyCount]:
    if not is_allowed_flux_table_name(table_name):
        raise ValueError(f"Nom de table Oracle invalide: {table_name}")

    sql = f"""
        SELECT TO_CHAR(dt_creation, 'YYYY-MM') AS annee_mois, COUNT(*) AS nb_records
        FROM {table_name}
        GROUP BY TO_CHAR(dt_creation, 'YYYY-MM')
        ORDER BY annee_mois
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return [MonthlyCount(annee_mois=row[0], nb_records=int(row[1])) for row in cursor.fetchall()]


def build_flux_workbook(output_path: Path, tables: list[TableMonthlyCounts]) -> None:
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = SUMMARY_SHEET_NAME
    summary_sheet.append(["table_name", "total_records"])
    _apply_header_style(summary_sheet, 1)

    used_sheet_names = {SUMMARY_SHEET_NAME}
    for index, table_data in enumerate(tables, start=2):
        sheet_name = build_sheet_name(table_data.table_name, used_sheet_names)
        used_sheet_names.add(sheet_name)
        table_sheet = workbook.create_sheet(title=sheet_name)
        _fill_table_sheet(table_sheet, table_data)
        total_row = len(table_data.rows) + 2

        summary_sheet.cell(row=index, column=1, value=table_data.table_name)
        total_cell = summary_sheet.cell(row=index, column=2, value=f"='{sheet_name}'!B{total_row}")
        total_cell.hyperlink = f"#'{sheet_name}'!B{total_row}"
        total_cell.style = "Hyperlink"

    _autosize(summary_sheet, ("A", "B"))
    workbook.save(output_path)


def build_sheet_name(table_name: str, used_names: set[str]) -> str:
    base_name = table_name[:SHEET_NAME_LIMIT]
    candidate = base_name
    suffix = 1
    while candidate in used_names:
        suffix_text = f"_{suffix}"
        candidate = f"{base_name[:SHEET_NAME_LIMIT - len(suffix_text)]}{suffix_text}"
        suffix += 1
    return candidate


def is_allowed_flux_table_name(table_name: str) -> bool:
    return bool(FLUX_TABLE_PATTERN.fullmatch(table_name))


def _fill_table_sheet(sheet, table_data: TableMonthlyCounts) -> None:
    sheet.append(["annee_mois", "nb_records"])
    _apply_header_style(sheet, 1)

    for row in table_data.rows:
        sheet.append([row.annee_mois, row.nb_records])

    total_row = len(table_data.rows) + 2
    if table_data.rows:
        total_formula = f"=SUM(B2:B{total_row - 1})"
    else:
        total_formula = "=0"
    sheet.cell(row=total_row, column=1, value="TOTAL")
    total_cell = sheet.cell(row=total_row, column=2, value=total_formula)
    total_cell.font = Font(bold=True)
    sheet.cell(row=total_row, column=1).font = Font(bold=True)
    sheet.freeze_panes = "A2"
    _autosize(sheet, ("A", "B"))


def _apply_header_style(sheet, row_number: int) -> None:
    for cell in sheet[row_number]:
        cell.font = Font(bold=True)


def _autosize(sheet, columns: tuple[str, ...]) -> None:
    for column in columns:
        max_length = 0
        for cell in sheet[column]:
            value = "" if cell.value is None else str(cell.value)
            max_length = max(max_length, len(value))
        sheet.column_dimensions[column].width = max(max_length + 2, 14)
