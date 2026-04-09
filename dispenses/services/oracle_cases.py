from __future__ import annotations

import logging
from typing import Any, cast

from django.core.handlers.wsgi import WSGIRequest

from dispenses.services.constants import (
    INTERNAL_ERROR_PATTERNS,
    SSIN_NOT_INTEGRATED_PATTERN,
    UNDO_ALREADY_PROCESSED_PATTERN,
    UNKNOWN_POSITIVE_EXEMPTION_PATTERN,
)
from dispenses.services.oracle_gateway import FetchMode, execute_query
from dispenses.services.oracle_schema import select_columns_sql

logger = logging.getLogger(__name__)


def fetch_webservice_internal_error_without_next(request: WSGIRequest) -> list[dict[str, Any]]:
    sql = f"""
        SELECT {select_columns_sql(request, "IB_UNEMPL_DECISION_DISPENSES", alias="indd")}
        FROM ib_unempl_decision_dispenses indd
        WHERE (
            indd.detail_statut_reponse LIKE '{INTERNAL_ERROR_PATTERNS[0]}'
            OR detail_statut_reponse LIKE '{INTERNAL_ERROR_PATTERNS[1]}'
        )
        AND NOT EXISTS (
            SELECT 1
            FROM ib_unempl_decision_dispenses indd2
            WHERE indd2.decisionidentification = indd.decisionidentification
              AND indd2.decisionsituationnbr > indd.decisionsituationnbr
        )
        ORDER BY dt_creation DESC
    """
    return cast(list[dict[str, Any]], execute_query(request, sql, {}, FetchMode.DICT))


def fetch_webservice_logs_undo_without_next(request: WSGIRequest) -> list[dict[str, Any]]:
    sql = f"""
        SELECT {select_columns_sql(request, "IB_UNEMPL_DECISION_DISPENSES", alias="indd")}
        FROM ib_unempl_decision_dispenses indd
        WHERE indd.detail_statut_reponse LIKE '{UNDO_ALREADY_PROCESSED_PATTERN}'
          AND NOT EXISTS (
              SELECT 1
              FROM ib_unempl_decision_dispenses indd2
              WHERE indd2.decisionidentification = indd.decisionidentification
                AND indd2.decisionsituationnbr > indd.decisionsituationnbr
          )
        ORDER BY dt_creation DESC
    """
    return cast(list[dict[str, Any]], execute_query(request, sql, {}, FetchMode.DICT))


def fetch_short_webservice_logs_undo_without_next(request: WSGIRequest) -> list[dict[str, Any]]:
    sql = f"""
        SELECT indd.id_dispense, indd.decisionsituationnbr
        FROM ib_unempl_decision_dispenses indd
        WHERE indd.detail_statut_reponse LIKE '{UNDO_ALREADY_PROCESSED_PATTERN}'
          AND NOT EXISTS (
              SELECT 1
              FROM ib_unempl_decision_dispenses indd2
              WHERE indd2.decisionidentification = indd.decisionidentification
                AND indd2.decisionsituationnbr > indd.decisionsituationnbr
          )
        ORDER BY dt_creation DESC
    """
    return cast(list[dict[str, Any]], execute_query(request, sql, {}, FetchMode.DICT))


def fetch_short_webservice_internal_error_without_next(request: WSGIRequest) -> list[dict[str, Any]]:
    logger.debug("Fetching short internal error webservice logs without next decision")
    sql = f"""
        SELECT indd.id_dispense, indd.decisionsituationnbr
        FROM ib_unempl_decision_dispenses indd
        WHERE (
            indd.detail_statut_reponse LIKE '{INTERNAL_ERROR_PATTERNS[0]}'
            OR detail_statut_reponse LIKE '{INTERNAL_ERROR_PATTERNS[1]}'
        )
        AND NOT EXISTS (
            SELECT 1
            FROM ib_unempl_decision_dispenses indd2
            WHERE indd2.decisionidentification = indd.decisionidentification
              AND indd2.decisionsituationnbr > indd.decisionsituationnbr
        )
        ORDER BY dt_creation DESC
    """
    return cast(list[dict[str, Any]], execute_query(request, sql, {}, FetchMode.DICT))


def fetch_webservice_ssin_not_integrated_without_next(request: WSGIRequest) -> list[dict[str, Any]]:
    sql = f"""
        SELECT {select_columns_sql(request, "IB_UNEMPL_DECISION_DISPENSES", alias="indd")}
        FROM ib_unempl_decision_dispenses indd
        WHERE indd.detail_statut_reponse LIKE '{SSIN_NOT_INTEGRATED_PATTERN}'
          AND NOT EXISTS (
              SELECT 1
              FROM ib_unempl_decision_dispenses indd2
              WHERE indd2.decisionidentification = indd.decisionidentification
                AND indd2.decisionsituationnbr > indd.decisionsituationnbr
          )
        ORDER BY dt_creation DESC
    """
    return cast(list[dict[str, Any]], execute_query(request, sql, {}, FetchMode.DICT))


def fetch_webservice_unknown_code_without_next(request: WSGIRequest) -> list[dict[str, Any]]:
    sql = f"""
        SELECT {select_columns_sql(request, "IB_UNEMPL_DECISION_DISPENSES", alias="indd")}
        FROM ib_unempl_decision_dispenses indd
        WHERE indd.detail_statut_reponse LIKE '{UNKNOWN_POSITIVE_EXEMPTION_PATTERN}'
          AND NOT EXISTS (
              SELECT 1
              FROM ib_unempl_decision_dispenses indd2
              WHERE indd2.decisionidentification = indd.decisionidentification
                AND indd2.decisionsituationnbr > indd.decisionsituationnbr
          )
        ORDER BY dt_creation DESC
    """
    return cast(list[dict[str, Any]], execute_query(request, sql, {}, FetchMode.DICT))
