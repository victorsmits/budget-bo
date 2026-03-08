"""Transaction enrichment job — sync Celery worker, no asyncio."""

from datetime import datetime, timedelta
from typing import Any

from celery import Task
from sqlalchemy import select

from app.core.database import get_worker_session
from app.models.models import Transaction
from app.services.enrichment_memory import (
    apply_rule_to_transaction,
    get_rule_for_label,
    upsert_rule_from_transaction,
)
from app.services.enrichment_pipeline import run_enrichment_pipeline
from app.services.ollama import OllamaService
from worker.celery_app import celery_app


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    time_limit=300,
    soft_time_limit=240,
)
def enrich_single_transaction(
    self: Task,
    transaction_id: str,
) -> dict[str, Any]:
    """Enrichit une transaction avec l'IA Ollama. 100% synchrone."""
    with get_worker_session() as session:
        tx = session.get(Transaction, transaction_id)

        if not tx:
            return {"status": "error", "transaction_id": transaction_id, "error": "Not found"}

        if tx.enriched_at:
            return {
                "status": "skipped",
                "transaction_id": transaction_id,
                "reason": "Already enriched",
            }

        raw_label = tx.raw_label  # lu avant tout appel externe

        try:
            learned_rule = get_rule_for_label(session, tx.user_id, raw_label)

            if learned_rule is not None:
                apply_rule_to_transaction(tx, learned_rule)
                learned_rule.usage_count += 1
                learned_rule.updated_at = datetime.utcnow()
            else:
                ollama_service = OllamaService()
                signed_amount = -float(tx.amount) if tx.is_expense else float(tx.amount)

                pipeline_result = run_enrichment_pipeline(
                    raw_label=raw_label,
                    signed_amount=signed_amount,
                    initial_is_expense=tx.is_expense,
                    ollama_service=ollama_service,
                )

                tx.cleaned_label = pipeline_result.cleaned_label
                tx.merchant_name = pipeline_result.merchant_name
                tx.ai_confidence = pipeline_result.confidence
                tx.ai_category_reasoning = pipeline_result.reasoning
                tx.is_expense = pipeline_result.is_expense
                tx.category = pipeline_result.category
                tx.enriched_at = datetime.utcnow()
                upsert_rule_from_transaction(session, tx)

            session.commit()

            return {
                "status":        "success",
                "transaction_id": str(tx.id),
                "task_id":        self.request.id,
                "cleaned_label":  tx.cleaned_label,
                "category":       tx.category.value,
                "confidence":     tx.ai_confidence,
            }

        except Exception as exc:
            session.rollback()
            raise self.retry(exc=exc) from exc


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    time_limit=600,
    soft_time_limit=480,
)
def enrich_user_transactions(
    self: Task,
    user_id: str,
    days_back: int = 7,
    max_transactions: int = 100,
) -> dict[str, Any]:
    """Enfile les tâches d'enrichissement pour un utilisateur."""
    from celery import group

    since_date = datetime.now() - timedelta(days=days_back)

    with get_worker_session() as session:
        rows = session.execute(
            select(Transaction.id).where(
                Transaction.user_id == user_id,
                Transaction.enriched_at.is_(None),
                Transaction.date >= since_date.date(),
            ).limit(max_transactions)
        ).scalars().all()

    if not rows:
        return {"status": "no_transactions", "user_id": user_id, "queued": 0}

    transaction_ids = [str(row) for row in rows]
    result = group(enrich_single_transaction.s(tx_id) for tx_id in transaction_ids).apply_async()

    return {
        "status":        "queued",
        "user_id":        user_id,
        "batch_task_id":  self.request.id,
        "group_task_id":  result.id,
        "queued":         len(transaction_ids),
        "transactions":   transaction_ids,
    }
