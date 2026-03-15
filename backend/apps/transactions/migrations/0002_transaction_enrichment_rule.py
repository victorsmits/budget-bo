import re

from django.db import migrations, models
import django.db.models.deletion


NOISE_TOKENS = {
    "carte",
    "cb",
    "prlv",
    "prlvm",
    "prelevement",
    "prelev",
    "sepa",
    "vir",
    "virement",
    "paiement",
    "achat",
}


def _label_fingerprint(raw_label: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", raw_label.lower())
    cleaned = re.sub(r"\b\d+[a-z]*\b", " ", cleaned)
    tokens = [token for token in cleaned.split() if token not in NOISE_TOKENS and len(token) > 2]
    if not tokens:
        return "unknown"
    return " ".join(tokens[:8])


def forward_fill_enrichment_rule(apps, schema_editor):
    Transaction = apps.get_model("transactions", "Transaction")
    EnrichmentRule = apps.get_model("transactions", "EnrichmentRule")

    for tx in Transaction.objects.filter(enrichment_rule__isnull=True).iterator(chunk_size=1000):
        fingerprint = _label_fingerprint(tx.raw_label)
        legacy_fingerprint = tx.raw_label.lower().strip()
        rule = (
            EnrichmentRule.objects.filter(
                user_id=tx.user_id,
                label_fingerprint__in=[fingerprint, legacy_fingerprint],
            )
            .order_by("-updated_at")
            .first()
        )
        if rule is None:
            continue
        tx.enrichment_rule_id = rule.id
        tx.save(update_fields=["enrichment_rule"])


def backward_clear_enrichment_rule(apps, schema_editor):
    Transaction = apps.get_model("transactions", "Transaction")
    Transaction.objects.update(enrichment_rule=None)


class Migration(migrations.Migration):

    dependencies = [
        ("transactions", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="enrichment_rule",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="transactions",
                to="transactions.enrichmentrule",
            ),
        ),
        migrations.RunPython(forward_fill_enrichment_rule, backward_clear_enrichment_rule),
    ]
