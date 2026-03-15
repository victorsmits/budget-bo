from django_rq import get_queue
from apps.bank_credentials.models import BankCredential
from apps.transactions.models import Transaction
from .sync import sync_credential_transactions
from .enrich import enrich_single_transaction


def sync_all_credentials(days_back=1):
    queue = get_queue("sync")
    for credential_id in BankCredential.objects.filter(is_active=True).values_list("id", flat=True):
        queue.enqueue(sync_credential_transactions, str(credential_id), days_back)


def enrich_all_transactions(days_back=7, batch_size=500):
    queue = get_queue("enrich")
    qs = Transaction.objects.filter(enriched_at__isnull=True).order_by("date")
    for tx_id in qs.values_list("id", flat=True)[:batch_size]:
        queue.enqueue(enrich_single_transaction, str(tx_id))


def detect_recurring_patterns(user_id):
    return {"user_id": user_id, "status": "queued"}
