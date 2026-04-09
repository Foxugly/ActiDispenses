from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.core.handlers.wsgi import WSGIRequest

from dispenses.services.oracle_people import (
    PersonInfo,
    fetch_dispenses,
    fetch_webservice_logs,
    identify_person,
    resolve_person,
)


@dataclass(frozen=True)
class DispenseSearchCriteria:
    search_key: str
    search_value: str


@dataclass(frozen=True)
class DispenseSearchResult:
    person: PersonInfo
    dispenses: list[dict[str, Any]]
    ws_logs: list[dict[str, Any]]


def run_dispense_search(request: WSGIRequest, criteria: DispenseSearchCriteria) -> DispenseSearchResult | None:
    resolved_key, resolved_value = criteria.search_key, criteria.search_value
    if resolved_key in {"id_dispense", "no_dispense"}:
        resolved_key, resolved_value = identify_person(request, resolved_key, resolved_value)

    person = resolve_person(request, resolved_key, resolved_value)
    if not person:
        return None

    return DispenseSearchResult(
        person=person,
        dispenses=fetch_dispenses(request, person.id_demandeur),
        ws_logs=fetch_webservice_logs(request, person.id_demandeur),
    )
