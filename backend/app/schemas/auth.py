

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel, MessageResponse


class LoginRequest(BaseModel):
    identifier: str = Field(
        min_length=3, max_length=255, description="E-mail address or institutional ID"
    )
    password: str = Field(min_length=1, max_length=256)

    @field_validator("identifier")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None
    user: "UserProfile"


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class LogoutRequest(BaseModel):
    refresh_token: str | None = None
    all_sessions: bool = False


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    
    delivered: bool = False


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=512)
    new_password: str = Field(min_length=8, max_length=256)

    @field_validator("new_password")
    @classmethod
    def _strength(cls, value: str) -> str:
        checks = [
            any(c.islower() for c in value),
            any(c.isupper() for c in value),
            any(c.isdigit() for c in value),
            any(not c.isalnum() for c in value),
        ]
        if sum(checks) < 3:
            raise ValueError(
                "Password must contain at least three of: lowercase, uppercase, digit, symbol."
            )
        return value


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)

    @field_validator("new_password")
    @classmethod
    def _strength(cls, value: str) -> str:
        checks = [
            any(c.islower() for c in value),
            any(c.isupper() for c in value),
            any(c.isdigit() for c in value),
            any(not c.isalnum() for c in value),
        ]
        if sum(checks) < 3:
            raise ValueError(
                "Password must contain at least three of: lowercase, uppercase, digit, symbol."
            )
        return value


class EmailVerificationRequest(BaseModel):
    token: str = Field(min_length=10, max_length=512)


class UserProfile(ORMModel):
    id: int
    email: str
    institutional_id: str | None = None
    first_name: str
    last_name: str
    full_name: str = ""
    phone: str | None = None
    role: str
    status: str
    membership_type: str
    membership_start: Any | None = None
    membership_expires: Any | None = None
    is_email_verified: bool
    last_login_at: Any | None = None
    avatar_url: str | None = None
    department_name: str | None = None
    course_name: str | None = None
    enrollment_number: str | None = None
    employee_id: str | None = None
    designation: str | None = None
    semester: int | None = None
    section: str | None = None
    academic_year: str | None = None


TokenResponse.model_rebuild()
