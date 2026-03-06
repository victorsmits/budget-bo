"""User profile API endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.auth import require_user
from app.core.database import AsyncSessionLocal
from app.models.models import (
    BankCredential,
    Transaction,
    User,
)

router = APIRouter(prefix="/users", tags=["users"])


async def get_session() -> AsyncSession:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/me", response_model=dict[str, Any])
async def get_user_profile(
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get current user profile with statistics."""
    # Get basic user info
    profile = {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "profile_picture": user.profile_picture,
        "created_at": user.created_at,
        "last_login": user.updated_at,
    }

    # Get statistics
    # Number of credentials
    credentials_result = await session.execute(
        select(func.count()).select_from(BankCredential).where(
            BankCredential.user_id == user.id,
            BankCredential.is_active == True,
        )
    )
    profile["active_credentials"] = credentials_result.scalar() or 0

    # Number of transactions
    transactions_result = await session.execute(
        select(func.count()).select_from(Transaction).where(
            Transaction.user_id == user.id
        )
    )
    profile["total_transactions"] = transactions_result.scalar() or 0

    # Last sync date
    last_sync_result = await session.execute(
        select(func.max(Transaction.date)).where(Transaction.user_id == user.id)
    )
    profile["last_transaction_date"] = last_sync_result.scalar()

    return profile


@router.patch("/me", response_model=dict[str, Any])
async def update_user_profile(
    updates: dict[str, Any],
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Update current user profile."""
    allowed_fields = {"display_name"}
    
    for field, value in updates.items():
        if field not in allowed_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Field '{field}' cannot be updated",
            )
        setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(user)

    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "profile_picture": user.profile_picture,
        "updated_at": user.updated_at,
    }


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete user account and all associated data (GDPR compliance)."""
    # Delete all user's transactions
    await session.execute(
        delete(Transaction).where(Transaction.user_id == user.id)
    )
    
    # Delete all user's credentials
    await session.execute(
        delete(BankCredential).where(BankCredential.user_id == user.id)
    )
    
    # Delete the user
    await session.delete(user)
    await session.commit()


@router.get("/me/stats", response_model=dict[str, Any])
async def get_user_stats(
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get detailed statistics for current user."""
    from datetime import date, timedelta
    from decimal import Decimal
    
    # Date ranges
    today = date.today()
    this_month_start = today.replace(day=1)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    three_months_ago = today - timedelta(days=90)
    
    stats = {}
    
    # Transaction counts by period
    for period_name, start_date in [
        ("this_month", this_month_start),
        ("last_month", last_month_start),
        ("last_three_months", three_months_ago),
    ]:
        count_result = await session.execute(
            select(func.count()).select_from(Transaction).where(
                Transaction.user_id == user.id,
                Transaction.date >= start_date,
            )
        )
        stats[f"transactions_{period_name}"] = count_result.scalar() or 0
    
    # Financial summaries
    for period_name, start_date in [
        ("this_month", this_month_start),
        ("last_month", last_month_start),
    ]:
        # Total expenses
        expense_result = await session.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == user.id,
                Transaction.date >= start_date,
                Transaction.is_expense == True,
            )
        )
        stats[f"total_expenses_{period_name}"] = float(expense_result.scalar() or Decimal('0'))
        
        # Total income
        income_result = await session.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == user.id,
                Transaction.date >= start_date,
                Transaction.is_expense == False,
            )
        )
        stats[f"total_income_{period_name}"] = float(income_result.scalar() or Decimal('0'))
    
    # Category breakdown for current month
    category_result = await session.execute(
        select(
            Transaction.category,
            func.count().label('count'),
            func.coalesce(func.sum(Transaction.amount), 0).label('total'),
        ).where(
            Transaction.user_id == user.id,
            Transaction.date >= this_month_start,
            Transaction.is_expense == True,
        ).group_by(Transaction.category)
    )
    
    stats["expenses_by_category_this_month"] = [
        {
            "category": row.category.value,
            "count": row.count,
            "total": float(row.total),
        }
        for row in category_result.all()
    ]
    
    return stats
