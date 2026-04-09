from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from query.models import QueryAudit


class Command(BaseCommand):
    help = "Purge les QueryAudit plus anciens qu'un nombre de jours donne."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=90, help="Age minimal des audits a supprimer.")
        parser.add_argument(
            "--only-failures",
            action="store_true",
            help="Supprime uniquement les audits en echec.",
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options["days"])
        queryset = QueryAudit.objects.filter(created_at__lt=cutoff)
        if options["only_failures"]:
            queryset = queryset.filter(success=False)

        deleted_count = queryset.count()
        queryset.delete()
        self.stdout.write(self.style.SUCCESS(f"{deleted_count} audit(s) supprime(s)."))
