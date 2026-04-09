from django.urls import path

from .views import (
    export_monitoring_abnormal_csv,
    get_new_sql_create_for_internal_error,
    get_new_sql_create_for_undo,
    internal_error,
    monitoring_dispenses,
    search_dispenses,
    ssin_not_integrated,
    undo_dispense,
    unknown_code,
)

urlpatterns = [
    path("monitoring/", monitoring_dispenses, name="dispenses_monitoring"),
    path("monitoring/export/", export_monitoring_abnormal_csv, name="dispenses_monitoring_export"),
    path("search/", search_dispenses, name="dispenses_search"),
    path("internal-error/", internal_error, name="dispenses_internal_error"),
    path("internal-error/solve", get_new_sql_create_for_internal_error, name="solve_dispenses_internal_error"),
    path("undo/", undo_dispense, name="dispenses_undo"),
    path("undo/solve", get_new_sql_create_for_undo, name="solve_dispenses_undo"),
    path("unknown_code/", unknown_code, name="dispenses_unknown_code"),
    path("ssin_not_integrated/", ssin_not_integrated, name="dispenses_ssin_not_integrated"),
]
