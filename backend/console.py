#!/usr/bin/env python
"""Interactive console for Budget Bo backend.

Usage:
    docker compose exec backend python console.py

This opens an IPython shell with pre-loaded models and utilities.
"""

import asyncio
import sys

# Add app to path
sys.path.insert(0, "/app")

# Pre-load common imports
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, func

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.security import get_encryption_service
from app.models.models import (
    User,
    BankCredential,
    Transaction,
    RecurringExpense,
    TransactionCategory,
)
from app.services.ollama import get_ollama_service
from app.services.recurring import RecurringExpenseService

settings = get_settings()
encryption = get_encryption_service()


async def get_db():
    """Get a database session."""
    return AsyncSessionLocal()


def run_async(coro):
    """Run an async function."""
    return asyncio.run(coro)


# Try to import IPython
try:
    from IPython import embed
    
    print("=" * 60)
    print("Budget Bo Console - FastAPI Interactive Shell")
    print("=" * 60)
    print()
    print("Pre-loaded objects:")
    print("  - User, BankCredential, Transaction, RecurringExpense")
    print("  - TransactionCategory")
    print("  - settings, encryption")
    print("  - get_db(), run_async()")
    print("  - get_ollama_service(), RecurringExpenseService")
    print()
    print("Example usage:")
    print("  >>> session = run_async(get_db().__aenter__())")
    print("  >>> result = run_async(session.execute(select(User)))")
    print("  >>> users = result.scalars().all()")
    print("  >>> run_async(session.close())")
    print()
    print("=" * 60)
    
    embed()
    
except ImportError:
    print("IPython not available, falling back to standard Python console")
    
    import code
    
    # Create local namespace
    locals_dict = {
        "asyncio": asyncio,
        "datetime": datetime,
        "timedelta": timedelta,
        "uuid4": uuid4,
        "select": select,
        "func": func,
        "settings": settings,
        "encryption": encryption,
        "User": User,
        "BankCredential": BankCredential,
        "Transaction": Transaction,
        "RecurringExpense": RecurringExpense,
        "TransactionCategory": TransactionCategory,
        "get_db": get_db,
        "run_async": run_async,
        "get_ollama_service": get_ollama_service,
        "RecurringExpenseService": RecurringExpenseService,
    }
    
    print("=" * 60)
    print("Budget Bo Console - Python Shell")
    print("=" * 60)
    print()
    print("Available: asyncio, select, User, Transaction, etc.")
    print()
    
    code.interact(local=locals_dict)
