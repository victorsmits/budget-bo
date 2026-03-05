#!/usr/bin/env python
"""
Interactive debug console for Budget Bo backend.

Usage:
    docker compose exec backend python -m scripts.console

This launches an IPython session with pre-loaded models and database session.
"""

import asyncio
from decimal import Decimal
from uuid import UUID

import ipdb
from IPython import embed
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.security import EncryptionService, get_encryption_service
from app.models.models import (
    BankCredential,
    BankCredentialCreate,
    RecurringExpense,
    Transaction,
    TransactionCategory,
    User,
    UserCreate,
)

settings = get_settings()
encryption = get_encryption_service()


async def init_console() -> dict:
    """Initialize console with database session and common objects."""
    session: AsyncSession = AsyncSessionLocal()

    # Pre-fetch some data for convenience
    users_result = await session.execute(select(User).limit(5))
    users = users_result.scalars().all()

    transactions_result = await session.execute(select(Transaction).limit(5))
    transactions = transactions_result.scalars().all()

    namespace = {
        # Database
        "session": session,
        "AsyncSessionLocal": AsyncSessionLocal,
        "select": select,
        # Models
        "User": User,
        "UserCreate": UserCreate,
        "BankCredential": BankCredential,
        "BankCredentialCreate": BankCredentialCreate,
        "Transaction": Transaction,
        "TransactionCategory": TransactionCategory,
        "RecurringExpense": RecurringExpense,
        # Utilities
        "settings": settings,
        "encryption": encryption,
        "EncryptionService": EncryptionService,
        "UUID": UUID,
        "Decimal": Decimal,
        # Pre-loaded data
        "users": users,
        "transactions": transactions,
    }

    return namespace


def run_console() -> None:
    """Run the interactive console."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║           Budget Bo - Debug Console (Rails-style)            ║
╠═══════════════════════════════════════════════════════════════╣
║ Available objects:                                            ║
║   session          - Async database session                   ║
║   User             - User model                               ║
║   BankCredential   - Bank credential model                  ║
║   Transaction      - Transaction model                      ║
║   RecurringExpense - Recurring expense model                ║
║   encryption       - EncryptionService instance             ║
║   settings         - Application settings                   ║
║                                                               ║
║ Example usage:                                                ║
║   await session.execute(select(User))                       ║
║   encryption.decrypt(credential.encrypted_login)            ║
╚═══════════════════════════════════════════════════════════════╝
    """

    # Run async init
    namespace = asyncio.run(init_console())

    # Start IPython
    embed(
        header=banner,
        colors="neutral",
        using=namespace,
    )


if __name__ == "__main__":
    run_console()
