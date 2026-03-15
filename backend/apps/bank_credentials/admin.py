from django.contrib import admin
from .models import BankCredential, BankAccount


@admin.register(BankCredential)
class BankCredentialAdmin(admin.ModelAdmin):
    list_display = ("user", "bank_name", "sync_status", "last_sync_at")


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "account_label", "balance", "currency")
