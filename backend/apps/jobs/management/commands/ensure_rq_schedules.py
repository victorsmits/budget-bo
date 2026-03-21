from __future__ import annotations

import os

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_rq import get_scheduler

from apps.jobs.batch import sync_all_credentials


class Command(BaseCommand):
    help = "Ensure recurring RQ schedules are present in Redis."

    def handle(self, *args, **options):
        interval_seconds = int(os.getenv("SYNC_INTERVAL_SECONDS", "3600"))
        days_back = int(os.getenv("SYNC_DAYS_BACK", "1"))

        scheduler = get_scheduler("sync")

        existing = False
        for job in scheduler.get_jobs():
            func_name = getattr(job, "func_name", "") or ""
            description = getattr(job, "description", "") or ""
            if func_name.endswith("sync_all_credentials") or description == "sync_all_credentials":
                existing = True
                break

        if existing:
            self.stdout.write(self.style.SUCCESS("RQ schedule already present"))
            return

        scheduler.schedule(
            scheduled_time=timezone.now(),
            func=sync_all_credentials,
            kwargs={"days_back": days_back},
            interval=interval_seconds,
            repeat=None,
            description="sync_all_credentials",
        )

        self.stdout.write(self.style.SUCCESS("RQ schedule created"))
