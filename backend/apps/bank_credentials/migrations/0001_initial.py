import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BankCredential",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("bank_name", models.CharField(max_length=128)),
                ("bank_label", models.CharField(blank=True, max_length=255, null=True)),
                ("bank_website", models.CharField(blank=True, max_length=255, null=True)),
                ("encrypted_login", models.TextField()),
                ("encrypted_password", models.TextField()),
                ("sync_status", models.CharField(default="pending", max_length=32)),
                ("sync_error_message", models.TextField(blank=True, null=True)),
                ("last_sync_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bank_credentials", to="accounts.user"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="BankAccount",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("account_id", models.CharField(max_length=255)),
                ("account_label", models.CharField(max_length=255)),
                ("account_type", models.CharField(default="unknown", max_length=128)),
                ("balance", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="EUR", max_length=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "credential",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="accounts", to="bank_credentials.bankcredential"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bank_accounts", to="accounts.user"),
                ),
            ],
        ),
    ]
