from django.contrib import admin
from .models import EnrichmentRule, Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "raw_label", "cleaned_label", "category", "amount", "enriched_at")


@admin.register(EnrichmentRule)
class EnrichmentRuleAdmin(admin.ModelAdmin):
    list_display = ("user", "label_fingerprint", "category", "usage_count")
