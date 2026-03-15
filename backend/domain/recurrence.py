"""Domain logic for detecting recurring expense patterns."""

from dataclasses import dataclass, field
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
    payment_schedule: list[date] = field(default_factory=list)


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
    AMOUNT_VARIANCE_THRESHOLD = 0.05  # +/-5% variation allowed (strict)
    AMOUNT_LOOSE_VARIANCE_THRESHOLD = 0.25  # +/-25% allowed for variable utilities
    MIN_STRICT_AMOUNT_RATIO = 0.8  # 80% of amounts must be within strict band
    MIN_LOOSE_AMOUNT_RATIO = 0.6  # 60% within loose band to accept variable recurring
    MIN_OCCURRENCES_FOR_VARIABLE = 4
    DATE_TOLERANCE_DAYS = 3  # +/-3 days tolerance around target cycle length
    MIN_PATTERN_MATCH_RATIO = 0.6  # At least 60% of intervals must be within tolerance
    PAYMENT_SCHEDULE_WINDOW_DAYS = 180  # Build calendar ~6 months ahead

    CANDIDATE_PATTERNS: dict[str, int] = {
        "weekly": 7,
        "monthly": 30,
        "annually": 365,
    }

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
    def _median_amount(amounts: list[Decimal]) -> float:
        """Return the median value as float for easier tolerance math."""

        if not amounts:
            return 0.0

        sorted_amounts = sorted(float(a) for a in amounts)
        mid = len(sorted_amounts) // 2

        if len(sorted_amounts) % 2:
            return sorted_amounts[mid]

        return (sorted_amounts[mid - 1] + sorted_amounts[mid]) / 2

    @classmethod
    def calculate_amount_match_ratio(
        cls, amounts: list[Decimal], tolerance_pct: float
    ) -> float:
        """Share of occurrences staying within the given tolerance around median."""

        if not amounts:
            return 0.0

        median = cls._median_amount(amounts)
        tolerance_value = abs(median) * tolerance_pct

        # When median is ≈0 (rare), fall back to absolute tolerance using 1 currency unit
        if tolerance_value == 0:
            tolerance_value = tolerance_pct or 1.0

        matches = sum(
            1
            for amount in amounts
            if abs(float(amount) - median) <= tolerance_value
        )

        return matches / len(amounts)

    @classmethod
    def analyze_frequency(cls, dates: list[date]) -> tuple[str, Optional[int], float]:
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

        best_pattern = "unknown"
        best_frequency: Optional[int] = None
        best_confidence = 0.0

        for pattern_name, target_days in cls.CANDIDATE_PATTERNS.items():
            matching_intervals = [
                interval
                for interval in intervals
                if abs(interval - target_days) <= cls.DATE_TOLERANCE_DAYS
            ]

            if not matching_intervals:
                continue

            match_ratio = len(matching_intervals) / len(intervals)
            if match_ratio < cls.MIN_PATTERN_MATCH_RATIO:
                continue

            avg_match_interval = int(
                round(sum(matching_intervals) / len(matching_intervals))
            )

            if match_ratio > best_confidence:
                best_pattern = pattern_name
                best_frequency = max(1, avg_match_interval)
                best_confidence = match_ratio

        return (best_pattern, best_frequency, best_confidence)

    @classmethod
    def build_payment_schedule(
        cls, next_expected: date, frequency_days: int
    ) -> list[date]:
        """Generate a payment calendar within the configured horizon."""

        schedule: list[date] = []
        horizon = next_expected + timedelta(days=cls.PAYMENT_SCHEDULE_WINDOW_DAYS)
        current = next_expected

        while current <= horizon:
            schedule.append(current)
            current += timedelta(days=frequency_days)

        return schedule

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
        
        # Calculate amount stability (strict vs loose for utilities)
        amount_variance = cls.calculate_amount_variance(amounts)
        strict_ratio = cls.calculate_amount_match_ratio(
            amounts, cls.AMOUNT_VARIANCE_THRESHOLD
        )
        loose_ratio = cls.calculate_amount_match_ratio(
            amounts, cls.AMOUNT_LOOSE_VARIANCE_THRESHOLD
        )

        amount_stable = strict_ratio >= cls.MIN_STRICT_AMOUNT_RATIO
        variable_amount_pattern = (
            not amount_stable
            and loose_ratio >= cls.MIN_LOOSE_AMOUNT_RATIO
            and len(amounts) >= cls.MIN_OCCURRENCES_FOR_VARIABLE
        )
        
        # Analyze frequency
        pattern_type, freq_days, freq_confidence = cls.analyze_frequency(dates)
        
        # Determine if recurring based on multiple factors
        is_recurring = (
            pattern_type != "unknown"
            and freq_confidence >= 0.6
            and len(dates) >= 2  # At least 2 occurrences
            and (amount_stable or variable_amount_pattern)
        )
        
        # Calculate average amount
        avg_amount = sum(amounts) / len(amounts)
        
        # Predict next expected date & future calendar
        next_expected: Optional[date] = None
        payment_schedule: list[date] = []
        if is_recurring and freq_days:
            last_date = max(dates)
            next_expected = last_date + timedelta(days=freq_days)
            payment_schedule = cls.build_payment_schedule(next_expected, freq_days)
        
        # Overall confidence score
        amount_score = strict_ratio if amount_stable else loose_ratio * 0.8
        confidence = (
            freq_confidence * 0.5
            + amount_score * 0.3
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
            payment_schedule=payment_schedule,
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
