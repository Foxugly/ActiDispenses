from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, cast

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest

from dispenses.services.oracle_gateway import FetchMode, execute_query
from dispenses.services.oracle_schema import select_columns_sql

DEMANDEURS_PERSON_COLUMNS = [
    "ID_DEMANDEUR",
    "NOM",
    "PRENOM",
    "NO_REGISTRE_NATIONAL",
    "NO_IBIS",
]


@dataclass(frozen=True)
class PersonInfo:
    id_demandeur: str
    nom: str
    prenom: str
    niss: str
    no_ibis: str


def identify_person(user: WSGIRequest, search_key: str, search_value: str) -> tuple[str, str]:
    sql_map = {
        "id_dispense": """
            SELECT id_demandeur
            FROM ib_dispenses
            WHERE id_dispense = :v
        """,
        "no_dispense": """
            SELECT id_demandeur
            FROM ib_dispenses
            WHERE no_dispense = :v
        """,
    }
    sql = sql_map.get(search_key)
    if not sql:
        return search_key, search_value
    row, columns = execute_query(user, sql, {"v": search_value}, FetchMode.ONE)
    if not row:
        return search_key, search_value
    return "id_demandeur", str(row[columns.index("ID_DEMANDEUR")])


def resolve_person(user: WSGIRequest, search_key: str, search_value: str) -> PersonInfo | None:
    sql_map = {
        "no_ibis": f"""
            SELECT {", ".join(DEMANDEURS_PERSON_COLUMNS)}
            FROM IB_DEMANDEURS
            WHERE no_ibis = :v
        """,
        "id_demandeur": f"""
            SELECT {", ".join(DEMANDEURS_PERSON_COLUMNS)}
            FROM IB_DEMANDEURS
            WHERE id_demandeur = :v
        """,
        "niss": f"""
            SELECT {", ".join(DEMANDEURS_PERSON_COLUMNS)}
            FROM IB_DEMANDEURS
            WHERE NO_REGISTRE_NATIONAL = :v
        """,
    }
    row, columns = execute_query(user, sql_map[search_key], {"v": search_value}, FetchMode.ONE)
    if not row:
        return None
    return PersonInfo(
        id_demandeur=str(row[columns.index("ID_DEMANDEUR")]),
        nom=str(row[columns.index("NOM")]),
        prenom=str(row[columns.index("PRENOM")]),
        niss=str(row[columns.index("NO_REGISTRE_NATIONAL")]),
        no_ibis=str(row[columns.index("NO_IBIS")]),
    )


def fetch_dispenses(request: WSGIRequest, id_demandeur: str) -> list[dict[str, Any]]:
    sql = f"""
        SELECT {select_columns_sql(request, "IB_DISPENSES")}
        FROM ib_dispenses
        WHERE id_demandeur = :id_demandeur
        ORDER BY dt_creation DESC
    """
    return cast(list[dict[str, Any]], execute_query(request, sql, {"id_demandeur": id_demandeur}, FetchMode.DICT))


def fetch_webservice_logs(request: WSGIRequest, id_demandeur: str) -> list[dict[str, Any]]:
    sql = f"""
        SELECT {select_columns_sql(request, "IB_UNEMPL_DECISION_DISPENSES")}
        FROM ib_unempl_decision_dispenses
        WHERE id_demandeur = :id_demandeur
        ORDER BY dt_creation DESC
    """
    return cast(list[dict[str, Any]], execute_query(request, sql, {"id_demandeur": id_demandeur}, FetchMode.DICT))


def fetch_dispenses_from_id_dispense(request: WSGIRequest, id_dispense: str, avenant: str) -> list[dict[str, Any]]:
    sql = f"""
        SELECT {select_columns_sql(request, "IB_DISPENSES")}
        FROM ib_dispenses
        WHERE id_dispense = :id_dispense
          AND no_avenant = :avenant
        ORDER BY dt_creation DESC
    """
    return cast(
        list[dict[str, Any]],
        execute_query(request, sql, {"id_dispense": id_dispense, "avenant": avenant}, FetchMode.DICT),
    )


def fetch_dispense_rows_by_pairs(
    request: WSGIRequest,
    pairs: Iterable[tuple[str, str]],
) -> dict[tuple[str, str], dict[str, Any]]:
    unique_pairs = list(dict.fromkeys(pairs))
    if not unique_pairs:
        return {}

    where_clauses: list[str] = []
    params: dict[str, object] = {}
    for index, (id_dispense, avenant) in enumerate(unique_pairs):
        id_key = f"id_dispense_{index}"
        avenant_key = f"avenant_{index}"
        where_clauses.append(f"(id_dispense = :{id_key} AND no_avenant = :{avenant_key})")
        params[id_key] = id_dispense
        params[avenant_key] = avenant

    sql = f"""
        SELECT {select_columns_sql(request, "IB_DISPENSES")}
        FROM ib_dispenses
        WHERE {" OR ".join(where_clauses)}
        ORDER BY dt_creation DESC
    """
    rows = cast(list[dict[str, Any]], execute_query(request, sql, params, FetchMode.DICT))
    rows_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        pair = (str(row["id_dispense"]), str(row["no_avenant"]))
        rows_by_pair.setdefault(pair, row)
    return rows_by_pair


def fetch_query(request: WSGIRequest, query: str) -> list[dict[str, Any]]:
    return cast(
        list[dict[str, Any]],
        execute_query(
            request,
            query,
            params=None,
            fetch=FetchMode.DICT,
            max_rows=settings.QUERY_PREVIEW_MAX_ROWS,
            call_timeout_ms=settings.ORACLE_CALL_TIMEOUT_MS,
            read_only_transaction=True,
        ),
    )
