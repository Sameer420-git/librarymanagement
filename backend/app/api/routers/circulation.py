

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, DbSession, StaffUser
from app.core.exceptions import PermissionDeniedError, ValidationError
from app.models.enums import LoanStatus
from app.schemas.circulation import (
    IssueRequest,
    LoanDetail,
    LoanRead,
    RenewRequest,
    ReturnRequest,
)
from app.schemas.common import Page
from app.services import circulation_service
from app.services.circulation_service import (
    get_loan,
    issue_book,
    list_loans,
    loan_payload,
    overdue_loans,
    renew_loan,
    return_book,
)

router = APIRouter(tags=["Circulation"])


def _is_staff(current_user) -> bool:
    return current_user.role.value in ("LIBRARIAN", "SUPER_ADMIN")


@router.post(
    "/loans/issue",
    response_model=LoanDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a physical copy to a member",
)
def issue(
    payload: IssueRequest, session: DbSession, current_user: StaffUser
) -> LoanDetail:
    loan = issue_book(
        session,
        member_id=payload.member_id,
        copy_id=payload.copy_id,
        actor=current_user,
        due_at=payload.due_at,
        notes=payload.notes,
    )
    return LoanDetail(**loan_payload(session, loan))


@router.post("/loans/{loan_id}/return", response_model=LoanDetail, summary="Process a return")
def process_return(
    loan_id: int,
    session: DbSession,
    current_user: StaffUser,
    payload: ReturnRequest | None = None,
) -> LoanDetail:
    notes = payload.notes if payload else None
    condition = payload.copy_condition if payload else None
    loan, _fine, _reservation = return_book(
        session, loan_id, current_user, notes=notes, copy_condition=condition
    )
    return LoanDetail(**loan_payload(session, loan))


@router.post("/loans/{loan_id}/renew", response_model=LoanDetail, summary="Renew a loan")
def renew(
    loan_id: int,
    session: DbSession,
    current_user: CurrentUser,
    payload: RenewRequest | None = None,
) -> LoanDetail:
    
    existing = get_loan(session, loan_id)
    if not _is_staff(current_user) and existing.member_id != current_user.id:
        raise PermissionDeniedError("You may only renew your own loans.")
    loan = renew_loan(session, loan_id, current_user, notes=payload.notes if payload else None)
    return LoanDetail(**loan_payload(session, loan))


@router.get("/loans", response_model=Page[LoanRead], summary="List loans")
def list_all_loans(
    session: DbSession,
    current_user: CurrentUser,
    member_id: Optional[int] = Query(default=None),
    book_id: Optional[int] = Query(default=None),
    copy_id: Optional[int] = Query(default=None),
    loan_status: Optional[str] = Query(default=None, alias="status"),
    search: Optional[str] = Query(default=None),
    sort_by: str = Query(default="issued_at"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[LoanRead]:
    
    status_value = None
    if loan_status:
        try:
            status_value = LoanStatus(loan_status.upper())
        except ValueError:
            raise ValidationError(f"Unknown loan status '{loan_status}'.")

    if not _is_staff(current_user):
        if member_id is not None and member_id != current_user.id:
            raise PermissionDeniedError("You may only view your own loans.")
        member_id = current_user.id

    loans, total = list_loans(
        session,
        {
            "member_id": member_id,
            "book_id": book_id,
            "copy_id": copy_id,
            "status": status_value,
            "search": search,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "page": page,
            "page_size": page_size,
        },
    )
    items = [LoanRead(**loan_payload(session, loan)) for loan in loans]
    return Page.build(items, page, page_size, total)


@router.get("/loans/overdue", response_model=Page[LoanRead], summary="Overdue loans")
def list_overdue(
    session: DbSession,
    current_user: CurrentUser,
    member_id: Optional[int] = Query(default=None),
    book_id: Optional[int] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[LoanRead]:
    if not _is_staff(current_user):
        member_id = current_user.id
    loans, total = overdue_loans(
        session,
        {"member_id": member_id, "book_id": book_id, "page": page, "page_size": page_size},
    )
    items = [LoanRead(**loan_payload(session, loan)) for loan in loans]
    return Page.build(items, page, page_size, total)


@router.get("/loans/{loan_id}", response_model=LoanDetail, summary="Loan detail")
def loan_detail(loan_id: int, session: DbSession, current_user: CurrentUser) -> LoanDetail:
    loan = get_loan(session, loan_id)
    if not _is_staff(current_user) and loan.member_id != current_user.id:
        raise PermissionDeniedError("You may only view your own loans.")
    payload = loan_payload(session, loan)
    renewals = [
        {
            "id": renewal.id,
            "loan_id": renewal.loan_id,
            "previous_due_at": renewal.previous_due_at,
            "new_due_at": renewal.new_due_at,
            "renewal_number": renewal.renewal_number,
            "renewed_at": renewal.renewed_at,
            "note": renewal.note,
            "renewed_by_name": None,
        }
        for renewal in loan.renewals
    ]
    payload["renewals"] = renewals
    return LoanDetail(**payload)
