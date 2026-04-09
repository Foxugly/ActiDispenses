from django.contrib import admin

from .models import QueryAudit


@admin.register(QueryAudit)
class QueryAuditAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "success", "row_count")
    list_filter = ("success", "created_at")
    search_fields = ("user__username", "query_text", "error_message")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    list_select_related = ("user",)
    actions = ("mark_success", "mark_failure")

    @admin.action(description="Marquer comme succes")
    def mark_success(self, request, queryset):
        queryset.update(success=True, error_message="")

    @admin.action(description="Marquer comme erreur")
    def mark_failure(self, request, queryset):
        queryset.update(success=False)
