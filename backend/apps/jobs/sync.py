from worker.jobs.sync_transactions import sync_credential_transactions as legacy_sync


def sync_credential_transactions(credential_id, days_back=7):
    return legacy_sync(credential_id=credential_id, days_back=days_back)
