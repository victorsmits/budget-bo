"""Utilities to learn and reuse user enrichment corrections."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.models import EnrichmentRule, Transaction, TransactionCategory

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


def build_label_fingerprint(raw_label: str) -> str:
    """Create a stable key for matching similar banking labels."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", raw_label.lower())
    cleaned = re.sub(r"\b\d+[a-z]*\b", " ", cleaned)
    tokens = [token for token in cleaned.split() if token not in NOISE_TOKENS and len(token) > 2]
    if not tokens:
        return "unknown"
    return " ".join(tokens[:8])


def apply_rule_to_transaction(transaction: Transaction, rule: EnrichmentRule) -> None:
    """Apply a learned rule to a transaction object."""
    transaction.cleaned_label = rule.cleaned_label
    transaction.category = rule.category
    transaction.merchant_name = rule.merchant_name
    transaction.ai_confidence = 1.0
    transaction.ai_category_reasoning = "Learned from previous user correction"
    transaction.enriched_at = datetime.utcnow()


def get_rule_for_label(session: Session, user_id: UUID | str, raw_label: str) -> Optional[EnrichmentRule]:
    """Find matching rule for a raw label."""
    fingerprint = build_label_fingerprint(raw_label)
    return session.execute(
        select(EnrichmentRule)
        .where(
            EnrichmentRule.user_id == user_id,
            EnrichmentRule.label_fingerprint == fingerprint,
        )
        .order_by(EnrichmentRule.updated_at.desc())
    ).scalar_one_or_none()


def upsert_rule_from_transaction(session: Session, transaction: Transaction) -> EnrichmentRule:
    """Create or update a rule based on a transaction enrichment/correction."""
    fingerprint = build_label_fingerprint(transaction.raw_label)
    existing = session.execute(
        select(EnrichmentRule).where(
            EnrichmentRule.user_id == transaction.user_id,
            EnrichmentRule.label_fingerprint == fingerprint,
        )
    ).scalar_one_or_none()

    now = datetime.utcnow()
    if existing:
        existing.cleaned_label = transaction.cleaned_label or transaction.raw_label
        existing.merchant_name = transaction.merchant_name
        existing.category = transaction.category
        existing.usage_count += 1
        existing.updated_at = now
        existing.learned_from_transaction_id = transaction.id
        return existing

    rule = EnrichmentRule(
        user_id=transaction.user_id,
        label_fingerprint=fingerprint,
        cleaned_label=transaction.cleaned_label or transaction.raw_label,
        merchant_name=transaction.merchant_name,
        category=transaction.category,
        usage_count=1,
        learned_from_transaction_id=transaction.id,
        created_at=now,
        updated_at=now,
    )
    session.add(rule)
    return rule


async def upsert_rule_from_transaction_async(
    session: AsyncSession,
    transaction: Transaction,
) -> EnrichmentRule:
    """Async variant used by FastAPI endpoints."""
    fingerprint = build_label_fingerprint(transaction.raw_label)
    result = await session.execute(
        select(EnrichmentRule).where(
            EnrichmentRule.user_id == transaction.user_id,
            EnrichmentRule.label_fingerprint == fingerprint,
        )
    )
    existing = result.scalar_one_or_none()

    now = datetime.utcnow()
    if existing:
        existing.cleaned_label = transaction.cleaned_label or transaction.raw_label
        existing.merchant_name = transaction.merchant_name
        existing.category = transaction.category
        existing.usage_count += 1
        existing.updated_at = now
        existing.learned_from_transaction_id = transaction.id
        return existing

    rule = EnrichmentRule(
        user_id=transaction.user_id,
        label_fingerprint=fingerprint,
        cleaned_label=transaction.cleaned_label or transaction.raw_label,
        merchant_name=transaction.merchant_name,
        category=transaction.category,
        usage_count=1,
        learned_from_transaction_id=transaction.id,
        created_at=now,
        updated_at=now,
    )
    session.add(rule)
    return rule
