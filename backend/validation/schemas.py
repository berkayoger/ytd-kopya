"""Pydantic schemas for comprehensive input validation."""

import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, validator


class UserRegistrationSchema(BaseModel):
    """User registration validation schema."""

    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(
        ..., min_length=8, max_length=128, description="Password (8-128 chars)"
    )
    username: str = Field(
        ..., min_length=3, max_length=50, description="Username (3-50 chars)"
    )
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")

    @validator("password")
    def validate_password_strength(cls, value: str) -> str:
        """Ensure password contains mixed characters for strength."""
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", value):
            raise ValueError("Password must contain at least one special character")
        return value

    @validator("username")
    def validate_username(cls, value: str) -> str:
        """Validate username format."""
        if not re.match(r"^[a-zA-Z0-9_]+$", value):
            raise ValueError(
                "Username can only contain letters, numbers, and underscores",
            )
        return value.lower()


class UserLoginSchema(BaseModel):
    """User login validation schema."""

    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=1, max_length=128, description="Password")


class CryptoAnalysisRequestSchema(BaseModel):
    """Crypto analysis request validation schema."""

    symbol: str = Field(..., min_length=1, max_length=20, description="Crypto symbol")
    timeframe: str = Field(
        ..., pattern=r"^(1h|4h|1d|1w)$", description="Valid timeframe"
    )
    indicators: List[str] = Field(..., max_items=10, description="Analysis indicators")
    start_date: Optional[datetime] = Field(None, description="Start date for analysis")
    end_date: Optional[datetime] = Field(None, description="End date for analysis")

    @validator("symbol")
    def validate_symbol(cls, value: str) -> str:
        """Validate crypto symbol format."""
        if not re.match(r"^[A-Z0-9]+$", value.upper()):
            raise ValueError("Invalid crypto symbol format")
        return value.upper()

    @validator("indicators")
    def validate_indicators(cls, value: List[str]) -> List[str]:
        """Validate allowed indicators list."""
        allowed_indicators = [
            "RSI",
            "MACD",
            "SMA",
            "EMA",
            "BB",
            "STOCH",
            "ADX",
            "CCI",
            "WILLR",
            "ATR",
        ]
        for indicator in value:
            if indicator.upper() not in allowed_indicators:
                raise ValueError(f"Invalid indicator: {indicator}")
        return [i.upper() for i in value]

    @validator("end_date")
    def validate_date_range(
        cls, value: Optional[datetime], values: Dict[str, Any]
    ) -> Optional[datetime]:
        """Ensure the end date is after start date."""
        start = values.get("start_date")
        if start and value and value <= start:
            raise ValueError("End date must be after start date")
        return value


class AdminAnalyticsRequestSchema(BaseModel):
    """Admin analytics request validation schema."""

    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")
    metric_type: str = Field(
        ..., pattern=r"^(users|payments|usage|plans)$", description="Metric type"
    )

    @validator("end_date")
    def validate_date_range(cls, value: datetime, values: Dict[str, Any]) -> datetime:
        """Ensure date range is valid and limited to one year."""
        start = values.get("start_date")
        if start and value <= start:
            raise ValueError("End date must be after start date")
        if start and (value - start).days > 365:
            raise ValueError("Date range cannot exceed 365 days")
        return value


class PaymentRequestSchema(BaseModel):
    """Payment request validation schema."""

    plan_id: int = Field(..., gt=0, description="Plan ID")
    amount: Decimal = Field(
        ..., gt=0, max_digits=10, decimal_places=2, description="Payment amount"
    )
    currency: str = Field(..., pattern=r"^[A-Z]{3}$", description="Currency code")
    payment_method: str = Field(
        ..., pattern=r"^(card|crypto|bank)$", description="Payment method"
    )


class PromoCodeSchema(BaseModel):
    """Promo code validation schema."""

    code: str = Field(..., min_length=4, max_length=20, description="Promo code")
    discount_percent: Optional[int] = Field(
        None, ge=1, le=100, description="Discount percentage"
    )
    discount_amount: Optional[Decimal] = Field(
        None, gt=0, description="Discount amount"
    )
    max_uses: Optional[int] = Field(None, ge=1, description="Maximum uses")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")

    @validator("code")
    def validate_promo_code(cls, value: str) -> str:
        """Validate promo code format."""
        if not re.match(r"^[A-Z0-9]+$", value.upper()):
            raise ValueError("Promo code can only contain letters and numbers")
        return value.upper()


class LoginSchema(BaseModel):
    """Basic login validation schema retained for backward compatibility."""

    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class CreateOrderSchema(BaseModel):
    """Existing order creation schema."""

    symbol: str = Field(min_length=1, max_length=20)
    amount: float = Field(gt=0)
