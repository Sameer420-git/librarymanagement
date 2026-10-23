

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.enums import (
    BookCopyStatus,
    FineStatus,
    LoanStatus,
    PaymentMethod,
    ReservationStatus,
)
from app.schemas.common import ORMModel





class IssueRequest(BaseModel):
    member_id: int = Field(gt=0)
    copy_id: int = Field(gt=0)
    due_at: datetime | None = None
    notes: str | None = None


class ReturnRequest(BaseModel):
    copy_condition: str | None = Field(default=None, max_length=32)
    notes: str | None = None


class RenewRequest(BaseModel):
    notes: str | None = None


class LoanRead(ORMModel):
    id: int
    copy_id: int
    member_id: int
    issued_at: datetime
    due_at: datetime
    returned_at: datetime | None = None
    status: LoanStatus
    renewal_count: int
    overdue_days: int
    notes: str | None = None
    book_id: int | None = None
    book_title: str | None = None
    accession_number: str | None = None
    member_name: str | None = None
    member_email: str | None = None
    issued_by_name: str | None = None
    returned_by_name: str | None = None
    days_overdue: int = 0
    is_overdue: bool = False
    fine_amount: float | None = None


class LoanDetail(LoanRead):
    renewals: list["LoanRenewalRead"] = Field(default_factory=list)
    fine_id: int | None = None


class LoanRenewalRead(ORMModel):
    id: int
    loan_id: int
    previous_due_at: datetime
    new_due_at: datetime
    renewal_number: int
    renewed_at: datetime
    note: str | None = None
    renewed_by_name: str | None = None





class ReservationCreate(BaseModel):
    book_id: int = Field(gt=0)
    notes: str | None = None


class ReservationRead(ORMModel):
    id: int
    book_id: int
    member_id: int
    copy_id: int | None = None
    status: ReservationStatus
    position: int
    queue_position: int
    reserved_at: datetime
    ready_at: datetime | None = None
    pickup_deadline: datetime | None = None
    fulfilled_at: datetime | None = None
    cancelled_at: datetime | None = None
    expired_at: datetime | None = None
    book_title: str | None = None
    book_authors: list[str] = Field(default_factory=list)
    member_name: str | None = None
    accession_number: str | None = None
    shelf_location: str | None = None





class FineAdjustment(BaseModel):
    amount: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2,
        description="New total amount. Omit to waive the fine.",
    )
    waive: bool = False
    reason: str = Field(min_length=3, max_length=255)

    @field_validator("reason")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class FinePaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    method: PaymentMethod = PaymentMethod.CASH
    reference: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class FinePaymentRead(ORMModel):
    id: int
    fine_id: int
    amount: Decimal
    method: PaymentMethod
    reference: str | None = None
    paid_at: datetime
    notes: str | None = None
    recorded_by_name: str | None = None


class FineRead(ORMModel):
    id: int
    member_id: int
    loan_id: int | None = None
    amount: Decimal
    amount_paid: Decimal
    outstanding: Decimal = Decimal("0.00")
    days_overdue: int
    rate_per_day: Decimal
    reason: str
    status: FineStatus
    assessed_at: datetime
    waived_at: datetime | None = None
    waiver_reason: str | None = None
    notes: str | None = None
    member_name: str | None = None
    member_email: str | None = None
    book_title: str | None = None
    payments: list[FinePaymentRead] = Field(default_factory=list)


class MemberLoanSummary(BaseModel):
    current_loans: list[LoanRead] = Field(default_factory=list)
    past_loans: list[LoanRead] = Field(default_factory=list)
    total_current: int = 0
    total_past: int = 0
    overdue_count: int = 0


LoanDetail.model_rebuild()
