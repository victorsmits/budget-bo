"""RQ Jobs - Functions that run in the worker."""

import asyncio
import hashlib
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

# Add /app to path for custom_woob_modules
sys.path.insert(0, "/app")

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.security import get_encryption_service
from app.models.models import BankCredential, Transaction, TransactionCategory
from sqlalchemy import select

settings = get_settings()
encryption = get_encryption_service()


async def _async_sync_transactions(user_id: str, credential_id: str, days_back: int) -> dict[str, Any]:
    """Async implementation of transaction sync."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BankCredential).where(
                BankCredential.id == credential_id,
                BankCredential.user_id == user_id,
                BankCredential.is_active == True,
            )
        )
        credential = result.scalar_one_or_none()

        if not credential:
            return {"status": "error", "error": "Credential not found or inactive"}

        try:
            login = encryption.decrypt(credential.encrypted_login)
            password = encryption.decrypt(credential.encrypted_password)
        except Exception as e:
            credential.sync_status = "error"
            credential.sync_error_message = f"Decryption failed: {e}"
            await session.commit()
            return {"status": "error", "error": f"Failed to decrypt credentials: {e}"}

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
        except Exception as e:
            credential.sync_status = "error"
            credential.sync_error_message = str(e)[:500]
            await session.commit()
            raise

        created_count = 0
        duplicate_count = 0

        for tx_data in transactions_data:
            try:
                key_data = f"{tx_data['date']}|{tx_data['amount']}|{tx_data['raw_label']}"
                tx_key = hashlib.sha256(key_data.encode()).hexdigest()

                existing = await session.execute(
                    select(Transaction).where(
                        Transaction.transaction_key == tx_key,
                        Transaction.user_id == user_id,
                    )
                )
                if existing.scalar_one_or_none():
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
                print(f"Error processing transaction: {e}")
                continue

        await session.commit()

        credential.sync_status = "success"
        credential.sync_error_message = None
        await session.commit()

        return {
            "status": "success",
            "credential_id": credential_id,
            "processed": len(transactions_data),
            "created": created_count,
            "duplicates": duplicate_count,
        }


def sync_transactions_job(user_id: str, credential_id: str, days_back: int = 30) -> dict[str, Any]:
    """RQ Job: Sync transactions for a specific credential."""
    return asyncio.run(_async_sync_transactions(user_id, credential_id, days_back))


async def _async_enrich_transactions(user_id: str, days_back: int) -> dict[str, Any]:
    """Async implementation of transaction enrichment."""
    from app.services.ollama import get_ollama_service

    ollama = get_ollama_service()
    enriched_count = 0
    error_count = 0

    async with AsyncSessionLocal() as session:
        since_date = datetime.now() - timedelta(days=days_back)

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
                normalization = await ollama.normalize_label(tx.raw_label)

                tx.cleaned_label = normalization["cleaned_label"]
                tx.merchant_name = normalization["merchant_name"]
                tx.ai_confidence = normalization["confidence"]

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


def enrich_transactions_job(user_id: str, days_back: int = 30) -> dict[str, Any]:
    """RQ Job: Enrich transactions with AI categorization."""
    return asyncio.run(_async_enrich_transactions(user_id, days_back))


async def _async_sync_all_users() -> dict[str, Any]:
    """Async implementation to queue sync for all users."""
    from worker.rq_queue import enqueue_sync_transactions

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BankCredential).where(BankCredential.is_active == True)
        )
        credentials = result.scalars().all()

        for c in credentials:
            enqueue_sync_transactions(str(c.user_id), str(c.id), days_back=1)

        return {
            "status": "queued",
            "credentials_count": len(credentials),
        }


def sync_all_users_job() -> dict[str, Any]:
    """RQ Job: Sync all active credentials."""
    return asyncio.run(_async_sync_all_users())


async def _fetch_woob_transactions(
    bank_name: str,
    bank_website: str | None,
    login: str,
    password: str,
    days_back: int,
) -> list[dict[str, Any]]:
    """Fetch transactions using Woob."""
    from datetime import datetime, timedelta as td
    from custom_woob_modules.cragr_custom.browser import CragrCustomBrowser

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

    website_url = bank_website
    if bank_website and bank_website in CA_REGION_URLS:
        website_url = CA_REGION_URLS[bank_website]

    backend = CragrCustomBrowser(website_url, login, password)

    transactions: list[dict[str, Any]] = []
    since_date = datetime.now() - td(days=days_back)

    for account in backend.iter_accounts():
        for history in backend.iter_history(account):
            if history.date < since_date:
                continue

            tx_date = history.date.date() if hasattr(history.date, 'date') else history.date

            transactions.append({
                "date": tx_date,
                "amount": float(history.amount),
                "raw_label": history.label or history.raw or "Unknown",
                "currency": account.currency or "EUR",
            })

    backend.deinit()

    return transactions
