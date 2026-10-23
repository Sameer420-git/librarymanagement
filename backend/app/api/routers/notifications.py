

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DbSession, StaffUser
from app.core.exceptions import NotFoundError, ValidationError
from app.models.enums import NotificationStatus
from app.models.notification import Notification
from app.schemas.common import Page
from app.schemas.notification import (
    NotificationAttemptRead,
    NotificationDetail,
    NotificationRead,
    NotificationStats,
    TestEmailRequest,
    TestEmailResponse,
)
from app.services import notification_service
from app.services.notification_service import pending_count, retry_notification

router = APIRouter(tags=["Notifications"])


@router.get(
    "/notifications",
    response_model=Page[NotificationRead],
    summary="Notification history of the signed-in account",
)
def list_my_notifications(
    session: DbSession,
    current_user: CurrentUser,
    notification_status: Optional[str] = Query(default=None, alias="status"),
    notification_type: Optional[str] = Query(default=None, alias="type"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[NotificationRead]:
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    if notification_status:
        try:
            stmt = stmt.where(Notification.status == NotificationStatus(notification_status.upper()))
        except ValueError:
            raise ValidationError(f"Unknown notification status '{notification_status}'.")
    if notification_type:
        stmt = stmt.where(Notification.type == notification_type.upper())

    from sqlalchemy import func

    total = session.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()
    stmt = stmt.order_by(Notification.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = list(session.execute(stmt).scalars())
    return Page.build([NotificationRead.model_validate(row) for row in rows], page, page_size, total)


@router.get(
    "/notifications/{notification_id}",
    response_model=NotificationDetail,
    summary="Notification detail",
)
def notification_detail(
    notification_id: int, session: DbSession, current_user: CurrentUser
) -> NotificationDetail:
    notification = session.get(Notification, notification_id)
    if notification is None:
        raise NotFoundError("Notification not found.")
    if (
        notification.user_id != current_user.id
        and current_user.role.value not in ("LIBRARIAN", "SUPER_ADMIN")
    ):
        raise NotFoundError("Notification not found.")

    attempts = [
        NotificationAttemptRead.model_validate(attempt)
        for attempt in notification.attempt_records
    ]
    detail = NotificationDetail.model_validate(notification)
    detail.attempts_log = attempts
    return detail





@router.get(
    "/admin/notifications",
    response_model=Page[NotificationRead],
    summary="Monitor the notification queue",
)
def list_all_notifications(
    session: DbSession,
    current_user: StaffUser,
    notification_status: Optional[str] = Query(default=None, alias="status"),
    notification_type: Optional[str] = Query(default=None, alias="type"),
    user_id: Optional[int] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[NotificationRead]:
    from sqlalchemy import func

    stmt = select(Notification)
    if notification_status:
        try:
            stmt = stmt.where(Notification.status == NotificationStatus(notification_status.upper()))
        except ValueError:
            raise ValidationError(f"Unknown notification status '{notification_status}'.")
    if notification_type:
        stmt = stmt.where(Notification.type == notification_type.upper())
    if user_id:
        stmt = stmt.where(Notification.user_id == user_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            Notification.subject.like(pattern) | Notification.recipient_email.like(pattern)
        )

    total = session.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()
    stmt = stmt.order_by(Notification.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = list(session.execute(stmt).scalars())
    return Page.build([NotificationRead.model_validate(row) for row in rows], page, page_size, total)


@router.get(
    "/admin/notifications/stats",
    response_model=NotificationStats,
    summary="Notification delivery statistics",
)
def notification_stats(session: DbSession, current_user: StaffUser) -> NotificationStats:
    counts = pending_count(session)
    total = sum(counts.values())
    failed = counts.get(NotificationStatus.FAILED.value, 0)
    sent = counts.get(NotificationStatus.SENT.value, 0)
    failure_rate = (failed / (failed + sent)) if (failed + sent) else 0.0
    return NotificationStats(
        queued=counts.get(NotificationStatus.QUEUED.value, 0),
        sending=counts.get(NotificationStatus.SENDING.value, 0),
        sent=sent,
        failed=failed,
        cancelled=counts.get(NotificationStatus.CANCELLED.value, 0),
        total=total,
        failure_rate=round(failure_rate, 4),
    )


@router.post(
    "/admin/notifications/{notification_id}/retry",
    response_model=NotificationRead,
    summary="Re-queue a failed notification",
)
def retry(
    notification_id: int,
    session: DbSession,
    current_user: StaffUser,
    reset_attempts: bool = Query(default=True),
) -> NotificationRead:
    from app.services.audit_service import log_action

    try:
        notification = retry_notification(
            session, notification_id, reset_attempts=reset_attempts
        )
    except ValueError as exc:
        raise ValidationError(str(exc))
    log_action(
        session,
        AuditAction.NOTIFICATION_RETRIED,
        actor=current_user,
        entity_type="notification",
        entity_id=notification.id,
        summary=f"Notification {notification.id} re-queued for delivery",
    )
    session.commit()
    return NotificationRead.model_validate(notification)


@router.post(
    "/admin/notifications/test",
    response_model=TestEmailResponse,
    summary="Send a test e-mail to verify the SMTP configuration",
)
def send_test_email(
    payload: TestEmailRequest, session: DbSession, current_user: StaffUser
) -> TestEmailResponse:
    from app.email.sender import EmailDeliveryError, EmailMessagePayload, get_sender
    from app.services.audit_service import log_action

    recipient = payload.to_email or current_user.email
    sender = get_sender()
    try:
        sender.send(
            EmailMessagePayload(
                to_email=recipient,
                subject=payload.subject or "College Library - SMTP test",
                html=(
                    "<html><body style=\"font-family:Segoe UI,Arial,sans-serif\">"
                    "<h2>College Library - SMTP configuration test</h2>"
                    f"<p>Sent by {current_user.email} to verify the e-mail configuration.</p>"
                    "</body></html>"
                ),
                text="College Library SMTP configuration test.",
            )
        )
    except EmailDeliveryError as exc:
        log_action(
            session,
            AuditAction.NOTIFICATION_FAILED,
            actor=current_user,
            entity_type="notification",
            summary="SMTP test e-mail failed",
        )
        session.commit()
        return TestEmailResponse(
            success=False,
            message="The test e-mail could not be delivered.",
            recipient=recipient,
            error=str(exc),
        )

    log_action(
        session,
        AuditAction.NOTIFICATION_SENT,
        actor=current_user,
        entity_type="notification",
        summary=f"SMTP test e-mail sent to {recipient}",
    )
    session.commit()
    return TestEmailResponse(
        success=True,
        message=f"Test e-mail sent to {recipient}.", recipient=recipient
    )
