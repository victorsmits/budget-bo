#!/usr/bin/env python3
"""Script to enrich all unprocessed transactions."""

import asyncio
import sys
from datetime import datetime, timedelta

# Add app to path
sys.path.insert(0, '/app')

from app.core.database import AsyncSessionLocal
from app.models.models import Transaction, TransactionCategory
from app.services.ollama import get_ollama_service
from sqlalchemy import select


async def enrich_all_transactions():
    """Enrich a sample of unprocessed transactions."""
    ollama = get_ollama_service()
    enriched_count = 0
    error_count = 0
    
    async with AsyncSessionLocal() as session:
        # Fetch only 3 unenriched transactions for testing
        result = await session.execute(
            select(Transaction).where(Transaction.enriched_at.is_(None)).limit(3)
        )
        transactions = result.scalars().all()
        
        print(f"Testing with {len(transactions)} unenriched transactions")
        
        for i, tx in enumerate(transactions):
            try:
                print(f"Processing {i+1}/{len(transactions)}: {tx.raw_label[:50]}...")
                
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
                
                # Commit every 5 transactions
                if (i + 1) % 5 == 0:
                    await session.commit()
                    print(f"  Committed {enriched_count} transactions so far...")
                
            except Exception as e:
                error_count += 1
                print(f"  Error: {e}")
                continue
        
        # Final commit
        await session.commit()
    
    print(f"\nDone! Enriched: {enriched_count}, Errors: {error_count}")


if __name__ == "__main__":
    asyncio.run(enrich_all_transactions())
