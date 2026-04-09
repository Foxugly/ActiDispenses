from __future__ import annotations

from dispenses.services.oracle_cases import (
    fetch_short_webservice_internal_error_without_next,
    fetch_short_webservice_logs_undo_without_next,
    fetch_webservice_internal_error_without_next,
    fetch_webservice_logs_undo_without_next,
    fetch_webservice_ssin_not_integrated_without_next,
    fetch_webservice_unknown_code_without_next,
)
from dispenses.services.oracle_gateway import (
    DatabaseUnavailableError,
    FetchMode,
    OracleClientConfigurationError,
    OracleCredentialError,
    OracleGateway,
    OracleQueryError,
    OracleServiceError,
    check_oracle_connection,
    connect_with_credential,
    execute_query,
)
from dispenses.services.oracle_gateway import (
    init_oracle_client as _init_oracle_client,
)
from dispenses.services.oracle_gateway import (
    map_oracle_error as _map_oracle_error,
)
from dispenses.services.oracle_monitoring_queries import (
    fetch_webservice_abnormal,
    fetch_webservice_daily,
    fetch_webservice_status,
)
from dispenses.services.oracle_people import (
    PersonInfo,
    fetch_dispense_rows_by_pairs,
    fetch_dispenses,
    fetch_dispenses_from_id_dispense,
    fetch_query,
    fetch_webservice_logs,
    identify_person,
    resolve_person,
)
from dispenses.services.oracle_schema import get_table_columns, select_columns_sql
from dispenses.services.oracle_sql import build_oracle_insert_sql_literal, build_oracle_update_sql_literal
from dispenses.services.oracle_utils import (
    add_month,
    default_visible_map,
    expect_one,
    fill_missing_days,
    infer_columns,
    parse_int,
    reorder_columns,
)

__all__ = [
    "DatabaseUnavailableError",
    "FetchMode",
    "OracleClientConfigurationError",
    "OracleCredentialError",
    "OracleGateway",
    "OracleQueryError",
    "OracleServiceError",
    "PersonInfo",
    "_init_oracle_client",
    "_map_oracle_error",
    "add_month",
    "build_oracle_insert_sql_literal",
    "build_oracle_update_sql_literal",
    "check_oracle_connection",
    "connect_with_credential",
    "default_visible_map",
    "execute_query",
    "expect_one",
    "fetch_dispenses",
    "fetch_dispense_rows_by_pairs",
    "fetch_dispenses_from_id_dispense",
    "fetch_query",
    "fetch_short_webservice_internal_error_without_next",
    "fetch_short_webservice_logs_undo_without_next",
    "fetch_webservice_abnormal",
    "fetch_webservice_daily",
    "fetch_webservice_internal_error_without_next",
    "fetch_webservice_logs",
    "fetch_webservice_logs_undo_without_next",
    "fetch_webservice_ssin_not_integrated_without_next",
    "fetch_webservice_status",
    "fetch_webservice_unknown_code_without_next",
    "fill_missing_days",
    "get_table_columns",
    "identify_person",
    "infer_columns",
    "parse_int",
    "reorder_columns",
    "resolve_person",
    "select_columns_sql",
]
