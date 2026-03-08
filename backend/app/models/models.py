"""Database models for the Budget Bo application."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, Numeric, String
from sqlmodel import Field, Relationship, SQLModel


class RecurrencePattern(str, Enum):
    """Enum for recurrence pattern types."""

    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    UNKNOWN = "unknown"


class TransactionCategory(str, Enum):
    """Enum for transaction categories."""

    HOUSING = "housing"
    TRANSPORTATION = "transportation"
    FOOD = "food"
    UTILITIES = "utilities"
    HEALTHCARE = "healthcare"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    SUBSCRIPTIONS = "subscriptions"
    INCOME = "income"
    INSURANCE = "insurance"
    EDUCATION = "education"
    TRAVEL = "travel"
    OTHER = "other"


# region User Models


class UserBase(SQLModel):
    """Base model for User."""

    email: str = Field(index=True, unique=True)
    oauth_id: str = Field(index=True, unique=True, description="Google OAuth ID")
    is_active: bool = Field(default=True)
    display_name: Optional[str] = None
    profile_picture: Optional[str] = None


class User(UserBase, table=True):
    """User model with encrypted data."""

    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    encryption_key_salt: Optional[str] = None

    # Relationships
    bank_credentials: list["BankCredential"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    bank_accounts: list["BankAccount"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    transactions: list["Transaction"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    recurring_expenses: list["RecurringExpense"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    enrichment_rules: list["EnrichmentRule"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class UserPublic(UserBase):
    """Public user model for API responses."""

    id: UUID
    created_at: datetime


class UserCreate(UserBase):
    """User creation model."""

    pass


# endregion


# region BankCredential Models


class BankCredentialBase(SQLModel):
    """Base model for BankCredential."""

    bank_name: str = Field(description="Bank identifier (e.g., 'bp', 'lcl', 'cragr')")
    bank_label: Optional[str] = Field(default=None, description="Human-readable bank name")
    bank_website: Optional[str] = Field(default=None, description="Bank website/region for cragr (e.g., 'ca-nord', 'ca-paris')")
    is_active: bool = Field(default=True)


class BankCredential(BankCredentialBase, table=True):
    """Encrypted bank credentials for Woob integration."""

    __tablename__ = "bank_credentials"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Encrypted fields - store as encrypted strings
    encrypted_login: str = Field(sa_column=Column(String))
    encrypted_password: str = Field(sa_column=Column(String))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_sync_at: Optional[datetime] = Field(default=None)
    sync_status: str = Field(default="pending")  # pending, syncing, error, success
    sync_error_message: Optional[str] = None

    # Relationships
    user: User = Relationship(back_populates="bank_credentials")


class BankCredentialPublic(BankCredentialBase):
    """Public bank credential model (without secrets)."""

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    last_sync_at: Optional[datetime]
    sync_status: str
    sync_error_message: Optional[str]


class BankCredentialCreate(SQLModel):
    """Bank credential creation model."""

    bank_name: str
    bank_label: Optional[str] = None
    bank_website: Optional[str] = None  # For cragr: ca-nord, ca-paris, etc.
    login: str
    password: str


class BankCredentialUpdate(SQLModel):
    """Bank credential update model - login/password optional."""

    bank_name: str
    bank_label: Optional[str] = None
    bank_website: Optional[str] = None
    login: Optional[str] = None  # Only update if provided
    password: Optional[str] = None  # Only update if provided


# endregion


# region BankAccount Models


class BankAccountBase(SQLModel):
    """Base model for BankAccount."""

    account_id: str = Field(description="Account ID from the bank (e.g., account number)")
    account_label: str = Field(description="Human-readable account name")
    account_type: str = Field(default="unknown", description="Account type (checking, savings, etc.)")
    balance: Decimal = Field(sa_column=Column(Numeric(12, 2)), description="Real balance from the bank")
    currency: str = Field(default="EUR")


class BankAccount(BankAccountBase, table=True):
    """Bank account information including real balance."""

    __tablename__ = "bank_accounts"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    credential_id: UUID = Field(foreign_key="bank_credentials.id", index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_sync_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="bank_accounts")


class BankAccountPublic(BankAccountBase):
    """Public bank account model for API responses."""

    id: UUID
    user_id: UUID
    credential_id: UUID
    created_at: datetime
    updated_at: datetime
    last_sync_at: datetime


# endregion


class TransactionBase(SQLModel):
    """Base model for Transaction."""

    date: date
    amount: Decimal = Field(sa_column=Column(Numeric(12, 2)))
    raw_label: str = Field(description="Original bank statement label")
    cleaned_label: Optional[str] = Field(default=None, description="AI-normalized label")
    category: TransactionCategory = Field(default=TransactionCategory.OTHER)
    is_expense: bool = Field(default=True)
    is_recurring: bool = Field(default=False)
    merchant_name: Optional[str] = None


class Transaction(TransactionBase, table=True):
    """Transaction model storing bank operations."""

    __tablename__ = "transactions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    credential_id: UUID = Field(foreign_key="bank_credentials.id", index=True)

    # Unique identifier for deduplication (composite key hash)
    transaction_key: str = Field(
        index=True,
        description="Hash of date+amount+raw_label for deduplication",
    )

    # Additional metadata
    currency: str = Field(default="EUR")
    original_currency: Optional[str] = None
    original_amount: Optional[Decimal] = Field(
        default=None, sa_column=Column(Numeric(12, 2))
    )

    # AI enrichment
    ai_confidence: Optional[float] = None  # 0.0 to 1.0
    ai_category_reasoning: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    enriched_at: Optional[datetime] = None

    # Relationships
    user: User = Relationship(back_populates="transactions")
    credential: "BankCredential" = Relationship()  # type: ignore[name-defined]


class TransactionPublic(TransactionBase):
    """Public transaction model for API responses."""

    id: UUID
    user_id: UUID
    credential_id: UUID
    transaction_key: str
    currency: str
    ai_confidence: Optional[float]
    created_at: datetime


class TransactionCreate(TransactionBase):
    """Transaction creation model."""

    credential_id: UUID
    transaction_key: str


class EnrichmentRule(SQLModel, table=True):
    """User-owned enrichment memory used to improve future classifications."""

    __tablename__ = "enrichment_rules"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    label_fingerprint: str = Field(index=True, max_length=255)
    merchant_name: Optional[str] = Field(default=None)
    cleaned_label: str = Field(max_length=255)
    category: TransactionCategory = Field(default=TransactionCategory.OTHER)
    usage_count: int = Field(default=1)
    learned_from_transaction_id: Optional[UUID] = Field(
        default=None,
        foreign_key="transactions.id",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    user: User = Relationship(back_populates="enrichment_rules")


# endregion


# region RecurringExpense Models


class RecurringExpenseBase(SQLModel):
    """Base model for RecurringExpense."""

    pattern_name: str = Field(description="Detected merchant/pattern name")
    pattern: RecurrencePattern = Field(default=RecurrencePattern.UNKNOWN)
    average_amount: Decimal = Field(sa_column=Column(Numeric(12, 2)))
    amount_variation_pct: float = Field(
        default=0.0, description="Coefficient of variation (std/mean)"
    )
    frequency_days: Optional[int] = None  # Average days between occurrences
    day_of_month: Optional[int] = None  # For monthly patterns
    day_of_week: Optional[int] = None  # For weekly patterns
    next_expected_date: Optional[date] = None
    is_active: bool = Field(default=True)
    confidence_score: float = Field(default=0.0)  # Detection confidence 0-1


class RecurringExpense(RecurringExpenseBase, table=True):
    """Detected recurring expense patterns."""

    __tablename__ = "recurring_expenses"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)

    # Matching criteria (stored for pattern matching)
    matching_label_pattern: str = Field(
        description="Regex or fuzzy pattern to match transactions"
    )
    matched_transaction_count: int = Field(default=0)
    first_seen_date: date
    last_seen_date: date

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="recurring_expenses")


class RecurringExpensePublic(RecurringExpenseBase):
    """Public recurring expense model for API responses."""

    id: UUID
    user_id: UUID
    matched_transaction_count: int
    first_seen_date: date
    last_seen_date: date
    created_at: datetime


# endregion
