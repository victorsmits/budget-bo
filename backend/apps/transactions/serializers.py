from rest_framework import serializers
from .models import EnrichmentRule, Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"
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
