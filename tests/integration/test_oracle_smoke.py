from __future__ import annotations

import os
from unittest import skipUnless

import pytest
from django.test import RequestFactory, TestCase

from dispenses.services.oracle import check_oracle_connection, fetch_query, get_table_columns, select_columns_sql
from dispenses.services.oracle_gateway import FetchMode, OracleGateway, execute_query
from oracle_accounts.services import SESSION_KEY
from tests.factories import make_oracle_credential, make_user


def _env_required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"The {name} environment variable must be set for Oracle integration tests.")
    return value


@pytest.mark.integration_oracle
@skipUnless(os.environ.get("RUN_ORACLE_INTEGRATION_TESTS") == "1", "Oracle integration tests are disabled.")
class OracleIntegrationSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user(username="oracle-integration-user")
        cls.credential = make_oracle_credential(
            user=cls.user,
            label="Oracle Integration",
            host=_env_required("ORACLE_TEST_HOST"),
            port=int(os.environ.get("ORACLE_TEST_PORT", "1521")),
            service_name=_env_required("ORACLE_TEST_SERVICE_NAME"),
            username=_env_required("ORACLE_TEST_USERNAME"),
            password=_env_required("ORACLE_TEST_PASSWORD"),
            current=True,
        )
        cls.sample_table = os.environ.get("ORACLE_TEST_SAMPLE_TABLE", "DUAL").strip() or "DUAL"

    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get("/")
        self.request.user = self.user
        self.request.session = {SESSION_KEY: self.credential.id}

    def test_check_oracle_connection_returns_ok(self):
        ok, message = check_oracle_connection(self.request)

        self.assertTrue(ok)
        self.assertEqual(message, "Connexion Oracle OK.")

    def test_gateway_execute_one_on_dual(self):
        row, columns = OracleGateway(self.request).execute("SELECT 1 AS value FROM dual", fetch=FetchMode.ONE)

        self.assertEqual(columns, ["VALUE"])
        self.assertEqual(row[0], 1)

    def test_fetch_query_returns_dict_rows(self):
        results = fetch_query(self.request, "SELECT 1 AS value FROM dual")

        self.assertEqual(results, [{"value": 1}])

    def test_execute_query_all_returns_raw_rows(self):
        rows = execute_query(self.request, "SELECT 1 FROM dual", fetch=FetchMode.ALL, max_rows=1)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], 1)

    def test_get_table_columns_describes_sample_table(self):
        columns = get_table_columns(self.request, self.sample_table)

        self.assertTrue(columns)
        self.assertTrue(all(isinstance(column, str) for column in columns))

    def test_select_columns_sql_uses_sample_table_columns(self):
        sql = select_columns_sql(self.request, self.sample_table)

        self.assertTrue(sql)
        self.assertNotIn("*", sql)

    def test_select_columns_sql_supports_alias(self):
        sql = select_columns_sql(self.request, self.sample_table, alias="t")

        self.assertTrue(sql)
        self.assertIn("t.", sql)

    def test_fetch_query_respects_preview_limit(self):
        results = fetch_query(self.request, "SELECT level AS value FROM dual CONNECT BY level <= 5")

        self.assertLessEqual(len(results), 5)
