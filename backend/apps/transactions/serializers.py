from rest_framework import serializers
from .models import EnrichmentRule, Transaction


class TransactionSerializer(serializers.ModelSerializer):
    cleaned_label = serializers.CharField(source="display_label", read_only=True)
    category = serializers.CharField(source="display_category", read_only=True)
    merchant_name = serializers.CharField(source="display_merchant", read_only=True, allow_null=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "user",
            "credential",
            "recurring_expense",
            "date",
            "amount",
            "raw_label",
            "cleaned_label",
            "category",
            "is_expense",
            "is_recurring",
            "merchant_name",
            "currency",
            "transaction_key",
            "ai_confidence",
            "enriched_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at", "enriched_at"]


class TransactionCategoryPatchSerializer(serializers.Serializer):
    category = serializers.CharField()


class TransactionCorrectionSerializer(serializers.Serializer):
    cleaned_label = serializers.CharField(required=False)
    merchant_name = serializers.CharField(required=False)
    category = serializers.CharField(required=False)


class RecurringFlagSerializer(serializers.Serializer):
    is_recurring = serializers.BooleanField()


class EnrichmentRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnrichmentRule
        fields = "__all__"


class TransactionBulkEnrichSerializer(serializers.Serializer):
    max_transactions = serializers.IntegerField(min_value=1, max_value=5000, required=False, default=100)
    days_back = serializers.IntegerField(min_value=1, max_value=365, required=False, default=7)
    worker_count = serializers.IntegerField(min_value=1, max_value=32, required=False, default=1)
    enrich_all = serializers.BooleanField(required=False, default=False)
