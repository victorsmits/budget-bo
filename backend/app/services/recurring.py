"""Recurring expense detection service."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.recurrence import RecurrenceDetectionResult, RecurrenceDetector
from app.models.models import (
    RecurringExpense,
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

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        self.session = session

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

            label_key = tx.merchant_name or tx.raw_label

            # Find similar transactions
            for other in transactions:
                if str(other.id) in processed:
                    continue

                other_label = other.merchant_name or other.raw_label
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
        merchant = transactions[0].merchant_name or transactions[0].raw_label[:50]

        # Check for existing pattern
        result = await self.session.execute(
            select(RecurringExpense).where(
                RecurringExpense.user_id == user_id,
                RecurringExpense.pattern_name == merchant,
            )
        )
        existing = result.scalar_one_or_none()

        dates = [t.date for t in transactions]
        amounts = [t.amount for t in transactions]

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
            await self.session.commit()
            return existing

        # Create new recurring expense
        expense = RecurringExpense(
            user_id=user_id,
            pattern_name=merchant,
            pattern=RecurrencePattern(detection.pattern_type),
            average_amount=detection.average_amount,
            amount_variation_pct=detection.amount_variation_pct,
            frequency_days=detection.frequency_days,
            day_of_month=detection.next_expected_date.day if detection.next_expected_date else None,
            next_expected_date=detection.next_expected_date,
            confidence_score=detection.confidence_score,
            matching_label_pattern=merchant[:30],
            matched_transaction_count=len(transactions),
            first_seen_date=min(dates),
            last_seen_date=max(dates),
        )

        self.session.add(expense)
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
