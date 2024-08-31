import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# Regex pattern for validating user name.
USERNAME_REGEX = r"^[a-z.A-Z0-9_]+$"
# Regex pattern for validating password strength.
STRENGTH_REGEX = r'[!@#$%^&*(),.?":{}|<>]'


def validate_username_alphanumeric(username: str) -> str:
    if not re.match(USERNAME_REGEX, username):
        msg = "Username must be alphanumeric"
        raise ValueError(msg)
    return username


def validate_password_strength(password: str) -> str:
    if not re.search(r"[A-Z]", password):
        msg = "Password must contain at least one uppercase letter"
        raise ValueError(msg)
    if not re.search(r"[a-z]", password):
        msg = "Password must contain at least one lowercase letter"
        raise ValueError(msg)
    if not re.search(r"\d", password):
        msg = "Password must contain at least one digit"
        raise ValueError(msg)
    if not re.search(STRENGTH_REGEX, password):
        msg = "Password must contain at least one special character"
        raise ValueError(msg)
    return password


class UserBase(BaseModel):
    id: str | None = Field(None, min_length=1, max_length=100)
    email: EmailStr | None = Field(None, max_length=100)
    name: str = Field(..., min_length=3, max_length=50)
    full_name: str | None = Field(None, max_length=100)
    is_active: bool = True

    @field_validator("name", mode="after")
    @classmethod
    def validate_username(cls, username_value: str) -> str:
        return validate_username_alphanumeric(username_value)


class UserCreate(UserBase):
    password: str | None = Field(None, min_length=8)

    @field_validator("password", mode="after")
    @classmethod
    def validate_password(cls, password_value: str | None) -> str | None:
        if password_value is not None:
            return validate_password_strength(password_value)
        return password_value


class UserResponse(UserBase):
    pass


class TransactionCreate(BaseModel):
    uid: str = Field(..., min_length=1, max_length=100)
    user_id: str = Field(..., min_length=1, max_length=100)
    amount: Decimal = Field(..., gt=0, max_digits=18, decimal_places=2)
    created_at: datetime = Field(default_factory=lambda: datetime.now().astimezone())
    type: str = Field(..., min_length=1, max_length=10)


class Transaction(BaseModel):
    id: str
    user_id: str
    uid: str
    type: str
    amount: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserBalance(BaseModel):
    balance: Decimal
