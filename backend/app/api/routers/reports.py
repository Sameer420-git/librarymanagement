

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from app.api.dependencies import CurrentUser, DbSession, StaffUser
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


def _rows_to_csv(rows: list[dict[str, Any]], filename: str) -> PlainTextResponse:
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return PlainTextResponse(
        buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/inventory", summary="Inventory report")
def inventory(
    session: DbSession,
    current_user: StaffUser,
    export: bool = Query(default=False),
) -> Any:
    data = report_service.inventory_report(session, {})
    if export:
        return _rows_to_csv(data["rows"], "inventory_report.csv")
    return data


@router.get("/circulation", summary="Circulation report")
def circulation(
    session: DbSession,
    current_user: StaffUser,
    from_date: Optional[datetime] = Query(default=None),
    to_date: Optional[datetime] = Query(default=None),
    granularity: str = Query(default="month", pattern="^(day|week|month|year)$"),
    export: bool = Query(default=False),
) -> Any:
    data = report_service.circulation_report(
        session, {"from_date": from_date, "to_date": to_date, "granularity": granularity}
    )
    if export:
        return _rows_to_csv(data["rows"], "circulation_report.csv")
    return data


@router.get("/overdue", summary="Overdue report")
def overdue(
    session: DbSession,
    current_user: StaffUser,
    member_id: Optional[int] = Query(default=None),
    export: bool = Query(default=False),
) -> Any:
    from app.services.circulation_service import loan_payload, overdue_loans

    loans, _total = overdue_loans(session, {"member_id": member_id, "page": 1, "page_size": 1000})
    rows = []
    for loan in loans:
        payload = loan_payload(session, loan)
        rows.append(
            {
                "loan_id": payload["id"],
                "member_id": payload["member_id"],
                "member_name": payload["member_name"],
                "book_title": payload["book_title"],
                "accession_number": payload["accession_number"],
                "due_at": payload["due_at"],
                "days_overdue": payload["days_overdue"],
                "fine_amount": payload["fine_amount"] or 0,
            }
        )
    if export:
        return _rows_to_csv(rows, "overdue_report.csv")
    return {"rows": rows, "totals": {"count": len(rows)}}


@router.get("/fines", summary="Fines report")
def fines(
    session: DbSession,
    current_user: StaffUser,
    from_date: Optional[datetime] = Query(default=None),
    to_date: Optional[datetime] = Query(default=None),
    export: bool = Query(default=False),
) -> Any:
    data = report_service.fines_report(session, {"from_date": from_date, "to_date": to_date})
    if export:
        return _rows_to_csv(data["rows"], "fines_report.csv")
    return data


@router.get("/popular-books", summary="Most borrowed titles")
def popular_books(
    session: DbSession,
    current_user: StaffUser,
    limit: int = Query(default=10, ge=1, le=100),
    export: bool = Query(default=False),
) -> Any:
    rows = report_service.popular_books(session, {}, limit=limit)
    if export:
        return _rows_to_csv(rows, "popular_books.csv")
    return {"rows": rows}


@router.get("/members", summary="Member statistics by role and status")
def members(
    session: DbSession,
    current_user: StaffUser,
    export: bool = Query(default=False),
) -> Any:
    data = report_service.members_report(session, {})
    if export:
        return _rows_to_csv(data["rows"], "members_report.csv")
    return data


@router.get("/departments", summary="Department circulation report")
def departments(
    session: DbSession,
    current_user: StaffUser,
    export: bool = Query(default=False),
) -> Any:
    rows = report_service.department_circulation(session, {})
    if export:
        return _rows_to_csv(rows, "department_circulation.csv")
    return {"rows": rows}


@router.get("/reservations", summary="Reservation activity report")
def reservations(
    session: DbSession,
    current_user: StaffUser,
    export: bool = Query(default=False),
) -> Any:
    rows = report_service.reservation_activity(session, {})
    if export:
        return _rows_to_csv(rows, "reservation_activity.csv")
    return {"rows": rows}


@router.get("/returns", summary="Returns in a date range")
def returns(
    session: DbSession,
    current_user: StaffUser,
    from_date: Optional[datetime] = Query(default=None),
    to_date: Optional[datetime] = Query(default=None),
    export: bool = Query(default=False),
) -> Any:
    rows = report_service.returns_in_range(session, {"from_date": from_date, "to_date": to_date})
    if export:
        return _rows_to_csv(rows, "returns_report.csv")
    return {"rows": rows}


@router.get("/member-history", summary="Member borrowing history")
def member_history(
    session: DbSession,
    current_user: StaffUser,
    member_id: Optional[int] = Query(default=None),
    export: bool = Query(default=False),
) -> Any:
    rows = report_service.member_borrowing_history(session, {"member_id": member_id})
    if export:
        return _rows_to_csv(rows, "member_history.csv")
    return {"rows": rows}


@router.get("/email-failures", summary="Failed e-mail deliveries")
def email_failures(
    session: DbSession,
    current_user: StaffUser,
    limit: int = Query(default=100, ge=1, le=1000),
    export: bool = Query(default=False),
) -> Any:
    rows = report_service.email_failures(session, {"limit": limit})
    if export:
        return _rows_to_csv(rows, "email_failures.csv")
    return {"rows": rows}


@router.get("/lost-damaged", summary="Lost and damaged copies")
def lost_damaged(
    session: DbSession,
    current_user: StaffUser,
    export: bool = Query(default=False),
) -> Any:
    from sqlalchemy import select

    from app.models.catalogue import BookCopy
    from app.models.enums import BookCopyStatus

    copies = list(
        session.execute(
            select(BookCopy)
            .where(BookCopy.status.in_([BookCopyStatus.LOST, BookCopyStatus.DAMAGED]))
            .order_by(BookCopy.id)
        ).scalars()
    )
    rows = [
        {
            "copy_id": copy.id,
            "accession_number": copy.accession_number,
            "book_id": copy.book_id,
            "book_title": copy.book.title if copy.book else "",
            "status": copy.status.value,
            "condition": copy.condition.value,
            "price": float(copy.price) if copy.price is not None else 0,
            "status_changed_at": copy.status_changed_at,
        }
        for copy in copies
    ]
    if export:
        return _rows_to_csv(rows, "lost_damaged_report.csv")
    return {"rows": rows}
