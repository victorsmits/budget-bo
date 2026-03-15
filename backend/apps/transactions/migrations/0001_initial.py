import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
        ("bank_credentials", "0001_initial"),
        ("recurring", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Transaction",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("date", models.DateField()),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("raw_label", models.TextField()),
                ("cleaned_label", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("housing", "Housing"),
                            ("transportation", "Transportation"),
                            ("food", "Food"),
                            ("utilities", "Utilities"),
                            ("healthcare", "Healthcare"),
                            ("entertainment", "Entertainment"),
                            ("groceries", "Groceries"),
                            ("dining", "Dining"),
                            ("shopping", "Shopping"),
                            ("home_improvement", "Home Improvement"),
                            ("subscriptions", "Subscriptions"),
                            ("income", "Income"),
                            ("insurance", "Insurance"),
                            ("education", "Education"),
                            ("travel", "Travel"),
                            ("other", "Other"),
                        ],
                        default="other",
                        max_length=64,
                    ),
                ),
                ("is_expense", models.BooleanField(default=True)),
                ("is_recurring", models.BooleanField(default=False)),
                ("merchant_name", models.CharField(blank=True, max_length=255, null=True)),
                ("currency", models.CharField(default="EUR", max_length=8)),
                ("transaction_key", models.CharField(db_index=True, max_length=255)),
                ("ai_confidence", models.FloatField(blank=True, null=True)),
                ("enriched_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "credential",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transactions", to="bank_credentials.bankcredential"),
                ),
                (
                    "recurring_expense",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="transactions", to="recurring.recurringexpense"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transactions", to="accounts.user"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="EnrichmentRule",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("label_fingerprint", models.CharField(db_index=True, max_length=255)),
                ("merchant_name", models.CharField(blank=True, max_length=255, null=True)),
                ("cleaned_label", models.CharField(max_length=255)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("housing", "Housing"),
                            ("transportation", "Transportation"),
                            ("food", "Food"),
                            ("utilities", "Utilities"),
                            ("healthcare", "Healthcare"),
                            ("entertainment", "Entertainment"),
                            ("groceries", "Groceries"),
                            ("dining", "Dining"),
                            ("shopping", "Shopping"),
                            ("home_improvement", "Home Improvement"),
                            ("subscriptions", "Subscriptions"),
                            ("income", "Income"),
                            ("insurance", "Insurance"),
                            ("education", "Education"),
                            ("travel", "Travel"),
                            ("other", "Other"),
                        ],
                        default="other",
                        max_length=64,
                    ),
                ),
                ("usage_count", models.IntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "learned_from_transaction",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="transactions.transaction"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="enrichment_rules", to="accounts.user"),
                ),
            ],
        ),
    ]
