import uuid
from django.db import models
from apps.accounts.models import User


class BankCredential(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bank_credentials")
    bank_name = models.CharField(max_length=128)
    bank_label = models.CharField(max_length=255, null=True, blank=True)
    bank_website = models.CharField(max_length=255, null=True, blank=True)
    encrypted_login = models.TextField()
    encrypted_password = models.TextField()
    sync_status = models.CharField(max_length=32, default="pending")
    sync_error_message = models.TextField(null=True, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class BankAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bank_accounts")
    credential = models.ForeignKey(BankCredential, on_delete=models.CASCADE, related_name="accounts")
    account_id = models.CharField(max_length=255)
    account_label = models.CharField(max_length=255)
    account_type = models.CharField(max_length=128, default="unknown")
    balance = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="EUR")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
