"""Recurring expenses API endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.auth import require_user
from app.core.database import AsyncSessionLocal
from app.models.models import RecurringExpense, RecurringExpensePublic, User
from app.services.recurring import RecurringExpenseService

router = APIRouter(prefix="/recurring", tags=["recurring"])


async def get_session() -> AsyncSession:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        yield session


@router.get("", response_model=list[RecurringExpensePublic])
async def list_recurring(
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> list[RecurringExpensePublic]:
    """List all recurring expenses for current user."""
    result = await session.execute(
        select(RecurringExpense).where(
            RecurringExpense.user_id == user.id,
            RecurringExpense.is_active == True,
        )
    )
    expenses = result.scalars().all()
    return list(expenses)


@router.get("/upcoming", response_model=list[RecurringExpensePublic])
async def get_upcoming(
    days_ahead: int = 30,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> list[RecurringExpensePublic]:
    """Get upcoming recurring expenses expected in next N days."""
    service = RecurringExpenseService(session)
    expenses = await service.get_upcoming_expenses(str(user.id), days_ahead)
    return expenses  # type: ignore


@router.get("/{expense_id}", response_model=RecurringExpensePublic)
async def get_recurring(
    expense_id: UUID,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> RecurringExpensePublic:
    """Get specific recurring expense by ID."""
    result = await session.execute(
        select(RecurringExpense).where(
            RecurringExpense.id == expense_id,
            RecurringExpense.user_id == user.id,
        )
    )
    expense = result.scalar_one_or_none()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring expense not found",
        )

    return RecurringExpensePublic.model_validate(expense)


@router.post("/detect", response_model=list[RecurringExpensePublic])
async def detect_recurring(
    months_back: int = 6,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> list[RecurringExpensePublic]:
    """Run recurrence detection on user's transaction history."""
    service = RecurringExpenseService(session)
    detected = await service.analyze_user_transactions(str(user.id), months_back)
    return detected  # type: ignore


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring(
    expense_id: UUID,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Deactivate a recurring expense pattern."""
    result = await session.execute(
        select(RecurringExpense).where(
            RecurringExpense.id == expense_id,
            RecurringExpense.user_id == user.id,
        )
    )
    expense = result.scalar_one_or_none()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring expense not found",
        )

    expense.is_active = False
    await session.commit()


@router.get("/stats/summary", response_model=dict[str, Any])
async def get_recurring_stats(
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get statistics about recurring expenses."""
    result = await session.execute(
        select(RecurringExpense).where(
            RecurringExpense.user_id == user.id,
            RecurringExpense.is_active == True,
        )
    )
    expenses = result.scalars().all()

    total_monthly = sum(
        float(e.average_amount)
        for e in expenses
        if e.pattern.value in ("monthly", "unknown")
    )

    total_annual = sum(
        float(e.average_amount)
        for e in expenses
        if e.pattern.value == "annually"
    )

    by_pattern = {}
    for e in expenses:
        pattern = e.pattern.value
        if pattern not in by_pattern:
            by_pattern[pattern] = {"count": 0, "total": 0.0}
        by_pattern[pattern]["count"] += 1
        by_pattern[pattern]["total"] += float(e.average_amount)

    return {
        "total_recurring": len(expenses),
        "estimated_monthly": total_monthly,
        "estimated_annual": total_annual,
        "by_pattern": by_pattern,
    }
