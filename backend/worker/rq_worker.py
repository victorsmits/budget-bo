#!/usr/bin/env python3
"""RQ Worker - Simple worker for running background jobs."""

import os
import sys

# Add /app to path
sys.path.insert(0, "/app")

from redis import Redis
from rq import Worker, Queue, Connection

redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

if __name__ == "__main__":
    with Connection(redis_conn):
        queues = [Queue("sync"), Queue("default")]
        worker = Worker(queues)
        worker.work()
