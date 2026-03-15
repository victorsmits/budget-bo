from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = (
        "List or drop database tables that are not mapped to installed Django models. "
        "Use --execute to apply DROP TABLE."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Actually drop detected unused tables (default is dry-run).",
        )

    def handle(self, *args, **options):
        execute = options["execute"]

        expected_tables = {model._meta.db_table for model in apps.get_models()}
        expected_tables.add("django_migrations")

        with connection.cursor() as cursor:
            existing_tables = set(connection.introspection.table_names(cursor))

        unused_tables = sorted(existing_tables - expected_tables)

        if not unused_tables:
            self.stdout.write(self.style.SUCCESS("No unused tables found."))
            return

        self.stdout.write("Unused tables detected:")
        for table in unused_tables:
            self.stdout.write(f"- {table}")

        if not execute:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run mode. Re-run with --execute to drop these tables."
                )
            )
            return

        with connection.cursor() as cursor:
            for table in unused_tables:
                cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')

        self.stdout.write(self.style.SUCCESS(f"Dropped {len(unused_tables)} table(s)."))
