"""RQ (Redis Queue) job queue module."""

import os
from redis import Redis
from rq import Queue
from rq_scheduler import Scheduler

# Redis connection
redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

# Default queue
default_queue = Queue("default", connection=redis_conn)

# High priority queue for sync jobs
sync_queue = Queue("sync", connection=redis_conn)

# Scheduler for cron jobs
scheduler = Scheduler(queue=default_queue, connection=redis_conn)


def enqueue_sync_transactions(user_id: str, credential_id: str, days_back: int = 30):
    """Enqueue a bank sync job."""
    from worker.rq_jobs import sync_transactions_job
    return sync_queue.enqueue(
        sync_transactions_job,
        user_id,
        credential_id,
        days_back,
        job_timeout="10m",
        failure_ttl=86400,
    )


def enqueue_enrich_transactions(user_id: str, days_back: int = 30):
    """Enqueue a transaction enrichment job."""
    from worker.rq_jobs import enrich_transactions_job
    return default_queue.enqueue(
        enrich_transactions_job,
        user_id,
        days_back,
        job_timeout="5m",
        failure_ttl=86400,
    )


def schedule_daily_sync():
    """Schedule daily sync for all users."""
    from worker.rq_jobs import sync_all_users_job
    scheduler.schedule(
        scheduled_time=datetime.utcnow(),
        func=sync_all_users_job,
        interval=86400,  # 24 hours
        repeat=None,  # Forever
    )
