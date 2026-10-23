

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.enums import NotificationStatus, NotificationType
from app.schemas.common import ORMModel


class NotificationRead(ORMModel):
    id: int
    user_id: int
    type: NotificationType
    status: NotificationStatus
    subject: str
    recipient_email: str
    scheduled_for: datetime
    attempts: int
    max_attempts: int
    last_error: str | None = None
    sent_at: datetime | None = None
    created_at: datetime | None = None
    user_name: str | None = None
    template_name: str | None = None


class NotificationAttemptRead(ORMModel):
    id: int
    notification_id: int
    attempt_number: int
    status: str
    error_message: str | None = None
    error_type: str | None = None
    duration_ms: int | None = None
    started_at: datetime
    finished_at: datetime | None = None
    was_retry: bool


class NotificationDetail(NotificationRead):
    body_html: str | None = None
    body_text: str | None = None
    dedupe_key: str | None = None
    payload: dict[str, Any] | None = None
    attempts_log: list[NotificationAttemptRead] = Field(default_factory=list)


class NotificationStats(BaseModel):
    queued: int = 0
    sending: int = 0
    sent: int = 0
    failed: int = 0
    cancelled: int = 0
    total: int = 0
    failure_rate: float = 0.0


class TestEmailRequest(BaseModel):
    to_email: str | None = Field(default=None, max_length=255)
    subject: str | None = Field(default=None, max_length=120)


class TestEmailResponse(BaseModel):
    success: bool
    message: str
    recipient: str | None = None
    error: str | None = None





class ReportDateRange(BaseModel):
    from_date: datetime | None = None
    to_date: datetime | None = None


class InventoryReportRow(BaseModel):
    category_name: str | None = None
    publisher_name: str | None = None
    total_titles: int = 0
    total_copies: int = 0
    available_copies: int = 0
    issued_copies: int = 0
    reserved_copies: int = 0
    lost_copies: int = 0
    damaged_copies: int = 0
    retired_copies: int = 0


class CirculationReportRow(BaseModel):
    period: str
    issued_count: int = 0
    returned_count: int = 0
    renewed_count: int = 0
    overdue_count: int = 0


class OverdueReportRow(BaseModel):
    loan_id: int
    member_id: int
    member_name: str
    book_title: str
    accession_number: str
    due_at: datetime
    days_overdue: int
    fine_amount: float = 0.0
    contact: str | None = None


class PopularBookRow(BaseModel):
    book_id: int
    title: str
    authors: list[str] = Field(default_factory=list)
    loan_count: int = 0
    reservation_count: int = 0
    total_copies: int = 0


class DepartmentCirculationRow(BaseModel):
    department_name: str
    member_count: int = 0
    loan_count: int = 0
    current_loans: int = 0
    overdue_loans: int = 0
    fine_total: float = 0.0


class FinesReportRow(BaseModel):
    member_id: int
    member_name: str
    assessed_count: int = 0
    assessed_total: float = 0.0
    paid_total: float = 0.0
    outstanding_total: float = 0.0


class ReservationActivityRow(BaseModel):
    book_id: int
    title: str
    created_count: int = 0
    fulfilled_count: int = 0
    cancelled_count: int = 0
    expired_count: int = 0


class EmailFailureRow(BaseModel):
    notification_id: int
    recipient_email: str
    subject: str
    type: str
    attempts: int
    last_error: str | None = None
    created_at: datetime | None = None
    last_attempt_at: datetime | None = None


class DashboardStats(BaseModel):
    total_books: int = 0
    total_copies: int = 0
    available_copies: int = 0
    issued_copies: int = 0
    total_members: int = 0
    active_members: int = 0
    active_loans: int = 0
    overdue_loans: int = 0
    due_today: int = 0
    pending_reservations: int = 0
    outstanding_fines: float = 0.0
    fines_collected: float = 0.0
    notifications_queued: int = 0
    notifications_failed: int = 0
    loans_issued_today: int = 0
    returns_today: int = 0
