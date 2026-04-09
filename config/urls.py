from time import perf_counter
from typing import TypedDict

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.handlers.wsgi import WSGIRequest
from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import include, path
from django.utils import timezone

from config.metrics import get_app_metrics_snapshot, increment_metric, set_metric
from config.services import build_ops_dashboard_data
from dispenses.services.oracle import OracleServiceError, check_oracle_connection
from query.permissions import ensure_can_view_ops_dashboard
from query.services import latest_successful_audit


class OracleSuccessCache(TypedDict):
    username: str
    timestamp: str
    message: str


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "home.html", {"page_title": "Accueil"})


def about(request: HttpRequest) -> HttpResponse:
    return render(request, "about.html", {"page_title": "A propos"})


@login_required
def settings_home(request: HttpRequest) -> HttpResponse:
    return render(request, "account/settings_home.html", {"page_title": "Parametres"})


@login_required
def ops_dashboard(request: HttpRequest) -> HttpResponse:
    ensure_can_view_ops_dashboard(request)
    return render(
        request,
        "ops_dashboard.html",
        {
            "page_title": "Tableau de bord technique",
            "dashboard": build_ops_dashboard_data(),
        },
    )


def healthz(request: WSGIRequest) -> HttpResponse:
    increment_metric("healthz.requests")
    db_ok = True
    oracle_requested = request.GET.get("oracle") == "1"
    oracle_ok: bool | None = None
    oracle_message = "Test Oracle non lance."
    started = perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        db_ok = False
    duration_ms = round((perf_counter() - started) * 1000, 2)
    set_metric("healthz.last_database_duration_ms", duration_ms)

    oracle_duration_ms = None
    if oracle_requested and request.user.is_authenticated:
        increment_metric("healthz.oracle.requests")
        oracle_started = perf_counter()
        try:
            oracle_ok, oracle_message = check_oracle_connection(request)
            if oracle_ok:
                cache.set(
                    "healthz:last_oracle_success",
                    {
                        "username": request.user.username,
                        "timestamp": timezone.now().isoformat(),
                        "message": oracle_message,
                    },
                    86400,
                )
        except OracleServiceError as exc:
            oracle_ok = False
            oracle_message = exc.user_message
            increment_metric("healthz.oracle.failure")
        oracle_duration_ms = round((perf_counter() - oracle_started) * 1000, 2)
        set_metric("healthz.last_oracle_duration_ms", oracle_duration_ms)
    elif oracle_requested:
        oracle_message = "Connecte-toi pour tester la connexion Oracle."

    last_oracle_success = cache.get("healthz:last_oracle_success")
    latest_audit = latest_successful_audit()

    context = {
        "page_title": "Sante applicative",
        "status": "OK" if db_ok else "Degrade",
        "database_status": "OK" if db_ok else "Erreur",
        "database_ok": db_ok,
        "database_duration_ms": duration_ms,
        "environment_name": "Developpement" if settings.DEBUG else "Production",
        "oracle_mode": "Thick" if settings.ORACLE_CLIENT_LIB_DIR else "Thin",
        "oracle_timeout_ms": settings.ORACLE_CALL_TIMEOUT_MS,
        "oracle_requested": oracle_requested,
        "oracle_ok": oracle_ok,
        "oracle_message": oracle_message,
        "oracle_duration_ms": oracle_duration_ms,
        "app_version": settings.APP_VERSION,
        "build_date": settings.BUILD_DATE or "Non renseignee",
        "last_oracle_success": last_oracle_success,
        "latest_successful_audit": latest_audit,
        "metrics": get_app_metrics_snapshot(),
    }
    return render(request, "healthz.html", context, status=200 if db_ok else 503)


def error_404(request: HttpRequest, exception: Exception) -> HttpResponse:
    return render(request, "errors/404.html", status=404)


def error_400(request: HttpRequest, exception: Exception) -> HttpResponse:
    return render(
        request,
        "errors/400.html",
        {
            "error_message": str(exception) or "La requete envoyee est invalide ou incomplete.",
        },
        status=400,
    )


def error_403(request: HttpRequest, exception: Exception) -> HttpResponse:
    return render(
        request,
        "errors/403.html",
        {
            "error_message": str(exception) or "Tu n'as pas les droits necessaires pour acceder a cette page.",
        },
        status=403,
    )


def error_500(request: HttpRequest) -> HttpResponse:
    return render(request, "errors/500.html", status=500)


def error_503(request: HttpRequest) -> HttpResponse:
    return render(request, "errors/503.html", status=503)


urlpatterns = [
    path("", home, name="home"),
    path("about", about, name="about"),
    path("accounts/settings/", settings_home, name="account_settings"),
    path("ops/", ops_dashboard, name="ops_dashboard"),
    path("healthz/", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("dispenses/", include("dispenses.urls")),
    path("query/", include("query.urls")),
    path("accounts/", include("allauth.urls")),
    path("oracle/", include("oracle_accounts.urls")),
]

handler400 = "config.urls.error_400"
handler404 = "config.urls.error_404"
handler403 = "config.urls.error_403"
handler500 = "config.urls.error_500"
handler503 = "config.urls.error_503"
