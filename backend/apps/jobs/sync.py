import hashlib
import json
import os
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone
from django_rq import get_queue

from apps.bank_credentials.models import BankAccount, BankCredential
from apps.transactions.models import Transaction
from services.security import EncryptionService

RETRYABLE_EXCEPTIONS = (TimeoutError, ConnectionError)


def _build_transaction_key(tx_date: date, amount: Decimal, raw_label: str) -> str:
    source = f"{tx_date.isoformat()}|{amount}|{raw_label.strip().lower()}"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _normalize_transaction(item: dict[str, Any]) -> dict[str, Any]:
    tx_date = item.get("date")
    if isinstance(tx_date, str):
        tx_date = datetime.fromisoformat(tx_date).date()

    amount = Decimal(str(item.get("amount", "0")))
    raw_label = str(item.get("raw_label") or item.get("label") or "").strip()

    return {
        "date": tx_date,
        "amount": amount,
        "raw_label": raw_label,
        "currency": str(item.get("currency") or "EUR"),
        "transaction_key": str(item.get("transaction_key") or _build_transaction_key(tx_date, amount, raw_label)),
    }


def _load_stub_payload() -> dict[str, Any] | None:
    """
    Optional local fallback to allow deterministic dev/testing without Woob runtime.
    Set BANK_SYNC_STUB_JSON to a JSON payload:
    {
      "transactions": [{"date":"2026-03-10","amount":-42.5,"raw_label":"..."}],
      "accounts": [{"account_id":"...","account_label":"...","balance":1200.0,"currency":"EUR"}]
    }
    """
    raw = os.getenv("BANK_SYNC_STUB_JSON")
    if not raw:
        return None
    return json.loads(raw)


def fetch_credential_data(
    credential: BankCredential,
    decrypted_login: str,
    decrypted_password: str,
    days_back: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Sync provider abstraction.
    For now we support a deterministic env-based stub payload.
    Hook Woob implementation here by returning (transactions, accounts).
    """
    payload = _load_stub_payload()
    if payload is None:
        return [], []

    transactions = payload.get("transactions") or []
    accounts = payload.get("accounts") or []
    return transactions, accounts


def _upsert_accounts(credential: BankCredential, accounts: list[dict[str, Any]]) -> int:
    upserted = 0
    for account in accounts:
        account_id = str(account.get("account_id") or "").strip()
        if not account_id:
            continue

        defaults = {
            "account_label": str(account.get("account_label") or account_id),
            "account_type": str(account.get("account_type") or "unknown"),
            "balance": Decimal(str(account.get("balance") or "0")),
            "currency": str(account.get("currency") or "EUR"),
            "user": credential.user,
            "credential": credential,
        }
        BankAccount.objects.update_or_create(
            credential=credential,
            account_id=account_id,
            defaults=defaults,
        )
        upserted += 1
    return upserted


def _insert_new_transactions(
    credential: BankCredential,
    transactions: list[dict[str, Any]],
) -> tuple[int, list[str]]:
    inserted = 0
    inserted_ids: list[str] = []
    for raw in transactions:
        normalized = _normalize_transaction(raw)
        if not normalized["date"] or not normalized["raw_label"]:
            continue

        exists = Transaction.objects.filter(
            user=credential.user,
            transaction_key=normalized["transaction_key"],
        ).exists()
        if exists:
            continue

        tx = Transaction.objects.create(
            user=credential.user,
            credential=credential,
            date=normalized["date"],
            amount=normalized["amount"],
            raw_label=normalized["raw_label"],
            currency=normalized["currency"],
            is_expense=normalized["amount"] < 0,
            transaction_key=normalized["transaction_key"],
        )
        inserted += 1
        inserted_ids.append(str(tx.id))

    return inserted, inserted_ids


def sync_credential_transactions(credential_id, days_back=7):
    credential = BankCredential.objects.select_related("user").get(id=credential_id)

    encryption = EncryptionService()
    queue = get_queue("enrich")

    credential.sync_status = "syncing"
    credential.sync_error_message = ""
    credential.save(update_fields=["sync_status", "sync_error_message", "updated_at"])

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            decrypted_login = encryption.decrypt(credential.encrypted_login)
            decrypted_password = encryption.decrypt(credential.encrypted_password)

            with transaction.atomic():
                provider_transactions, provider_accounts = fetch_credential_data(
                    credential=credential,
                    decrypted_login=decrypted_login,
                    decrypted_password=decrypted_password,
                    days_back=days_back,
                )

                upserted_accounts = _upsert_accounts(credential, provider_accounts)
                inserted_count, inserted_ids = _insert_new_transactions(
                    credential,
                    provider_transactions,
                )

                credential.sync_status = "success"
                credential.sync_error_message = ""
                credential.last_sync_at = timezone.now()
                credential.save(
                    update_fields=[
                        "sync_status",
                        "sync_error_message",
                        "last_sync_at",
                        "updated_at",
                    ]
                )

            for tx_id in inserted_ids:
                queue.enqueue("apps.jobs.enrich.enrich_single_transaction", tx_id)

            return {
                "credential_id": str(credential_id),
                "status": "success",
                "inserted_transactions": inserted_count,
                "upserted_accounts": upserted_accounts,
                "enqueued_enrichment_jobs": len(inserted_ids),
            }

        except RETRYABLE_EXCEPTIONS as exc:
            if attempt >= max_attempts:
                credential.sync_status = "error"
                credential.sync_error_message = f"{type(exc).__name__}: {exc}"
                credential.save(update_fields=["sync_status", "sync_error_message", "updated_at"])
                raise
            time.sleep(2 ** (attempt - 1))
        except Exception as exc:
            credential.sync_status = "error"
            credential.sync_error_message = f"{type(exc).__name__}: {exc}"
            credential.save(update_fields=["sync_status", "sync_error_message", "updated_at"])
            raise

    return {
        "credential_id": str(credential_id),
        "status": "error",
    }
