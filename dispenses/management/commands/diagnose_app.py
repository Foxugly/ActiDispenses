from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = "Affiche un diagnostic rapide de la configuration locale."

    def handle(self, *args, **options):
        self.stdout.write("== ActiDispenses diagnostic ==")
        self.stdout.write(f"DEBUG: {settings.DEBUG}")
        self.stdout.write(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
        self.stdout.write(f"Oracle client dir: {settings.ORACLE_CLIENT_LIB_DIR}")
        self.stdout.write(f"Oracle timeout: {settings.ORACLE_CALL_TIMEOUT_MS} ms")
        self.stdout.write(f"Monitoring cache TTL: {settings.MONITORING_CACHE_TTL_SECONDS} s")

        configured_client_dir = settings.ORACLE_CLIENT_LIB_DIR.strip()
        client_dir = Path(configured_client_dir) if configured_client_dir else None
        if client_dir and client_dir.exists():
            self.stdout.write(self.style.SUCCESS("Oracle Instant Client detecte sur le disque."))
        else:
            self.stdout.write(self.style.WARNING("Oracle Instant Client introuvable sur le disque."))

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            self.stdout.write(self.style.SUCCESS("Base locale Django OK."))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Base locale Django KO: {exc}"))

        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        plan = executor.migration_plan(targets)
        if plan:
            self.stdout.write(self.style.WARNING(f"Migrations en attente: {len(plan)}"))
            for migration, _backwards in plan:
                self.stdout.write(f" - {migration.app_label}.{migration.name}")
        else:
            self.stdout.write(self.style.SUCCESS("Aucune migration en attente."))
