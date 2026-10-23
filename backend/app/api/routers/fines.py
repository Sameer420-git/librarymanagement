

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query, status

from app.api.dependencies import CurrentUser, DbSession, StaffUser
from app.core.exceptions import PermissionDeniedError, ValidationError
from app.models.enums import FineStatus
from app.schemas.circulation import FineAdjustment, FinePaymentCreate, FinePaymentRead, FineRead
from app.schemas.common import Page
from app.services import fine_service
from app.services.fine_service import adjust_fine, get_fine, list_fines, record_payment

router = APIRouter(prefix="/fines", tags=["Fines"])


def _is_staff(current_user) -> bool:
    return current_user.role.value in ("LIBRARIAN", "SUPER_ADMIN")


@router.get("", response_model=Page[FineRead], summary="List fines")
def list_all_fines(
    session: DbSession,
    current_user: CurrentUser,
    member_id: Optional[int] = Query(default=None),
    fine_status: Optional[str] = Query(default=None, alias="status"),
    outstanding_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[FineRead]:
    status_value = None
    if fine_status:
        try:
            status_value = FineStatus(fine_status.upper())
        except ValueError:
            raise ValidationError(f"Unknown fine status '{fine_status}'.")

    if not _is_staff(current_user):
        if member_id is not None and member_id != current_user.id:
            raise PermissionDeniedError("You may only view your own fines.")
        member_id = current_user.id

    fines, total = list_fines(
        session,
        {
            "member_id": member_id,
            "status": status_value,
            "outstanding_only": outstanding_only,
            "page": page,
            "page_size": page_size,
        },
        restrict_to_member=None if _is_staff(current_user) else current_user.id,
    )
    return Page.build([FineRead(**fine_service.fine_payload(fine)) for fine in fines], page, page_size, total)


@router.get("/{fine_id}", response_model=FineRead, summary="Fine detail")
def fine_detail(fine_id: int, session: DbSession, current_user: CurrentUser) -> FineRead:
    fine = get_fine(session, fine_id)
    if not _is_staff(current_user) and fine.member_id != current_user.id:
        raise PermissionDeniedError("You may only view your own fines.")
    return FineRead(**fine_service.fine_payload(fine))


@router.post(
    "/{fine_id}/adjust",
    response_model=FineRead,
    summary="Adjust or waive a fine",
)
def adjust(
    fine_id: int,
    payload: FineAdjustment,
    session: DbSession,
    current_user: StaffUser,
) -> FineRead:
    fine = adjust_fine(
        session,
        fine_id,
        current_user,
        amount=payload.amount,
        waive=payload.waive,
        reason=payload.reason,
    )
    return FineRead(**fine_service.fine_payload(fine))


@router.post(
    "/{fine_id}/payments",
    response_model=FineRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record a fine payment",
)
def pay(
    fine_id: int,
    payload: FinePaymentCreate,
    session: DbSession,
    current_user: StaffUser,
) -> FineRead:
    fine = record_payment(
        session,
        fine_id,
        current_user,
        amount=payload.amount,
        method=payload.method,
        reference=payload.reference,
        notes=payload.notes,
    )
    return FineRead(**fine_service.fine_payload(fine))
