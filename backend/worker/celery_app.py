"""Celery application configuration with separate queues for sync and enrichment jobs."""

import logging
import os

from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging

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

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Time
    timezone="UTC",
    enable_utc=True,

    # Tracking
    task_track_started=True,

    # Timeouts — jobs longs (Ollama peut prendre plusieurs minutes)
    task_time_limit=1800,       # 30 min hard limit
    task_soft_time_limit=1500,  # 25 min soft limit

    # Worker — optimisé pour jobs longs
    worker_concurrency=int(os.getenv("CELERY_WORKER_CONCURRENCY", "8")),
    worker_prefetch_multiplier=1,       # 1 job à la fois par worker
    worker_max_tasks_per_child=50,      # recycle après 50 jobs (évite les memory leaks)

    # Fiabilité
    task_acks_late=True,                # ack après succès, pas avant
    task_reject_on_worker_lost=True,    # re-queue si le worker crash

    # Résultats
    result_expires=7200,                # 2h

    # Queues
    task_default_queue="default",
    task_routes={
        "worker.jobs.sync_transactions.*":                      {"queue": "sync"},
        "worker.jobs.batch_operations.sync_all_credentials":    {"queue": "sync"},
        "worker.jobs.enrich_transactions.*":                    {"queue": "enrich"},
        "worker.jobs.batch_operations.enrich_all_transactions": {"queue": "enrich"},
    },
)

celery_app.conf.beat_schedule = {
    "daily-sync-all-credentials": {
        "task": "worker.jobs.batch_operations.sync_all_credentials",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "sync"},
    },
    "daily-enrich-all-transactions": {
        "task": "worker.jobs.batch_operations.enrich_all_transactions",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "enrich"},
    },
}


@setup_logging.connect
def config_loggers(*args, **kwargs):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )