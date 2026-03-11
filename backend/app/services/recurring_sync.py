"""Utilities to keep recurring expense names synchronized with transactions."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.models import RecurringExpense, Transaction


def _derive_transaction_name(transaction: Transaction) -> Optional[str]:
    """Determine the best display name for a transaction."""

    for candidate in (
        transaction.cleaned_label,
        transaction.merchant_name,
        transaction.raw_label,
    ):
        if candidate:
            trimmed = candidate.strip()
            if trimmed:
                return trimmed[:50]
    return None


def _apply_name_to_expense(expense: RecurringExpense, new_name: str) -> None:
    """Apply a canonical name to a recurring expense and its transactions."""

    old_name = expense.pattern_name or ""
    expense.pattern_name = new_name
    expense.matching_label_pattern = new_name[:30]
    expense.updated_at = datetime.utcnow()

    for tx in expense.transactions:
        if not tx.merchant_name or tx.merchant_name == old_name:
            tx.merchant_name = new_name
        if not tx.cleaned_label or tx.cleaned_label == old_name:
            tx.cleaned_label = new_name


async def sync_recurring_name_from_transaction_async(
    session: AsyncSession,
    transaction: Transaction,
) -> None:
    """Ensure the recurring expense linked to this transaction shares its name."""

    if not transaction.recurring_expense_id:
        return

    new_name = _derive_transaction_name(transaction)
    if not new_name:
        return

    result = await session.execute(
        select(RecurringExpense)
        .where(RecurringExpense.id == transaction.recurring_expense_id)
        .options(selectinload(RecurringExpense.transactions))
    )
    expense = result.scalar_one_or_none()

    if not expense:
        return

    _apply_name_to_expense(expense, new_name)


def sync_recurring_name_from_transaction(
    session: Session,
    transaction: Transaction,
) -> None:
    """Synchronous variant to run inside Celery worker sessions."""

    if not transaction.recurring_expense_id:
        return

    new_name = _derive_transaction_name(transaction)
    if not new_name:
        return

    expense = (
        session.execute(
            select(RecurringExpense)
            .where(RecurringExpense.id == transaction.recurring_expense_id)
            .options(selectinload(RecurringExpense.transactions))
        )
        .scalar_one_or_none()
    )

    if not expense:
        return

    _apply_name_to_expense(expense, new_name)
