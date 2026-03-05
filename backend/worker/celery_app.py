"""Celery application configuration."""

from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "budget_bo",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["worker.tasks.sync_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # Soft limit 55 min
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Retry configuration for bank timeouts
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    # Result expiry
    result_expires=3600,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "daily-transaction-sync": {
        "task": "worker.tasks.sync_tasks.sync_all_users_transactions",
        "schedule": 86400.0,  # Daily
    },
}
