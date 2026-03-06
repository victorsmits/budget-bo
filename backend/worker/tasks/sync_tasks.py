"""Transaction synchronization tasks using Woob."""

import asyncio
import hashlib
import sys
from datetime import datetime
from decimal import Decimal
from typing import Any

# Add /app to path for custom_woob_modules
sys.path.insert(0, "/app")

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.security import get_encryption_service
from app.models.models import (
    BankCredential,
    Transaction,
    TransactionCategory,
)
from celery import Task, group
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded
from sqlalchemy import select
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
)
def sync_user_transactions(
    self: Task,
    user_id: str,
    credential_id: str,
    days_back: int = 7,
) -> dict[str, Any]:
    """
    Sync transactions for a specific user's bank credential.

    Uses Woob/cragr to fetch transactions with robust error handling
    and retry logic for bank timeouts.
    """
    try:
        return asyncio.run(_async_sync_user_transactions(user_id, credential_id, days_back))
    except SoftTimeLimitExceeded:
        raise
    except TimeoutError as exc:
        if self.request.retries < self.max_retries:
            retry_in = 60 * (2**self.request.retries)
            raise self.retry(
                exc=exc,
                countdown=min(retry_in, 600),
                reason=f"Bank timeout, retrying in {retry_in}s",
            )
        raise
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise MaxRetriesExceededError(
            f"Failed to sync transactions after {self.max_retries} retries: {exc}"
        )


async def _async_sync_user_transactions(
    user_id: str,
    credential_id: str,
    days_back: int,
) -> dict[str, Any]:
    """Async implementation of transaction sync."""
    session = None
    try:
        session = AsyncSessionLocal()
        created_count = 0
        duplicate_count = 0
        error_count = 0
        transactions_data: list[dict] = []

        result = await session.execute(
            select(BankCredential).where(
                BankCredential.id == credential_id,
                BankCredential.user_id == user_id,
                BankCredential.is_active == True,
            )
        )
        credential = result.scalar_one_or_none()

        if not credential:
            return {
                "status": "error",
                "error": "Credential not found or inactive",
            }

        try:
            login = encryption.decrypt(credential.encrypted_login)
            password = encryption.decrypt(credential.encrypted_password)
        except Exception as e:
            credential.sync_status = "error"
            credential.sync_error_message = f"Decryption failed: {e}"
            await session.commit()
            return {
                "status": "error",
                "error": f"Failed to decrypt credentials: {e}",
            }

        credential.sync_status = "syncing"
        credential.last_sync_at = datetime.utcnow()
        await session.commit()

        try:
            transactions_data = await _fetch_woob_transactions(
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

        for tx_data in transactions_data:
            try:
                key_data = (
                    f"{tx_data['date']}|{tx_data['amount']}|{tx_data['raw_label']}"
                )
                tx_key = hashlib.sha256(key_data.encode()).hexdigest()

                existing = await session.execute(
                    select(Transaction).where(
                        Transaction.transaction_key == tx_key,
                        Transaction.user_id == user_id,
                    )
                )
                if existing.first():  # Utiliser first() au lieu de scalar_one_or_none()
                    duplicate_count += 1
                    continue

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

        credential.sync_status = "success"
        credential.sync_error_message = None
        await session.commit()

        if created_count > 0:
            enrich_new_transactions.delay(user_id, days_back)

        return {
            "status": "success",
            "credential_id": credential_id,
            "processed": len(transactions_data),
            "created": created_count,
            "duplicates": duplicate_count,
            "errors": error_count,
        }

    except Exception as e:
        if session:
            await session.rollback()
        raise
    finally:
        if session:
            await session.close()


async def _fetch_woob_transactions(
    bank_name: str,
    bank_website: str | None,
    login: str,
    password: str,
    days_back: int,
) -> list[dict[str, Any]]:
    """
    Fetch transactions using Woob - using custom patched module for API 2025.
    """
    from datetime import datetime
    from datetime import timedelta as td

    # Mapping de région CA vers URL valide (basé sur la liste des sites acceptés par Woob)
    CA_REGION_URLS = {
        'ca-alpesprovence': 'www.ca-alpesprovence.fr',
        'ca-alsace-vosges': 'www.ca-alsace-vosges.fr',
        'ca-anjou-maine': 'www.ca-anjou-maine.fr',
        'ca-aquitaine': 'www.ca-aquitaine.fr',
        'ca-atlantique-vendee': 'www.ca-atlantique-vendee.fr',
        'ca-briepicardie': 'www.ca-briepicardie.fr',
        'ca-cb': 'www.ca-cb.fr',
        'ca-centrefrance': 'www.ca-centrefrance.fr',
        'ca-centreloire': 'www.ca-centreloire.fr',
        'ca-centreouest': 'www.ca-centreouest.fr',
        'ca-centrest': 'www.ca-centrest.fr',
        'ca-charente-perigord': 'www.ca-charente-perigord.fr',
        'ca-cmds': 'www.ca-cmds.fr',
        'ca-corse': 'www.ca-corse.fr',
        'ca-cotesdarmor': 'www.ca-cotesdarmor.fr',
        'ca-des-savoie': 'www.ca-des-savoie.fr',
        'ca-finistere': 'www.ca-finistere.fr',
        'ca-franchecomte': 'www.ca-franchecomte.fr',
        'ca-guadeloupe': 'www.ca-guadeloupe.fr',
        'ca-illeetvilaine': 'www.ca-illeetvilaine.fr',
        'ca-languedoc': 'www.ca-languedoc.fr',
        'ca-loirehauteloire': 'www.ca-loirehauteloire.fr',
        'ca-lorraine': 'www.ca-lorraine.fr',
        'ca-martinique': 'www.ca-martinique.fr',
        'ca-morbihan': 'www.ca-morbihan.fr',
        'ca-nmp': 'www.ca-nmp.fr',
        'ca-nord-est': 'www.ca-nord-est.fr',
        'ca-norddefrance': 'www.ca-norddefrance.fr',
        'ca-normandie-seine': 'www.ca-normandie-seine.fr',
        'ca-normandie': 'www.ca-normandie.fr',
        'ca-paris': 'www.ca-paris.fr',
        'ca-pca': 'www.ca-pca.fr',
        'ca-pyrenees-gascogne': 'www.ca-pyrenees-gascogne.fr',
        'ca-reunion': 'www.ca-reunion.fr',
        'ca-sudmed': 'www.ca-sudmed.fr',
        'ca-sudrhonealpes': 'www.ca-sudrhonealpes.fr',
        'ca-toulouse': 'www.ca-toulouse31.fr',
        'ca-tourainepoitou': 'www.ca-tourainepoitou.fr',
        'ca-valdefrance': 'www.ca-valdefrance.fr',
        'ca-champagne-bourgogne': 'www.ca-champagnebourgogne.fr',
        'ca-bretagne-pays-de-loire': 'www.ca-bretagnepaysdelaloire.fr',
    }
    
    transactions: list[dict[str, Any]] = []
    
    # Convertir code région en URL valide
    website_url = bank_website
    if bank_website and bank_website in CA_REGION_URLS:
        website_url = CA_REGION_URLS[bank_website]
    
    # Import and use custom browser
    from custom_woob_modules.cragr_custom.browser import CragrCustomBrowser
    
    backend = CragrCustomBrowser(
        website_url,
        login,
        password,
    )
    
    # Fetch accounts and transactions using iter_accounts/iter_history
    since_date = datetime.now() - td(days=days_back)
    
    for account in backend.iter_accounts():
        for history in backend.iter_history(account):
            if history.date < since_date:
                continue
            
            # Handle both date and datetime objects
            tx_date = history.date.date() if hasattr(history.date, 'date') else history.date
            
            transactions.append({
                "date": tx_date,
                "amount": float(history.amount),
                "raw_label": history.label or history.raw or "Unknown",
                "currency": account.currency or "EUR",
            })
    
    backend.deinit()
    
    return transactions



@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def enrich_new_transactions(
    self: Task,
    user_id: str,
    days_back: int = 7,
) -> dict[str, Any]:
    """
    Enrich unprocessed transactions using local AI (Ollama).
    """
    try:
        return asyncio.run(_async_enrich_transactions(user_id, days_back))
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise


async def _async_enrich_transactions(
    user_id: str,
    days_back: int,
) -> dict[str, Any]:
    """Async implementation of transaction enrichment."""
    from datetime import datetime
    from datetime import timedelta as td

    from app.services.ollama import get_ollama_service
    from sqlalchemy import select

    ollama = get_ollama_service()
    enriched_count = 0
    error_count = 0

    async with AsyncSessionLocal() as session:
        since_date = datetime.now() - td(days=days_back)

        # Fetch unenriched transactions
        result = await session.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.enriched_at.is_(None),
                Transaction.date >= since_date.date(),
            )
        )
        transactions = result.scalars().all()

        for tx in transactions:
            try:
                # Normalize label with AI
                normalization = await ollama.normalize_label(tx.raw_label)

                tx.cleaned_label = normalization["cleaned_label"]
                tx.merchant_name = normalization["merchant_name"]
                tx.ai_confidence = normalization["confidence"]

                # Map category string to enum
                category_str = normalization["category"].upper()
                try:
                    tx.category = TransactionCategory[category_str]
                except KeyError:
                    tx.category = TransactionCategory.OTHER

                tx.enriched_at = datetime.utcnow()
                enriched_count += 1

            except Exception as e:
                error_count += 1
                print(f"Error enriching transaction {tx.id}: {e}")
                continue

        await session.commit()

    return {
        "status": "success",
        "enriched": enriched_count,
        "errors": error_count,
        "user_id": user_id,
    }


@celery_app.task(bind=True)
def sync_all_users_transactions(self: Task) -> dict[str, Any]:
    """Daily job to sync transactions for all active users."""
    try:
        return asyncio.run(_async_sync_all_users())
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


async def _async_sync_all_users() -> dict[str, Any]:
    """Async implementation to queue sync tasks for all users."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BankCredential).where(BankCredential.is_active == True)
        )
        credentials = result.scalars().all()

        tasks = [
            sync_user_transactions.s(
                str(c.user_id),
                str(c.id),
                days_back=1,
            )
            for c in credentials
        ]

        if tasks:
            job = group(tasks)
            result = job.apply_async()

            return {
                "status": "queued",
                "credentials_count": len(credentials),
                "task_id": result.id,
            }

        return {
            "status": "no_credentials",
            "credentials_count": 0,
        }
