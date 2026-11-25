from __future__ import annotations

import os

import oracledb
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from dispenses.services.oracle_flux_export import (
    TableMonthlyCounts,
    build_flux_workbook,
    fetch_monthly_counts,
    list_flux_tables,
    normalize_output_path,
)
from dispenses.services.oracle_gateway import connect_with_credential, init_oracle_client
from oracle_accounts.models import OracleCredential


class Command(BaseCommand):
    help = "Exporte les volumes mensuels des tables IB_FLUX_* vers un fichier Excel."

    def add_arguments(self, parser):
        parser.add_argument("--credential-id", type=int, help="Identifiant OracleCredential a utiliser.")
        parser.add_argument("--host", help="Hote Oracle. Fallback: ORACLE_EXPORT_HOST ou ORACLE_TEST_HOST.")
        parser.add_argument("--port", type=int, help="Port Oracle. Fallback: ORACLE_EXPORT_PORT ou ORACLE_TEST_PORT.")
        parser.add_argument(
            "--service-name",
            help="Service name Oracle. Fallback: ORACLE_EXPORT_SERVICE_NAME ou ORACLE_TEST_SERVICE_NAME.",
        )
        parser.add_argument(
            "--username",
            help="Utilisateur Oracle. Fallback: ORACLE_EXPORT_USERNAME ou ORACLE_TEST_USERNAME.",
        )
        parser.add_argument(
            "--password",
            help="Mot de passe Oracle. Fallback: ORACLE_EXPORT_PASSWORD ou ORACLE_TEST_PASSWORD.",
        )
        parser.add_argument(
            "--output",
            default="ib_flux_counts.xlsx",
            help="Chemin du fichier Excel de sortie. Le format produit est .xlsx.",
        )

    def handle(self, *args, **options):
        output_path = normalize_output_path(options["output"])

        if output_path.suffix.lower() != ".xlsx":
            raise CommandError("Le fichier de sortie doit etre au format .xlsx.")

        self._init_oracle_client()
        credential = self._resolve_credential(options)
        connection_label = f"{credential.username}@{credential.host}:{credential.port}/{credential.service_name}"

        self.stdout.write(f"Connexion Oracle: {connection_label}")
        self.stdout.write("Recuperation de la liste des tables IB_FLUX_*...")

        try:
            with connect_with_credential(credential, call_timeout_ms=settings.ORACLE_CALL_TIMEOUT_MS) as connection:
                connection.call_timeout = settings.ORACLE_CALL_TIMEOUT_MS
                table_names = list_flux_tables(connection)
                if not table_names:
                    raise CommandError("Aucune table IB_FLUX_* trouvee.")

                self.stdout.write(f"{len(table_names)} table(s) trouvee(s).")
                tables: list[TableMonthlyCounts] = []
                skipped_tables: list[str] = []
                for index, table_name in enumerate(table_names, start=1):
                    self.stdout.write(f"[{index}/{len(table_names)}] Traitement de {table_name}...")
                    try:
                        rows = fetch_monthly_counts(connection, table_name)
                    except oracledb.Error as exc:
                        if self._is_missing_dt_creation_error(exc):
                            self.stdout.write(
                                self.style.WARNING(
                                    f"[{index}/{len(table_names)}] {table_name} ignoree: colonne DT_CREATION absente."
                                )
                            )
                            skipped_tables.append(table_name)
                            continue
                        raise
                    tables.append(TableMonthlyCounts(table_name=table_name, rows=rows))

        except oracledb.Error as exc:
            raise CommandError(f"Erreur Oracle: {exc}") from exc

        build_flux_workbook(output_path, tables)
        if skipped_tables:
            self.stdout.write(
                self.style.WARNING(f"Tables ignorees ({len(skipped_tables)}): {', '.join(skipped_tables)}")
            )
        self.stdout.write(self.style.SUCCESS(f"Export genere: {output_path.resolve()}"))

    def _resolve_option(
        self,
        options,
        option_name: str,
        primary_env: str,
        fallback_env: str,
        *,
        default: str | None = None,
    ) -> str:
        option_value = options.get(option_name)
        if option_value not in (None, ""):
            return str(option_value)

        for env_name in (primary_env, fallback_env):
            env_value = os.environ.get(env_name, "").strip()
            if env_value:
                return env_value

        if default is not None:
            return default

        raise CommandError(
            f"Option manquante: --{option_name.replace('_', '-')} ou variable {primary_env}/{fallback_env}."
        )

    def _init_oracle_client(self) -> None:
        try:
            init_oracle_client()
        except Exception as exc:
            raise CommandError(str(exc)) from exc

    def _is_missing_dt_creation_error(self, exc: oracledb.Error) -> bool:
        error_obj = exc.args[0] if exc.args else None
        error_code = getattr(error_obj, "code", None)
        return error_code == 904 and '"DT_CREATION"' in str(exc).upper()

    def _resolve_credential(self, options) -> OracleCredential:
        credential_id = options.get("credential_id")
        if credential_id:
            try:
                credential: OracleCredential = OracleCredential.objects.get(pk=credential_id, enabled=True)
                return credential
            except OracleCredential.DoesNotExist as exc:
                raise CommandError(f"OracleCredential introuvable ou desactive: {credential_id}") from exc

        host = self._resolve_option(options, "host", "ORACLE_EXPORT_HOST", "ORACLE_TEST_HOST")
        port = int(self._resolve_option(options, "port", "ORACLE_EXPORT_PORT", "ORACLE_TEST_PORT", default="1521"))
        service_name = self._resolve_option(
            options,
            "service_name",
            "ORACLE_EXPORT_SERVICE_NAME",
            "ORACLE_TEST_SERVICE_NAME",
        )
        username = self._resolve_option(options, "username", "ORACLE_EXPORT_USERNAME", "ORACLE_TEST_USERNAME")
        password = self._resolve_option(options, "password", "ORACLE_EXPORT_PASSWORD", "ORACLE_TEST_PASSWORD")

        credential = OracleCredential(
            host=host,
            port=port,
            service_name=service_name,
            username=username,
            enabled=True,
        )
        credential.set_password(password)
        return credential
