"""Bank accounts API endpoints for real balances."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.auth import require_user
from app.core.database import AsyncSessionLocal
from app.models.models import (
    BankAccount,
    BankAccountPublic,
    User,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


async def get_session() -> AsyncSession:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        yield session


@router.get("", response_model=list[BankAccountPublic])
async def list_accounts(
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> list[BankAccountPublic]:
    """List all bank accounts with real balances for current user."""
    result = await session.execute(
        select(BankAccount).where(BankAccount.user_id == user.id)
    )
    accounts = result.scalars().all()
    return list(accounts)


@router.get("/summary", response_model=dict[str, Any])
async def get_accounts_summary(
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get summary of all account balances."""
    result = await session.execute(
        select(
            func.count(BankAccount.id).label("total_accounts"),
            func.sum(BankAccount.balance).label("total_balance"),
        ).where(
            BankAccount.user_id == user.id
        )
    )
    row = result.one_or_none()
    
    total_accounts = row.total_accounts if row else 0
    total_balance = float(row.total_balance) if row and row.total_balance else 0.0
    
    return {
        "total_accounts": total_accounts,
        "total_balance": total_balance,
        "currency": "EUR",
    }


@router.get("/{account_id}", response_model=BankAccountPublic)
async def get_account(
    account_id: UUID,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> BankAccountPublic:
    """Get specific account by ID."""
    result = await session.execute(
        select(BankAccount).where(
            BankAccount.id == account_id,
            BankAccount.user_id == user.id,
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    return BankAccountPublic.model_validate(account)
