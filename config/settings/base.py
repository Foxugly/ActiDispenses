import os
import sys
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env", overwrite=True)

APP_VERSION = env("APP_VERSION", default="dev")
BUILD_DATE = env("BUILD_DATE", default="")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])
ORACLE_CREDENTIAL_KEY = env("ORACLE_CREDENTIAL_KEY")
ORACLE_CLIENT_LIB_DIR = env("ORACLE_CLIENT_LIB_DIR", default="").strip()
ORACLE_CALL_TIMEOUT_MS = env.int("ORACLE_CALL_TIMEOUT_MS", default=30000)
QUERY_PREVIEW_MAX_ROWS = env.int("QUERY_PREVIEW_MAX_ROWS", default=500)
QUERY_ALLOWED_TABLES = env.list(
    "QUERY_ALLOWED_TABLES",
    default=["DUAL", "IB_DISPENSES", "IB_DEMANDEURS", "IB_UNEMPL_DECISION_DISPENSES"],
)
QUERY_ALLOWED_SCHEMAS = env.list("QUERY_ALLOWED_SCHEMAS", default=[])
MONITORING_CACHE_TTL_SECONDS = env.int("MONITORING_CACHE_TTL_SECONDS", default=30)
DJANGO_LOG_LEVEL = env("DJANGO_LOG_LEVEL", default="INFO")
TESTING = "test" in sys.argv or "PYTEST_CURRENT_TEST" in os.environ

SITE_ID = 1

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "crispy_forms",
    "crispy_bootstrap5",
    "allauth",
    "allauth.account",
    "dispenses.apps.DispensesConfig",
    "query.apps.QueryConfig",
    "oracle_accounts.apps.OracleAccountsConfig",
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "dispenses.services.middleware.OracleUnavailableMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "oracle_accounts.context_processors.oracle_credentials_nav",
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Brussels"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True

LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"
ACCOUNT_LOGOUT_ON_GET = False

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": DJANGO_LOG_LEVEL,
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "ERROR" if TESTING else DJANGO_LOG_LEVEL, "propagate": False},
        "django.request": {"handlers": ["console"], "level": "CRITICAL" if TESTING else "ERROR", "propagate": False},
        "dispenses": {
            "handlers": ["console"],
            "level": "CRITICAL" if TESTING else DJANGO_LOG_LEVEL,
            "propagate": False,
        },
        "oracle_accounts": {
            "handlers": ["console"],
            "level": "CRITICAL" if TESTING else DJANGO_LOG_LEVEL,
            "propagate": False,
        },
        "query": {"handlers": ["console"], "level": "CRITICAL" if TESTING else DJANGO_LOG_LEVEL, "propagate": False},
    },
}
