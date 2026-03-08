"""Bank transaction synchronization job - dedicated file for sync operations."""

import asyncio
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
from app.core.database import create_worker_session
from app.core.security import get_encryption_service
from app.models.models import BankCredential, BankAccount, Transaction, TransactionCategory
from worker.celery_app import celery_app

settings = get_settings()
encryption = get_encryption_service()


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(TimeoutError, ConnectionError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=1800,  # 30 minutes
    soft_time_limit=1500,  # 25 minutes
)
def sync_credential_transactions(
    self: Task,
    credential_id: str,
    days_back: int = 7,
) -> dict[str, Any]:
    """
    Sync transactions for a specific bank credential.

    This task runs in the 'sync' queue and can execute in parallel
    with other sync tasks for different credentials.
    """
    try:
        return asyncio.run(
            _async_sync_credential(credential_id, days_back, self.request.id)
        )
    except SoftTimeLimitExceeded:
        _update_credential_status(credential_id, "timeout", "Task exceeded time limit")
        raise
    except TimeoutError as exc:
        if self.request.retries < self.max_retries:
            retry_in = 60 * (2**self.request.retries)
            raise self.retry(
                exc=exc,
                countdown=min(retry_in, 600),
                reason=f"Bank timeout, retrying in {retry_in}s",
            )
        _update_credential_status(credential_id, "error", "Max retries exceeded")
        raise MaxRetriesExceededError(
            f"Failed to sync after {self.max_retries} retries"
        )
    except Exception as exc:
        _update_credential_status(credential_id, "error", str(exc)[:500])
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise MaxRetriesExceededError(
            f"Failed to sync after {self.max_retries} retries: {exc}"
        )


async def _async_sync_credential(
    credential_id: str,
    days_back: int,
    task_id: str | None,
) -> dict[str, Any]:
    """Async implementation of credential transaction sync."""
    session = create_worker_session()
    try:
        # Fetch credential
        result = await session.execute(
            select(BankCredential).where(
                BankCredential.id == credential_id,
                BankCredential.is_active == True,
            )
        )
        credential = result.scalar_one_or_none()

        if not credential:
            return {
                "status": "error",
                "credential_id": credential_id,
                "error": "Credential not found or inactive",
            }

        # Decrypt credentials
        try:
            login = encryption.decrypt(credential.encrypted_login)
            password = encryption.decrypt(credential.encrypted_password)
        except Exception as e:
            credential.sync_status = "error"
            credential.sync_error_message = f"Decryption failed: {e}"
            await session.commit()
            return {
                "status": "error",
                "credential_id": credential_id,
                "error": f"Failed to decrypt credentials: {e}",
            }

        # Mark as syncing
        credential.sync_status = "syncing"
        credential.last_sync_at = datetime.utcnow()
        await session.commit()

        # Fetch transactions and account data
        try:
            woob_data = await _fetch_woob_data(
                bank_name=credential.bank_name,
                bank_website=credential.bank_website,
                login=login,
                password=password,
                days_back=days_back,
            )
        except TimeoutError:
            credential.sync_status = "error"
            credential.sync_error_message = "Bank connection timeout"
            await session.commit()
            raise
        except Exception as e:
            credential.sync_status = "error"
            credential.sync_error_message = str(e)[:500]
            await session.commit()
            raise

        # Process transactions
        stats = await _process_transactions(
            session, credential.user_id, credential_id, woob_data["transactions"]
        )

        # Process accounts (store/update balances)
        await _process_accounts(
            session, credential.user_id, credential_id, woob_data["accounts"]
        )

        # Mark as success
        credential.sync_status = "success"
        credential.sync_error_message = None
        await session.commit()

        return {
            "status": "success",
            "credential_id": credential_id,
            "task_id": task_id,
            "processed": len(woob_data["transactions"]),
            "created": stats["created"],
            "duplicates": stats["duplicates"],
            "errors": stats["errors"],
        }

    except Exception:
        await session.rollback()
        raise
    finally:
        engine = session.bind
        await session.close()
        await engine.dispose()


async def _process_transactions(
    session: Any,
    user_id: str,
    credential_id: str,
    transactions_data: list[dict],
) -> dict[str, int]:
    """Process and store fetched transactions."""
    created_count = 0
    duplicate_count = 0
    error_count = 0

    for tx_data in transactions_data:
        try:
            # Generate unique key
            key_data = f"{tx_data['date']}|{tx_data['amount']}|{tx_data['raw_label']}"
            tx_key = hashlib.sha256(key_data.encode()).hexdigest()

            # Check for duplicates
            result = await session.execute(
                select(Transaction).where(
                    Transaction.transaction_key == tx_key,
                    Transaction.user_id == user_id,
                )
            )
            if result.first():
                duplicate_count += 1
                continue

            # Create transaction
            is_expense = tx_data["amount"] < 0
            amount = abs(Decimal(str(tx_data["amount"])))

            transaction = Transaction(
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
            )
            session.add(transaction)
            created_count += 1

        except Exception as e:
            error_count += 1
            print(f"Error processing transaction: {e}")
            continue

    await session.commit()

    return {
        "created": created_count,
        "duplicates": duplicate_count,
        "errors": error_count,
    }


async def _fetch_woob_data(
    bank_name: str,
    bank_website: str | None,
    login: str,
    password: str,
    days_back: int,
) -> dict[str, Any]:
    """Fetch transactions and account data using Woob with custom patched module."""
    from custom_woob_modules.cragr_custom.browser import CragrCustomBrowser

    # Region mapping
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

    transactions: list[dict[str, Any]] = []
    accounts: list[dict[str, Any]] = []

    # Convert region code to URL
    website_url = bank_website
    if bank_website and bank_website in CA_REGION_URLS:
        website_url = CA_REGION_URLS[bank_website]

    backend = CragrCustomBrowser(website_url, login, password)

    since_date = datetime.now() - timedelta(days=days_back)

    for account in backend.iter_accounts():
        # Store account info with balance
        account_data = {
            "id": account.id,
            "label": account.label,
            "type": account.type,
            "balance": float(account.balance) if hasattr(account, "balance") and account.balance else 0.0,
            "currency": account.currency or "EUR",
            "number": account.number if hasattr(account, "number") else None,
        }
        accounts.append(account_data)

        # Fetch transactions for this account
        for history in backend.iter_history(account):
            if history.date < since_date:
                continue

            tx_date = history.date.date() if hasattr(history.date, "date") else history.date

            transactions.append({
                "date": tx_date,
                "amount": float(history.amount),
                "raw_label": history.label or history.raw or "Unknown",
                "currency": account.currency or "EUR",
            })

    backend.deinit()

    return {
        "transactions": transactions,
        "accounts": accounts,
    }


async def _process_accounts(
    session: Any,
    user_id: str,
    credential_id: str,
    accounts_data: list[dict],
) -> dict[str, int]:
    """Process and store/update account balances."""
    created_count = 0
    updated_count = 0
    
    for account_data in accounts_data:
        try:
            # Check if account already exists
            result = await session.execute(
                select(BankAccount).where(
                    BankAccount.account_id == account_data["id"],
                    BankAccount.user_id == user_id,
                )
            )
            existing_account = result.scalar_one_or_none()
            
            if existing_account:
                # Update existing account
                existing_account.balance = Decimal(str(account_data["balance"]))
                existing_account.account_label = account_data["label"]
                existing_account.account_type = str(account_data["type"])
                existing_account.currency = account_data["currency"]
                existing_account.last_sync_at = datetime.utcnow()
                updated_count += 1
            else:
                # Create new account
                account = BankAccount(
                    user_id=user_id,
                    credential_id=credential_id,
                    account_id=account_data["id"],
                    account_label=account_data["label"],
                    account_type=str(account_data["type"]),
                    balance=Decimal(str(account_data["balance"])),
                    currency=account_data["currency"],
                    last_sync_at=datetime.utcnow(),
                )
                session.add(account)
                created_count += 1
                
        except Exception as e:
            print(f"Error processing account {account_data.get('id')}: {e}")
            continue
    
    await session.commit()
    
    return {
        "created": created_count,
        "updated": updated_count,
    }


def _update_credential_status(credential_id: str, status: str, message: str | None) -> None:
    """Update credential sync status (best effort)."""
    try:
        asyncio.run(_async_update_status(credential_id, status, message))
    except Exception:
        pass


async def _async_update_status(
    credential_id: str, status: str, message: str | None
) -> None:
    """Async status update."""
    session = create_worker_session()
    try:
        result = await session.execute(
            select(BankCredential).where(BankCredential.id == credential_id)
        )
        credential = result.scalar_one_or_none()
        if credential:
            credential.sync_status = status
            credential.sync_error_message = message
            await session.commit()
    finally:
        engine = session.bind
        await session.close()
        await engine.dispose()
