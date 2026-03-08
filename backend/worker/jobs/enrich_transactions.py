"""Transaction enrichment job - dedicated file for AI enrichment operations.

This module contains tasks for enriching transactions with AI-powered
categorization and label normalization. These tasks run in the 'enrich'
queue and can execute fully in parallel.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from celery import Task
from celery.exceptions import MaxRetriesExceededError
from sqlalchemy import select

from app.core.database import create_worker_session
from app.models.models import Transaction, TransactionCategory
from app.services.ollama import OllamaService  # Import class directly, not singleton
from worker.celery_app import celery_app


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    time_limit=300,  # 5 minutes per transaction
    soft_time_limit=240,
)
def enrich_single_transaction(
    self: Task,
    transaction_id: str,
) -> dict[str, Any]:
    """
    Enrich a single transaction using local AI (Ollama).

    This task runs in the 'enrich' queue and can process multiple
transactions in parallel across different workers.
    """
    try:
        return asyncio.run(_async_enrich_transaction(transaction_id, self.request.id))
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise MaxRetriesExceededError(
            f"Failed to enrich transaction after {self.max_retries} retries: {exc}"
        )


async def _async_enrich_transaction(
    transaction_id: str,
    task_id: str | None,
) -> dict[str, Any]:
    """Async implementation of single transaction enrichment."""
    session = create_worker_session()
    try:
        # Fetch transaction
        result = await session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        tx = result.scalar_one_or_none()

        if not tx:
            return {
                "status": "error",
                "transaction_id": transaction_id,
                "error": "Transaction not found",
            }

        if tx.enriched_at:
            return {
                "status": "skipped",
                "transaction_id": transaction_id,
                "reason": "Already enriched",
            }

        # Create AI service fresh for this task (avoid async loop issues)
        ollama = OllamaService()

        try:
            # Normalize label with AI
            normalization = await ollama.normalize_label(tx.raw_label)

            tx.cleaned_label = normalization["cleaned_label"]
            tx.merchant_name = normalization["merchant_name"]
            tx.ai_confidence = normalization["confidence"]

            # Map category
            category_str = normalization["category"].upper()
            try:
                tx.category = TransactionCategory[category_str]
            except KeyError:
                tx.category = TransactionCategory.OTHER

            tx.enriched_at = datetime.utcnow()
            await session.commit()

            return {
                "status": "success",
                "transaction_id": transaction_id,
                "task_id": task_id,
                "cleaned_label": tx.cleaned_label,
                "category": tx.category.value,
                "confidence": tx.ai_confidence,
            }

        except Exception as e:
            await session.rollback()
            print(f"Error enriching transaction {tx.id}: {e}")
            raise
    finally:
        engine = session.bind
        await session.close()
        await engine.dispose()


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    time_limit=600,  # 10 minutes for batch
    soft_time_limit=480,
)
def enrich_user_transactions(
    self: Task,
    user_id: str,
    days_back: int = 7,
    max_transactions: int = 100,
) -> dict[str, Any]:
    """
    Queue enrichment tasks for all unenriched user transactions.

    This creates parallel tasks for each transaction to be enriched.
    """
    try:
        return asyncio.run(
            _async_queue_user_enrichment(user_id, days_back, max_transactions, self.request.id)
        )
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise MaxRetriesExceededError(
            f"Failed to queue enrichment after {self.max_retries} retries: {exc}"
        )


async def _async_queue_user_enrichment(
    user_id: str,
    days_back: int,
    max_transactions: int,
    task_id: str | None,
) -> dict[str, Any]:
    """Queue individual enrichment tasks for user's transactions."""
    from celery import group
    from worker.jobs.enrich_transactions import enrich_single_transaction

    session = create_worker_session()
    try:
        since_date = datetime.now() - timedelta(days=days_back)

        # Fetch unenriched transactions
        result = await session.execute(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.enriched_at.is_(None),
                Transaction.date >= since_date.date(),
            )
            .limit(max_transactions)
        )
        transactions = result.scalars().all()

        if not transactions:
            return {
                "status": "no_transactions",
                "user_id": user_id,
                "queued": 0,
            }

        # Create parallel enrichment tasks
        enrichment_tasks = [
            enrich_single_transaction.s(str(tx.id))
            for tx in transactions
        ]

        # Execute in parallel using Celery group
        job = group(enrichment_tasks)
        async_result = job.apply_async()

        return {
            "status": "queued",
            "user_id": user_id,
            "batch_task_id": task_id,
            "group_task_id": async_result.id,
            "queued": len(transactions),
            "transactions": [str(tx.id) for tx in transactions],
        }
    finally:
        engine = session.bind
        await session.close()
        await engine.dispose()
