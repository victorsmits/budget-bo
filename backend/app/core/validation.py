"""Advanced validation utilities."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel, validator


class ValidationMixin:
    """Mixin class with advanced validation methods."""
    
    @validator('date', pre=True)
    def validate_date_not_future(cls, v):
        """Validate that date is not in the future."""
        if isinstance(v, date) and v > date.today():
            raise ValueError("Date cannot be in the future")
        return v
    
    @validator('date', pre=True)
    def validate_date_not_too_old(cls, v):
        """Validate that date is not older than 2 years."""
        if isinstance(v, date):
            two_years_ago = date.today().replace(year=date.today().year - 2)
            if v < two_years_ago:
                raise ValueError("Date cannot be older than 2 years")
        return v
    
    @validator('amount')
    def validate_amount_positive(cls, v):
        """Validate that amount is positive."""
        if isinstance(v, (int, float, Decimal)) and v <= 0:
            raise ValueError("Amount must be positive")
        return v
    
    @validator('amount')
    def validate_amount_reasonable(cls, v):
        """Validate that amount is reasonable (not too large)."""
        if isinstance(v, (int, float, Decimal)):
            if abs(v) > 10_000_000:  # 10 million
                raise ValueError("Amount seems unreasonably large")
        return v
    
    @validator('email')
    def validate_email_length(cls, v):
        """Validate email length."""
        if isinstance(v, str) and len(v) > 255:
            raise ValueError("Email too long (max 255 characters)")
        return v
    
    @validator('display_name')
    def validate_display_name(cls, v):
        """Validate display name."""
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("Display name cannot be empty")
            if len(v) > 100:
                raise ValueError("Display name too long (max 100 characters)")
        return v
    
    @validator('raw_label')
    def validate_raw_label(cls, v):
        """Validate transaction label."""
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("Label cannot be empty")
            if len(v) > 500:
                raise ValueError("Label too long (max 500 characters)")
        return v


def validate_date_range(start_date: date | None, end_date: date | None) -> None:
    """Validate that date range is logical."""
    if start_date and end_date:
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date cannot be after end date",
            )
        
        # Validate range is not too large
        delta = end_date - start_date
        if delta.days > 365:  # More than 1 year
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date range cannot exceed 1 year",
            )


def validate_pagination(page: int, size: int) -> None:
    """Validate pagination parameters."""
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page must be >= 1",
        )
    
    if size < 1 or size > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page size must be between 1 and 1000",
        )


def validate_uuid_format(uuid_str: str) -> None:
    """Validate UUID format."""
    try:
        UUID(uuid_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format",
        )


def validate_bank_credentials(bank_name: str, login: str, password: str) -> None:
    """Validate bank credential fields."""
    if not bank_name or not bank_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bank name is required",
        )
    
    if len(bank_name) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bank name too long (max 100 characters)",
        )
    
    if not login or not login.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login is required",
        )
    
    if len(login) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login too long (max 255 characters)",
        )
    
    if not password or not password.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required",
        )
    
    if len(password) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password too long (max 255 characters)",
        )
