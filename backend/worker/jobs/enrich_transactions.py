"""Transaction enrichment job — sync Celery worker, no asyncio."""

from datetime import datetime, timedelta
from typing import Any

from celery import Task
from sqlalchemy import select

from app.core.database import get_worker_session
from app.models.models import Transaction, TransactionCategory
from app.services.enrichment_memory import (
    apply_rule_to_transaction,
    get_rule_for_label,
    upsert_rule_from_transaction,
)
from app.services.enrichment_intelligence import (
    infer_category_from_text,
    normalize_consumer_merchant,
)
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
            return {"status": "skipped", "transaction_id": transaction_id, "reason": "Already enriched"}

        raw_label = tx.raw_label  # lu avant tout appel externe

        try:
            learned_rule = get_rule_for_label(session, tx.user_id, raw_label)

            if learned_rule is not None:
                apply_rule_to_transaction(tx, learned_rule)
                learned_rule.usage_count += 1
                learned_rule.updated_at = datetime.utcnow()
            else:
                ollama_service = OllamaService()
                normalization = ollama_service.normalize_label(raw_label)

                normalized_merchant = normalize_consumer_merchant(
                    normalization.get("merchant_name"),
                    normalization.get("cleaned_label", raw_label),
                    raw_label,
                )
                tx.cleaned_label = normalization.get("cleaned_label", raw_label)
                tx.merchant_name = normalized_merchant

                categorization = ollama_service.categorize_transaction(
                    label=tx.cleaned_label,
                    amount=float(tx.amount),
                    merchant_hint=tx.merchant_name,
                )

                rule_based_category = infer_category_from_text(
                    label=tx.cleaned_label,
                    merchant=tx.merchant_name or "",
                    amount=float(tx.amount),
                )
                selected_category = rule_based_category or categorization.get("category") or normalization.get("category")

                tx.ai_confidence = max(
                    float(normalization.get("confidence", 0.0)),
                    float(categorization.get("confidence", 0.0)),
                )
                tx.ai_category_reasoning = categorization.get("reasoning", "")
                tx.is_expense = bool(categorization.get("is_expense", tx.amount < 0))
                tx.category = _map_category(str(selected_category))
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
            raise self.retry(exc=exc)


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


def _map_category(category_str: str) -> TransactionCategory:
    try:
        return TransactionCategory[category_str.upper()]
    except KeyError:
        return TransactionCategory.OTHER