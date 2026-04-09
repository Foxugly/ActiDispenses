from django.urls import path

from .views import query_audit_detail, query_audit_export, query_audit_list, run_query

urlpatterns = [
    path("", run_query, name="query"),
    path("audit/", query_audit_list, name="query_audit"),
    path("audit/export/", query_audit_export, name="query_audit_export"),
    path("audit/<int:audit_id>/", query_audit_detail, name="query_audit_detail"),
]
