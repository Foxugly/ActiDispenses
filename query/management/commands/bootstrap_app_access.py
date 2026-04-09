from __future__ import annotations

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError

GROUP_PERMISSIONS = {
    "sql_console_users": ["run_sql_console"],
    "sql_audit_users": ["view_queryaudit"],
    "ops_dashboard_users": ["view_ops_dashboard"],
    "app_staff_users": ["run_sql_console", "view_queryaudit", "view_ops_dashboard"],
}


class Command(BaseCommand):
    help = "Cree les groupes et permissions applicatives utiles pour la console SQL et le dashboard ops."

    def handle(self, *args, **options):
        for group_name, codenames in GROUP_PERMISSIONS.items():
            permissions = list(Permission.objects.filter(codename__in=codenames))
            missing = sorted(set(codenames) - {permission.codename for permission in permissions})
            if missing:
                raise CommandError(f"Permissions introuvables pour {group_name}: {', '.join(missing)}")

            group, _created = Group.objects.get_or_create(name=group_name)
            group.permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS(f"{group_name}: {', '.join(sorted(codenames))}"))
