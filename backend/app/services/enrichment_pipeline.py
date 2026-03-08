"""High-reliability transaction enrichment pipeline with confidence calibration."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.models import TransactionCategory
from app.services.ai_constants import VALID_CATEGORIES
from app.services.enrichment_intelligence import (
    has_explicit_income_signal,
    infer_category_from_text,
    normalize_consumer_merchant,
    resolve_known_merchant_alias,
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

    alias_resolution = resolve_known_merchant_alias(raw_label)
    if alias_resolution is not None:
        cleaned_label = alias_resolution.cleaned_label
        merchant_name = alias_resolution.merchant_name

    merchant_resolution: dict[str, object] = {}
    if alias_resolution is None and _should_force_public_merchant_resolution(
        raw_label,
        cleaned_label,
        merchant_name,
    ):
        merchant_resolution = ollama_service.resolve_public_merchant(raw_label, merchant_name)
        resolved_merchant = str(merchant_resolution.get("merchant_name", "")).strip()
        if resolved_merchant and float(merchant_resolution.get("confidence", 0.0)) >= 0.55:
            merchant_name = resolved_merchant
            cleaned_candidate = str(merchant_resolution.get("cleaned_label", "")).strip()
            if cleaned_candidate:
                cleaned_label = cleaned_candidate

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
    alias_category = _safe_category(alias_resolution.category if alias_resolution else None)
    resolver_category = _safe_category(merchant_resolution.get("category"))
    second_pass_category = _safe_category(categorization.get("category"))
    selected_category = _choose_category(
        heuristic_category=heuristic_category,
        second_pass_category=second_pass_category,
        alias_category=alias_category,
        resolver_category=resolver_category,
        llm_category=llm_category,
    )

    if selected_category == "income" and not has_explicit_income_signal(
        text_for_category,
        merchant_name,
    ):
        selected_category = heuristic_category or (
            llm_category if llm_category != "income" else "other"
        )

    final_is_expense = bool(categorization.get("is_expense", initial_is_expense))
    confidence = _calibrate_confidence(
        raw_label=raw_label,
        cleaned_label=cleaned_label,
        merchant_name=merchant_name,
        normalization_confidence=float(normalization.get("confidence", 0.5)),
        alias_confidence=float(alias_resolution.confidence if alias_resolution else 0.0),
        resolver_confidence=float(merchant_resolution.get("confidence", 0.0)),
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
    if alias_resolution is not None:
        reasoning_parts.append(f"source=merchant_alias({alias_resolution.category})")
        reasoning_parts.append(f"alias_reasoning={alias_resolution.reasoning}")

    if merchant_resolution:
        reasoning_parts.append(f"source=merchant_resolution({resolver_category})")
        if resolver_reasoning := str(merchant_resolution.get("reasoning", "")).strip():
            reasoning_parts.append(f"resolver_reasoning={resolver_reasoning}")
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



def _choose_category(
    *,
    heuristic_category: str | None,
    second_pass_category: str,
    alias_category: str,
    resolver_category: str,
    llm_category: str,
) -> str:
    if heuristic_category:
        return heuristic_category

    prioritized = (second_pass_category, alias_category, resolver_category, llm_category)
    for category in prioritized:
        if category and category not in {"other", "shopping"}:
            return category

    for category in prioritized:
        if category and category != "other":
            return category

    return "other"

def _map_category(category_str: str) -> TransactionCategory:
    try:
        return TransactionCategory[category_str.upper()]
    except KeyError:
        return TransactionCategory.OTHER


def _safe_category(value: object) -> str:
    category = str(value or "other").lower().strip()
    return category if category in VALID_CATEGORIES else "other"


def _should_force_public_merchant_resolution(
    raw_label: str,
    cleaned_label: str,
    merchant_name: str,
) -> bool:
    if cleaned_label.strip() and not _is_opaque_token(cleaned_label):
        return False

    if _is_opaque_token(merchant_name):
        return True

    # Trigger on terminal-like labels such as "X7722 SOMETHING TOULOUSE"
    return bool(re.search(r"\bx\d{3,6}\b", raw_label.lower()))


def _is_opaque_token(value: str) -> bool:
    token = value.strip().lower()
    if not token:
        return True

    words = re.findall(r"[a-zà-ÿ0-9]+", token)
    if len(words) == 1 and len(words[0]) >= 6:
        return True

    return any(code in token for code in ("x7722", " toul", " paris")) and len(words) <= 3


def _calibrate_confidence(
    *,
    raw_label: str,
    cleaned_label: str,
    merchant_name: str,
    normalization_confidence: float,
    alias_confidence: float,
    resolver_confidence: float,
    categorization_confidence: float,
    heuristic_category: str | None,
    selected_category: str,
    llm_category: str,
    second_pass_category: str,
) -> float:
    """Blend confidence from multiple signals to prioritize precision over recall."""
    score = 0.15
    score += max(0.0, min(normalization_confidence, 1.0)) * 0.45
    score += max(0.0, min(alias_confidence, 1.0)) * 0.25
    score += max(0.0, min(resolver_confidence, 1.0)) * 0.15
    score += max(0.0, min(categorization_confidence, 1.0)) * 0.25

    if heuristic_category:
        score += 0.15
        if heuristic_category == selected_category:
            score += 0.1

    agreements = [cat for cat in (llm_category, second_pass_category, heuristic_category) if cat]
    unique = set(agreements)
    if len(unique) == 1 and agreements:
        score += 0.1
    elif len(unique) >= 3:
        score -= 0.12

    if selected_category == "other":
        score -= 0.2
    if selected_category in {"shopping", "food", "entertainment"}:
        score -= 0.07
    if len(raw_label.strip()) < 8:
        score -= 0.08
    if not cleaned_label.strip():
        score -= 0.18
    if _is_opaque_token(merchant_name):
        score -= 0.15

    return round(max(0.05, min(score, 0.99)), 4)
