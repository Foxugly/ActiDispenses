from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from query.forms import QueryForm
from query.models import QueryAudit
from tests.factories import grant_permissions, make_query_audit, make_staff_user, make_user


class QueryFormTests(TestCase):
    def test_accepts_select_query(self):
        form = QueryForm(data={"query": "SELECT * FROM dual;"})

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["query"], "SELECT * FROM dual")

    def test_rejects_non_read_only_query(self):
        form = QueryForm(data={"query": "DELETE FROM users"})

        self.assertFalse(form.is_valid())
        self.assertIn("Seules les requetes SELECT et WITH sont autorisees.", form.errors["query"])

    def test_rejects_multiple_statements(self):
        form = QueryForm(data={"query": "SELECT 1; SELECT 2"})

        self.assertFalse(form.is_valid())
        self.assertIn("Les requetes multiples ne sont pas autorisees.", form.errors["query"])

    def test_rejects_sql_comments(self):
        form = QueryForm(data={"query": "SELECT 1 -- comment"})

        self.assertFalse(form.is_valid())
        self.assertIn("Les commentaires SQL ne sont pas autorises.", form.errors["query"])

    def test_rejects_select_for_update(self):
        form = QueryForm(data={"query": "SELECT * FROM dual FOR UPDATE"})

        self.assertFalse(form.is_valid())
        self.assertIn("La requete contient des mots-cles interdits.", form.errors["query"])

    def test_rejects_with_function_blocks(self):
        form = QueryForm(data={"query": "WITH FUNCTION demo RETURN NUMBER SELECT 1 FROM dual"})

        self.assertFalse(form.is_valid())
        self.assertIn("Les blocs WITH FUNCTION/PROCEDURE ne sont pas autorises.", form.errors["query"])

    def test_rejects_disallowed_table(self):
        form = QueryForm(data={"query": "SELECT * FROM user_tables"})

        self.assertFalse(form.is_valid())
        self.assertIn("Sources SQL non autorisees", form.errors["query"][0])


class RunQueryViewTests(TestCase):
    def setUp(self):
        self.url = reverse("query")

    def test_redirects_anonymous_user(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_rejects_non_staff_user(self):
        user = make_user(username="user")
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_search_page_shows_recent_user_queries(self):
        user = grant_permissions(make_user(username="sql-user"), "run_sql_console")
        other_user = grant_permissions(make_user(username="other-sql-user"), "run_sql_console")
        make_query_audit(user=user, query_text="SELECT 1", row_count=1, success=True)
        make_query_audit(user=user, query_text="SELECT 2", row_count=2, success=False)
        make_query_audit(user=other_user, query_text="SELECT 999", row_count=999, success=True)
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dernieres requetes")
        self.assertContains(response, "SELECT 1")
        self.assertContains(response, "SELECT 2")
        self.assertNotContains(response, "SELECT 999")
        self.assertContains(response, "Relancer")
        self.assertContains(response, "Autres")

    @patch("query.views.fetch_query", return_value=[{"col1": 1}])
    def test_user_with_run_sql_permission_can_run_query(self, fetch_query_mock):
        user = grant_permissions(make_user(username="sql-user"), "run_sql_console")
        self.client.force_login(user)

        response = self.client.post(self.url, {"query": "SELECT 1 AS col1 FROM dual"})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "query/result.html")
        fetch_query_mock.assert_called_once()

    @patch("query.views.fetch_query", return_value=[{"col1": 1}])
    def test_staff_user_can_run_read_only_query(self, fetch_query_mock):
        user = make_staff_user(username="staff")
        self.client.force_login(user)

        response = self.client.post(self.url, {"query": "SELECT 1 AS col1 FROM dual"})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "query/result.html")
        self.assertEqual(response.context["results"], [{"col1": 1}])
        self.assertEqual(response.context["max_rows"], settings.QUERY_PREVIEW_MAX_ROWS)
        self.assertContains(response, f"apercu limite a {settings.QUERY_PREVIEW_MAX_ROWS} ligne")
        self.assertContains(response, "Colonnes")
        self.assertContains(response, 'placeholder="Filtrer..."')
        self.assertContains(response, "Nouvelle requete")
        fetch_query_mock.assert_called_once()
        audit = QueryAudit.objects.get()
        self.assertTrue(audit.success)
        self.assertEqual(audit.row_count, 1)

    @patch("query.views.fetch_query", side_effect=RuntimeError("boom"))
    def test_staff_query_failure_is_audited(self, _fetch_query_mock):
        user = make_staff_user(username="staff-fail")
        self.client.force_login(user)

        with self.assertRaises(RuntimeError):
            self.client.post(self.url, {"query": "SELECT 1"})

        audit = QueryAudit.objects.get()
        self.assertFalse(audit.success)
        self.assertEqual(audit.error_message, "boom")

    @patch("query.views.fetch_query", return_value=[{"col1": 1}])
    def test_can_rerun_saved_query_from_history(self, fetch_query_mock):
        user = grant_permissions(make_user(username="sql-rerun"), "run_sql_console")
        make_query_audit(user=user, query_text="SELECT 7 AS col1 FROM dual", row_count=1, success=True)
        self.client.force_login(user)

        response = self.client.post(self.url, {"query": "SELECT 7 AS col1 FROM dual"})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "query/result.html")
        fetch_query_mock.assert_called_once()


class QueryHistoryViewTests(TestCase):
    def setUp(self):
        self.url = reverse("query_history")

    def test_user_with_run_permission_can_access_history_page(self):
        user = grant_permissions(make_user(username="history-user"), "run_sql_console")
        make_query_audit(user=user, query_text="SELECT 1", row_count=1, success=True)
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "query/history_list.html")
        self.assertContains(response, "Toutes mes requetes")
        self.assertContains(response, "SELECT 1")
        self.assertContains(response, "Relancer")

    def test_history_page_is_limited_to_current_user(self):
        user = grant_permissions(make_user(username="history-owner"), "run_sql_console")
        other_user = grant_permissions(make_user(username="history-other"), "run_sql_console")
        make_query_audit(user=user, query_text="SELECT owner_value", row_count=1, success=True)
        make_query_audit(user=other_user, query_text="SELECT other_value", row_count=1, success=True)
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertContains(response, "SELECT owner_value")
        self.assertNotContains(response, "SELECT other_value")

    def test_history_page_is_paginated(self):
        user = grant_permissions(make_user(username="history-paginated"), "run_sql_console")
        for index in range(30):
            make_query_audit(user=user, query_text=f"SELECT {index}", row_count=index, success=True)
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["page_obj"].paginator.num_pages >= 2)
        self.assertEqual(len(response.context["queries"]), 25)


class QueryAuditViewTests(TestCase):
    def setUp(self):
        self.url = reverse("query_audit")

    def test_non_staff_cannot_access_audit_page(self):
        user = make_user(username="audit-user")
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_staff_can_access_audit_page(self):
        user = make_staff_user(username="audit-staff")
        QueryAudit.objects.create(user=user, query_text="SELECT 1", row_count=1, success=True)
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "query/audit_list.html")
        self.assertContains(response, "Audit des requetes SQL")

    def test_user_with_view_permission_can_access_audit_page(self):
        user = grant_permissions(make_user(username="audit-perm"), "view_queryaudit")
        QueryAudit.objects.create(user=user, query_text="SELECT 1", row_count=1, success=True)
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "query/audit_list.html")

    def test_audit_page_is_paginated(self):
        user = make_staff_user(username="audit-paginated")
        for index in range(30):
            QueryAudit.objects.create(user=user, query_text=f"SELECT {index}", row_count=index, success=True)
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["page_obj"].paginator.num_pages >= 2)
        self.assertEqual(len(response.context["audits"]), 25)

    def test_staff_can_access_audit_detail_page(self):
        user = make_staff_user(username="audit-detail")
        audit = QueryAudit.objects.create(user=user, query_text="SELECT 1", row_count=1, success=True)
        self.client.force_login(user)

        response = self.client.get(reverse("query_audit_detail", args=[audit.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "query/audit_detail.html")
        self.assertContains(response, "Detail audit SQL")
        self.assertContains(response, "SELECT 1")

    def test_staff_can_export_audit_csv(self):
        user = make_staff_user(username="audit-export")
        QueryAudit.objects.create(user=user, query_text="SELECT 1", row_count=1, success=True)
        self.client.force_login(user)

        response = self.client.get(reverse("query_audit_export"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn("SELECT 1", response.content.decode())

    def test_audit_page_filters_by_username_and_status(self):
        user = make_staff_user(username="audit-filter-owner")
        other_user = make_staff_user(username="other-user")
        QueryAudit.objects.create(user=user, query_text="SELECT 1", row_count=1, success=True)
        QueryAudit.objects.create(user=other_user, query_text="SELECT 2", row_count=0, success=False)
        self.client.force_login(user)

        response = self.client.get(self.url, {"username": "audit-filter", "success": "true"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["audits"]), [QueryAudit.objects.get(user=user)])

    def test_audit_page_filters_by_date_range(self):
        user = make_staff_user(username="audit-date")
        old_audit = QueryAudit.objects.create(user=user, query_text="SELECT old", row_count=1, success=True)
        new_audit = QueryAudit.objects.create(user=user, query_text="SELECT new", row_count=1, success=True)
        QueryAudit.objects.filter(pk=old_audit.pk).update(created_at=timezone.now() - timezone.timedelta(days=5))
        self.client.force_login(user)

        response = self.client.get(self.url, {"date_from": timezone.localdate().isoformat()})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["audits"]), [QueryAudit.objects.get(pk=new_audit.pk)])


class PurgeQueryAuditsCommandTests(TestCase):
    def test_purge_query_audits_removes_old_records(self):
        user = make_staff_user(username="audit-purge")
        old_audit = QueryAudit.objects.create(user=user, query_text="SELECT old", row_count=1, success=False)
        recent_audit = QueryAudit.objects.create(user=user, query_text="SELECT new", row_count=1, success=True)
        QueryAudit.objects.filter(pk=old_audit.pk).update(created_at=timezone.now() - timezone.timedelta(days=120))

        output = StringIO()
        call_command("purge_query_audits", "--days", "90", stdout=output)

        self.assertFalse(QueryAudit.objects.filter(pk=old_audit.pk).exists())
        self.assertTrue(QueryAudit.objects.filter(pk=recent_audit.pk).exists())
        self.assertIn("1 audit(s) supprime(s).", output.getvalue())


class BootstrapAppAccessCommandTests(TestCase):
    def test_bootstrap_app_access_creates_groups(self):
        output = StringIO()

        call_command("bootstrap_app_access", stdout=output)

        self.assertIn("sql_console_users", output.getvalue())
        self.assertIn("app_staff_users", output.getvalue())
