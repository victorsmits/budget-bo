"""Batch operations job - orchestrates parallel sync and enrichment across all users.

This module contains high-level orchestration tasks that queue multiple
parallel sync or enrichment jobs for all users/credentials.
"""

import asyncio
from typing import Any

from celery import Task
from celery.exceptions import MaxRetriesExceededError
from sqlalchemy import select

from app.core.database import create_worker_session
from app.models.models import BankCredential, Transaction
from worker.celery_app import celery_app


@celery_app.task(
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    time_limit=300,  # 5 minutes to queue all syncs
)
def sync_all_credentials(
    self: Task,
    days_back: int = 1,
) -> dict[str, Any]:
    """
    Queue sync tasks for all active bank credentials.

    This creates parallel sync tasks that each run in the 'sync' queue,
    allowing multiple bank synchronizations to happen simultaneously.
    """
    try:
        return asyncio.run(_async_sync_all_credentials(days_back, self.request.id))
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise MaxRetriesExceededError(
            f"Failed to queue sync jobs after {self.max_retries} retries: {exc}"
        )


async def _async_sync_all_credentials(
    days_back: int,
    task_id: str | None,
) -> dict[str, Any]:
    """Queue parallel sync tasks for all active credentials."""
    from celery import group
    from worker.jobs.sync_transactions import sync_credential_transactions

    session = create_worker_session()
    try:
        result = await session.execute(
            select(BankCredential).where(BankCredential.is_active == True)
        )
        credentials = result.scalars().all()

        if not credentials:
            return {
                "status": "no_credentials",
                "queued": 0,
            }

        # Create parallel sync tasks - one per credential
        sync_tasks = [
            sync_credential_transactions.s(str(c.id), days_back)
            for c in credentials
        ]

        # Execute all syncs in parallel using Celery group
        # Each sync runs independently and can be processed by different workers
        job = group(sync_tasks)
        async_result = job.apply_async()

        return {
            "status": "queued",
            "batch_task_id": task_id,
            "group_task_id": async_result.id,
            "credentials_count": len(credentials),
            "credentials": [str(c.id) for c in credentials],
        }
    finally:
        engine = session.bind
        await session.close()
        await engine.dispose()


@celery_app.task(
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    time_limit=600,  # 10 minutes to queue all enrichments
)
def enrich_all_transactions(
    self: Task,
    days_back: int = 7,
    batch_size: int = 500,
) -> dict[str, Any]:
    """
    Queue enrichment tasks for all unenriched transactions.

    This creates parallel enrichment tasks that run in the 'enrich' queue,
    allowing AI processing to happen simultaneously across transactions.
    """
    try:
        return asyncio.run(
            _async_enrich_all_transactions(days_back, batch_size, self.request.id)
        )
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise MaxRetriesExceededError(
            f"Failed to queue enrichment jobs after {self.max_retries} retries: {exc}"
        )


async def _async_enrich_all_transactions(
    days_back: int,
    batch_size: int,
    task_id: str | None,
) -> dict[str, Any]:
    """Queue parallel enrichment tasks for all unenriched transactions."""
    from datetime import datetime, timedelta

    from celery import group
    from worker.jobs.enrich_transactions import enrich_single_transaction

    session = create_worker_session()
    try:
        since_date = datetime.now() - timedelta(days=days_back)

        # Fetch unenriched transactions
        result = await session.execute(
            select(Transaction)
            .where(
                Transaction.enriched_at.is_(None),
                Transaction.date >= since_date.date(),
            )
            .limit(batch_size)
        )
        transactions = result.scalars().all()

        if not transactions:
            return {
                "status": "no_transactions",
                "queued": 0,
            }

        # Create parallel enrichment tasks
        enrichment_tasks = [
            enrich_single_transaction.s(str(tx.id))
            for tx in transactions
        ]

        # Execute all enrichments in parallel
        job = group(enrichment_tasks)
        async_result = job.apply_async()

        return {
            "status": "queued",
            "batch_task_id": task_id,
            "group_task_id": async_result.id,
            "transactions_count": len(transactions),
            "transactions": [str(tx.id) for tx in transactions],
        }
    finally:
        engine = session.bind
        await session.close()
        await engine.dispose()


@celery_app.task(bind=True)
def trigger_enrichment_after_sync(
    self: Task,
    user_id: str,
    days_back: int = 7,
) -> dict[str, Any]:
    """
    Trigger enrichment for a user after their sync completes.

    This task chains from sync completion to start enrichment.
    """
    from worker.jobs.enrich_transactions import enrich_user_transactions

    # Queue enrichment for this user's new transactions
    result = enrich_user_transactions.delay(user_id, days_back)

    return {
        "status": "enrichment_triggered",
        "user_id": user_id,
        "enrichment_task_id": result.id,
    }
