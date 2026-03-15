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
            name="RecurringExpense",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("pattern_name", models.CharField(max_length=255)),
                (
                    "pattern",
                    models.CharField(
                        choices=[
                            ("weekly", "Weekly"),
                            ("monthly", "Monthly"),
                            ("quarterly", "Quarterly"),
                            ("annually", "Annually"),
                            ("unknown", "Unknown"),
                        ],
                        default="unknown",
                        max_length=32,
                    ),
                ),
                ("average_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("amount_variation_pct", models.FloatField(default=0.0)),
                ("frequency_days", models.IntegerField(blank=True, null=True)),
                ("day_of_month", models.IntegerField(blank=True, null=True)),
                ("next_expected_date", models.DateField(blank=True, null=True)),
                ("confidence_score", models.FloatField(default=0.0)),
                ("is_active", models.BooleanField(default=True)),
                ("matching_label_pattern", models.TextField()),
                ("matched_transaction_count", models.IntegerField(default=0)),
                ("first_seen_date", models.DateField()),
                ("last_seen_date", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recurring_expenses", to="accounts.user"),
                ),
            ],
        ),
    ]
