"""High-reliability transaction enrichment pipeline with confidence calibration."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.models import TransactionCategory
from app.services.ai_constants import VALID_CATEGORIES
from app.services.enrichment_intelligence import (
    has_explicit_income_signal,
    infer_category_from_text,
    normalize_consumer_merchant,
)
from app.services.ollama import OllamaService


@dataclass
class EnrichmentPipelineResult:
    """Final enriched payload produced by the pipeline."""

    cleaned_label: str
    merchant_name: str
    category: TransactionCategory
    is_expense: bool
    confidence: float
    reasoning: str


def run_enrichment_pipeline(
    *,
    raw_label: str,
    signed_amount: float,
    initial_is_expense: bool,
    ollama_service: OllamaService,
) -> EnrichmentPipelineResult:
    """Run a multi-step enrichment process optimized for reliability and explainability."""
    normalization = ollama_service.normalize_label(raw_label)

    cleaned_label = normalization.get("cleaned_label", "") or ""
    merchant_name = normalize_consumer_merchant(
        normalization.get("merchant_name"),
        cleaned_label,
        raw_label,
    )

    text_for_category = cleaned_label or merchant_name or raw_label

    heuristic_category = infer_category_from_text(
        label=text_for_category,
        merchant=merchant_name,
        amount=signed_amount,
    )

    needs_llm_categorization = (
        heuristic_category is None
        and str(normalization.get("category", "other")) in {"other", "shopping", "income"}
    )

    categorization: dict[str, object] = {}
    if needs_llm_categorization:
        categorization = ollama_service.categorize_transaction(
            label=text_for_category,
            amount=signed_amount,
            merchant_hint=merchant_name,
        )

    llm_category = _safe_category(normalization.get("category"))
    second_pass_category = _safe_category(categorization.get("category"))
    selected_category = heuristic_category or second_pass_category or llm_category

    if selected_category == "income" and not has_explicit_income_signal(
        text_for_category,
        merchant_name,
    ):
        # Fintech-grade guardrail: a positive amount never implies income by itself.
        selected_category = heuristic_category or (
            llm_category if llm_category != "income" else "other"
        )

    final_is_expense = bool(categorization.get("is_expense", initial_is_expense))
    confidence = _calibrate_confidence(
        raw_label=raw_label,
        normalization_confidence=float(normalization.get("confidence", 0.5)),
        categorization_confidence=float(categorization.get("confidence", 0.0)),
        heuristic_category=heuristic_category,
        selected_category=selected_category,
        llm_category=llm_category,
        second_pass_category=second_pass_category,
    )

    reasoning_parts = [
        f"source=llm_normalization({llm_category})",
        f"source=heuristic({heuristic_category or 'none'})",
    ]
    if categorization:
        reasoning_parts.append(f"source=llm_categorization({second_pass_category})")
        if model_reasoning := str(categorization.get("reasoning", "")).strip():
            reasoning_parts.append(f"llm_reasoning={model_reasoning}")

    return EnrichmentPipelineResult(
        cleaned_label=cleaned_label,
        merchant_name=merchant_name,
        category=_map_category(selected_category),
        is_expense=final_is_expense,
        confidence=confidence,
        reasoning=" | ".join(reasoning_parts),
    )


def _map_category(category_str: str) -> TransactionCategory:
    try:
        return TransactionCategory[category_str.upper()]
    except KeyError:
        return TransactionCategory.OTHER


def _safe_category(value: object) -> str:
    category = str(value or "other").lower().strip()
    return category if category in VALID_CATEGORIES else "other"


def _calibrate_confidence(
    *,
    raw_label: str,
    normalization_confidence: float,
    categorization_confidence: float,
    heuristic_category: str | None,
    selected_category: str,
    llm_category: str,
    second_pass_category: str,
) -> float:
    """Blend confidence from multiple signals to prioritize precision over recall."""
    score = 0.2
    score += max(0.0, min(normalization_confidence, 1.0)) * 0.5
    score += max(0.0, min(categorization_confidence, 1.0)) * 0.3

    if heuristic_category:
        score += 0.15
        if heuristic_category == selected_category:
            score += 0.1

    agreements = [cat for cat in (llm_category, second_pass_category, heuristic_category) if cat]
    unique = set(agreements)
    if len(unique) == 1 and agreements:
        score += 0.12
    elif len(unique) >= 3:
        score -= 0.1

    if selected_category == "other":
        score -= 0.15
    if selected_category in {"shopping", "food"}:
        score -= 0.05
    if len(raw_label.strip()) < 8:
        score -= 0.08

    return round(max(0.05, min(score, 0.99)), 4)
