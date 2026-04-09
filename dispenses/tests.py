from datetime import date
from io import StringIO
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from dispenses.forms import DispenseSearchForm
from dispenses.services.oracle import (
    DatabaseUnavailableError,
    FetchMode,
    OracleClientConfigurationError,
    OracleCredentialError,
    OracleGateway,
    OracleQueryError,
    _map_oracle_error,
    build_oracle_insert_sql_literal,
    build_oracle_update_sql_literal,
    expect_one,
    fill_missing_days,
)
from dispenses.services.oracle_gateway import _safe_params, check_oracle_connection, init_oracle_client
from dispenses.services.oracle_people import PersonInfo
from dispenses.use_cases.search_dispenses import DispenseSearchCriteria, DispenseSearchResult, run_dispense_search
from tests.factories import make_oracle_credential, make_user


class FakeOracleError:
    def __init__(self, message, code=None):
        self.args = [type("ErrorDetails", (), {"code": code})()]
        self._message = message

    def __str__(self):
        return self._message


class DispenseSearchFormTests(TestCase):
    def test_requires_exactly_one_field(self):
        form = DispenseSearchForm(data={})

        self.assertFalse(form.is_valid())
        self.assertIn("Tu dois completer exactement 1 champ.", form.errors["__all__"][0])

    def test_normalizes_single_field(self):
        form = DispenseSearchForm(data={"niss": " 12345678901 "})

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["search_key"], "niss")
        self.assertEqual(form.cleaned_data["search_value"], "12345678901")

    def test_rejects_invalid_niss_format(self):
        form = DispenseSearchForm(data={"niss": "123"})

        self.assertFalse(form.is_valid())
        self.assertIn("Le NISS doit contenir exactement 11 chiffres.", form.errors["niss"])

    def test_rejects_non_numeric_id_demandeur(self):
        form = DispenseSearchForm(data={"id_demandeur": "ABC"})

        self.assertFalse(form.is_valid())
        self.assertIn("L'ID_DEMANDEUR doit contenir uniquement des chiffres.", form.errors["id_demandeur"])

    def test_accepts_alphanumeric_no_ibis(self):
        form = DispenseSearchForm(data={"no_ibis": "H78047076"})

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["search_key"], "no_ibis")
        self.assertEqual(form.cleaned_data["search_value"], "H78047076")


class OracleServiceHelperTests(TestCase):
    def tearDown(self):
        from dispenses.services import oracle_gateway

        oracle_gateway._ORACLE_INIT_DONE = False

    def test_safe_params_masks_sensitive_identifiers(self):
        params = _safe_params({"niss": "12345678901", "no_registre_national": "123", "id_demandeur": "42"})

        self.assertEqual(params["niss"], "***")
        self.assertEqual(params["no_registre_national"], "***")
        self.assertEqual(params["id_demandeur"], "42")

    def test_map_oracle_error_for_invalid_credentials(self):
        self.assertIsInstance(
            _map_oracle_error(cast(Any, FakeOracleError("ORA-01017", code=1017))),
            OracleCredentialError,
        )

    def test_map_oracle_error_for_unavailable_database(self):
        self.assertIsInstance(
            _map_oracle_error(cast(Any, FakeOracleError("ORA-12170", code=12170))),
            DatabaseUnavailableError,
        )

    def test_map_oracle_error_for_thin_mode_verifier_issue(self):
        self.assertIsInstance(
            _map_oracle_error(cast(Any, FakeOracleError("DPY-3015: unsupported verifier"))),
            OracleClientConfigurationError,
        )

    def test_map_oracle_error_falls_back_to_query_error(self):
        self.assertIsInstance(
            _map_oracle_error(cast(Any, FakeOracleError("ORA-00942", code=942))),
            OracleQueryError,
        )

    def test_fill_missing_days_adds_missing_dates(self):
        filled = fill_missing_days(
            [{"day": date(2026, 3, 2), "count": 4}],
            date(2026, 3, 1),
            date(2026, 3, 4),
        )

        self.assertEqual(
            filled,
            [
                {"day": date(2026, 3, 1), "count": 0},
                {"day": date(2026, 3, 2), "count": 4},
                {"day": date(2026, 3, 3), "count": 0},
            ],
        )

    def test_expect_one_validates_row_count(self):
        self.assertIsNone(expect_one([]))
        self.assertEqual(expect_one([{"id": 1}]), {"id": 1})
        with self.assertRaises(ValueError):
            expect_one([{"id": 1}, {"id": 2}])

    def test_build_oracle_update_sql_literal(self):
        sql = build_oracle_update_sql_literal(
            table="ib_dispenses",
            row={"id_dispense": 1, "no_avenant": 2},
            key_fields={"id_dispense"},
            set_fields={"flg_envoye_onem": "N"},
            increment_fields={"no_avenant"},
        )

        self.assertIn("UPDATE ib_dispenses SET", sql)
        self.assertIn("flg_envoye_onem = 'N'", sql)
        self.assertIn("no_avenant = 3", sql)

    def test_build_oracle_insert_sql_literal(self):
        sql = build_oracle_insert_sql_literal(
            table="ib_dispenses",
            row={"id_dispense": 1, "no_avenant": 2, "flg_envoye_onem": "Y"},
            exclude={"id_dispense"},
            set_fields={"flg_envoye_onem": "N"},
            increment_fields={"no_avenant"},
        )

        self.assertIn("INSERT INTO ib_dispenses", sql)
        self.assertIn("no_avenant", sql)
        self.assertIn("'N'", sql)

    @patch("dispenses.services.oracle_gateway.init_oracle_client")
    @patch("dispenses.services.oracle_gateway.get_current_oracle_credential")
    @patch("dispenses.services.oracle_gateway.oracledb.connect")
    def test_oracle_gateway_sets_call_timeout(self, connect_mock, _credential_mock, _init_mock):
        connect_mock.return_value = SimpleNamespace(call_timeout=None)

        gateway = OracleGateway(SimpleNamespace(), call_timeout_ms=1234)
        connection = gateway.connect()

        self.assertEqual(connection.call_timeout, 1234)

    @patch("dispenses.services.oracle.OracleGateway.connect")
    def test_oracle_gateway_execute_returns_dict_rows(self, connect_mock):
        cursor = SimpleNamespace(
            execute=lambda sql, params: None,
            description=[("COL1",)],
            fetchall=lambda: [(1,)],
        )

        class CursorContext:
            def __enter__(self_inner):
                return cursor

            def __exit__(self_inner, exc_type, exc, tb):
                return False

        class ConnectionContext:
            def __enter__(self_inner):
                return SimpleNamespace(cursor=lambda: CursorContext())

            def __exit__(self_inner, exc_type, exc, tb):
                return False

        connect_mock.return_value = ConnectionContext()

        rows = OracleGateway(SimpleNamespace()).execute("SELECT 1", fetch=FetchMode.DICT)

        self.assertEqual(rows, [{"col1": 1}])

    @patch("dispenses.services.oracle.OracleGateway.connect")
    def test_oracle_gateway_execute_limits_rows(self, connect_mock):
        cursor = SimpleNamespace(
            execute=lambda sql, params: None,
            description=[("COL1",)],
            fetchmany=lambda size: [(1,), (2,)][:size],
        )

        class CursorContext:
            def __enter__(self_inner):
                return cursor

            def __exit__(self_inner, exc_type, exc, tb):
                return False

        class ConnectionContext:
            def __enter__(self_inner):
                return SimpleNamespace(cursor=lambda: CursorContext())

            def __exit__(self_inner, exc_type, exc, tb):
                return False

        connect_mock.return_value = ConnectionContext()

        rows = OracleGateway(SimpleNamespace()).execute("SELECT 1", fetch=FetchMode.DICT, max_rows=1)

        self.assertEqual(rows, [{"col1": 1}])

    @patch("dispenses.services.oracle_gateway.oracledb.init_oracle_client")
    @patch("dispenses.services.oracle_gateway.settings.ORACLE_CLIENT_LIB_DIR", "C:\\Oracle\\instantclient")
    def test_init_oracle_client_uses_thick_mode_when_lib_dir_is_configured(self, init_mock):
        init_oracle_client()

        init_mock.assert_called_once_with(lib_dir="C:\\Oracle\\instantclient")

    @patch("dispenses.services.oracle_gateway.oracledb.init_oracle_client")
    @patch("dispenses.services.oracle_gateway.settings.ORACLE_CLIENT_LIB_DIR", "")
    def test_init_oracle_client_skips_driver_init_in_thin_mode(self, init_mock):
        init_oracle_client()

        init_mock.assert_not_called()

    @patch("dispenses.services.oracle_gateway.execute_query", side_effect=OracleCredentialError())
    def test_check_oracle_connection_returns_mapped_error_message(self, _execute_query):
        ok, message = check_oracle_connection(SimpleNamespace())

        self.assertFalse(ok)
        self.assertEqual(message, OracleCredentialError.user_message)

    @patch("dispenses.services.oracle_people.execute_query", return_value=[{"value": 1}])
    def test_fetch_query_uses_read_only_transaction(self, execute_query_mock):
        request = SimpleNamespace()

        from dispenses.services.oracle_people import fetch_query

        self.assertEqual(fetch_query(request, "SELECT 1 AS value FROM dual"), [{"value": 1}])
        execute_query_mock.assert_called_once()
        self.assertTrue(execute_query_mock.call_args.kwargs["read_only_transaction"])

    def test_table_columns_cache_isolated_by_credential(self):
        cache.clear()
        user = make_user(username="schema-user")
        other_user = make_user(username="schema-user-2")
        credential = make_oracle_credential(user=user, username="scott", host="db1.local", service_name="ORCL")
        other_credential = make_oracle_credential(
            user=other_user,
            username="scott",
            host="db2.local",
            service_name="ORCL",
        )
        request = SimpleNamespace(user=user, session={"oracle_cred_id": credential.id})
        other_request = SimpleNamespace(user=other_user, session={"oracle_cred_id": other_credential.id})

        with patch("dispenses.services.oracle_schema.OracleGateway.connect") as connect_mock:

            def make_connection(columns):
                cursor = SimpleNamespace(
                    execute=lambda sql: None,
                    description=[(column,) for column in columns],
                )

                class CursorContext:
                    def __enter__(self_inner):
                        return cursor

                    def __exit__(self_inner, exc_type, exc, tb):
                        return False

                class ConnectionContext:
                    def __enter__(self_inner):
                        return SimpleNamespace(cursor=lambda: CursorContext())

                    def __exit__(self_inner, exc_type, exc, tb):
                        return False

                return ConnectionContext()

            connect_mock.side_effect = [
                make_connection(["COL_A"]),
                make_connection(["COL_B"]),
            ]

            from dispenses.services.oracle_schema import get_table_columns

            self.assertEqual(get_table_columns(request, "IB_DISPENSES"), ["COL_A"])
            self.assertEqual(get_table_columns(request, "IB_DISPENSES"), ["COL_A"])
            self.assertEqual(get_table_columns(other_request, "IB_DISPENSES"), ["COL_B"])

        self.assertEqual(connect_mock.call_count, 2)


class DispenseSearchUseCaseTests(TestCase):
    @patch(
        "dispenses.use_cases.search_dispenses.fetch_webservice_logs",
        return_value=[{"decisionidentification": "D1"}],
    )
    @patch("dispenses.use_cases.search_dispenses.fetch_dispenses", return_value=[{"id_dispense": "1"}])
    @patch("dispenses.use_cases.search_dispenses.resolve_person")
    @patch("dispenses.use_cases.search_dispenses.identify_person", return_value=("id_demandeur", "10"))
    def test_resolves_id_dispense_then_loads_person_data(
        self,
        identify_person_mock,
        resolve_person_mock,
        fetch_dispenses_mock,
        fetch_ws_logs_mock,
    ):
        request = SimpleNamespace()
        resolve_person_mock.return_value = SimpleNamespace(id_demandeur="10", nom="Doe", prenom="Jane")

        result = run_dispense_search(request, DispenseSearchCriteria(search_key="id_dispense", search_value="123"))

        self.assertIsNotNone(result)
        result = cast(DispenseSearchResult, result)
        self.assertEqual(result.person.id_demandeur, "10")
        self.assertEqual(result.dispenses, [{"id_dispense": "1"}])
        self.assertEqual(result.ws_logs, [{"decisionidentification": "D1"}])
        identify_person_mock.assert_called_once_with(request, "id_dispense", "123")
        resolve_person_mock.assert_called_once_with(request, "id_demandeur", "10")
        fetch_dispenses_mock.assert_called_once_with(request, "10")
        fetch_ws_logs_mock.assert_called_once_with(request, "10")

    @patch("dispenses.use_cases.search_dispenses.resolve_person", return_value=None)
    def test_returns_none_when_person_is_missing(self, resolve_person_mock):
        request = SimpleNamespace()

        result = run_dispense_search(request, DispenseSearchCriteria(search_key="niss", search_value="12345678901"))

        self.assertIsNone(result)
        resolve_person_mock.assert_called_once_with(request, "niss", "12345678901")


class DispensesViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user(username="viewer")
        self.monitoring_url = reverse("dispenses_monitoring")
        self.monitoring_export_url = reverse("dispenses_monitoring_export")
        self.search_url = reverse("dispenses_search")
        self.undo_sql_url = reverse("solve_dispenses_undo")
        self.error_sql_url = reverse("solve_dispenses_internal_error")

    def test_monitoring_requires_authentication(self):
        response = self.client.get(self.monitoring_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    @patch("dispenses.services.monitoring.fetch_webservice_daily", side_effect=OracleCredentialError())
    def test_monitoring_renders_oracle_error_page(self, _fetch_webservice_daily):
        self.client.force_login(self.user)

        response = self.client.get(self.monitoring_url)

        self.assertEqual(response.status_code, 502)
        self.assertTemplateUsed(response, "errors/503_db.html")
        self.assertContains(response, "Identifiants Oracle invalides", status_code=502)

    @patch("dispenses.services.monitoring.fetch_webservice_abnormal", return_value=[])
    @patch("dispenses.services.monitoring.fetch_webservice_status", return_value=[{"status": "OK", "count": 2}])
    @patch("dispenses.services.monitoring.fetch_webservice_daily", return_value=[{"day": date(2026, 3, 1), "count": 2}])
    def test_monitoring_uses_cache(self, daily_mock, status_mock, abnormal_mock):
        self.client.force_login(self.user)

        response_one = self.client.get(self.monitoring_url, {"month": 3, "year": 2026})
        response_two = self.client.get(self.monitoring_url, {"month": 3, "year": 2026})

        self.assertEqual(response_one.status_code, 200)
        self.assertEqual(response_two.status_code, 200)
        daily_mock.assert_called_once()
        status_mock.assert_called_once()
        abnormal_mock.assert_called_once()

    @patch("dispenses.services.monitoring.fetch_webservice_abnormal", return_value=[])
    @patch("dispenses.services.monitoring.fetch_webservice_status", return_value=[{"status": "OK", "count": 2}])
    @patch(
        "dispenses.services.monitoring.fetch_webservice_daily",
        side_effect=[[{"day": date(2026, 3, 1), "count": 2}], [{"day": date(2026, 3, 1), "count": 4}]],
    )
    def test_monitoring_refresh_bypasses_cache(self, daily_mock, status_mock, abnormal_mock):
        self.client.force_login(self.user)

        first_response = self.client.get(self.monitoring_url, {"month": 3, "year": 2026})
        refreshed_response = self.client.get(self.monitoring_url, {"month": 3, "year": 2026, "refresh": 1})

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(refreshed_response.status_code, 200)
        self.assertEqual(daily_mock.call_count, 2)
        self.assertContains(refreshed_response, "rafraichissement force")

    @patch("dispenses.services.monitoring.fetch_webservice_abnormal", return_value=[{"id_dispense": 1, "nom": "Doe"}])
    @patch("dispenses.services.monitoring.fetch_webservice_status", return_value=[])
    @patch("dispenses.services.monitoring.fetch_webservice_daily", return_value=[])
    def test_monitoring_export_returns_csv(self, _daily_mock, _status_mock, _abnormal_mock):
        self.client.force_login(self.user)

        response = self.client.get(self.monitoring_export_url, {"month": 3, "year": 2026})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn("id_dispense", response.content.decode())

    @patch("dispenses.views.run_dispense_search")
    def test_search_dispenses_renders_results(self, run_search_mock):
        self.client.force_login(self.user)
        run_search_mock.return_value = DispenseSearchResult(
            person=PersonInfo(id_demandeur="10", nom="Doe", prenom="Jane", niss="12345678901", no_ibis="H78047076"),
            dispenses=[{"id_dispense": "1"}],
            ws_logs=[{"decisionidentification": "D1"}],
        )

        response = self.client.get(self.search_url, {"id_demandeur": "10"})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dispenses/result.html")
        self.assertEqual(response.context["person"].id_demandeur, "10")
        self.assertContains(response, "Historique d'envoi ONEM")
        self.assertNotContains(response, '{% include "dispenses/includes/data_table_card.html" with')
        run_search_mock.assert_called_once()

    @patch("dispenses.views.run_dispense_search", return_value=None)
    def test_search_dispenses_shows_not_found(self, _run_search):
        self.client.force_login(self.user)

        response = self.client.get(self.search_url, {"niss": "12345678901"})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dispenses/search.html")
        self.assertTrue(response.context["not_found"])

    @patch(
        "dispenses.views.fetch_dispense_rows_by_pairs",
        return_value={("1", "2"): {"id_dispense": 1, "no_avenant": 2}},
    )
    @patch(
        "dispenses.views.fetch_short_webservice_logs_undo_without_next",
        return_value=[{"id_dispense": 1, "decisionsituationnbr": 2}],
    )
    def test_undo_sql_download_returns_attachment(self, _fetch_short, _fetch_rows):
        self.client.force_login(self.user)

        response = self.client.get(self.undo_sql_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn("INSERT INTO ib_dispenses", response.content.decode())

    @patch(
        "dispenses.views.fetch_dispense_rows_by_pairs",
        return_value={("1", "2"): {"id_dispense": 1, "no_avenant": 2}},
    )
    @patch(
        "dispenses.views.fetch_short_webservice_internal_error_without_next",
        return_value=[{"id_dispense": 1, "decisionsituationnbr": 2}],
    )
    def test_internal_error_sql_download_returns_attachment(self, _fetch_short, _fetch_rows):
        self.client.force_login(self.user)

        response = self.client.get(self.error_sql_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn("UPDATE ib_dispenses SET", response.content.decode())

    @patch(
        "dispenses.views.fetch_webservice_internal_error_without_next",
        return_value=[{"detail_statut_reponse": "NOK"}],
    )
    def test_internal_error_page_uses_shared_template(self, _fetch_logs):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dispenses_internal_error"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dispenses/ws_issue.html")
        self.assertContains(response, "Erreurs internes")


class HealthzViewTests(TestCase):
    def test_healthz_returns_ok(self):
        response = self.client.get(reverse("healthz"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "healthz.html")
        self.assertContains(response, "Sante applicative")
        self.assertContains(response, "Base locale Django")
        self.assertContains(response, "Timeout Oracle")
        self.assertContains(response, settings.APP_VERSION)

    def test_healthz_oracle_requires_authenticated_user(self):
        response = self.client.get(f"{reverse('healthz')}?oracle=1")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Connecte-toi pour tester la connexion Oracle.")

    @patch("config.urls.check_oracle_connection", return_value=(True, "Connexion Oracle OK."))
    def test_healthz_can_run_optional_oracle_check(self, oracle_mock):
        user = make_user(username="oracle-health")
        self.client.force_login(user)

        response = self.client.get(f"{reverse('healthz')}?oracle=1")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Connexion Oracle OK.")
        oracle_mock.assert_called_once()
        self.assertIsNotNone(cache.get("healthz:last_oracle_success"))


class DiagnoseCommandTests(TestCase):
    def test_diagnose_command_runs(self):
        output = StringIO()
        with patch("pathlib.Path.exists", return_value=True):
            call_command("diagnose_app", stdout=output)

        self.assertIn("ActiDispenses diagnostic", output.getvalue())
