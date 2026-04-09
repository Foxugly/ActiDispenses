from __future__ import annotations

import logging
from enum import IntEnum
from typing import Any, Mapping, Protocol

import oracledb
from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest

from oracle_accounts.services import get_current_oracle_credential

logger = logging.getLogger(__name__)

_ORACLE_INIT_DONE = False


class OracleCredentialLike(Protocol):
    username: str

    def get_password(self) -> str: ...

    def makedsn(self) -> str: ...


class OracleServiceError(Exception):
    status_code = 500
    title = "Erreur Oracle"
    user_message = "Une erreur Oracle est survenue."

    def __init__(self, user_message: str | None = None):
        super().__init__(user_message or self.user_message)
        self.user_message = user_message or self.user_message


class DatabaseUnavailableError(OracleServiceError):
    status_code = 503
    title = "Service indisponible"
    user_message = "La base de donnees Oracle est momentanement indisponible."


class OracleCredentialError(OracleServiceError):
    status_code = 502
    title = "Identifiants Oracle invalides"
    user_message = "Les identifiants Oracle configures sont invalides ou expires."


class OracleClientConfigurationError(OracleServiceError):
    status_code = 500
    title = "Client Oracle introuvable"
    user_message = "Le client Oracle local est absent ou mal configure."


class OracleQueryError(OracleServiceError):
    status_code = 500
    title = "Erreur de requete Oracle"
    user_message = "La requete Oracle a echoue."


class FetchMode(IntEnum):
    DICT = 0
    ALL = 1
    ONE = 2


def _safe_params(params: Mapping[str, object]) -> dict[str, object]:
    hidden = {"niss", "no_registre_national"}
    return {key: ("***" if key.lower() in hidden else value) for key, value in params.items()}


def map_oracle_error(exc: oracledb.Error) -> OracleServiceError:
    message = str(exc)
    error_obj = exc.args[0] if exc.args else None
    code = getattr(error_obj, "code", None)

    if "DPI-1047" in message:
        return OracleClientConfigurationError("Le client Oracle n'est pas disponible. Verifiez ORACLE_CLIENT_LIB_DIR.")
    if "DPY-3015" in message:
        return OracleClientConfigurationError(
            "Cette base Oracle necessite le mode thick. Verifiez ORACLE_CLIENT_LIB_DIR."
        )
    if code in {1017, 28000, 28001, 28002, 28009, 28040}:
        return OracleCredentialError()
    if code in {12170, 12514, 12541, 12543, 12545, 12547}:
        return DatabaseUnavailableError()
    return OracleQueryError()


def init_oracle_client() -> None:
    global _ORACLE_INIT_DONE
    if _ORACLE_INIT_DONE:
        return

    lib_dir = settings.ORACLE_CLIENT_LIB_DIR or None
    try:
        if lib_dir:
            logger.info("Initializing Oracle client in thick mode with lib_dir=%s", lib_dir)
            oracledb.init_oracle_client(lib_dir=lib_dir)
        _ORACLE_INIT_DONE = True
    except oracledb.Error as exc:
        mapped = map_oracle_error(exc)
        logger.exception("Oracle client initialization failed")
        raise mapped from exc


def connect_with_credential(
    credential: OracleCredentialLike,
    *,
    call_timeout_ms: int | None = None,
):
    init_oracle_client()
    connection = oracledb.connect(
        user=credential.username,
        password=credential.get_password(),
        dsn=credential.makedsn(),
    )
    connection.call_timeout = call_timeout_ms or settings.ORACLE_CALL_TIMEOUT_MS
    return connection


def fetchall_dict(cursor, *, max_rows: int | None = None) -> list[dict[str, Any]]:
    columns = [column[0].lower() for column in cursor.description]
    rows = cursor.fetchmany(max_rows) if max_rows else cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


class OracleGateway:
    def __init__(self, request: WSGIRequest, *, call_timeout_ms: int | None = None):
        self.request = request
        self.call_timeout_ms = call_timeout_ms or settings.ORACLE_CALL_TIMEOUT_MS

    def execute(
        self,
        sql: str,
        params: Mapping[str, object] | None = None,
        fetch: int = FetchMode.DICT,
        *,
        max_rows: int | None = None,
        read_only_transaction: bool = False,
    ):
        logger.debug("SQL:\n%s", sql)
        if params:
            logger.debug("Params: %s", _safe_params(params))
        try:
            with self.connect() as connection:
                with connection.cursor() as cursor:
                    if read_only_transaction:
                        cursor.execute("SET TRANSACTION READ ONLY")
                    cursor.execute(sql, params or {})
                    match fetch:
                        case FetchMode.DICT:
                            return fetchall_dict(cursor, max_rows=max_rows)
                        case FetchMode.ALL:
                            return cursor.fetchmany(max_rows) if max_rows else cursor.fetchall()
                        case FetchMode.ONE:
                            return cursor.fetchone(), [column[0].upper() for column in cursor.description]
                        case _:
                            raise ValueError(f"Unknown fetch mode: {fetch}")
        except oracledb.Error as exc:
            mapped = map_oracle_error(exc)
            logger.exception("Oracle error mapped to %s", mapped.__class__.__name__)
            raise mapped from exc

    def connect(self):
        credential = get_current_oracle_credential(self.request)
        return connect_with_credential(
            credential,
            call_timeout_ms=self.call_timeout_ms,
        )


def execute_query(
    request: WSGIRequest,
    sql: str,
    params: Mapping[str, object] | None = None,
    fetch: int = FetchMode.DICT,
    *,
    max_rows: int | None = None,
    call_timeout_ms: int | None = None,
    read_only_transaction: bool = False,
):
    return OracleGateway(request, call_timeout_ms=call_timeout_ms).execute(
        sql,
        params,
        fetch,
        max_rows=max_rows,
        read_only_transaction=read_only_transaction,
    )


def check_oracle_connection(request: WSGIRequest) -> tuple[bool, str]:
    try:
        result, _columns = execute_query(request, "SELECT 1 FROM dual", fetch=FetchMode.ONE, max_rows=1)
    except OracleServiceError as exc:
        return False, exc.user_message
    return bool(result), "Connexion Oracle OK."
