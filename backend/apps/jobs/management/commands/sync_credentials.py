from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.jobs.batch import sync_all_credentials


class Command(BaseCommand):
    help = "Enqueue sync jobs for all active bank credentials."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days-back",
            type=int,
            default=1,
            help="How many days back to fetch transactions for each credential.",
        )

    def handle(self, *args, **options):
        days_back = int(options["days_back"])
        sync_all_credentials(days_back=days_back)
        self.stdout.write(self.style.SUCCESS("Queued sync jobs"))
