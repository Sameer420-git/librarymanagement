

from __future__ import annotations

import logging
import socket
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.email.sender import EmailDeliveryError, EmailMessagePayload, get_sender, render
from app.models.enums import NotificationStatus, NotificationType
from app.models.notification import Notification, NotificationAttempt
from app.models.user import User

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)





def queue_notification(
    session: Session,
    *,
    user: User,
    notification_type: NotificationType,
    template_name: str,
    context: dict[str, Any],
    dedupe_key: str,
    subject: str | None = None,
    scheduled_for: datetime | None = None,
    recipient_email: str | None = None,
    max_attempts: int | None = None,
) -> Notification | None:
    
    existing = session.execute(
        select(Notification.id).where(Notification.dedupe_key == dedupe_key)
    ).first()
    if existing is not None:
        return None

    try:
        rendered = render(template_name, context)
    except KeyError:
        logger.exception("Unknown template %s; falling back to generic", template_name)
        rendered = render("system", context)

    notification = Notification(
        user_id=user.id,
        type=notification_type,
        status=NotificationStatus.QUEUED,
        subject=subject or rendered.subject,
        body_html=rendered.html,
        body_text=rendered.text,
        template_name=template_name,
        recipient_email=recipient_email or user.email,
        dedupe_key=dedupe_key,
        payload=context,
        scheduled_for=scheduled_for or _now(),
        max_attempts=max_attempts or settings.NOTIFICATION_MAX_ATTEMPTS,
    )
    session.add(notification)
    try:
        
        
        with session.begin_nested():
            session.flush()
    except IntegrityError:
        
        return None
    return notification





def claim_notifications(
    session: Session, *, limit: int | None = None, worker_id: str | None = None
) -> list[int]:
    
    limit = limit or settings.NOTIFICATION_BATCH_SIZE
    worker_id = worker_id or f"worker-{socket.gethostname()}-{uuid.uuid4().hex[:8]}"

    now = _now()
    stmt = (
        select(Notification)
        .where(
            Notification.status.in_([NotificationStatus.QUEUED, NotificationStatus.SENDING]),
            Notification.scheduled_for <= now,
            Notification.attempts < Notification.max_attempts,
        )
        .order_by(Notification.scheduled_for.asc(), Notification.id.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    rows = list(session.execute(stmt).scalars())

    claimed: list[int] = []
    for notification in rows:
        
        
        if notification.status == NotificationStatus.SENDING:
            locked_at = notification.locked_at
            if locked_at is not None:
                locked_at = (
                    locked_at.replace(tzinfo=timezone.utc)
                    if locked_at.tzinfo is None
                    else locked_at
                )
                if locked_at > now - timedelta(minutes=15):
                    continue
        notification.status = NotificationStatus.SENDING
        notification.locked_at = now
        notification.locked_by = worker_id
        notification.attempts += 1
        notification.last_attempt_at = now
        claimed.append(notification.id)

    session.commit()
    return claimed


def deliver_notification(session: Session, notification_id: int) -> bool:
    
    notification = session.get(Notification, notification_id)
    if notification is None:
        return False

    attempt_number = notification.attempts
    started = _now()
    sender = get_sender()
    payload = EmailMessagePayload(
        to_email=notification.recipient_email,
        subject=notification.subject,
        html=notification.body_html,
        text=notification.body_text,
    )

    status = NotificationStatus.SENT
    error_message: str | None = None
    error_type: str | None = None

    try:
        sender.send(payload)
    except EmailDeliveryError as exc:
        status = NotificationStatus.FAILED
        error_type = exc.__class__.__name__
        error_message = _sanitize_error(str(exc))
    except Exception as exc:  
        status = NotificationStatus.FAILED
        error_type = exc.__class__.__name__
        error_message = _sanitize_error(str(exc))

    finished = _now()
    duration_ms = int((finished - started).total_seconds() * 1000)

    
    session.rollback()
    notification = session.get(Notification, notification_id)
    if notification is None:
        return False

    attempt = NotificationAttempt(
        notification_id=notification.id,
        attempt_number=attempt_number,
        status=status.value,
        error_message=error_message,
        error_type=error_type,
        duration_ms=duration_ms,
        started_at=started,
        finished_at=finished,
        was_retry=attempt_number > 1,
    )
    session.add(attempt)

    notification.last_error = error_message
    notification.sent_at = finished if status == NotificationStatus.SENT else None

    if status == NotificationStatus.SENT:
        notification.status = NotificationStatus.SENT
    elif notification.attempts < notification.max_attempts:
        notification.status = NotificationStatus.QUEUED
        notification.scheduled_for = _now() + _backoff_seconds(notification.attempts)
    else:
        notification.status = NotificationStatus.FAILED

    notification.locked_at = None
    notification.locked_by = None
    session.commit()
    return status == NotificationStatus.SENT


def _backoff_seconds(attempt: int) -> timedelta:
    
    base = settings.NOTIFICATION_RETRY_BASE_SECONDS
    delay = min(base * (2 ** max(0, attempt - 1)), 3600)
    return timedelta(seconds=delay)


def _sanitize_error(message: str) -> str:
    
    sanitised = message.replace("\n", " ").strip()
    for secret_marker in ("password", "secret", "auth", "credential"):
        if secret_marker in sanitised.lower():
            sanitised = "Delivery failed (details redacted)"
            break
    return sanitised[:500]


def process_pending(session: Session, *, limit: int | None = None) -> dict[str, int]:
    
    claimed = claim_notifications(session, limit=limit)
    sent = 0
    failed = 0
    for notification_id in claimed:
        if deliver_notification(session, notification_id):
            sent += 1
        else:
            failed += 1
    return {"claimed": len(claimed), "sent": sent, "failed": failed}


def retry_notification(
    session: Session, notification_id: int, *, reset_attempts: bool = False
) -> Notification:
    
    notification = session.get(Notification, notification_id)
    if notification is None:
        raise ValueError("Notification not found")
    if notification.status == NotificationStatus.SENT:
        raise ValueError("Notification has already been delivered")
    if reset_attempts:
        notification.attempts = 0
    notification.status = NotificationStatus.QUEUED
    notification.scheduled_for = _now()
    notification.locked_at = None
    notification.locked_by = None
    session.commit()
    return notification


def cancel_notification(session: Session, notification_id: int) -> Notification:
    notification = session.get(Notification, notification_id)
    if notification is None:
        raise ValueError("Notification not found")
    if notification.status == NotificationStatus.SENT:
        raise ValueError("Notification has already been delivered")
    notification.status = NotificationStatus.CANCELLED
    session.commit()
    return notification


def pending_count(session: Session) -> dict[str, int]:
    from sqlalchemy import func

    rows = session.execute(
        select(Notification.status, func.count(Notification.id)).group_by(Notification.status)
    ).all()
    counts = {status.value: 0 for status in NotificationStatus}
    for status_value, count in rows:
        counts[status_value] = int(count)
    return counts


def find_by_dedupe_key(session: Session, dedupe_key: str) -> Optional[Notification]:
    return session.execute(
        select(Notification).where(Notification.dedupe_key == dedupe_key)
    ).scalar_one_or_none()
