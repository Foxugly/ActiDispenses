from django.contrib import admin

from .models import OracleCredential


@admin.register(OracleCredential)
class OracleCredentialAdmin(admin.ModelAdmin):
    list_display = ("label", "user", "host", "port", "service_name", "username", "enabled", "current", "updated_at")
    list_filter = ("enabled", "current", "updated_at")
    search_fields = ("label", "user__username", "host", "service_name", "username")
    autocomplete_fields = ("user",)
    readonly_fields = ("updated_at",)
    list_select_related = ("user",)
    actions = ("enable_selected", "disable_selected")

    @admin.action(description="Activer les identifiants selectionnes")
    def enable_selected(self, request, queryset):
        queryset.update(enabled=True)

    @admin.action(description="Desactiver les identifiants selectionnes")
    def disable_selected(self, request, queryset):
        queryset.update(enabled=False)
