"""Google OAuth authentication endpoints."""

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.security import get_encryption_service
from app.models.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
encryption = get_encryption_service()


async def get_session() -> AsyncSession:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/test-login", response_model=dict[str, Any])
async def test_login(
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Development-only: Create a test session without Google OAuth.
    
    This endpoint is only available in development mode for testing purposes.
    """
    if settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test login not available in production",
        )

    from uuid import uuid4
    from datetime import datetime

    # Find or create test user
    result = await session.execute(
        select(User).where(User.email == "test@example.com")
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=uuid4(),
            email="test@example.com",
            oauth_id="test_oauth_dev",
            display_name="Test User",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    # Create session cookie
    session_token = encryption.encrypt(str(user.id))

    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        secure=False,  # Allow HTTP in development
        samesite="lax",
        max_age=86400 * 7,
    )

    return {
        "message": "Test login successful",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
        },
        "note": "This endpoint is for development only",
    }


@router.get("/login")
async def login() -> RedirectResponse:
    """Redirect to Google OAuth login."""
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth not configured",
        )

    # Build Google OAuth URL - use backend URL for callback
    redirect_uri = "http://localhost:8000/auth/callback"
    scope = "openid email profile"

    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.google_client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&access_type=offline"
        f"&prompt=consent"
    )

    return RedirectResponse(url=google_auth_url)


@router.get("/callback")
async def auth_callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    """Handle Google OAuth callback."""
    if error:
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error={error}"
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code missing",
        )

    # Exchange code for tokens
    token_data = await _exchange_code_for_token(code)
    if not token_data:
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=token_exchange_failed"
        )

    # Get user info from Google
    user_info = await _get_google_user_info(token_data["access_token"])
    if not user_info:
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=user_info_failed"
        )

    # Find or create user
    user = await _get_or_create_user(session, user_info)

    # Create session cookie
    session_token = encryption.encrypt(str(user.id))

    response = RedirectResponse(url=f"{settings.frontend_url}/dashboard")
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=86400 * 7,  # 7 days
    )

    return response


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    """Logout and clear session cookie."""
    response.delete_cookie(key="session")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=dict[str, Any])
async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get current authenticated user."""
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        user_id = encryption.decrypt(session_cookie)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        )

    result = await session.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "profile_picture": user.profile_picture,
    }


async def _exchange_code_for_token(code: str) -> dict[str, Any] | None:
    """Exchange authorization code for access token."""
    if not settings.google_client_secret:
        return None

    redirect_uri = "http://localhost:8000/auth/callback"

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        if response.status_code == 200:
            return response.json()
    return None


async def _get_google_user_info(access_token: str) -> dict[str, Any] | None:
    """Get user info from Google API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code == 200:
            return response.json()
    return None


async def _get_or_create_user(
    session: AsyncSession,
    user_info: dict[str, Any],
) -> User:
    """Get existing user or create new one from Google info."""
    from uuid import uuid4
    from datetime import datetime

    oauth_id = user_info.get("id")
    email = user_info.get("email")

    # Check if user exists
    result = await session.execute(
        select(User).where(User.oauth_id == oauth_id)
    )
    user = result.scalar_one_or_none()

    if user:
        # Update profile info
        user.display_name = user_info.get("name", user.display_name)
        user.profile_picture = user_info.get("picture", user.profile_picture)
        user.updated_at = datetime.utcnow()
        await session.commit()
        return user

    # Create new user
    user = User(
        id=uuid4(),
        email=email,
        oauth_id=oauth_id,
        display_name=user_info.get("name"),
        profile_picture=user_info.get("picture"),
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


async def require_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Dependency to require authenticated user."""
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        user_id = encryption.decrypt(session_cookie)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        )

    result = await session.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
