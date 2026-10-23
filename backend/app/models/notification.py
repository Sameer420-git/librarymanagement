

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, utcnow
from app.db.types import JSONPayload, enum_column
from app.models.enums import (
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)

if TYPE_CHECKING:  
    from app.models.user import User


class Notification(Base, TimestampMixin):
    

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[NotificationType] = mapped_column(
        enum_column(NotificationType, 48), nullable=False, index=True
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        enum_column(NotificationChannel, 16),
        default=NotificationChannel.EMAIL,
        nullable=False,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        enum_column(NotificationStatus, 16),
        default=NotificationStatus.QUEUED,
        nullable=False,
        index=True,
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    template_name: Mapped[str] = mapped_column(String(64), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    
    
    dedupe_key: Mapped[str] = mapped_column(String(191), nullable=False)
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONPayload, nullable=True)
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    user: Mapped["User"] = relationship()
    attempt_records: Mapped[list["NotificationAttempt"]] = relationship(
        back_populates="notification", cascade="all, delete-orphan", order_by="NotificationAttempt.id"
    )

    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_notifications_dedupe_key"),
        Index("ix_notifications_queue", "status", "scheduled_for"),
        Index("ix_notifications_user_type", "user_id", "type"),
    )


class NotificationAttempt(Base):
    

    __tablename__ = "notification_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    notification_id: Mapped[int] = mapped_column(
        ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    error_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    was_retry: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    notification: Mapped["Notification"] = relationship(back_populates="attempt_records")

    __table_args__ = (
        UniqueConstraint("notification_id", "attempt_number", name="uq_notification_attempt_number"),
    )
