from django.contrib import admin
from .models import RecurringExpense


@admin.register(RecurringExpense)
class RecurringExpenseAdmin(admin.ModelAdmin):
    list_display = ("pattern_name", "pattern", "average_amount", "next_expected_date")
