from __future__ import annotations

from typing import Any, Mapping, cast

from django.core.handlers.wsgi import WSGIRequest

from dispenses.services.oracle_gateway import FetchMode, execute_query
from dispenses.services.oracle_schema import select_columns_sql


def fetch_webservice_daily(request: WSGIRequest, params_common: Mapping[str, object]) -> list[dict[str, Any]]:
    sql = """
        SELECT TRUNC(dt_creation) AS day, COUNT(*) AS cnt
        FROM ib_unempl_decision_dispenses
        WHERE dt_creation >= :date_start
          AND dt_creation < :date_end
        GROUP BY TRUNC(dt_creation)
        ORDER BY day
    """
    response = execute_query(request, sql, params_common, FetchMode.ALL)
    return [{"day": row[0], "count": row[1]} for row in response]


def fetch_webservice_status(request: WSGIRequest, params_common: Mapping[str, object]) -> list[dict[str, Any]]:
    sql = """
        SELECT NVL(detail_statut_reponse, '(NULL)') AS statut, COUNT(*) AS cnt
        FROM ib_unempl_decision_dispenses
        WHERE dt_creation >= :date_start
          AND dt_creation < :date_end
        GROUP BY NVL(detail_statut_reponse, '(NULL)')
        ORDER BY cnt DESC
    """
    response = execute_query(request, sql, params_common, FetchMode.ALL)
    return [{"status": row[0], "count": row[1]} for row in response]


def fetch_webservice_abnormal(request: WSGIRequest, params_common: Mapping[str, object]) -> list[dict[str, Any]]:
    sql = f"""
        SELECT {select_columns_sql(request, "IB_UNEMPL_DECISION_DISPENSES")}
        FROM ib_unempl_decision_dispenses
        WHERE dt_creation >= :date_start
          AND dt_creation < :date_end
          AND (detail_statut_reponse IS NULL OR detail_statut_reponse <> :ok_status)
        ORDER BY dt_creation DESC
    """
    return cast(list[dict[str, Any]], execute_query(request, sql, params_common, FetchMode.DICT))
