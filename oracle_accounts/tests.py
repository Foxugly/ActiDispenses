from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase
from django.urls import reverse

from oracle_accounts.forms import OracleCredentialForm
from oracle_accounts.models import OracleCredential
from oracle_accounts.services import (
    SESSION_KEY,
    get_current_oracle_credential,
    set_current_oracle_credential,
)
from tests.factories import make_oracle_credential, make_user


class OracleCredentialFormTests(TestCase):
    def setUp(self):
        self.user = make_user(username="alice")

    def test_password_required_on_create(self):
        form = OracleCredentialForm(
            data={
                "label": "Main",
                "host": "db.local",
                "port": 1521,
                "service_name": "ORCL",
                "username": "scott",
                "password": "",
                "enabled": True,
                "current": False,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("Le mot de passe Oracle est requis.", form.errors["password"])

    def test_blank_password_keeps_existing_secret_on_update(self):
        credential = OracleCredential.objects.create(
            user=self.user,
            label="Main",
            host="db.local",
            port=1521,
            service_name="ORCL",
            username="scott",
            enabled=True,
            current=False,
            password_encrypted="",
        )
        credential.set_password("old-secret")
        credential.save()
        encrypted_before = credential.password_encrypted

        form = OracleCredentialForm(
            instance=credential,
            data={
                "label": "Main updated",
                "host": "db.local",
                "port": 1521,
                "service_name": "ORCL",
                "username": "scott",
                "password": "",
                "enabled": True,
                "current": False,
            },
        )

        self.assertTrue(form.is_valid())
        saved = form.save()
        self.assertEqual(saved.password_encrypted, encrypted_before)


class OracleCredentialServiceTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = make_user(username="bob")

    def _request_for(self, user=None):
        request = self.factory.get("/")
        request.user = user or self.user
        request.session = {}
        return request

    def _create_credential(self, **kwargs):
        return make_oracle_credential(user=self.user, **kwargs)

    def test_get_current_credential_prefers_session_value(self):
        self._create_credential(label="First", current=True)
        second = self._create_credential(label="Second", current=False)
        request = self._request_for()
        request.session[SESSION_KEY] = second.id

        current = get_current_oracle_credential(request)

        self.assertEqual(current.id, second.id)

    def test_get_current_credential_falls_back_to_current_flag(self):
        current_credential = self._create_credential(label="Current", current=True)
        self._create_credential(label="Other", current=False)
        request = self._request_for()

        current = get_current_oracle_credential(request)

        self.assertEqual(current.id, current_credential.id)
        self.assertEqual(request.session[SESSION_KEY], current_credential.id)

    def test_get_current_credential_raises_without_configured_credential(self):
        request = self._request_for()

        with self.assertRaises(PermissionDenied):
            get_current_oracle_credential(request)

    def test_set_current_oracle_credential_switches_current_flag(self):
        old_current = self._create_credential(label="Old", current=True)
        new_current = self._create_credential(label="New", current=False)
        request = self._request_for()

        set_current_oracle_credential(request, new_current)

        old_current.refresh_from_db()
        new_current.refresh_from_db()
        self.assertFalse(old_current.current)
        self.assertTrue(new_current.current)

    def test_saving_new_current_credential_unsets_previous_one(self):
        old_current = self._create_credential(label="Old", current=True)
        new_current = self._create_credential(label="New", current=False)

        new_current.current = True
        new_current.save()

        old_current.refresh_from_db()
        new_current.refresh_from_db()
        self.assertFalse(old_current.current)
        self.assertTrue(new_current.current)


class OracleCredentialPageTests(TestCase):
    def setUp(self):
        self.user = make_user(username="ui-user")
        self.credential = make_oracle_credential(user=self.user, label="Main Oracle", current=True)

    def test_list_page_renders(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("oracle_accounts:list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "oracle_accounts/credential_list.html")
        self.assertContains(response, "Liste des credentials")
        self.assertContains(response, "Main Oracle")

    def test_detail_page_renders(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("oracle_accounts:detail", args=[self.credential.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "oracle_accounts/credential_detail.html")
        self.assertContains(response, "Main Oracle")

    def test_create_page_renders(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("oracle_accounts:create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "oracle_accounts/credential_form.html")
