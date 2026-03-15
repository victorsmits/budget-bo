from worker.jobs.enrich_transactions import enrich_single_transaction as legacy_enrich


def enrich_single_transaction(transaction_id):
    return legacy_enrich(transaction_id=transaction_id)
