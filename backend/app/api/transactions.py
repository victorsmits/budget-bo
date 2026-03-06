"""Transactions API endpoints."""

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.auth import require_user
from app.core.database import AsyncSessionLocal
from app.core.validation import validate_date_range
from app.models.models import (
    Transaction,
    TransactionCategory,
    TransactionPublic,
    User,
)
from app.models.pagination import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/transactions", tags=["transactions"])


async def get_session() -> AsyncSession:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        yield session


@router.get("", response_model=PaginatedResponse[TransactionPublic])
async def list_transactions(
    pagination: PaginationParams = Depends(),
    category: TransactionCategory | None = None,
    is_expense: bool | None = None,
    is_recurring: bool | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[TransactionPublic]:
    """
    List transactions for current user with filtering.
    
    Query params:
    - pagination: Page and size for pagination
    - category: Filter by category
    - is_expense: Filter expenses/income
    - is_recurring: Filter recurring transactions
    - start_date/end_date: Date range filter
    """
    # Validate date range if both provided
    if start_date and end_date:
        validate_date_range(start_date, end_date)
    query = select(Transaction).where(Transaction.user_id == user.id)

    if category:
        query = query.where(Transaction.category == category)
    if is_expense is not None:
        query = query.where(Transaction.is_expense == is_expense)
    if is_recurring is not None:
        query = query.where(Transaction.is_recurring == is_recurring)
    if start_date:
        query = query.where(Transaction.date >= start_date)
    if end_date:
        query = query.where(Transaction.date <= end_date)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.order_by(Transaction.date.desc()).offset(pagination.skip).limit(pagination.size)
    result = await session.execute(query)
    transactions = result.scalars().all()

    return PaginatedResponse.create(
        items=list(transactions),
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.get("/summary", response_model=dict[str, Any])
async def get_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get transaction summary (totals by category)."""
    if not start_date:
        start_date = date.today().replace(day=1)  # First day of current month
    if not end_date:
        end_date = date.today()
    
    # Validate date range
    validate_date_range(start_date, end_date)

    # Total expenses
    result = await session.execute(
        select(func.sum(Transaction.amount)).where(
            Transaction.user_id == user.id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.is_expense == True,
        )
    )
    total_expenses = result.scalar() or 0

    # Total income
    result = await session.execute(
        select(func.sum(Transaction.amount)).where(
            Transaction.user_id == user.id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.is_expense == False,
        )
    )
    total_income = result.scalar() or 0

    # By category
    result = await session.execute(
        select(
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
            func.count().label("count"),
        ).where(
            Transaction.user_id == user.id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.is_expense == True,
        ).group_by(Transaction.category)
    )
    by_category = [
        {
            "category": row.category.value,
            "total": float(row.total),
            "count": row.count,
        }
        for row in result.all()
    ]

    return {
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "total_expenses": float(total_expenses),
        "total_income": float(total_income),
        "net": float(total_income - total_expenses),
        "by_category": by_category,
    }


@router.get("/{transaction_id}", response_model=TransactionPublic)
async def get_transaction(
    transaction_id: UUID,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> TransactionPublic:
    """Get specific transaction by ID."""
    result = await session.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user.id,
        )
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    return TransactionPublic.model_validate(transaction)


@router.patch("/{transaction_id}/category", response_model=TransactionPublic)
async def update_category(
    transaction_id: UUID,
    category: TransactionCategory,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> TransactionPublic:
    """Update transaction category (user correction)."""
    result = await session.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user.id,
        )
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    transaction.category = category
    await session.commit()
    await session.refresh(transaction)

    return TransactionPublic.model_validate(transaction)


@router.patch("/{transaction_id}/recurring", response_model=TransactionPublic)
async def mark_recurring(
    transaction_id: UUID,
    is_recurring: bool = True,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> TransactionPublic:
    """Mark transaction as recurring (user feedback)."""
    result = await session.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user.id,
        )
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    transaction.is_recurring = is_recurring
    await session.commit()
    await session.refresh(transaction)

    return TransactionPublic.model_validate(transaction)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: UUID,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a transaction."""
    result = await session.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user.id,
        )
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    await session.delete(transaction)
    await session.commit()
