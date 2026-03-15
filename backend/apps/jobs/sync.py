import hashlib
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone
from django_rq import get_queue

from apps.bank_credentials.models import BankAccount, BankCredential
from apps.transactions.models import Transaction
from services.security import EncryptionService

RETRYABLE_EXCEPTIONS = (TimeoutError, ConnectionError)

CA_REGION_URLS = {
    "ca-alpesprovence": "www.ca-alpesprovence.fr",
    "ca-alsace-vosges": "www.ca-alsace-vosges.fr",
    "ca-anjou-maine": "www.ca-anjou-maine.fr",
    "ca-aquitaine": "www.ca-aquitaine.fr",
    "ca-atlantique-vendee": "www.ca-atlantique-vendee.fr",
    "ca-briepicardie": "www.ca-briepicardie.fr",
    "ca-cb": "www.ca-cb.fr",
    "ca-centrefrance": "www.ca-centrefrance.fr",
    "ca-centreloire": "www.ca-centreloire.fr",
    "ca-centreouest": "www.ca-centreouest.fr",
    "ca-centrest": "www.ca-centrest.fr",
    "ca-charente-perigord": "www.ca-charente-perigord.fr",
    "ca-cmds": "www.ca-cmds.fr",
    "ca-corse": "www.ca-corse.fr",
    "ca-cotesdarmor": "www.ca-cotesdarmor.fr",
    "ca-des-savoie": "www.ca-des-savoie.fr",
    "ca-finistere": "www.ca-finistere.fr",
    "ca-franchecomte": "www.ca-franchecomte.fr",
    "ca-guadeloupe": "www.ca-guadeloupe.fr",
    "ca-illeetvilaine": "www.ca-illeetvilaine.fr",
    "ca-languedoc": "www.ca-languedoc.fr",
    "ca-loirehauteloire": "www.ca-loirehauteloire.fr",
    "ca-lorraine": "www.ca-lorraine.fr",
    "ca-martinique": "www.ca-martinique.fr",
    "ca-morbihan": "www.ca-morbihan.fr",
    "ca-nmp": "www.ca-nmp.fr",
    "ca-nord-est": "www.ca-nord-est.fr",
    "ca-norddefrance": "www.ca-norddefrance.fr",
    "ca-normandie-seine": "www.ca-normandie-seine.fr",
    "ca-normandie": "www.ca-normandie.fr",
    "ca-paris": "www.ca-paris.fr",
    "ca-pca": "www.ca-pca.fr",
    "ca-pyrenees-gascogne": "www.ca-pyrenees-gascogne.fr",
    "ca-reunion": "www.ca-reunion.fr",
    "ca-sudmed": "www.ca-sudmed.fr",
    "ca-sudrhonealpes": "www.ca-sudrhonealpes.fr",
    "ca-toulouse": "www.ca-toulouse31.fr",
    "ca-tourainepoitou": "www.ca-tourainepoitou.fr",
    "ca-valdefrance": "www.ca-valdefrance.fr",
    "ca-champagne-bourgogne": "www.ca-champagnebourgogne.fr",
    "ca-bretagne-pays-de-loire": "www.ca-bretagnepaysdelaloire.fr",
}


def _build_transaction_key(tx_date: date, amount: Decimal, raw_label: str) -> str:
    source = f"{tx_date.isoformat()}|{amount}|{raw_label.strip().lower()}"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _normalize_transaction(item: dict[str, Any]) -> dict[str, Any] | None:
    tx_date = item.get("date")
    if isinstance(tx_date, str):
        tx_date = datetime.fromisoformat(tx_date).date()
    if not isinstance(tx_date, date):
        return None

    amount = Decimal(str(item.get("amount", "0")))
    raw_label = str(item.get("raw_label") or item.get("label") or "").strip()
    if not raw_label:
        return None

    return {
        "date": tx_date,
        "amount": amount,
        "raw_label": raw_label,
        "currency": str(item.get("currency") or "EUR"),
        "transaction_key": str(item.get("transaction_key") or _build_transaction_key(tx_date, amount, raw_label)),
    }


def _map_bank_website(bank_website: str | None) -> str | None:
    if not bank_website:
        return None
    return CA_REGION_URLS.get(bank_website, bank_website)


def fetch_credential_data(
    credential: BankCredential,
    decrypted_login: str,
    decrypted_password: str,
    days_back: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Fetch real accounts + transactions from Woob custom module."""
    if credential.bank_name not in {"cragr", "credit_agricole", "ca"}:
        raise NotImplementedError(
            f"Woob sync not implemented for bank_name={credential.bank_name}"
        )

    try:
        from custom_woob_modules.cragr_custom.browser import CragrCustomBrowser
    except Exception as exc:
        raise RuntimeError(
            "Unable to import Woob custom browser. Ensure woob + modules are installed."
        ) from exc

    website = _map_bank_website(credential.bank_website)
    backend = CragrCustomBrowser(website, decrypted_login, decrypted_password)

    since_date = (timezone.now() - timedelta(days=days_back)).date()
    transactions: list[dict[str, Any]] = []
    accounts: list[dict[str, Any]] = []

    try:
        for account in backend.iter_accounts():
            account_id = str(getattr(account, "id", "") or "").strip()
            if not account_id:
                continue

            accounts.append(
                {
                    "account_id": account_id,
                    "account_label": str(getattr(account, "label", "") or account_id),
                    "account_type": str(getattr(account, "type", "unknown") or "unknown"),
                    "balance": str(getattr(account, "balance", "0") or "0"),
                    "currency": str(getattr(account, "currency", "EUR") or "EUR"),
                }
            )

            for history in backend.iter_history(account):
                history_date = getattr(history, "date", None)
                if hasattr(history_date, "date"):
                    history_date = history_date.date()
                if not history_date or history_date < since_date:
                    continue

                amount = Decimal(str(getattr(history, "amount", "0") or "0"))
                label = (
                    getattr(history, "label", None)
                    or getattr(history, "raw", None)
                    or "Unknown"
                )
                transactions.append(
                    {
                        "date": history_date,
                        "amount": amount,
                        "raw_label": str(label),
                        "currency": str(getattr(account, "currency", "EUR") or "EUR"),
                    }
                )
    finally:
        try:
            backend.deinit()
        except Exception:
            pass

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
        if not normalized:
            continue

        exists = Transaction.objects.filter(
            user=credential.user,
            transaction_key=normalized["transaction_key"],
        ).exists()
        if exists:
            continue

        raw_amount = normalized["amount"]
        tx = Transaction.objects.create(
            user=credential.user,
            credential=credential,
            date=normalized["date"],
            amount=abs(raw_amount),
            raw_label=normalized["raw_label"],
            currency=normalized["currency"],
            is_expense=raw_amount < 0,
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
