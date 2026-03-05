"""Bank credentials API endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.auth import require_user
from app.core.database import AsyncSessionLocal
from app.core.security import get_encryption_service
from app.models.models import (
    BankCredential,
    BankCredentialCreate,
    BankCredentialPublic,
    User,
)

router = APIRouter(prefix="/credentials", tags=["credentials"])
encryption = get_encryption_service()


async def get_session() -> AsyncSession:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        yield session


@router.get("", response_model=list[BankCredentialPublic])
async def list_credentials(
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> list[BankCredentialPublic]:
    """List all bank credentials for current user."""
    result = await session.execute(
        select(BankCredential).where(BankCredential.user_id == user.id)
    )
    credentials = result.scalars().all()
    return list(credentials)


@router.post("", response_model=BankCredentialPublic, status_code=status.HTTP_201_CREATED)
async def create_credential(
    credential: BankCredentialCreate,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> BankCredentialPublic:
    """Create new bank credential (encrypted)."""
    # Encrypt sensitive data
    try:
        encrypted_login = encryption.encrypt(credential.login)
        encrypted_password = encryption.encrypt(credential.password)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Encryption failed: {e}",
        )

    db_credential = BankCredential(
        user_id=user.id,
        bank_name=credential.bank_name,
        bank_label=credential.bank_label,
        encrypted_login=encrypted_login,
        encrypted_password=encrypted_password,
        is_active=True,
        sync_status="pending",
    )

    session.add(db_credential)
    await session.commit()
    await session.refresh(db_credential)

    return BankCredentialPublic.model_validate(db_credential)


@router.get("/{credential_id}", response_model=BankCredentialPublic)
async def get_credential(
    credential_id: UUID,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> BankCredentialPublic:
    """Get specific credential by ID."""
    result = await session.execute(
        select(BankCredential).where(
            BankCredential.id == credential_id,
            BankCredential.user_id == user.id,
        )
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    return BankCredentialPublic.model_validate(credential)


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    credential_id: UUID,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete (deactivate) a credential."""
    result = await session.execute(
        select(BankCredential).where(
            BankCredential.id == credential_id,
            BankCredential.user_id == user.id,
        )
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    credential.is_active = False
    await session.commit()


@router.post("/{credential_id}/sync", response_model=dict[str, Any])
async def trigger_sync(
    credential_id: UUID,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Trigger manual sync for a credential."""
    from worker.tasks.sync_tasks import sync_user_transactions

    result = await session.execute(
        select(BankCredential).where(
            BankCredential.id == credential_id,
            BankCredential.user_id == user.id,
            BankCredential.is_active == True,
        )
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found or inactive",
        )

    # Queue sync task
    task = sync_user_transactions.delay(
        str(user.id),
        str(credential_id),
        days_back=7,
    )

    return {
        "message": "Sync queued",
        "credential_id": str(credential_id),
        "task_id": task.id,
    }
