from django.utils import timezone
from apps.bank_credentials.models import BankCredential


def sync_credential_transactions(credential_id, days_back=7):
    credential = BankCredential.objects.get(id=credential_id)
    credential.sync_status = "success"
    credential.sync_error_message = ""
    credential.last_sync_at = timezone.now()
    credential.save(update_fields=["sync_status", "sync_error_message", "last_sync_at", "updated_at"])
    return {"credential_id": str(credential_id), "days_back": days_back, "status": "success"}
