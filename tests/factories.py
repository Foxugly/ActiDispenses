from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from oracle_accounts.models import OracleCredential
from query.models import QueryAudit


def make_user(**kwargs):
    defaults = {
        "username": kwargs.pop("username", "user"),
        "password": kwargs.pop("password", "secret"),
    }
    return get_user_model().objects.create_user(**defaults, **kwargs)


def make_staff_user(**kwargs):
    return make_user(is_staff=True, **kwargs)


def grant_permissions(user, *codenames: str):
    permissions = Permission.objects.filter(codename__in=codenames)
    user.user_permissions.add(*permissions)
    return user


def make_oracle_credential(*, user, password="secret", **kwargs):
    defaults = {
        "label": "Oracle",
        "host": "db.local",
        "port": 1521,
        "service_name": "ORCL",
        "username": "scott",
        "enabled": True,
        "current": False,
        "password_encrypted": "",
    }
    defaults.update(kwargs)
    credential = OracleCredential.objects.create(user=user, **defaults)
    credential.set_password(password)
    credential.save()
    return credential


def make_query_audit(*, user=None, **kwargs):
    defaults = {
        "query_text": "SELECT 1 FROM dual",
        "row_count": 1,
        "success": True,
        "error_message": "",
    }
    defaults.update(kwargs)
    return QueryAudit.objects.create(user=user, **defaults)
