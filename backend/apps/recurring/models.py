import uuid
from django.db import models
from apps.accounts.models import User


class RecurrencePattern(models.TextChoices):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    UNKNOWN = "unknown"


class RecurringExpense(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recurring_expenses")
    pattern_name = models.CharField(max_length=255)
    pattern = models.CharField(max_length=32, choices=RecurrencePattern.choices, default=RecurrencePattern.UNKNOWN)
    average_amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_variation_pct = models.FloatField(default=0.0)
    frequency_days = models.IntegerField(null=True, blank=True)
    day_of_month = models.IntegerField(null=True, blank=True)
    next_expected_date = models.DateField(null=True, blank=True)
    confidence_score = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True)
    matching_label_pattern = models.TextField()
    matched_transaction_count = models.IntegerField(default=0)
    first_seen_date = models.DateField()
    last_seen_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
