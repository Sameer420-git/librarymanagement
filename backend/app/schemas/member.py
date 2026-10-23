

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.enums import MembershipType, UserRole, UserStatus


class MemberBase(BaseModel):
    email: EmailStr
    institutional_id: str | None = Field(default=None, max_length=64)
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    role: UserRole = UserRole.STUDENT
    membership_type: MembershipType | None = None
    membership_start: date | None = None
    membership_expires: date | None = None
    status: UserStatus = UserStatus.ACTIVE
    avatar_url: str | None = Field(default=None, max_length=512)
    notes: str | None = None

    
    enrollment_number: str | None = Field(default=None, max_length=64)
    course_id: int | None = None
    course_code: str | None = Field(default=None, max_length=32)
    semester: int | None = Field(default=None, ge=1, le=12)
    section: str | None = Field(default=None, max_length=32)
    academic_year: str | None = Field(default=None, max_length=32)
    guardian_name: str | None = Field(default=None, max_length=160)
    guardian_phone: str | None = Field(default=None, max_length=32)
    address: str | None = None

    
    employee_id: str | None = Field(default=None, max_length=64)
    department_id: int | None = None
    designation: str | None = Field(default=None, max_length=120)
    office_location: str | None = Field(default=None, max_length=120)
    office_phone: str | None = Field(default=None, max_length=32)
    specialization: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _validate_role_fields(self) -> "MemberBase":
        if self.role == UserRole.FACULTY and self.enrollment_number:
            raise ValueError("Faculty members cannot have an enrollment number.")
        if self.role == UserRole.STUDENT and self.employee_id:
            raise ValueError("Students cannot have an employee ID.")
        return self

    @field_validator("email")
    @classmethod
    def _lower_email(cls, value: str) -> str:
        return value.strip().lower()


class MemberCreate(MemberBase):
    password: str | None = Field(default=None, min_length=8, max_length=256)


class MemberUpdate(BaseModel):
    email: EmailStr | None = None
    institutional_id: str | None = Field(default=None, max_length=64)
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    membership_type: MembershipType | None = None
    membership_start: date | None = None
    membership_expires: date | None = None
    status: UserStatus | None = None
    avatar_url: str | None = Field(default=None, max_length=512)
    notes: str | None = None
    enrollment_number: str | None = Field(default=None, max_length=64)
    course_id: int | None = None
    semester: int | None = Field(default=None, ge=1, le=12)
    section: str | None = Field(default=None, max_length=32)
    academic_year: str | None = Field(default=None, max_length=32)
    employee_id: str | None = Field(default=None, max_length=64)
    department_id: int | None = None
    designation: str | None = Field(default=None, max_length=120)
    office_location: str | None = Field(default=None, max_length=120)
    office_phone: str | None = Field(default=None, max_length=32)
    specialization: str | None = Field(default=None, max_length=255)

    @field_validator("email")
    @classmethod
    def _lower_email(cls, value: str | None) -> str | None:
        return value.strip().lower() if value else value


class MemberProfileRead(BaseModel):
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
    membership_start: date | None = None
    membership_expires: date | None = None
    is_email_verified: bool
    last_login_at: datetime | None = None
    created_at: datetime | None = None
    avatar_url: str | None = None
    notes: str | None = None
    department_id: int | None = None
    department_name: str | None = None
    course_id: int | None = None
    course_name: str | None = None
    enrollment_number: str | None = None
    semester: int | None = None
    section: str | None = None
    academic_year: str | None = None
    employee_id: str | None = None
    designation: str | None = None
    office_location: str | None = None
    guardian_name: str | None = None
    guardian_phone: str | None = None
    address: str | None = None
    active_loans: int = 0
    overdue_loans: int = 0
    active_reservations: int = 0
    outstanding_fines: float = 0.0
    borrow_limit: int = 0
    eligible_to_borrow: bool = True
    ineligibility_reason: str | None = None


class MemberListItem(BaseModel):
    id: int
    email: str
    institutional_id: str | None = None
    full_name: str
    role: str
    status: str
    membership_type: str
    membership_expires: date | None = None
    department_name: str | None = None
    course_name: str | None = None
    enrollment_number: str | None = None
    employee_id: str | None = None
    active_loans: int = 0
    outstanding_fines: float = 0.0


class MemberImportResult(BaseModel):
    total_rows: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)
    created_ids: list[int] = Field(default_factory=list)


class DepartmentCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None


class DepartmentRead(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None
    is_active: bool
    course_count: int = 0


class CourseCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=160)
    department_id: int | None = None
    duration_semesters: int | None = Field(default=None, ge=1, le=12)


class CourseRead(BaseModel):
    id: int
    code: str
    name: str
    department_id: int | None = None
    department_name: str | None = None
    duration_semesters: int | None = None
    is_active: bool
