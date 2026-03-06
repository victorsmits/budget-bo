"""Celery application configuration."""

import os
from celery import Celery
from celery.signals import setup_logging

# Create Celery app
celery_app = Celery(
    "budget_bo",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
    include=["worker.tasks"],
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max
    worker_prefetch_multiplier=1,
    result_expires=3600,  # Results expire after 1 hour
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "daily-sync": {
        "task": "worker.tasks.sync_all_users",
        "schedule": 86400.0,  # Every 24 hours
        "args": (),
    },
}


@setup_logging.connect
def config_loggers(*args, **kwargs):
    """Configure logging for Celery."""
    pass  # Use default logging configuration
