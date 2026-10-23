

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, utcnow
from app.db.types import Money, enum_column
from app.models.enums import (
    FineStatus,
    LoanStatus,
    PaymentMethod,
    ReservationStatus,
)

if TYPE_CHECKING:  
    from app.models.catalogue import Book, BookCopy
    from app.models.user import User


class Loan(Base, TimestampMixin):
    

    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    copy_id: Mapped[int] = mapped_column(
        ForeignKey("book_copies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    member_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    issued_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    returned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    returned_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[LoanStatus] = mapped_column(
        enum_column(LoanStatus, 24), default=LoanStatus.ACTIVE, nullable=False, index=True
    )
    renewal_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    
    due_date_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    
    active_copy_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("book_copies.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    overdue_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fine_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("fines.id", ondelete="SET NULL", use_alter=True), nullable=True, unique=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    copy: Mapped["BookCopy"] = relationship(back_populates="loans", foreign_keys=[copy_id])
    member: Mapped["User"] = relationship(foreign_keys=[member_id])
    issued_by: Mapped[Optional["User"]] = relationship(foreign_keys=[issued_by_id])
    returned_by: Mapped[Optional["User"]] = relationship(foreign_keys=[returned_by_id])
    renewals: Mapped[list["LoanRenewal"]] = relationship(
        back_populates="loan", cascade="all, delete-orphan", order_by="LoanRenewal.id"
    )
    fine: Mapped[Optional["Fine"]] = relationship(
        "Fine",
        primaryjoin="Loan.fine_id == Fine.id",
        foreign_keys="Loan.fine_id",
        uselist=False,
        viewonly=True,
    )

    __table_args__ = (
        Index("ix_loans_member_status", "member_id", "status"),
        Index("ix_loans_due_status", "due_at", "status"),
        Index("ix_loans_issued_at", "issued_at"),
    )


class LoanRenewal(Base):
    

    __tablename__ = "loan_renewals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_id: Mapped[int] = mapped_column(
        ForeignKey("loans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    renewed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    previous_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    new_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    renewal_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    renewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    loan: Mapped["Loan"] = relationship(back_populates="renewals")


class Reservation(Base, TimestampMixin):
    

    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    member_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    copy_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("book_copies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[ReservationStatus] = mapped_column(
        enum_column(ReservationStatus, 24),
        default=ReservationStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    queue_position: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    reserved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    ready_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    pickup_deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    fulfilled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expired_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    
    active_key: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, unique=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    book: Mapped["Book"] = relationship(back_populates="reservations")
    member: Mapped["User"] = relationship()
    copy: Mapped[Optional["BookCopy"]] = relationship(back_populates="reservations")

    __table_args__ = (
        Index("ix_reservations_book_status", "book_id", "status"),
        Index("ix_reservations_member_status", "member_id", "status"),
        Index("ix_reservations_queue", "book_id", "status", "reserved_at"),
    )


class Fine(Base, TimestampMixin):
    

    __tablename__ = "fines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    loan_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("loans.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0.00"))
    amount_paid: Mapped[Decimal] = mapped_column(
        Money, nullable=False, default=Decimal("0.00")
    )
    days_overdue: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rate_per_day: Mapped[Decimal] = mapped_column(Money, nullable=False, default=Decimal("0.00"))
    reason: Mapped[str] = mapped_column(String(255), nullable=False, default="Overdue return")
    status: Mapped[FineStatus] = mapped_column(
        enum_column(FineStatus, 24), default=FineStatus.PENDING, nullable=False, index=True
    )
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    assessed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    waived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    waived_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    waiver_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    member: Mapped["User"] = relationship(foreign_keys=[member_id])
    loan: Mapped[Optional["Loan"]] = relationship(
        "Loan",
        primaryjoin="Fine.loan_id == Loan.id",
        foreign_keys="Fine.loan_id",
        uselist=False,
        viewonly=True,
    )
    payments: Mapped[list["FinePayment"]] = relationship(
        back_populates="fine", cascade="all, delete-orphan", order_by="FinePayment.id"
    )

    __table_args__ = (Index("ix_fines_member_status", "member_id", "status"),)


class FinePayment(Base):
    

    __tablename__ = "fine_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fine_id: Mapped[int] = mapped_column(
        ForeignKey("fines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        enum_column(PaymentMethod, 32), default=PaymentMethod.CASH, nullable=False
    )
    reference: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    recorded_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    fine: Mapped["Fine"] = relationship(back_populates="payments")


class InventoryAdjustment(Base):
    

    __tablename__ = "inventory_adjustments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    copy_id: Mapped[int] = mapped_column(
        ForeignKey("book_copies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_status: Mapped[str] = mapped_column(String(24), nullable=False)
    new_status: Mapped[str] = mapped_column(String(24), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    changed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    __table_args__ = (Index("ix_inventory_adjustments_copy", "copy_id", "changed_at"),)
