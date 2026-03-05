#!/usr/bin/env python3
"""RQ Scheduler - Cron jobs scheduler."""

import os
import sys

# Add /app to path
sys.path.insert(0, "/app")

from redis import Redis
from rq_scheduler import Scheduler

redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

if __name__ == "__main__":
    scheduler = Scheduler(connection=redis_conn)
    
    # Schedule daily sync at 6 AM
    from datetime import datetime
    from worker.rq_jobs import sync_all_users_job
    
    scheduler.schedule(
        scheduled_time=datetime.utcnow().replace(hour=6, minute=0, second=0),
        func=sync_all_users_job,
        interval=86400,  # Every 24 hours
        repeat=None,  # Forever
    )
    
    print("Scheduler started. Daily sync scheduled for 6:00 AM.")
    scheduler.run()
