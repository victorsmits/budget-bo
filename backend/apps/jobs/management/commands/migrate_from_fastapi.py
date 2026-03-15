from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Migrate existing data from legacy FastAPI schema"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("migrate_from_fastapi is scaffolded and should be customized for production data migration."))
