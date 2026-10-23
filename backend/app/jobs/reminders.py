

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.catalogue import BookCopy
from app.models.circulation import Loan
from app.models.enums import LoanStatus, NotificationType, UserStatus
from app.models.notification import Notification
from app.models.user import User
from app.services.notification_service import queue_notification
from app.utils.helpers import utcnow

logger = logging.getLogger(__name__)


def _window_match(value: int, offsets: list[int], *, ascending: bool) -> Optional[int]:
    
    if not offsets:
        return None
    ordered = sorted(set(offsets), reverse=not ascending)
    for index, offset in enumerate(ordered):
        if ascending:
            upper = ordered[index + 1] if index + 1 < len(ordered) else None
            if upper is None:
                if value >= offset:
                    return offset
            elif offset <= value < upper:
                return offset
        else:
            lower = ordered[index + 1] if index + 1 < len(ordered) else None
            if lower is None:
                if value == offset:
                    return offset
            elif lower < value <= offset:
                return offset
    return None


def eligible_loans(session: Session) -> list[Loan]:
    
    return list(
        session.execute(
            select(Loan)
            .options(
                selectinload(Loan.copy).selectinload(BookCopy.book),
                selectinload(Loan.member),
            )
            .where(
                Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
                Loan.returned_at.is_(None),
                Loan.active_copy_id.isnot(None),
            )
        ).scalars()
        .unique()
    )


def generate_due_reminders(session: Session, policy) -> dict[str, int]:
    
    offsets = list(policy.due_reminder_days or [])
    if not offsets:
        return {"queued": 0}

    now = utcnow()
    today = now.date()
    queued = 0

    for loan in eligible_loans(session):
        if loan.due_at is None:
            continue
        due_date = loan.due_at.date()
        days_until_due = (due_date - today).days
        offset = _window_match(days_until_due, offsets, ascending=False)
        if offset is None:
            continue

        member = loan.member
        if member is None or member.status != UserStatus.ACTIVE:
            continue

        book = loan.copy.book if loan.copy else None
        dedupe_key = f"due_soon:{loan.id}:{loan.due_date_version}:{offset}"
        notification = queue_notification(
            session,
            user=member,
            notification_type=NotificationType.BOOK_DUE_SOON,
            template_name="book_due_soon",
            context={
                "name": member.first_name,
                "title": book.title if book else "",
                "accession_number": loan.copy.accession_number if loan.copy else "",
                "due_at": loan.due_at,
                "days_remaining": max(0, days_until_due),
            },
            dedupe_key=dedupe_key,
        )
        if notification is not None:
            queued += 1

    session.commit()
    if queued:
        logger.info("Queued %s due-date reminder(s)", queued)
    return {"queued": queued}


def generate_overdue_reminders(session: Session, policy) -> dict[str, int]:
    
    offsets = list(policy.overdue_reminder_days or [])
    if not offsets:
        return {"queued": 0}

    now = utcnow()
    today = now.date()
    queued = 0

    for loan in eligible_loans(session):
        if loan.due_at is None:
            continue
        days_overdue = (today - loan.due_at.date()).days
        if days_overdue <= 0:
            continue
        offset = _window_match(days_overdue, offsets, ascending=True)
        if offset is None:
            continue

        
        
        sent_count = session.execute(
            select(func.count(Notification.id)).where(
                Notification.dedupe_key.like(f"overdue:{loan.id}:%")
            )
        ).scalar_one()
        if sent_count >= policy.max_overdue_reminders:
            continue

        member = loan.member
        if member is None or member.status != UserStatus.ACTIVE:
            continue

        book = loan.copy.book if loan.copy else None
        estimated = policy.fine_per_day * max(
            0, days_overdue - policy.grace_period_days
        )
        if policy.max_fine_per_loan is not None and estimated > policy.max_fine_per_loan:
            estimated = policy.max_fine_per_loan

        dedupe_key = f"overdue:{loan.id}:{loan.due_date_version}:{offset}"
        notification = queue_notification(
            session,
            user=member,
            notification_type=NotificationType.BOOK_OVERDUE,
            template_name="book_overdue",
            context={
                "name": member.first_name,
                "title": book.title if book else "",
                "accession_number": loan.copy.accession_number if loan.copy else "",
                "due_at": loan.due_at,
                "overdue_days": days_overdue,
                "fine_amount": float(estimated),
                "currency": policy.currency_code,
            },
            dedupe_key=dedupe_key,
        )
        if notification is not None:
            queued += 1

    session.commit()
    if queued:
        logger.info("Queued %s overdue reminder(s)", queued)
    return {"queued": queued}


def generate_membership_reminders(session: Session, policy) -> dict[str, int]:
    
    offsets = list(policy.membership_expiry_reminder_days or [])
    if not offsets:
        return {"queued": 0}

    now = utcnow()
    today = now.date()
    queued = 0

    members = list(
        session.execute(
            select(User).where(
                User.role.in_(["STUDENT", "FACULTY"]),
                User.status == UserStatus.ACTIVE,
                User.membership_expires.isnot(None),
            )
        ).scalars()
    )

    for member in members:
        expires = member.membership_expires
        if expires is None:
            continue
        expires_date = expires if isinstance(expires, date) else expires.date()
        days_remaining = (expires_date - today).days
        if days_remaining < 0:
            continue
        offset = _window_match(days_remaining, offsets, ascending=False)
        if offset is None:
            continue

        dedupe_key = (
            f"membership_expiring:{member.id}:{expires_date.isoformat()}:{offset}"
        )
        notification = queue_notification(
            session,
            user=member,
            notification_type=NotificationType.MEMBERSHIP_EXPIRING,
            template_name="membership_expiring",
            context={
                "name": member.first_name,
                "membership_type": member.membership_type.value,
                "membership_expires": expires,
                "days_remaining": days_remaining,
            },
            dedupe_key=dedupe_key,
        )
        if notification is not None:
            queued += 1

    session.commit()
    if queued:
        logger.info("Queued %s membership reminder(s)", queued)
    return {"queued": queued}


def generate_all_reminders(session: Session, policy) -> dict[str, int]:
    
    due = generate_due_reminders(session, policy)
    overdue = generate_overdue_reminders(session, policy)
    membership = generate_membership_reminders(session, policy)
    return {
        "due": due["queued"],
        "overdue": overdue["queued"],
        "membership": membership["queued"],
        "total": due["queued"] + overdue["queued"] + membership["queued"],
    }
