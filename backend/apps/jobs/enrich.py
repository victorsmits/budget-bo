import logging
import re
from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.transactions.models import EnrichmentRule, Transaction, TransactionCategory
from services.enrichment_intelligence import (
    has_explicit_income_signal,
    normalize_consumer_merchant,
)
from services.gemini_enrichment import (
    GeminiDailyLimitError,
    GeminiEnrichmentService,
    TransactionInput,
)

logger = logging.getLogger(__name__)


NOISE_TOKENS = {
    "carte",
    "cb",
    "prlv",
    "prlvm",
    "prelevement",
    "prelev",
    "sepa",
    "vir",
    "virement",
    "paiement",
    "achat",
}


def _label_fingerprint(raw_label: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", raw_label.lower())
    cleaned = re.sub(r"\b\d+[a-z]*\b", " ", cleaned)
    tokens = [token for token in cleaned.split() if token not in NOISE_TOKENS and len(token) > 2]
    if not tokens:
        return "unknown"
    return " ".join(tokens[:8])


def _get_matching_rule(transaction: Transaction) -> EnrichmentRule | None:
    fingerprint = _label_fingerprint(transaction.raw_label)
    legacy_fingerprint = transaction.raw_label.lower().strip()
    return (
        EnrichmentRule.objects.filter(
            user=transaction.user,
            label_fingerprint__in=[fingerprint, legacy_fingerprint],
        )
        .order_by("-updated_at")
        .first()
    )


def _apply_rule(transaction: Transaction, rule: EnrichmentRule) -> None:
    transaction.enrichment_rule = rule
    transaction.ai_confidence = 1.0
    if hasattr(transaction, "ai_category_reasoning"):
        transaction.ai_category_reasoning = "Learned from previous user correction"
    transaction.enriched_at = timezone.now()


def _upsert_rule_from_transaction(transaction: Transaction) -> EnrichmentRule:
    fingerprint = _label_fingerprint(transaction.raw_label)
    rule, created = EnrichmentRule.objects.get_or_create(
        user=transaction.user,
        label_fingerprint=fingerprint,
        defaults={
            "cleaned_label": transaction.cleaned_label or "",
            "merchant_name": transaction.merchant_name,
            "category": transaction.category,
            "usage_count": 1,
            "learned_from_transaction": transaction,
        },
    )
    if not created:
        rule.cleaned_label = transaction.cleaned_label or ""
        rule.merchant_name = transaction.merchant_name
        rule.category = transaction.category
        rule.usage_count = (rule.usage_count or 0) + 1
        rule.learned_from_transaction = transaction
        rule.save(
            update_fields=[
                "cleaned_label",
                "merchant_name",
                "category",
                "usage_count",
                "learned_from_transaction",
                "updated_at",
            ]
        )

    transaction.enrichment_rule = rule
    return rule


def _persist_transaction(transaction: Transaction) -> None:
    transaction.save(
        update_fields=[
            "cleaned_label",
            "merchant_name",
            "category",
            "is_expense",
            "enrichment_rule",
            "ai_confidence",
            "enriched_at",
            "updated_at",
        ]
    )

def _serialize_ai_result(result: Any) -> dict[str, Any]:
    return {
        "cleaned_label": result.cleaned_label,
        "merchant_name": result.merchant_name,
        "category": result.category,
        "is_expense": result.is_expense,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
    }


def _serialize_transaction_state(transaction: Transaction) -> dict[str, Any]:
    return {
        "transaction_id": str(transaction.id),
        "cleaned_label": transaction.display_label,
        "merchant_name": transaction.display_merchant,
        "category": transaction.display_category,
        "is_expense": transaction.is_expense,
        "ai_confidence": transaction.ai_confidence,
        "ai_category_reasoning": getattr(transaction, "ai_category_reasoning", ""),
    }

def _apply_gemini_result(transaction: Transaction, result: Any) -> None:
    transaction.cleaned_label = result.cleaned_label or ""
    merchant = normalize_consumer_merchant(
        result.merchant_name,
        result.cleaned_label,
        transaction.raw_label,
    )
    transaction.merchant_name = merchant

    category = result.category
    has_income_signal = has_explicit_income_signal(
        transaction.raw_label,
        merchant,
    )
    if category == TransactionCategory.INCOME and not has_income_signal:
        category = TransactionCategory.OTHER

    transaction.category = category
    # Guardrail: preserve original debit/credit direction unless we have an explicit income signal.
    # Gemini can over-predict income; transaction direction from bank sync is more reliable.
    if category == TransactionCategory.INCOME and has_income_signal:
        transaction.is_expense = False
    transaction.ai_confidence = result.confidence
    if hasattr(transaction, "ai_category_reasoning"):
        transaction.ai_category_reasoning = result.reasoning
    transaction.enriched_at = timezone.now()


def enrich_single_transaction(transaction_id: str) -> dict:
    transaction = Transaction.objects.select_related("user").get(id=transaction_id)

    rule = _get_matching_rule(transaction)
    if rule is not None:
        _apply_rule(transaction, rule)
        transaction.save(
            update_fields=[
                "enrichment_rule",
                "ai_confidence",
                "enriched_at",
                "updated_at",
            ]
        )
        return {
            "transaction_id": str(transaction_id),
            "status": "enriched_from_cache",
            "transaction": _serialize_transaction_state(transaction),
        }

    service = GeminiEnrichmentService()
    signed_amount = -float(transaction.amount) if transaction.is_expense else float(transaction.amount)
    tx_input = TransactionInput(
        id=str(transaction.id),
        raw_label=transaction.raw_label,
        amount=signed_amount,
        date=transaction.date.isoformat(),
    )

    try:
        result = service.enrich_batch([tx_input])[0]
    except GeminiDailyLimitError:
        logger.warning("Gemini daily limit reached during single enrichment", extra={"transaction_id": str(transaction.id)})
        return {"transaction_id": str(transaction.id), "status": "skipped_daily_limit"}
    except Exception:
        logger.exception("Gemini enrichment failed", extra={"transaction_id": str(transaction.id)})
        return {"transaction_id": str(transaction.id), "status": "error"}

    _apply_gemini_result(transaction, result)
    transaction.save(
        update_fields=[
            "cleaned_label",
            "merchant_name",
            "category",
            "is_expense",
            "enrichment_rule",
            "ai_confidence",
            "enriched_at",
            "updated_at",
        ]
    )
    transaction.enrichment_rule = _upsert_rule_from_transaction(transaction)
    transaction.save(update_fields=["enrichment_rule", "updated_at"])

    return {
        "transaction_id": str(transaction_id),
        "status": "enriched_from_gemini",
        "ai_result": _serialize_ai_result(result),
        "transaction": _serialize_transaction_state(transaction),
    }


def _enrich_transactions(transactions: list[Transaction], user_id: str) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "enriched_from_cache": 0,
        "enriched_from_gemini": 0,
        "errors": 0,
        "skipped": 0,
    }

    to_enrich: list[Transaction] = []
    ai_results: list[dict[str, Any]] = []
    for tx in transactions:
        rule = _get_matching_rule(tx)
        if rule is None:
            to_enrich.append(tx)
            continue

        _apply_rule(tx, rule)
        tx.save(update_fields=["enrichment_rule", "ai_confidence", "enriched_at", "updated_at"])
        stats["enriched_from_cache"] += 1

    max_batch_size = settings.GEMINI_MAX_BATCH_SIZE
    service = GeminiEnrichmentService()

    for idx in range(0, len(to_enrich), max_batch_size):
        batch = to_enrich[idx: idx + max_batch_size]
        payload = [
            TransactionInput(
                id=str(tx.id),
                raw_label=tx.raw_label,
                amount=-float(tx.amount) if tx.is_expense else float(tx.amount),
                date=tx.date.isoformat(),
            )
            for tx in batch
        ]

        try:
            results = service.enrich_batch(payload)
        except GeminiDailyLimitError:
            logger.warning("Gemini daily limit reached during user batch enrichment", extra={"user_id": str(user_id)})
            stats["skipped"] += len(batch)
            continue
        except Exception:
            logger.exception("Gemini batch enrichment failed", extra={"user_id": str(user_id)})
            stats["errors"] += len(batch)
            continue

        result_map = {result.id: result for result in results}
        for tx in batch:
            result = result_map.get(str(tx.id))
            if result is None:
                stats["errors"] += 1
                continue

            _apply_gemini_result(tx, result)
            _persist_transaction(tx)
            ai_results.append(
                {
                    "transaction_id": str(tx.id),
                    "ai_result": _serialize_ai_result(result),
                    "transaction": _serialize_transaction_state(tx),
                }
            )
            try:
                tx.enrichment_rule = _upsert_rule_from_transaction(tx)
                tx.save(update_fields=["enrichment_rule", "updated_at"])
            except Exception:
                logger.exception("Failed to upsert enrichment rule", extra={"transaction_id": str(tx.id), "user_id": str(user_id)})
            stats["enriched_from_gemini"] += 1

    stats["ai_results"] = ai_results
    return stats


def enrich_user_transactions(user_id: str, max_transactions: int = 100) -> dict[str, Any]:
    queryset = (
        Transaction.objects.select_related("user")
        .filter(user_id=user_id, enriched_at__isnull=True)
        .order_by("date")[:max_transactions]
    )
    return _enrich_transactions(list(queryset), user_id)


def enrich_user_transactions_chunk(user_id: str, transaction_ids: list[str]) -> dict[str, Any]:
    queryset = (
        Transaction.objects.select_related("user")
        .filter(user_id=user_id, enriched_at__isnull=True, id__in=transaction_ids)
        .order_by("date")
    )
    stats = _enrich_transactions(list(queryset), user_id)
    stats["worker"] = "chunk"
    return stats
