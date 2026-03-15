from rest_framework import serializers
from .models import RecurringExpense


class RecurringExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringExpense
        fields = "__all__"
        read_only_fields = ["id", "user", "created_at", "updated_at"]
