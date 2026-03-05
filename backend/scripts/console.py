#!/usr/bin/env python
"""Interactive console for Budget Bo backend.

Usage:
    docker compose exec backend python -m scripts.console
"""

import asyncio
import sys

sys.path.insert(0, "/app")

# Import after path setup
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

# Import worker tasks
from worker.tasks.sync_tasks import sync_user_transactions, _async_sync_user_transactions

settings = get_settings()
encryption = get_encryption_service()


async def _query(q):
    """Execute a query and return results."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(q)
        return result.scalars().all()


async def _count(model):
    """Count records in a table."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count()).select_from(model))
        return result.scalar()


banner = """
╔═══════════════════════════════════════════════════════════════╗
║           Budget Bo - Interactive Console                      ║
╠═══════════════════════════════════════════════════════════════╣
║ Available:                                                    ║
║   - User, BankCredential, Transaction, RecurringExpense       ║
║   - TransactionCategory                                       ║
║   - settings, encryption                                      ║
║   - _query(), _count(), AsyncSessionLocal                     ║
╠═══════════════════════════════════════════════════════════════╣
║ Examples:                                                     ║
║   >>> import asyncio                                          ║
║   >>> asyncio.run(_count(User))                               ║
║   >>> asyncio.run(_query(select(Transaction)))                ║
║   >>> session = asyncio.run(AsyncSessionLocal().__aenter__()) ║
╚═══════════════════════════════════════════════════════════════╝
"""


# Import IPython
try:
    from IPython import start_ipython
    
    # Start IPython with our namespace
    user_ns = {
        "User": User,
        "BankCredential": BankCredential,
        "Transaction": Transaction,
        "RecurringExpense": RecurringExpense,
        "TransactionCategory": TransactionCategory,
        "select": select,
        "func": func,
        "settings": settings,
        "encryption": encryption,
        "_query": _query,
        "_count": _count,
        "AsyncSessionLocal": AsyncSessionLocal,
        "asyncio": __import__("asyncio"),
        "sync_user_transactions": sync_user_transactions,
        "_async_sync_user_transactions": _async_sync_user_transactions,
    }
    
    print(banner)
    start_ipython(argv=[], user_ns=user_ns)
    
except ImportError:
    print("IPython not available")
    import code
    code.interact(local={
        "User": User,
        "BankCredential": BankCredential,
        "Transaction": Transaction,
        "select": select,
    })
