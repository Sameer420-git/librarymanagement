

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, utcnow
from app.db.types import JSONPayload
from app.db.types import Money


class LibraryPolicy(Base, TimestampMixin):
    

    __tablename__ = "library_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    institution_name: Mapped[str] = mapped_column(
        String(200), default="College Library", nullable=False
    )
    library_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    library_phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    library_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    opening_hours: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    
    max_books_student: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_books_faculty: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_books_staff: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    loan_period_days_student: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    loan_period_days_faculty: Mapped[int] = mapped_column(Integer, default=28, nullable=False)
    max_renewals: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    renewal_period_days: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    max_fine_blocks_renewal: Mapped[Decimal] = mapped_column(
        Money, default=Decimal("0.00"), nullable=False
    )
    max_fine_blocks_issue: Mapped[Decimal] = mapped_column(
        Money, default=Decimal("100.00"), nullable=False
    )

    
    fine_per_day: Mapped[Decimal] = mapped_column(Money, default=Decimal("5.00"), nullable=False)
    grace_period_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_fine_per_loan: Mapped[Decimal] = mapped_column(
        Money, default=Decimal("500.00"), nullable=False
    )
    currency_code: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)

    
    reservation_pickup_days: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    max_active_reservations: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    reservation_expiry_hours: Mapped[int] = mapped_column(Integer, default=72, nullable=False)

    
    due_reminder_days: Mapped[list[int]] = mapped_column(
        JSON, default=lambda: [3, 1, 0], nullable=False
    )
    overdue_reminder_days: Mapped[list[int]] = mapped_column(
        JSON, default=lambda: [1, 3, 7, 14, 30], nullable=False
    )
    membership_expiry_reminder_days: Mapped[list[int]] = mapped_column(
        JSON, default=lambda: [7, 1], nullable=False
    )
    max_overdue_reminders: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    
    membership_validity_days_student: Mapped[int] = mapped_column(Integer, default=365, nullable=False)
    membership_validity_days_faculty: Mapped[int] = mapped_column(Integer, default=730, nullable=False)

    updated_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    @classmethod
    def get_current(cls, session) -> "LibraryPolicy":
        
        policy = session.get(cls, 1)
        if policy is None:
            policy = cls(id=1)
            session.add(policy)
            session.flush()
        return policy


class AuditLog(Base):
    

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONPayload, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )

    __table_args__ = (
        Index("ix_audit_logs_actor_created", "actor_id", "created_at"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
    )
