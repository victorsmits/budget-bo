#!/usr/bin/env python
"""Seed database with test data for development."""

import asyncio
from uuid import uuid4

from app.core.database import AsyncSessionLocal
from app.core.security import get_encryption_service
from app.models.models import User


async def seed_test_user() -> None:
    """Create a test user if none exists."""
    async with AsyncSessionLocal() as session:
        # Check if test user exists
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.email == "test@example.com")
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"Test user already exists: {existing.id}")
            return
        
        # Create test user
        user = User(
            id=uuid4(),
            email="test@example.com",
            oauth_id="test_oauth_123",
            display_name="Test User",
            is_active=True,
        )
        
        session.add(user)
        await session.commit()
        
        print(f"Created test user: {user.id}")
        print(f"Email: {user.email}")


if __name__ == "__main__":
    asyncio.run(seed_test_user())
