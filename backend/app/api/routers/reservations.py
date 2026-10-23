

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query, status

from app.api.dependencies import CurrentUser, DbSession, StaffUser
from app.core.exceptions import PermissionDeniedError, ValidationError
from app.models.enums import ReservationStatus
from app.schemas.circulation import ReservationCreate, ReservationRead
from app.schemas.common import Page
from app.services import reservation_service
from app.services.reservation_service import (
    cancel_reservation,
    create_reservation,
    get_reservation,
    list_reservations,
    reservation_payload,
)

router = APIRouter(prefix="/reservations", tags=["Reservations"])


def _is_staff(current_user) -> bool:
    return current_user.role.value in ("LIBRARIAN", "SUPER_ADMIN")


@router.post(
    "",
    response_model=ReservationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Reserve a book",
)
def reserve(
    payload: ReservationCreate, session: DbSession, current_user: CurrentUser
) -> ReservationRead:
    
    member_id = current_user.id
    reservation = create_reservation(
        session,
        member_id=member_id,
        book_id=payload.book_id,
        actor=current_user,
        notes=payload.notes,
    )
    return ReservationRead(**reservation_payload(reservation))


@router.get("", response_model=Page[ReservationRead], summary="List reservations")
def list_all_reservations(
    session: DbSession,
    current_user: CurrentUser,
    member_id: Optional[int] = Query(default=None),
    book_id: Optional[int] = Query(default=None),
    reservation_status: Optional[str] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[ReservationRead]:
    status_value = None
    if reservation_status:
        try:
            status_value = ReservationStatus(reservation_status.upper())
        except ValueError:
            raise ValidationError(f"Unknown reservation status '{reservation_status}'.")

    if not _is_staff(current_user):
        if member_id is not None and member_id != current_user.id:
            raise PermissionDeniedError("You may only view your own reservations.")
        member_id = current_user.id

    reservations, total = list_reservations(
        session,
        {
            "member_id": member_id,
            "book_id": book_id,
            "status": status_value,
            "page": page,
            "page_size": page_size,
        },
    )
    items = [ReservationRead(**reservation_payload(reservation)) for reservation in reservations]
    return Page.build(items, page, page_size, total)


@router.get("/{reservation_id}", response_model=ReservationRead, summary="Reservation detail")
def reservation_detail(
    reservation_id: int, session: DbSession, current_user: CurrentUser
) -> ReservationRead:
    reservation = get_reservation(session, reservation_id)
    if not _is_staff(current_user) and reservation.member_id != current_user.id:
        raise PermissionDeniedError("You may only view your own reservations.")
    return ReservationRead(**reservation_payload(reservation))


@router.post(
    "/{reservation_id}/cancel",
    response_model=ReservationRead,
    summary="Cancel a reservation",
)
def cancel(
    reservation_id: int, session: DbSession, current_user: CurrentUser
) -> ReservationRead:
    reservation = get_reservation(session, reservation_id)
    if not _is_staff(current_user) and reservation.member_id != current_user.id:
        raise PermissionDeniedError("You may only cancel your own reservations.")
    updated = cancel_reservation(
        session,
        reservation_id,
        current_user,
        member_id=None if _is_staff(current_user) else current_user.id,
    )
    return ReservationRead(**reservation_payload(updated))
