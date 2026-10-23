

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.catalogue import Book, BookCopy
from app.models.circulation import Fine, Loan, LoanRenewal, Reservation
from app.models.enums import (
    AuditAction,
    BookCopyStatus,
    FineStatus,
    LoanStatus,
    NotificationType,
    ReservationStatus,
)
from app.models.user import User
from app.services.audit_service import log_action
from app.services.policy_service import get_policy, loan_period_for, max_books_for
from app.services.notification_service import queue_notification
from app.utils.helpers import money, naive_utc, utcnow

logger = logging.getLogger(__name__)





def get_loan(session: Session, loan_id: int, *, for_update: bool = False) -> Loan:
    stmt = (
        select(Loan)
        .where(Loan.id == loan_id)
        .options(
            selectinload(Loan.copy).selectinload(BookCopy.book),
            selectinload(Loan.member),
        )
    )
    if for_update:
        stmt = stmt.with_for_update()
    loan = session.execute(stmt).scalar_one_or_none()
    if loan is None:
        raise NotFoundError("Loan not found.")
    return loan


def loan_payload(session: Session, loan: Loan) -> dict[str, Any]:
    book = loan.copy.book if loan.copy else None
    due_at = loan.due_at
    now = utcnow()
    days_overdue = 0
    is_overdue = False
    if loan.returned_at is None and due_at is not None:
        if due_at.tzinfo is None:
            reference = due_at
        else:
            reference = due_at.replace(tzinfo=None)
        days_overdue = max(0, (now - reference).days)
        is_overdue = days_overdue > 0

    fine_amount = None
    if loan.fine is not None:
        fine_amount = float(money(loan.fine.amount - loan.fine.amount_paid))

    return {
        "id": loan.id,
        "copy_id": loan.copy_id,
        "member_id": loan.member_id,
        "issued_at": loan.issued_at,
        "due_at": loan.due_at,
        "returned_at": loan.returned_at,
        "status": loan.status,
        "renewal_count": loan.renewal_count,
        "overdue_days": days_overdue,
        "notes": loan.notes,
        "book_id": book.id if book else None,
        "book_title": book.title if book else None,
        "accession_number": loan.copy.accession_number if loan.copy else None,
        "member_name": loan.member.full_name if loan.member else None,
        "member_email": loan.member.email if loan.member else None,
        "issued_by_name": loan.issued_by.full_name if loan.issued_by else None,
        "returned_by_name": loan.returned_by.full_name if loan.returned_by else None,
        "days_overdue": days_overdue,
        "is_overdue": is_overdue,
        "fine_amount": fine_amount,
        "fine_id": loan.fine_id,
    }





def issue_book(
    session: Session,
    *,
    member_id: int,
    copy_id: int,
    actor: User,
    due_at: datetime | None = None,
    notes: str | None = None,
) -> Loan:
    
    try:
        policy = get_policy(session)

        member = session.execute(
            select(User).where(User.id == member_id).with_for_update()
        ).scalar_one_or_none()
        if member is None:
            raise NotFoundError("Member not found.")

        copy = session.execute(
            select(BookCopy)
            .where(BookCopy.id == copy_id)
            .options(selectinload(BookCopy.book))
            .with_for_update()
        ).scalar_one_or_none()
        if copy is None:
            raise NotFoundError("Book copy not found.")

        book = copy.book
        if book is None:
            raise NotFoundError("Catalogue entry for this copy is missing.")
        if not book.is_active:
            raise ValidationError("This title has been retired and cannot be issued.")
        if book.is_reference_only:
            raise ValidationError("This title is reference-only and cannot be issued.")

        
        if member.status.value != "ACTIVE":
            raise ValidationError("The member's account is not active.")
        if not member.is_email_verified:
            raise ValidationError("The member's e-mail address is not verified.")
        if member.membership_expires is not None:
            expires = member.membership_expires
            if isinstance(expires, datetime):
                expires = expires.date()
            if expires < utcnow().date():
                raise ValidationError("The member's library membership has expired.")

        
        outstanding = session.execute(
            select(func.coalesce(func.sum(Fine.amount - Fine.amount_paid), 0)).where(
                Fine.member_id == member.id,
                Fine.status.in_([FineStatus.PENDING, FineStatus.PARTIALLY_PAID]),
            )
        ).scalar_one()
        outstanding_decimal = money(outstanding)
        if outstanding_decimal > policy.max_fine_blocks_issue:
            raise ValidationError(
                f"The member has outstanding fines of {policy.currency_code} "
                f"{outstanding_decimal:.2f} which exceeds the borrowing limit."
            )

        
        limit = max_books_for(policy, member.role)
        active_loans = session.execute(
            select(func.count(Loan.id)).where(
                Loan.member_id == member.id,
                Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
            )
        ).scalar_one()
        if active_loans >= limit:
            raise ValidationError(
                f"The member already has {active_loans} of {limit} permitted book(s) on loan."
            )

        
        if copy.status != BookCopyStatus.AVAILABLE:
            if copy.status == BookCopyStatus.RESERVED:
                raise ConflictError(
                    "This copy is reserved for another member and cannot be issued."
                )
            raise ConflictError(
                f"Copy {copy.accession_number} is not available (status: {copy.status.value})."
            )

        existing_active = session.execute(
            select(Loan.id).where(
                Loan.copy_id == copy.id,
                Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
            )
        ).first()
        if existing_active is not None:
            raise ConflictError("This copy is already on loan to another member.")

        
        issued_at = utcnow()
        if due_at is None:
            period_days = loan_period_for(policy, member.role)
            due_at = issued_at + timedelta(days=period_days)
        else:
            due_at = naive_utc(due_at)
            if due_at <= issued_at:
                raise ValidationError("The due date must be in the future.")

        loan = Loan(
            copy_id=copy.id,
            member_id=member.id,
            issued_by_id=actor.id,
            issued_at=issued_at,
            due_at=due_at,
            status=LoanStatus.ACTIVE,
            renewal_count=0,
            due_date_version=1,
            active_copy_id=copy.id,
        )
        if notes:
            loan.notes = notes
        session.add(loan)
        session.flush()

        copy.status = BookCopyStatus.ISSUED
        copy.status_changed_at = issued_at
        copy.status_changed_by_id = actor.id

        from app.services.book_service import recalculate_availability

        recalculate_availability(session, book)

        queue_notification(
            session,
            user=member,
            notification_type=NotificationType.BOOK_ISSUED,
            template_name="book_issued",
            context={
                "name": member.first_name,
                "title": book.title,
                "authors": [author.name for author in book.authors],
                "accession_number": copy.accession_number,
                "issued_at": issued_at,
                "due_at": due_at,
            },
            dedupe_key=f"loan_issued:{loan.id}",
        )

        log_action(
            session,
            AuditAction.LOAN_ISSUED,
            actor=actor,
            entity_type="loan",
            entity_id=loan.id,
            summary=(
                f"Issued '{book.title}' ({copy.accession_number}) to "
                f"{member.full_name}; due {due_at:%Y-%m-%d}"
            ),
        )
        session.commit()
        return get_loan(session, loan.id)
    except Exception:
        session.rollback()
        raise





def return_book(
    session: Session,
    loan_id: int,
    actor: User,
    *,
    notes: str | None = None,
    copy_condition: str | None = None,
) -> tuple[Loan, Optional[Fine], Optional[Reservation]]:
    
    try:
        policy = get_policy(session)
        loan = get_loan(session, loan_id, for_update=True)

        if loan.status in (LoanStatus.RETURNED, LoanStatus.LOST):
            raise ValidationError("This loan has already been closed.")
        if loan.active_copy_id is None:
            raise ValidationError("This loan has already been closed.")

        copy = session.execute(
            select(BookCopy).where(BookCopy.id == loan.copy_id).with_for_update()
        ).scalar_one_or_none()
        if copy is None:
            raise NotFoundError("Book copy not found.")

        member = loan.member
        returned_at = utcnow()
        due_at = loan.due_at
        overdue_days = max(0, (returned_at - due_at).days)

        fine = _assess_fine(session, policy, loan, overdue_days, actor)

        loan.status = LoanStatus.RETURNED
        loan.returned_at = returned_at
        loan.returned_by_id = actor.id
        loan.active_copy_id = None
        loan.overdue_days = overdue_days
        if notes:
            loan.notes = notes
        session.flush()

        
        
        from app.models.enums import CopyCondition

        if copy_condition:
            try:
                copy.condition = CopyCondition(copy_condition)
            except ValueError:
                raise ValidationError(f"Unknown copy condition '{copy_condition}'.")
        if copy.condition == CopyCondition.DAMAGED:
            copy.status = BookCopyStatus.DAMAGED
        else:
            copy.status = BookCopyStatus.AVAILABLE
        copy.status_changed_at = returned_at
        copy.status_changed_by_id = actor.id

        from app.services.book_service import recalculate_availability

        recalculate_availability(session, copy.book)

        
        from app.services.reservation_service import allocate_next_reservation

        reservation = allocate_next_reservation(session, copy.book_id, actor=actor)

        queue_notification(
            session,
            user=member,
            notification_type=NotificationType.BOOK_RETURNED,
            template_name="book_returned",
            context={
                "name": member.first_name,
                "title": copy.book.title if copy.book else "",
                "accession_number": copy.accession_number,
                "issued_at": loan.issued_at,
                "returned_at": returned_at,
                "overdue_days": overdue_days,
                "fine_amount": float(fine.amount) if fine else 0,
                "currency": policy.currency_code,
            },
            dedupe_key=f"loan_returned:{loan.id}",
        )

        if fine is not None:
            queue_notification(
                session,
                user=member,
                notification_type=NotificationType.FINE_ASSESSED,
                template_name="fine_assessed",
                context={
                    "name": member.first_name,
                    "title": copy.book.title if copy.book else "",
                    "overdue_days": overdue_days,
                    "rate_per_day": float(policy.fine_per_day),
                    "amount": float(fine.amount),
                    "outstanding": float(fine.amount - fine.amount_paid),
                    "currency": policy.currency_code,
                },
                dedupe_key=f"fine_assessed:{fine.id}",
            )

        log_action(
            session,
            AuditAction.LOAN_RETURNED,
            actor=actor,
            entity_type="loan",
            entity_id=loan.id,
            summary=(
                f"Returned '{copy.book.title if copy.book else copy.accession_number}' "
                f"from {member.full_name}; {overdue_days} day(s) overdue"
            ),
        )
        session.commit()
        return get_loan(session, loan.id), fine, reservation
    except Exception:
        session.rollback()
        raise


def _assess_fine(
    session: Session,
    policy: Any,
    loan: Loan,
    overdue_days: int,
    actor: User,
) -> Optional[Fine]:
    
    if overdue_days <= policy.grace_period_days:
        return None

    chargeable_days = overdue_days - policy.grace_period_days
    amount = money(Decimal(str(policy.fine_per_day)) * Decimal(chargeable_days))
    if policy.max_fine_per_loan is not None and amount > policy.max_fine_per_loan:
        amount = money(policy.max_fine_per_loan)
    if amount <= 0:
        return None

    fine = Fine(
        member_id=loan.member_id,
        loan_id=loan.id,
        amount=amount,
        amount_paid=Decimal("0.00"),
        days_overdue=overdue_days,
        rate_per_day=money(policy.fine_per_day),
        reason="Overdue return",
        status=FineStatus.PENDING,
        assessed_at=utcnow(),
        assessed_by_id=actor.id,
    )
    session.add(fine)
    session.flush()
    loan.fine_id = fine.id
    session.flush()
    log_action(
        session,
        AuditAction.FINE_ASSESSED,
        actor=actor,
        entity_type="fine",
        entity_id=fine.id,
        summary=f"Assessed fine of {policy.currency_code} {amount:.2f} on loan {loan.id}",
    )
    return fine





def renew_loan(
    session: Session, loan_id: int, actor: User, *, notes: str | None = None
) -> Loan:
    
    try:
        policy = get_policy(session)
        loan = get_loan(session, loan_id, for_update=True)

        if loan.status not in (LoanStatus.ACTIVE, LoanStatus.OVERDUE):
            raise ValidationError("Only active loans can be renewed.")
        if loan.returned_at is not None:
            raise ValidationError("This loan has already been returned.")

        member = loan.member
        now = utcnow()
        if loan.due_at < now:
            raise ValidationError(
                "An overdue loan cannot be renewed. Please return the book first."
            )

        if loan.renewal_count >= policy.max_renewals:
            raise ValidationError(
                f"The renewal limit of {policy.max_renewals} has been reached."
            )

        outstanding = session.execute(
            select(func.coalesce(func.sum(Fine.amount - Fine.amount_paid), 0)).where(
                Fine.member_id == member.id,
                Fine.status.in_([FineStatus.PENDING, FineStatus.PARTIALLY_PAID]),
            )
        ).scalar_one()
        if money(outstanding) > policy.max_fine_blocks_renewal:
            raise ValidationError(
                "Outstanding fines must be settled before a loan can be renewed."
            )

        
        
        waiting = session.execute(
            select(func.count(Reservation.id)).where(
                Reservation.book_id == loan.copy.book_id,
                Reservation.status == ReservationStatus.ACTIVE,
                Reservation.member_id != member.id,
            )
        ).scalar_one()
        if waiting:
            raise ConflictError(
                "Another member is waiting for this title, so the loan cannot be renewed."
            )

        previous_due_at = loan.due_at
        new_due_at = loan.due_at + timedelta(days=policy.renewal_period_days)

        session.add(
            LoanRenewal(
                loan_id=loan.id,
                renewed_by_id=actor.id,
                previous_due_at=previous_due_at,
                new_due_at=new_due_at,
                renewal_number=loan.renewal_count + 1,
                renewed_at=now,
                note=notes,
            )
        )
        loan.due_at = new_due_at
        loan.renewal_count += 1
        loan.due_date_version += 1
        if loan.status == LoanStatus.OVERDUE:
            loan.status = LoanStatus.ACTIVE
        session.flush()

        queue_notification(
            session,
            user=member,
            notification_type=NotificationType.BOOK_DUE_SOON,
            template_name="book_due_soon",
            context={
                "name": member.first_name,
                "title": loan.copy.book.title if loan.copy and loan.copy.book else "",
                "accession_number": loan.copy.accession_number if loan.copy else "",
                "due_at": new_due_at,
                "days_remaining": policy.renewal_period_days,
            },
            dedupe_key=f"loan_renewed:{loan.id}:{loan.due_date_version}",
        )

        log_action(
            session,
            AuditAction.LOAN_RENEWED,
            actor=actor,
            entity_type="loan",
            entity_id=loan.id,
            summary=(
                f"Renewed loan {loan.id} until {new_due_at:%Y-%m-%d} "
                f"(renewal {loan.renewal_count})"
            ),
        )
        session.commit()
        return get_loan(session, loan.id)
    except Exception:
        session.rollback()
        raise





def list_loans(
    session: Session, params: dict[str, Any], *, restrict_to_member: int | None = None
) -> tuple[list[Loan], int]:
    stmt = select(Loan).options(
        selectinload(Loan.copy).selectinload(BookCopy.book),
        selectinload(Loan.member),
        selectinload(Loan.fine),
    )
    if restrict_to_member is not None:
        stmt = stmt.where(Loan.member_id == restrict_to_member)
    if params.get("member_id"):
        stmt = stmt.where(Loan.member_id == params["member_id"])
    if params.get("book_id"):
        stmt = stmt.where(Loan.copy_id.in_(
            select(BookCopy.id).where(BookCopy.book_id == params["book_id"])
        ))
    if params.get("copy_id"):
        stmt = stmt.where(Loan.copy_id == params["copy_id"])
    if params.get("status"):
        stmt = stmt.where(Loan.status == params["status"])
    if params.get("search"):
        pattern = f"%{params['search']}%"
        stmt = stmt.where(
            or_(
                Loan.member.has(User.first_name.ilike(pattern)),
                Loan.member.has(User.last_name.ilike(pattern)),
                Loan.member.has(User.email.ilike(pattern)),
                Loan.copy.has(BookCopy.accession_number.ilike(pattern)),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = session.execute(count_stmt).scalar_one()

    order = (params.get("sort_order") or "desc").lower()
    column = Loan.issued_at
    if params.get("sort_by") == "due_at":
        column = Loan.due_at
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), Loan.id.desc())

    page = params.get("page", 1)
    page_size = params.get("page_size", 20)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    return list(session.execute(stmt).scalars().unique()), total


def overdue_loans(session: Session, params: dict[str, Any]) -> tuple[list[Loan], int]:
    now = utcnow()
    stmt = (
        select(Loan)
        .options(
            selectinload(Loan.copy).selectinload(BookCopy.book),
            selectinload(Loan.member),
            selectinload(Loan.fine),
        )
        .where(
            Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
            Loan.returned_at.is_(None),
            Loan.due_at < now,
        )
    )
    if params.get("member_id"):
        stmt = stmt.where(Loan.member_id == params["member_id"])
    if params.get("book_id"):
        stmt = stmt.where(Loan.copy_id.in_(
            select(BookCopy.id).where(BookCopy.book_id == params["book_id"])
        ))

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = session.execute(count_stmt).scalar_one()

    page = params.get("page", 1)
    page_size = params.get("page_size", 20)
    stmt = stmt.order_by(Loan.due_at.asc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    return list(session.execute(stmt).scalars().unique()), total


def mark_overdue_loans(session: Session) -> int:
    
    now = utcnow()
    result = session.execute(
        select(Loan.id).where(
            Loan.status == LoanStatus.ACTIVE, Loan.due_at < now
        )
    ).all()
    for (loan_id,) in result:
        session.execute(
            Loan.__table__.update()
            .where(Loan.id == loan_id)
            .values(status=LoanStatus.OVERDUE)
        )
    session.commit()
    return len(result)
