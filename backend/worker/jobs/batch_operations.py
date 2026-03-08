"""Batch operations — orchestration sync des jobs parallèles."""

from datetime import datetime, timedelta
from typing import Any

from celery import Task, group
from celery.exceptions import MaxRetriesExceededError
from sqlalchemy import select

from app.core.database import get_worker_session
from app.models.models import BankCredential, Transaction
from worker.celery_app import celery_app


@celery_app.task(
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    time_limit=300,
)
def sync_all_credentials(
    self: Task,
    days_back: int = 1,
) -> dict[str, Any]:
    """Queue les sync tasks pour toutes les credentials actives."""
    from worker.jobs.sync_transactions import sync_credential_transactions

    try:
        with get_worker_session() as session:
            credentials = session.execute(
                select(BankCredential).where(BankCredential.is_active == True)
            ).scalars().all()

            credential_ids = [str(c.id) for c in credentials]

        if not credential_ids:
            return {"status": "no_credentials", "queued": 0}

        result = group(
            sync_credential_transactions.s(cred_id, days_back)
            for cred_id in credential_ids
        ).apply_async()

        return {
            "status": "queued",
            "batch_task_id": self.request.id,
            "group_task_id": result.id,
            "credentials_count": len(credential_ids),
            "credentials": credential_ids,
        }

    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise MaxRetriesExceededError(str(exc))


@celery_app.task(
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    time_limit=600,
)
def enrich_all_transactions(
    self: Task,
    days_back: int = 7,
    batch_size: int = 500,
) -> dict[str, Any]:
    """Queue les enrichment tasks pour toutes les transactions non enrichies."""
    from worker.jobs.enrich_transactions import enrich_single_transaction

    since_date = datetime.now() - timedelta(days=days_back)

    try:
        with get_worker_session() as session:
            transaction_ids = session.execute(
                select(Transaction.id)
                .where(
                    Transaction.enriched_at.is_(None),
                    Transaction.date >= since_date.date(),
                )
                .limit(batch_size)
            ).scalars().all()

            transaction_ids = [str(tx_id) for tx_id in transaction_ids]

        if not transaction_ids:
            return {"status": "no_transactions", "queued": 0}

        result = group(
            enrich_single_transaction.s(tx_id)
            for tx_id in transaction_ids
        ).apply_async()

        return {
            "status": "queued",
            "batch_task_id": self.request.id,
            "group_task_id": result.id,
            "transactions_count": len(transaction_ids),
            "transactions": transaction_ids,
        }

    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise MaxRetriesExceededError(str(exc))


@celery_app.task(bind=True)
def trigger_enrichment_after_sync(
    self: Task,
    user_id: str,
    days_back: int = 7,
) -> dict[str, Any]:
    """Déclenche l'enrichissement pour un user après son sync."""
    from worker.jobs.enrich_transactions import enrich_user_transactions

    result = enrich_user_transactions.delay(user_id, days_back)

    return {
        "status": "enrichment_triggered",
        "user_id": user_id,
        "enrichment_task_id": result.id,
    }