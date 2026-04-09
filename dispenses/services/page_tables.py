from __future__ import annotations

import json
from typing import TypedDict

from dispenses.services.oracle import default_visible_map, infer_columns, reorder_columns


class DataTableConfig(TypedDict):
    tableId: str
    filename: str
    columns: list[str]
    defaultVisible: list[bool]
    toggleButtonId: str
    panelId: str
    checklistId: str
    resetButtonId: str
    closeButtonId: str


class TablePayload(TypedDict):
    rows: list[dict[str, object]]
    columns: list[str]
    columns_json: str
    default_visible_json: str
    table_config: DataTableConfig


def build_table_payload(
    *,
    rows: list[dict[str, object]],
    wanted_columns: list[str],
    table_id: str,
    filename: str,
    toggle_button_id: str,
    panel_id: str,
    checklist_id: str,
    reset_button_id: str,
    close_button_id: str,
) -> TablePayload:
    columns = reorder_columns(infer_columns(rows), wanted_columns)
    default_visible = default_visible_map(columns, wanted_columns)
    table_config: DataTableConfig = {
        "tableId": table_id,
        "filename": filename,
        "columns": columns,
        "defaultVisible": default_visible,
        "toggleButtonId": toggle_button_id,
        "panelId": panel_id,
        "checklistId": checklist_id,
        "resetButtonId": reset_button_id,
        "closeButtonId": close_button_id,
    }
    return {
        "rows": rows,
        "columns": columns,
        "columns_json": json.dumps(columns),
        "default_visible_json": json.dumps(default_visible),
        "table_config": table_config,
    }
