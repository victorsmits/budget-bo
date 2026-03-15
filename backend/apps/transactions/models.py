import uuid
from django.db import models
from apps.accounts.models import User
from apps.bank_credentials.models import BankCredential


class TransactionCategory(models.TextChoices):
    HOUSING = "housing"
    TRANSPORTATION = "transportation"
    FOOD = "food"
    UTILITIES = "utilities"
    HEALTHCARE = "healthcare"
    ENTERTAINMENT = "entertainment"
    GROCERIES = "groceries"
    DINING = "dining"
    SHOPPING = "shopping"
    HOME_IMPROVEMENT = "home_improvement"
    SUBSCRIPTIONS = "subscriptions"
    INCOME = "income"
    INSURANCE = "insurance"
    EDUCATION = "education"
    TRAVEL = "travel"
    OTHER = "other"


class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    credential = models.ForeignKey(BankCredential, on_delete=models.CASCADE, related_name="transactions")
    recurring_expense = models.ForeignKey("recurring.RecurringExpense", null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    raw_label = models.TextField()
    cleaned_label = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=64, choices=TransactionCategory.choices, default=TransactionCategory.OTHER)
    is_expense = models.BooleanField(default=True)
    is_recurring = models.BooleanField(default=False)
    merchant_name = models.CharField(max_length=255, null=True, blank=True)
    currency = models.CharField(max_length=8, default="EUR")
    transaction_key = models.CharField(max_length=255, db_index=True)
    ai_confidence = models.FloatField(null=True, blank=True)
    enriched_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class EnrichmentRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrichment_rules")
    label_fingerprint = models.CharField(max_length=255, db_index=True)
    merchant_name = models.CharField(max_length=255, null=True, blank=True)
    cleaned_label = models.CharField(max_length=255)
    category = models.CharField(max_length=64, choices=TransactionCategory.choices, default=TransactionCategory.OTHER)
    usage_count = models.IntegerField(default=1)
    learned_from_transaction = models.ForeignKey(Transaction, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
