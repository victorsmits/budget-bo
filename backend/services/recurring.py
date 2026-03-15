"""Recurring expense detection service."""

import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.recurrence import RecurrenceDetectionResult, RecurrenceDetector
from app.models.models import (
    RecurringExpense,
    RecurringExpenseDetail,
    RecurringExpensePublic,
    RecurringExpenseTransactionSummary,
    RecurrencePattern,
    Transaction,
    TransactionCategory,
)


class RecurringExpenseService:
    """
    Service for detecting and managing recurring expenses.
    
    Combines algorithmic detection (Levenshtein, amount variance, frequency analysis)
    with AI-assisted pattern recognition.
    """

    LABEL_MERGE_THRESHOLD = 0.9
    NOISE_TOKENS = {
        "dublin",
        "paris",
        "london",
        "tokyo",
        "ireland",
        "france",
        "uk",
        "usa",
        "web",
        "online",
    }

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        self.session = session

    @staticmethod
    def _transaction_sort_key(tx: Transaction) -> tuple[int, Decimal, str]:
        label = (tx.cleaned_label or tx.merchant_name or tx.raw_label or "").lower()
        # Negative ordinals to keep most recent / highest amounts first
        return (-tx.date.toordinal(), -tx.amount, label)

    @staticmethod
    def _normalize_label(label: str | None) -> str:
        if not label:
            return ""
        normalized = label.lower()
        normalized = re.sub(r"\b(cb|carte|visa|mastercard|prlv|sepa|abonnement|facture|payment|paiement|achat|achats|subscr|subscription)\b", " ", normalized)
        normalized = re.sub(r"\d+", " ", normalized)
        normalized = re.sub(r"[^a-z]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if not normalized:
            return label.lower()
        tokens = [t for t in normalized.split() if t not in RecurringExpenseService.NOISE_TOKENS]
        if not tokens:
            return normalized
        return " ".join(tokens)

    @classmethod
    def _canonical_label(cls, transactions: list[Transaction]) -> str:
        for tx in transactions:
            for candidate in (tx.cleaned_label, tx.merchant_name, tx.raw_label):
                if candidate and candidate.strip():
                    return candidate.strip()[:60]
        return transactions[0].raw_label[:60]

    async def _find_existing_expense(self, user_id: str, merchant_label: str) -> RecurringExpense | None:
        normalized_merchant = self._normalize_label(merchant_label)
        result = await self.session.execute(
            select(RecurringExpense).where(RecurringExpense.user_id == user_id)
        )
        candidates = result.scalars().all()

        best_match: RecurringExpense | None = None
        best_score = 0.0

        for expense in candidates:
            score = RecurrenceDetector.calculate_label_similarity(
                normalized_merchant,
                self._normalize_label(expense.pattern_name),
            )
            if score >= self.LABEL_MERGE_THRESHOLD and score > best_score:
                best_match = expense
                best_score = score

        return best_match

    async def analyze_user_transactions(
        self,
        user_id: str,
        months_back: int = 6,
    ) -> list[RecurringExpense]:
        """
        Analyze user's transaction history to detect recurring patterns.
        
        Args:
            user_id: UUID of user to analyze
            months_back: How many months of history to consider
            
        Returns:
            List of detected recurring expenses (new and existing)
        """
        since_date = datetime.now() - timedelta(days=months_back * 30)

        # Fetch user's transactions
        result = await self.session.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.date >= since_date.date(),
                Transaction.is_expense == True,
            )
        )
        transactions = result.scalars().all()

        if len(transactions) < 2:
            return []

        # Group transactions by merchant/label similarity
        groups = self._group_similar_transactions(transactions)

        detected_patterns: list[RecurringExpense] = []

        for group in groups:
            if len(group) < 2:
                continue

            amounts = [t.amount for t in group]
            dates = [t.date for t in group]
            merchant = group[0].merchant_name or group[0].raw_label[:30]

            # Use domain logic to detect recurrence
            detection = RecurrenceDetector.detect_recurrence(
                label=merchant,
                amounts=amounts,
                dates=dates,
            )

            if detection.is_recurring and detection.confidence_score >= 0.6:
                expense = await self._save_recurring_expense(
                    user_id=user_id,
                    detection=detection,
                    transactions=group,
                )
                if expense:
                    detected_patterns.append(expense)

        return detected_patterns

    def _group_similar_transactions(
        self,
        transactions: list[Transaction],
    ) -> list[list[Transaction]]:
        """
        Group transactions by merchant/label similarity.
        
        Uses Levenshtein distance to find similar labels.
        """
        groups: list[list[Transaction]] = []
        processed: set[str] = set()

        for tx in transactions:
            if str(tx.id) in processed:
                continue

            # Start a new group
            group = [tx]
            processed.add(str(tx.id))

            label_key = self._normalize_label(
                tx.cleaned_label or tx.merchant_name or tx.raw_label
            )

            # Find similar transactions
            for other in transactions:
                if str(other.id) in processed:
                    continue

                other_label = self._normalize_label(
                    other.cleaned_label or other.merchant_name or other.raw_label
                )
                similarity = RecurrenceDetector.calculate_label_similarity(
                    label_key, other_label
                )

                if similarity >= RecurrenceDetector.LABEL_SIMILARITY_THRESHOLD:
                    group.append(other)
                    processed.add(str(other.id))

            if len(group) >= 2:
                groups.append(group)

        return groups

    async def _save_recurring_expense(
        self,
        user_id: str,
        detection: RecurrenceDetectionResult,
        transactions: list[Transaction],
    ) -> RecurringExpense | None:
        """Save or update a recurring expense pattern."""
        merchant = self._canonical_label(transactions)

        # Check for existing pattern (first exact match, then fuzzy)
        result = await self.session.execute(
            select(RecurringExpense)
            .where(
                RecurringExpense.user_id == user_id,
                RecurringExpense.pattern_name == merchant,
            )
            .options(selectinload(RecurringExpense.transactions))
        )
        existing = result.scalar_one_or_none()

        if not existing:
            existing = await self._find_existing_expense(user_id, merchant)
            if existing:
                await self.session.refresh(existing, attribute_names=["transactions"])

        dates = [t.date for t in transactions]

        if existing:
            # Update existing
            existing.average_amount = detection.average_amount
            existing.amount_variation_pct = detection.amount_variation_pct
            existing.frequency_days = detection.frequency_days
            existing.pattern = RecurrencePattern(detection.pattern_type)
            existing.next_expected_date = detection.next_expected_date
            existing.last_seen_date = max(dates)
            existing.matched_transaction_count = len(transactions)
            existing.confidence_score = detection.confidence_score
            existing.updated_at = datetime.utcnow()
            await self.session.flush()
            await self._attach_transactions_to_expense(existing, transactions)
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        # Create new recurring expense
        expense = RecurringExpense(
            user_id=user_id,
            pattern_name=merchant,
            pattern=RecurrencePattern(detection.pattern_type),
            average_amount=detection.average_amount,
            amount_variation_pct=detection.amount_variation_pct,
            frequency_days=detection.frequency_days,
            day_of_month=
            detection.next_expected_date.day if detection.next_expected_date else None,
            next_expected_date=detection.next_expected_date,
            confidence_score=detection.confidence_score,
            matching_label_pattern=self._normalize_label(merchant)[:50] or merchant[:50],
            matched_transaction_count=len(transactions),
            first_seen_date=min(dates),
            last_seen_date=max(dates),
        )

        self.session.add(expense)
        await self.session.flush()
        await self._attach_transactions_to_expense(expense, transactions)
        await self.session.commit()
        await self.session.refresh(expense)

        return expense

    async def get_upcoming_expenses(
        self,
        user_id: str,
        days_ahead: int = 30,
    ) -> list[RecurringExpense]:
        """
        Get recurring expenses expected in the next N days.
        
        Args:
            user_id: User to check
            days_ahead: Look ahead window
            
        Returns:
            List of upcoming recurring expenses
        """
        target_date = date.today() + timedelta(days=days_ahead)

        result = await self.session.execute(
            select(RecurringExpense).where(
                RecurringExpense.user_id == user_id,
                RecurringExpense.is_active == True,
                RecurringExpense.next_expected_date <= target_date,
            )
        )

        return list(result.scalars().all())

    async def mark_transaction_recurring(
        self,
        transaction_id: str,
        is_recurring: bool = True,
    ) -> bool:
        """Mark a transaction as recurring (user feedback)."""
        result = await self.session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        transaction = result.scalar_one_or_none()

        if not transaction:
            return False

        transaction.is_recurring = is_recurring
        await self.session.commit()
        return True

    async def get_recurring_detail(
        self,
        user_id: str,
        expense_id: str,
    ) -> RecurringExpenseDetail | None:
        """Fetch recurring expense with contributing transactions and schedule."""

        result = await self.session.execute(
            select(RecurringExpense)
            .where(
                RecurringExpense.id == expense_id,
                RecurringExpense.user_id == user_id,
            )
            .options(selectinload(RecurringExpense.transactions))
        )
        expense = result.scalar_one_or_none()

        if not expense:
            return None

        public = RecurringExpensePublic.model_validate(expense)
        detail = RecurringExpenseDetail(**public.model_dump(), payment_schedule=[], transactions=[])

        if expense.next_expected_date and expense.frequency_days:
            detail.payment_schedule = RecurrenceDetector.build_payment_schedule(
                expense.next_expected_date,
                expense.frequency_days,
            )

        sorted_transactions = sorted(
            expense.transactions,
            key=self._transaction_sort_key,
        )

        detail.transactions = [
            RecurringExpenseTransactionSummary(
                transaction_id=tx.id,
                date=tx.date,
                amount=tx.amount,
                merchant_name=tx.merchant_name,
                cleaned_label=tx.cleaned_label,
                category=tx.category,
            )
            for tx in sorted_transactions
        ]

        return detail

    async def cancel_recurring_expense(
        self,
        user_id: str,
        expense_id: str,
    ) -> RecurringExpense | None:
        """Mark a recurring expense as inactive/cancelled."""

        result = await self.session.execute(
            select(RecurringExpense).where(
                RecurringExpense.id == expense_id,
                RecurringExpense.user_id == user_id,
            )
        )
        expense = result.scalar_one_or_none()

        if not expense:
            return None

        expense.is_active = False
        expense.next_expected_date = None
        await self.session.commit()
        await self.session.refresh(expense)
        return expense

    async def rename_recurring_expense(
        self,
        user_id: str,
        expense_id: str,
        new_name: str,
    ) -> RecurringExpense | None:
        """Rename a recurring expense and propagate to its transactions."""

        if not new_name:
            return None

        result = await self.session.execute(
            select(RecurringExpense)
            .where(
                RecurringExpense.id == expense_id,
                RecurringExpense.user_id == user_id,
            )
            .options(selectinload(RecurringExpense.transactions))
        )
        expense = result.scalar_one_or_none()

        if not expense:
            return None

        old_name = expense.pattern_name
        expense.pattern_name = new_name
        expense.matching_label_pattern = new_name[:30]

        for tx in expense.transactions:
            if not tx.merchant_name or tx.merchant_name == old_name:
                tx.merchant_name = new_name
            if not tx.cleaned_label or tx.cleaned_label == old_name:
                tx.cleaned_label = new_name

        await self.session.commit()
        await self.session.refresh(expense)
        return expense

    async def delete_recurring_expense(
        self,
        user_id: str,
        expense_id: str,
    ) -> bool:
        """Deactivate and detach a recurring expense."""

        result = await self.session.execute(
            select(RecurringExpense)
            .where(
                RecurringExpense.id == expense_id,
                RecurringExpense.user_id == user_id,
            )
            .options(selectinload(RecurringExpense.transactions))
        )
        expense = result.scalar_one_or_none()

        if not expense:
            return False

        expense.is_active = False
        expense.next_expected_date = None
        for tx in expense.transactions:
            tx.recurring_expense_id = None
            tx.is_recurring = False

        await self.session.commit()
        return True

    async def _attach_transactions_to_expense(
        self,
        expense: RecurringExpense,
        transactions: list[Transaction],
    ) -> None:
        """Associate transactions to a recurring expense."""

        for tx in transactions:
            tx.recurring_expense_id = expense.id
            tx.is_recurring = True
            if not tx.merchant_name:
                tx.merchant_name = expense.pattern_name

        await self.session.flush()
