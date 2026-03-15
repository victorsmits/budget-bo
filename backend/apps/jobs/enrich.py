from django.utils import timezone
from apps.transactions.models import Transaction


def enrich_single_transaction(transaction_id):
    transaction = Transaction.objects.get(id=transaction_id)
    if not transaction.cleaned_label:
        transaction.cleaned_label = transaction.raw_label
    transaction.enriched_at = timezone.now()
    transaction.save(update_fields=["cleaned_label", "enriched_at", "updated_at"])
    return {"transaction_id": str(transaction_id), "status": "enriched"}
