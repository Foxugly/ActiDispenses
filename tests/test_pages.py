from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from config.metrics import increment_metric, set_metric
from config.urls import error_400, error_403, error_404, error_500, error_503
from tests.factories import grant_permissions, make_query_audit, make_staff_user, make_user


class StaticPageTests(TestCase):
    def test_home_page_renders(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")
        self.assertContains(response, "ActiDispenses")
        self.assertContains(response, "Parcours principaux")
        self.assertContains(response, "Reperes")

    def test_about_page_renders(self):
        response = self.client.get(reverse("about"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "about.html")
        self.assertContains(response, "Une interface de travail")
        self.assertContains(response, "Requetes SQL")
        self.assertContains(response, "Sante applicative")

    def test_settings_page_requires_authentication(self):
        response = self.client.get(reverse("account_settings"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_settings_page_renders_for_authenticated_user(self):
        user = make_user(username="settings-user")
        self.client.force_login(user)

        response = self.client.get(reverse("account_settings"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/settings_home.html")
        self.assertContains(response, "Centre de configuration")
        self.assertContains(response, "Mot de passe")
        self.assertContains(response, "Emails")

    def test_ops_dashboard_requires_staff(self):
        user = make_user(username="plain-user")
        self.client.force_login(user)

        with override_settings(DEBUG=False):
            response = self.client.get(reverse("ops_dashboard"))

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "errors/403.html")
        self.assertContains(response, "Acces refuse", status_code=403)

    def test_ops_dashboard_renders_for_staff(self):
        staff_user = make_staff_user(username="staff-user")
        make_query_audit(user=staff_user, success=True, row_count=12)
        self.client.force_login(staff_user)

        response = self.client.get(reverse("ops_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ops_dashboard.html")
        self.assertContains(response, "Tableau de bord technique")
        self.assertContains(response, "Audit SQL")

    def test_ops_dashboard_renders_for_user_with_permission(self):
        cache.clear()
        user = grant_permissions(make_user(username="ops-user"), "view_ops_dashboard")
        make_query_audit(user=user, success=True, row_count=12)
        increment_metric("query.requests")
        set_metric("healthz.last_database_duration_ms", 12.5)
        self.client.force_login(user)

        response = self.client.get(reverse("ops_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Metriques applicatives")
        self.assertContains(response, "12.5 ms")

    def test_login_page_renders_local_form_by_default(self):
        response = self.client.get(reverse("account_login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/login.html")
        self.assertContains(response, "Se connecter")
        self.assertContains(response, "Mot de passe")

    @override_settings(
        AZUREAD_AUTH_ENABLED=True,
        AZUREAD_AUTH_CONFIGURED=True,
        LOCAL_LOGIN_ENABLED=True,
        AZUREAD_SSO_ONLY=False,
    )
    def test_login_page_can_show_azuread_button_in_hybrid_mode(self):
        response = self.client.get(reverse("account_login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Se connecter avec Azure AD")
        self.assertContains(response, "Mot de passe")

    @override_settings(AZUREAD_AUTH_ENABLED=True, LOCAL_LOGIN_ENABLED=False, AZUREAD_SSO_ONLY=True)
    def test_login_page_redirects_to_microsoft_in_sso_only_mode(self):
        response = self.client.get(reverse("account_login"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("microsoft_login"))


class ErrorPageTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(DEBUG=False)
    def test_custom_400_view_renders_template(self):
        request = self.factory.get("/bad-request/")
        request.user = AnonymousUser()

        response = error_400(request, Exception("Parametres invalides."))

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Requete invalide", status_code=400)
        self.assertContains(response, "Parametres invalides.", status_code=400)

    @override_settings(DEBUG=False)
    def test_custom_403_view_renders_template(self):
        request = self.factory.get("/forbidden/")
        request.user = AnonymousUser()

        response = error_403(request, Exception("Acces interdit."))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Acces refuse", status_code=403)
        self.assertContains(response, "Acces interdit.", status_code=403)

    @override_settings(DEBUG=False)
    def test_custom_404_view_renders_template(self):
        request = self.factory.get("/missing/")
        request.user = AnonymousUser()

        response = error_404(request, Exception("missing"))

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Page introuvable", status_code=404)

    @override_settings(DEBUG=False)
    def test_custom_500_view_renders_template(self):
        request = self.factory.get("/boom/")
        request.user = AnonymousUser()

        response = error_500(request)

        self.assertEqual(response.status_code, 500)
        self.assertContains(response, "Erreur interne", status_code=500)

    @override_settings(DEBUG=False)
    def test_custom_503_view_renders_template(self):
        request = self.factory.get("/maintenance/")
        request.user = AnonymousUser()

        response = error_503(request)

        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "Service indisponible", status_code=503)
