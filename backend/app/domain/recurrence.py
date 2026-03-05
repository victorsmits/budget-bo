"""Domain logic for detecting recurring expense patterns."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from Levenshtein import distance as levenshtein_distance


@dataclass
class TransactionPattern:
    """Represents a detected pattern in transactions."""

    label: str
    amount: Decimal
    dates: list[date]
    similarity_score: float


@dataclass
class RecurrenceDetectionResult:
    """Result of recurrence detection analysis."""

    is_recurring: bool
    pattern_type: str  # "weekly", "monthly", "quarterly", "annually", "unknown"
    average_amount: Decimal
    amount_variation_pct: float
    frequency_days: Optional[int]
    confidence_score: float
    next_expected_date: Optional[date]


class RecurrenceDetector:
    """
    Service for detecting recurring expense patterns.
    
    Analyzes transaction history to identify repeating payments using:
    - Label similarity (Levenshtein distance)
    - Amount stability (+/- 5% tolerance)
    - Temporal frequency analysis
    """

    # Tolerance thresholds
    LABEL_SIMILARITY_THRESHOLD = 0.8  # 80% similar
    AMOUNT_VARIANCE_THRESHOLD = 0.05  # 5% variation allowed
    DATE_TOLERANCE_DAYS = 3  # +/- 3 days for monthly patterns

    @staticmethod
    def calculate_label_similarity(label1: str, label2: str) -> float:
        """
        Calculate similarity between two labels using Levenshtein distance.
        
        Returns a score between 0.0 and 1.0 where 1.0 is identical.
        """
        if not label1 or not label2:
            return 0.0
        
        max_len = max(len(label1), len(label2))
        if max_len == 0:
            return 1.0
        
        dist = levenshtein_distance(label1.lower(), label2.lower())
        return 1.0 - (dist / max_len)

    @staticmethod
    def calculate_amount_variance(amounts: list[Decimal]) -> float:
        """
        Calculate coefficient of variation (std/mean) for amounts.
        
        Returns a value where lower is more stable (0.0 = identical amounts).
        """
        if len(amounts) < 2:
            return 0.0
        
        # Convert to float for calculation
        float_amounts = [float(a) for a in amounts]
        mean = sum(float_amounts) / len(float_amounts)
        
        if mean == 0:
            return 0.0
        
        variance = sum((x - mean) ** 2 for x in float_amounts) / len(float_amounts)
        std = variance ** 0.5
        
        return std / mean

    @staticmethod
    def analyze_frequency(dates: list[date]) -> tuple[str, Optional[int], float]:
        """
        Analyze the frequency pattern of dates.
        
        Returns:
            - pattern_type: "weekly", "monthly", "quarterly", "annually", "unknown"
            - average_days: average days between occurrences
            - confidence: 0.0 to 1.0
        """
        if len(dates) < 2:
            return ("unknown", None, 0.0)
        
        sorted_dates = sorted(dates)
        intervals = [
            (sorted_dates[i + 1] - sorted_dates[i]).days
            for i in range(len(sorted_dates) - 1)
        ]
        
        avg_interval = sum(intervals) / len(intervals)
        
        # Calculate variance in intervals
        if len(intervals) > 1:
            variance = sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)
            std = variance ** 0.5
            interval_consistency = max(0.0, 1.0 - (std / avg_interval if avg_interval > 0 else 0))
        else:
            interval_consistency = 0.5  # Single interval, moderate confidence
        
        # Determine pattern type based on average interval
        pattern_map = [
            (7, "weekly"),
            (14, "biweekly"),
            (30, "monthly"),
            (90, "quarterly"),
            (365, "annually"),
        ]
        
        closest_pattern = "unknown"
        pattern_confidence = 0.0
        
        for target_days, pattern_name in pattern_map:
            diff = abs(avg_interval - target_days)
            tolerance = target_days * 0.1  # 10% tolerance
            
            if diff <= tolerance:
                closest_pattern = pattern_name
                pattern_confidence = 1.0 - (diff / target_days)
                break
        
        # Overall confidence combines interval consistency and pattern match
        confidence = (interval_consistency + pattern_confidence) / 2
        
        return (closest_pattern, int(avg_interval), confidence)

    @classmethod
    def detect_recurrence(
        cls,
        label: str,
        amounts: list[Decimal],
        dates: list[date],
    ) -> RecurrenceDetectionResult:
        """
        Analyze a set of transactions to detect if they form a recurring pattern.
        
        Args:
            label: The transaction label/payee
            amounts: List of transaction amounts
            dates: List of transaction dates
            
        Returns:
            RecurrenceDetectionResult with analysis results
        """
        if len(amounts) < 2 or len(dates) < 2:
            return RecurrenceDetectionResult(
                is_recurring=False,
                pattern_type="unknown",
                average_amount=amounts[0] if amounts else Decimal("0"),
                amount_variation_pct=0.0,
                frequency_days=None,
                confidence_score=0.0,
                next_expected_date=None,
            )
        
        # Calculate amount stability
        amount_variance = cls.calculate_amount_variance(amounts)
        amount_stable = amount_variance <= cls.AMOUNT_VARIANCE_THRESHOLD
        
        # Analyze frequency
        pattern_type, freq_days, freq_confidence = cls.analyze_frequency(dates)
        
        # Determine if recurring based on multiple factors
        is_recurring = (
            amount_stable
            and pattern_type != "unknown"
            and freq_confidence >= 0.6
            and len(dates) >= 2  # At least 2 occurrences
        )
        
        # Calculate average amount
        avg_amount = sum(amounts) / len(amounts)
        
        # Predict next expected date
        next_expected: Optional[date] = None
        if is_recurring and freq_days:
            last_date = max(dates)
            next_expected = last_date + timedelta(days=freq_days)
        
        # Overall confidence score
        confidence = (
            freq_confidence * 0.5
            + (1.0 - min(amount_variance, 1.0)) * 0.3
            + (min(len(dates), 12) / 12) * 0.2  # More occurrences = higher confidence
        )
        
        return RecurrenceDetectionResult(
            is_recurring=is_recurring,
            pattern_type=pattern_type,
            average_amount=avg_amount,
            amount_variation_pct=amount_variance,
            frequency_days=freq_days,
            confidence_score=round(confidence, 2),
            next_expected_date=next_expected,
        )

    @classmethod
    def find_similar_transactions(
        cls,
        target_label: str,
        transactions: list[tuple[str, Decimal, date]],
    ) -> list[tuple[str, Decimal, date]]:
        """
        Find transactions with similar labels to the target.
        
        Args:
            target_label: The label to match against
            transactions: List of (label, amount, date) tuples
            
        Returns:
            Filtered list of similar transactions
        """
        similar = []
        for label, amount, date_val in transactions:
            similarity = cls.calculate_label_similarity(target_label, label)
            if similarity >= cls.LABEL_SIMILARITY_THRESHOLD:
                similar.append((label, amount, date_val))
        return similar
