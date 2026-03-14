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
    has_explicit_income_signal,
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
    time_limit=420,
    soft_time_limit=360,
)
def enrich_transactions_batch(
    self: Task,
    transaction_ids: list[str],
) -> dict[str, Any]:
    """Enrichit un lot de transactions pour réduire les IO + appels LLM."""
    if not transaction_ids:
        return {"status": "no_transactions", "processed": 0, "succeeded": 0, "skipped": 0}

    with get_worker_session() as session:
        rows = session.execute(
            select(Transaction).where(Transaction.id.in_(transaction_ids))
        ).scalars().all()

        if not rows:
            return {"status": "no_transactions", "processed": 0, "succeeded": 0, "skipped": 0}

        ollama_service = OllamaService()
        to_enrich: list[Transaction] = []
        skipped = 0

        for tx in rows:
            if tx.enriched_at:
                skipped += 1
                continue

            learned_rule = get_rule_for_label(session, tx.user_id, tx.raw_label)
            if learned_rule is not None:
                apply_rule_to_transaction(tx, learned_rule)
                learned_rule.usage_count += 1
                learned_rule.updated_at = datetime.utcnow()
                continue

            to_enrich.append(tx)

        normalizations: list[dict[str, Any]] = []
        if to_enrich:
            normalizations = ollama_service.normalize_labels_batch([tx.raw_label for tx in to_enrich])

        llm_candidates: list[dict[str, Any]] = []
        llm_indexes: list[int] = []

        for idx, tx in enumerate(to_enrich):
            normalization = normalizations[idx]
            raw_label = tx.raw_label

            normalized_merchant = normalize_consumer_merchant(
                normalization.get("merchant_name"),
                normalization.get("cleaned_label", ""),
                raw_label,
            )
            tx.cleaned_label = normalization.get("cleaned_label", "")
            tx.merchant_name = normalized_merchant

            rule_based_category = infer_category_from_text(
                label=tx.cleaned_label or tx.merchant_name or raw_label,
                merchant=tx.merchant_name or "",
                amount=float(tx.amount),
            )
            normalized_category = str(normalization.get("category", "other")).lower()

            needs_llm_categorization = (
                rule_based_category is None
                and normalized_category in {"other", "shopping", "income"}
            )

            signed_amount = -float(tx.amount) if tx.is_expense else float(tx.amount)

            categorization: dict[str, Any] = {}
            if needs_llm_categorization:
                llm_indexes.append(idx)
                llm_candidates.append(
                    {
                        "label": tx.cleaned_label or tx.merchant_name or raw_label,
                        "amount": signed_amount,
                        "merchant_hint": tx.merchant_name,
                    }
                )

            tx._bb_rule_based_category = rule_based_category  # type: ignore[attr-defined]
            tx._bb_normalized_category = normalized_category  # type: ignore[attr-defined]
            tx._bb_normalization_confidence = float(normalization.get("confidence", 0.0))  # type: ignore[attr-defined]
            tx._bb_categorization = categorization  # type: ignore[attr-defined]

        llm_results: list[dict[str, Any]] = []
        if llm_candidates:
            llm_results = ollama_service.categorize_transactions_batch(llm_candidates)

        for mapped_idx, result in zip(llm_indexes, llm_results):
            to_enrich[mapped_idx]._bb_categorization = result  # type: ignore[attr-defined]

        for tx in to_enrich:
            rule_based_category = tx._bb_rule_based_category  # type: ignore[attr-defined]
            normalized_category = tx._bb_normalized_category  # type: ignore[attr-defined]
            categorization = tx._bb_categorization  # type: ignore[attr-defined]

            selected_category = (
                rule_based_category
                or categorization.get("category")
                or normalized_category
            )

            if str(selected_category) == "income" and not has_explicit_income_signal(
                tx.cleaned_label or tx.merchant_name or tx.raw_label,
                tx.merchant_name or "",
            ):
                fallback_category = rule_based_category or normalized_category
                if fallback_category and str(fallback_category) != "income":
                    selected_category = fallback_category
                else:
                    selected_category = "other"

            tx.ai_confidence = max(
                float(tx._bb_normalization_confidence),  # type: ignore[attr-defined]
                float(categorization.get("confidence", 0.0)),
            )
            tx.ai_category_reasoning = categorization.get(
                "reasoning",
                "Category inferred from normalization/rules",
            )
            tx.is_expense = bool(categorization.get("is_expense", tx.is_expense))
            tx.category = _map_category(str(selected_category))
            tx.enriched_at = datetime.utcnow()
            upsert_rule_from_transaction(session, tx)

        session.commit()

        return {
            "status": "success",
            "task_id": self.request.id,
            "processed": len(rows),
            "succeeded": len(rows) - skipped,
            "skipped": skipped,
            "transactions": [str(tx.id) for tx in rows],
        }


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
    """Backward-compatible wrapper: enrich one transaction via batch task."""
    return enrich_transactions_batch.run([transaction_id])


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
    chunk_size: int = 20,
) -> dict[str, Any]:
    """Enfile des lots d'enrichissement pour un utilisateur."""
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
    chunk_size = max(1, min(chunk_size, 50))
    chunks = [
        transaction_ids[i:i + chunk_size]
        for i in range(0, len(transaction_ids), chunk_size)
    ]

    result = group(enrich_transactions_batch.s(chunk) for chunk in chunks).apply_async()

    return {
        "status": "queued",
        "user_id": user_id,
        "batch_task_id": self.request.id,
        "group_task_id": result.id,
        "queued": len(transaction_ids),
        "batches": len(chunks),
        "chunk_size": chunk_size,
        "transactions": transaction_ids,
    }


def _map_category(category_str: str) -> TransactionCategory:
    try:
        return TransactionCategory[category_str.upper()]
    except KeyError:
        return TransactionCategory.OTHER
