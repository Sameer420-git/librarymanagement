

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.catalogue import Book, BookCopy
from app.models.circulation import Loan, Reservation
from app.models.enums import (
    AuditAction,
    BookCopyStatus,
    LoanStatus,
    NotificationType,
    ReservationStatus,
    UserRole,
)
from app.models.user import User
from app.services.audit_service import log_action
from app.services.notification_service import queue_notification
from app.services.policy_service import get_policy
from app.utils.helpers import utcnow

logger = logging.getLogger(__name__)


def get_reservation(session: Session, reservation_id: int, *, for_update: bool = False) -> Reservation:
    stmt = (
        select(Reservation)
        .where(Reservation.id == reservation_id)
        .options(
            selectinload(Reservation.book).selectinload(Book.authors),
            selectinload(Reservation.member),
            selectinload(Reservation.copy),
        )
    )
    if for_update:
        stmt = stmt.with_for_update()
    reservation = session.execute(stmt).scalar_one_or_none()
    if reservation is None:
        raise NotFoundError("Reservation not found.")
    return reservation


def reservation_payload(reservation: Reservation) -> dict[str, Any]:
    book = reservation.book
    return {
        "id": reservation.id,
        "book_id": reservation.book_id,
        "member_id": reservation.member_id,
        "copy_id": reservation.copy_id,
        "status": reservation.status,
        "position": reservation.position,
        "queue_position": reservation.queue_position,
        "reserved_at": reservation.reserved_at,
        "ready_at": reservation.ready_at,
        "pickup_deadline": reservation.pickup_deadline,
        "fulfilled_at": reservation.fulfilled_at,
        "cancelled_at": reservation.cancelled_at,
        "expired_at": reservation.expired_at,
        "book_title": book.title if book else None,
        "book_authors": [author.name for author in book.authors] if book else [],
        "member_name": reservation.member.full_name if reservation.member else None,
        "accession_number": reservation.copy.accession_number if reservation.copy else None,
        "shelf_location": reservation.copy.shelf_location if reservation.copy else None,
    }





def create_reservation(
    session: Session, *, member_id: int, book_id: int, actor: User, notes: str | None = None
) -> Reservation:
    
    try:
        policy = get_policy(session)
        member = session.execute(
            select(User).where(User.id == member_id).with_for_update()
        ).scalar_one_or_none()
        if member is None:
            raise NotFoundError("Member not found.")

        book = session.execute(
            select(Book).where(Book.id == book_id).with_for_update()
        ).scalar_one_or_none()
        if book is None:
            raise NotFoundError("Book not found.")
        if not book.is_active:
            raise ValidationError("This title is not available for reservation.")
        if book.is_reference_only:
            raise ValidationError("Reference-only titles cannot be reserved.")

        
        on_loan = session.execute(
            select(Loan.id)
            .join(BookCopy, BookCopy.id == Loan.copy_id)
            .where(
                Loan.member_id == member.id,
                BookCopy.book_id == book.id,
                Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
            )
        ).first()
        if on_loan is not None:
            raise ConflictError("You already have this title on loan.")

        existing = session.execute(
            select(Reservation).where(
                Reservation.member_id == member.id,
                Reservation.book_id == book.id,
                Reservation.status.in_([ReservationStatus.ACTIVE, ReservationStatus.READY]),
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise ConflictError("You have already reserved this title.")

        active_count = session.execute(
            select(func.count(Reservation.id)).where(
                Reservation.member_id == member.id,
                Reservation.status.in_([ReservationStatus.ACTIVE, ReservationStatus.READY]),
            )
        ).scalar_one()
        if active_count >= policy.max_active_reservations:
            raise ValidationError(
                f"You already hold {active_count} of {policy.max_active_reservations} "
                "permitted active reservations."
            )

        position = (
            session.execute(
                select(func.coalesce(func.max(Reservation.position), 0)).where(
                    Reservation.book_id == book.id
                )
            ).scalar_one()
            or 0
        ) + 1

        reservation = Reservation(
            book_id=book.id,
            member_id=member.id,
            status=ReservationStatus.ACTIVE,
            position=position,
            queue_position=position,
            reserved_at=utcnow(),
            active_key=f"{member.id}:{book.id}",
            notes=notes,
        )
        session.add(reservation)
        session.flush()

        log_action(
            session,
            AuditAction.RESERVATION_CREATED,
            actor=actor,
            entity_type="reservation",
            entity_id=reservation.id,
            summary=f"Reserved '{book.title}' for {member.full_name} (position {position})",
        )
        session.commit()
        return get_reservation(session, reservation.id)
    except Exception:
        session.rollback()
        raise


def cancel_reservation(
    session: Session, reservation_id: int, actor: User, *, member_id: int | None = None
) -> Reservation:
    
    try:
        reservation = get_reservation(session, reservation_id, for_update=True)
        if member_id is not None and reservation.member_id != member_id:
            raise ValidationError("You can only cancel your own reservations.")
        if reservation.status in (
            ReservationStatus.CANCELLED,
            ReservationStatus.FULFILLED,
            ReservationStatus.EXPIRED,
        ):
            raise ValidationError("This reservation is already closed.")

        now = utcnow()
        reservation.status = ReservationStatus.CANCELLED
        reservation.cancelled_at = now
        reservation.active_key = None
        if reservation.copy_id:
            copy = session.get(BookCopy, reservation.copy_id)
            if copy is not None and copy.status == BookCopyStatus.RESERVED:
                copy.status = BookCopyStatus.AVAILABLE
                copy.status_changed_at = now
                from app.services.book_service import recalculate_availability

                recalculate_availability(session, copy.book)
        session.flush()
        _reposition_queue(session, reservation.book_id)
        log_action(
            session,
            AuditAction.RESERVATION_CANCELLED,
            actor=actor,
            entity_type="reservation",
            entity_id=reservation.id,
            summary="Reservation cancelled",
        )
        session.commit()
        return get_reservation(session, reservation.id)
    except Exception:
        session.rollback()
        raise


def _reposition_queue(session: Session, book_id: int) -> None:
    
    rows = list(
        session.execute(
            select(Reservation)
            .where(
                Reservation.book_id == book_id,
                Reservation.status == ReservationStatus.ACTIVE,
            )
            .order_by(Reservation.reserved_at.asc(), Reservation.id.asc())
        ).scalars()
    )
    for index, reservation in enumerate(rows, start=1):
        reservation.position = index
        reservation.queue_position = index
    session.flush()





def allocate_next_reservation(
    session: Session, book_id: int, actor: User | None = None
) -> Optional[Reservation]:
    
    policy = get_policy(session)

    reservation = session.execute(
        select(Reservation)
        .where(
            Reservation.book_id == book_id,
            Reservation.status == ReservationStatus.ACTIVE,
        )
        .order_by(Reservation.reserved_at.asc(), Reservation.id.asc())
        .with_for_update()
        .limit(1)
    ).scalar_one_or_none()
    if reservation is None:
        return None

    copy = session.execute(
        select(BookCopy)
        .where(
            BookCopy.book_id == book_id,
            BookCopy.status == BookCopyStatus.AVAILABLE,
        )
        .with_for_update()
        .limit(1)
    ).scalar_one_or_none()
    if copy is None:
        return None

    now = utcnow()
    copy.status = BookCopyStatus.RESERVED
    copy.status_changed_at = now
    copy.status_changed_by_id = actor.id if actor else None

    reservation.status = ReservationStatus.READY
    reservation.copy_id = copy.id
    reservation.ready_at = now
    reservation.pickup_deadline = now + timedelta(days=policy.reservation_pickup_days)
    reservation.queue_position = 0
    session.flush()

    member = reservation.member
    if member is not None:
        queue_notification(
            session,
            user=member,
            notification_type=NotificationType.RESERVATION_AVAILABLE,
            template_name="reservation_available",
            context={
                "name": member.first_name,
                "title": reservation.book.title if reservation.book else "",
                "authors": [a.name for a in reservation.book.authors] if reservation.book else [],
                "accession_number": copy.accession_number,
                "shelf_location": copy.shelf_location,
                "pickup_deadline": reservation.pickup_deadline,
            },
            dedupe_key=f"reservation_ready:{reservation.id}",
        )

    log_action(
        session,
        AuditAction.RESERVATION_ALLOCATED,
        actor=actor,
        entity_type="reservation",
        entity_id=reservation.id,
        summary=f"Allocated copy {copy.accession_number} to reservation #{reservation.id}",
    )
    return reservation


def expire_reservations(session: Session) -> int:
    
    now = utcnow()
    expired = 0
    rows = list(
        session.execute(
            select(Reservation)
            .where(
                Reservation.status == ReservationStatus.READY,
                Reservation.pickup_deadline.isnot(None),
                Reservation.pickup_deadline < now,
            )
            .options(selectinload(Reservation.book), selectinload(Reservation.member))
            .with_for_update()
        ).scalars()
    )
    for reservation in rows:
        reservation.status = ReservationStatus.EXPIRED
        reservation.expired_at = now
        reservation.active_key = None
        if reservation.copy_id:
            copy = session.get(BookCopy, reservation.copy_id)
            if copy is not None and copy.status == BookCopyStatus.RESERVED:
                copy.status = BookCopyStatus.AVAILABLE
                copy.status_changed_at = now
                from app.services.book_service import recalculate_availability

                recalculate_availability(session, copy.book)
        session.flush()

        member = reservation.member
        if member is not None:
            queue_notification(
                session,
                user=member,
                notification_type=NotificationType.RESERVATION_EXPIRED,
                template_name="reservation_expired",
                context={
                    "name": member.first_name,
                    "title": reservation.book.title if reservation.book else "",
                    "expired_at": now,
                },
                dedupe_key=f"reservation_expired:{reservation.id}",
            )
        log_action(
            session,
            AuditAction.RESERVATION_EXPIRED,
            entity_type="reservation",
            entity_id=reservation.id,
            summary="Reservation expired - hold released",
        )
        expired += 1

    if expired:
        session.commit()
        
        book_ids = {row.book_id for row in rows}
        for book_id in book_ids:
            copy = session.execute(
                select(BookCopy).where(
                    BookCopy.book_id == book_id, BookCopy.status == BookCopyStatus.AVAILABLE
                )
            ).first()
            if copy is not None:
                allocate_next_reservation(session, book_id)
                session.commit()
    return expired





def fulfil_reservation(session: Session, reservation_id: int, actor: User) -> Reservation:
    
    reservation = get_reservation(session, reservation_id, for_update=True)
    if reservation.status != ReservationStatus.READY:
        raise ValidationError("This reservation is not ready for pickup.")
    reservation.status = ReservationStatus.FULFILLED
    reservation.fulfilled_at = utcnow()
    reservation.active_key = None
    session.flush()
    return reservation





def list_reservations(
    session: Session, params: dict[str, Any], *, restrict_to_member: int | None = None
) -> tuple[list[Reservation], int]:
    stmt = select(Reservation).options(
        selectinload(Reservation.book).selectinload(Book.authors),
        selectinload(Reservation.member),
        selectinload(Reservation.copy),
    )
    if restrict_to_member is not None:
        stmt = stmt.where(Reservation.member_id == restrict_to_member)
    if params.get("member_id"):
        stmt = stmt.where(Reservation.member_id == params["member_id"])
    if params.get("book_id"):
        stmt = stmt.where(Reservation.book_id == params["book_id"])
    if params.get("status"):
        stmt = stmt.where(Reservation.status == params["status"])

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = session.execute(count_stmt).scalar_one()

    stmt = stmt.order_by(Reservation.reserved_at.desc())
    page = params.get("page", 1)
    page_size = params.get("page_size", 20)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    return list(session.execute(stmt).scalars().unique()), total


def reservation_queue(session: Session, book_id: int) -> list[Reservation]:
    return list(
        session.execute(
            select(Reservation)
            .where(
                Reservation.book_id == book_id,
                Reservation.status.in_([ReservationStatus.ACTIVE, ReservationStatus.READY]),
            )
            .options(selectinload(Reservation.member), selectinload(Reservation.copy))
            .order_by(Reservation.reserved_at.asc())
        ).scalars()
    )


def member_can_reserve(member: User) -> bool:
    return member.role in (UserRole.STUDENT, UserRole.FACULTY)
