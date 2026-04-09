from django.conf import settings


def auth_flags(_request):
    return {
        "auth_azuread_enabled": settings.AZUREAD_AUTH_CONFIGURED,
        "auth_local_login_enabled": settings.LOCAL_LOGIN_ENABLED,
    }
