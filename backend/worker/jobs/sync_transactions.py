"""Bank transaction synchronization job — sync Celery worker, no asyncio."""

import hashlib
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from celery import Task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded
from sqlalchemy import select

sys.path.insert(0, "/app")

from app.core.config import get_settings
from app.core.database import get_worker_session
from app.core.security import get_encryption_service
from app.models.models import BankAccount, BankCredential, Transaction, TransactionCategory
from worker.celery_app import celery_app

settings = get_settings()
encryption = get_encryption_service()


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(TimeoutError, ConnectionError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=1800,
    soft_time_limit=1500,
)
def sync_credential_transactions(
    self: Task,
    credential_id: str,
    days_back: int = 7,
) -> dict[str, Any]:
    """Sync les transactions d'une credential bancaire. 100% synchrone."""
    try:
        return _sync_credential(credential_id, days_back, self.request.id)

    except SoftTimeLimitExceeded:
        _update_credential_status(credential_id, "timeout", "Task exceeded time limit")
        raise

    except TimeoutError as exc:
        _update_credential_status(credential_id, "error", "Bank connection timeout")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=min(60 * (2 ** self.request.retries), 600))
        raise MaxRetriesExceededError(f"Failed to sync after {self.max_retries} retries")

    except Exception as exc:
        _update_credential_status(credential_id, "error", str(exc)[:500])
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise MaxRetriesExceededError(f"Failed to sync after {self.max_retries} retries: {exc}")


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _sync_credential(
    credential_id: str,
    days_back: int,
    task_id: str | None,
) -> dict[str, Any]:
    with get_worker_session() as session:
        credential = session.execute(
            select(BankCredential).where(
                BankCredential.id == credential_id,
                BankCredential.is_active == True,
            )
        ).scalar_one_or_none()

        if not credential:
            return {
                "status": "error",
                "credential_id": credential_id,
                "error": "Credential not found or inactive",
            }

        # Decrypt
        try:
            login    = encryption.decrypt(credential.encrypted_login)
            password = encryption.decrypt(credential.encrypted_password)
        except Exception as e:
            credential.sync_status = "error"
            credential.sync_error_message = f"Decryption failed: {e}"
            session.commit()
            return {"status": "error", "credential_id": credential_id, "error": str(e)}

        # Mark syncing
        credential.sync_status = "syncing"
        credential.last_sync_at = datetime.utcnow()
        session.commit()

        # Fetch from bank (Woob — sync, blocking)
        try:
            woob_data = _fetch_woob_data(
                bank_name=credential.bank_name,
                bank_website=credential.bank_website,
                login=login,
                password=password,
                days_back=days_back,
            )
        except Exception as e:
            credential.sync_status = "error"
            credential.sync_error_message = str(e)[:500]
            session.commit()
            raise

        # Process
        user_id = credential.user_id
        stats = _process_transactions(session, user_id, credential_id, woob_data["transactions"])
        _process_accounts(session, user_id, credential_id, woob_data["accounts"])

        credential.sync_status = "success"
        credential.sync_error_message = None
        session.commit()

        return {
            "status":        "success",
            "credential_id":  credential_id,
            "task_id":        task_id,
            "processed":      len(woob_data["transactions"]),
            "created":        stats["created"],
            "duplicates":     stats["duplicates"],
            "errors":         stats["errors"],
        }


def _process_transactions(
    session: Any,
    user_id: str,
    credential_id: str,
    transactions_data: list[dict],
) -> dict[str, int]:
    created = duplicates = errors = 0

    for tx_data in transactions_data:
        try:
            key_data = f"{tx_data['date']}|{tx_data['amount']}|{tx_data['raw_label']}"
            tx_key   = hashlib.sha256(key_data.encode()).hexdigest()

            exists = session.execute(
                select(Transaction).where(
                    Transaction.transaction_key == tx_key,
                    Transaction.user_id == user_id,
                )
            ).first()

            if exists:
                duplicates += 1
                continue

            is_expense = tx_data["amount"] < 0
            amount     = abs(Decimal(str(tx_data["amount"])))

            session.add(Transaction(
                user_id=user_id,
                credential_id=credential_id,
                date=tx_data["date"],
                amount=amount,
                raw_label=tx_data["raw_label"],
                cleaned_label=None,
                category=TransactionCategory.OTHER,
                is_expense=is_expense,
                is_recurring=False,
                merchant_name=None,
                transaction_key=tx_key,
                currency=tx_data.get("currency", "EUR"),
            ))
            created += 1

        except Exception as e:
            errors += 1
            print(f"Error processing transaction: {e}")

    session.commit()
    return {"created": created, "duplicates": duplicates, "errors": errors}


def _process_accounts(
    session: Any,
    user_id: str,
    credential_id: str,
    accounts_data: list[dict],
) -> dict[str, int]:
    created = updated = 0

    for account_data in accounts_data:
        try:
            existing = session.execute(
                select(BankAccount).where(
                    BankAccount.account_id == account_data["id"],
                    BankAccount.user_id == user_id,
                )
            ).scalar_one_or_none()

            if existing:
                existing.balance       = Decimal(str(account_data["balance"]))
                existing.account_label = account_data["label"]
                existing.account_type  = str(account_data["type"])
                existing.currency      = account_data["currency"]
                existing.last_sync_at  = datetime.utcnow()
                updated += 1
            else:
                session.add(BankAccount(
                    user_id=user_id,
                    credential_id=credential_id,
                    account_id=account_data["id"],
                    account_label=account_data["label"],
                    account_type=str(account_data["type"]),
                    balance=Decimal(str(account_data["balance"])),
                    currency=account_data["currency"],
                    last_sync_at=datetime.utcnow(),
                ))
                created += 1

        except Exception as e:
            print(f"Error processing account {account_data.get('id')}: {e}")

    session.commit()
    return {"created": created, "updated": updated}


def _fetch_woob_data(
    bank_name: str,
    bank_website: str | None,
    login: str,
    password: str,
    days_back: int,
) -> dict[str, Any]:
    """Fetch via Woob (sync, blocking)."""
    from custom_woob_modules.cragr_custom.browser import CragrCustomBrowser

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

    website_url = CA_REGION_URLS.get(bank_website, bank_website) if bank_website else bank_website
    backend     = CragrCustomBrowser(website_url, login, password)
    since_date  = datetime.now() - timedelta(days=days_back)

    transactions: list[dict] = []
    accounts:     list[dict] = []

    for account in backend.iter_accounts():
        accounts.append({
            "id":       account.id,
            "label":    account.label,
            "type":     account.type,
            "balance":  float(account.balance) if hasattr(account, "balance") and account.balance else 0.0,
            "currency": account.currency or "EUR",
            "number":   account.number if hasattr(account, "number") else None,
        })

        for history in backend.iter_history(account):
            if history.date < since_date:
                continue
            tx_date = history.date.date() if hasattr(history.date, "date") else history.date
            transactions.append({
                "date":      tx_date,
                "amount":    float(history.amount),
                "raw_label": history.label or history.raw or "Unknown",
                "currency":  account.currency or "EUR",
            })

    backend.deinit()
    return {"transactions": transactions, "accounts": accounts}


def _update_credential_status(credential_id: str, status: str, message: str | None) -> None:
    """Mise à jour du statut (best effort, ne lève pas d'exception)."""
    try:
        with get_worker_session() as session:
            credential = session.execute(
                select(BankCredential).where(BankCredential.id == credential_id)
            ).scalar_one_or_none()
            if credential:
                credential.sync_status = status
                credential.sync_error_message = message
                session.commit()
    except Exception:
        pass