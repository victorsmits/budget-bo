"""Celery application configuration with separate queues for sync and enrichment jobs."""

import os
from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging

# Create Celery app with dedicated queues
celery_app = Celery(
    "budget_bo",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
    include=[
        "worker.jobs.sync_transactions",
        "worker.jobs.enrich_transactions",
        "worker.jobs.batch_operations",
    ],
)

# Configuration optimized for parallel execution
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes max for long sync operations
    task_soft_time_limit=1500,  # Soft limit 25 minutes
    worker_prefetch_multiplier=1,  # Don't prefetch - allow parallel processing
    worker_concurrency=int(os.getenv("CELERY_WORKER_CONCURRENCY", "4")),
    result_expires=7200,  # Results expire after 2 hours
    task_acks_late=True,  # Acknowledge after task completes (safer for long tasks)
    task_reject_on_worker_lost=True,  # Requeue if worker dies
    task_default_queue="default",
    task_routes={
        "worker.jobs.sync_transactions.*": {"queue": "sync"},
        "worker.jobs.batch_operations.sync_all_credentials": {"queue": "sync"},
        "worker.jobs.enrich_transactions.*": {"queue": "enrich"},
        "worker.jobs.batch_operations.enrich_all_transactions": {"queue": "enrich"},
    },
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "daily-sync-all-credentials": {
        "task": "worker.jobs.batch_operations.sync_all_credentials",
        "schedule": crontab(hour=2, minute=0),
        "args": (),
        "options": {"queue": "sync"},
    },
    "daily-enrich-all-transactions": {
        "task": "worker.jobs.batch_operations.enrich_all_transactions",
        "schedule": crontab(hour=3, minute=0),
        "args": (),
        "options": {"queue": "enrich"},
    },
}


@setup_logging.connect
def config_loggers(*args, **kwargs):
    """Configure logging for Celery."""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
