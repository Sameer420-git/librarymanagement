

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Integer, case, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.catalogue import Author, Book, BookAuthor, BookCopy, Category, Publisher
from app.models.circulation import Fine, FinePayment, Loan, LoanRenewal, Reservation
from app.models.enums import (
    BookCopyStatus,
    FineStatus,
    LoanStatus,
    NotificationStatus,
    ReservationStatus,
    UserStatus,
)
from app.models.member import Course, Department, FacultyProfile, StudentProfile
from app.models.notification import Notification
from app.models.user import User
from app.utils.helpers import money, utcnow


def _period_key(moment: datetime, granularity: str) -> str:
    if granularity == "day":
        return moment.strftime("%Y-%m-%d")
    if granularity == "week":
        year, week, _ = moment.isocalendar()
        return f"{year}-W{week:02d}"
    if granularity == "year":
        return str(moment.year)
    return moment.strftime("%Y-%m")


def _range(params: dict[str, Any]) -> tuple[Optional[datetime], Optional[datetime]]:
    from_date = params.get("from_date")
    to_date = params.get("to_date")
    if from_date is not None and from_date.tzinfo is None:
        from_date = from_date.replace(tzinfo=None)
    if to_date is not None and to_date.tzinfo is not None:
        to_date = to_date.replace(tzinfo=None)
    return from_date, to_date





def inventory_report(session: Session, params: dict[str, Any]) -> dict[str, Any]:
    
    stmt = (
        select(
            Category.name.label("category_name"),
            Publisher.name.label("publisher_name"),
            func.count(func.distinct(Book.id)).label("total_titles"),
            func.count(BookCopy.id).label("total_copies"),
            func.sum(case((BookCopy.status == BookCopyStatus.AVAILABLE, 1), else_=0)).label(
                "available_copies"
            ),
            func.sum(case((BookCopy.status == BookCopyStatus.ISSUED, 1), else_=0)).label(
                "issued_copies"
            ),
            func.sum(case((BookCopy.status == BookCopyStatus.RESERVED, 1), else_=0)).label(
                "reserved_copies"
            ),
            func.sum(case((BookCopy.status == BookCopyStatus.LOST, 1), else_=0)).label("lost_copies"),
            func.sum(case((BookCopy.status == BookCopyStatus.DAMAGED, 1), else_=0)).label(
                "damaged_copies"
            ),
            func.sum(case((BookCopy.status == BookCopyStatus.RETIRED, 1), else_=0)).label(
                "retired_copies"
            ),
        )
        .select_from(BookCopy)
        .join(Book, Book.id == BookCopy.book_id)
        .outerjoin(Category, Category.id == Book.category_id)
        .outerjoin(Publisher, Publisher.id == Book.publisher_id)
        .group_by(Category.name, Publisher.name)
        .order_by(Category.name.asc().nulls_last(), Publisher.name.asc().nulls_last())
    )

    rows = []
    for row in session.execute(stmt).all():
        rows.append(
            {
                "category_name": row.category_name,
                "publisher_name": row.publisher_name,
                "total_titles": int(row.total_titles or 0),
                "total_copies": int(row.total_copies or 0),
                "available_copies": int(row.available_copies or 0),
                "issued_copies": int(row.issued_copies or 0),
                "reserved_copies": int(row.reserved_copies or 0),
                "lost_copies": int(row.lost_copies or 0),
                "damaged_copies": int(row.damaged_copies or 0),
                "retired_copies": int(row.retired_copies or 0),
            }
        )

    totals = session.execute(
        select(
            func.count(func.distinct(Book.id)),
            func.count(BookCopy.id),
            func.sum(case((BookCopy.status == BookCopyStatus.AVAILABLE, 1), else_=0)),
            func.sum(case((BookCopy.status == BookCopyStatus.ISSUED, 1), else_=0)),
            func.sum(case((BookCopy.status == BookCopyStatus.RESERVED, 1), else_=0)),
            func.sum(case((BookCopy.status == BookCopyStatus.LOST, 1), else_=0)),
            func.sum(case((BookCopy.status == BookCopyStatus.DAMAGED, 1), else_=0)),
            func.sum(case((BookCopy.status == BookCopyStatus.RETIRED, 1), else_=0)),
        ).select_from(BookCopy).join(Book, Book.id == BookCopy.book_id)
    ).one()

    return {
        "rows": rows,
        "totals": {
            "total_titles": int(totals[0] or 0),
            "total_copies": int(totals[1] or 0),
            "available_copies": int(totals[2] or 0),
            "issued_copies": int(totals[3] or 0),
            "reserved_copies": int(totals[4] or 0),
            "lost_copies": int(totals[5] or 0),
            "damaged_copies": int(totals[6] or 0),
            "retired_copies": int(totals[7] or 0),
        },
    }





def circulation_report(session: Session, params: dict[str, Any]) -> dict[str, Any]:
    
    from_date, to_date = _range(params)
    granularity = params.get("granularity", "month")

    issued_stmt = select(Loan.issued_at, Loan.status).where(Loan.issued_at.isnot(None))
    returned_stmt = select(Loan.returned_at, Loan.status).where(Loan.returned_at.isnot(None))
    if from_date:
        issued_stmt = issued_stmt.where(Loan.issued_at >= from_date)
        returned_stmt = returned_stmt.where(Loan.returned_at >= from_date)
    if to_date:
        issued_stmt = issued_stmt.where(Loan.issued_at <= to_date)
        returned_stmt = returned_stmt.where(Loan.returned_at <= to_date)

    issued: dict[str, int] = {}
    for issued_at, _ in session.execute(issued_stmt).all():
        key = _period_key(issued_at, granularity)
        issued[key] = issued.get(key, 0) + 1

    returned: dict[str, int] = {}
    for returned_at, _ in session.execute(returned_stmt).all():
        key = _period_key(returned_at, granularity)
        returned[key] = returned.get(key, 0) + 1

    renewed_stmt = select(LoanRenewal.renewed_at).where(LoanRenewal.id.isnot(None))
    if from_date:
        renewed_stmt = renewed_stmt.where(LoanRenewal.renewed_at >= from_date)
    if to_date:
        renewed_stmt = renewed_stmt.where(LoanRenewal.renewed_at <= to_date)

    renewed: dict[str, int] = {}
    for (renewed_at,) in session.execute(renewed_stmt).all():
        key = _period_key(renewed_at, granularity)
        renewed[key] = renewed.get(key, 0) + 1

    overdue_stmt = select(func.count(Loan.id)).where(
        Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
        Loan.due_at < utcnow(),
    )
    overdue_total = int(session.execute(overdue_stmt).scalar_one() or 0)

    keys = sorted(set(issued) | set(returned) | set(renewed))
    rows = [
        {
            "period": key,
            "issued_count": issued.get(key, 0),
            "returned_count": returned.get(key, 0),
            "renewed_count": renewed.get(key, 0),
            "overdue_count": 0,
        }
        for key in keys
    ]

    return {
        "rows": rows,
        "totals": {
            "issued": sum(issued.values()),
            "returned": sum(returned.values()),
            "renewed": sum(renewed.values()),
            "overdue": overdue_total,
        },
    }


def returns_in_range(session: Session, params: dict[str, Any]) -> list[dict[str, Any]]:
    from_date, to_date = _range(params)
    stmt = (
        select(Loan)
        .options(
            selectinload(Loan.copy).selectinload(BookCopy.book),
            selectinload(Loan.member),
        )
        .where(Loan.returned_at.isnot(None))
    )
    if from_date:
        stmt = stmt.where(Loan.returned_at >= from_date)
    if to_date:
        stmt = stmt.where(Loan.returned_at <= to_date)
    stmt = stmt.order_by(Loan.returned_at.desc())
    return [
        {
            "loan_id": loan.id,
            "book_title": loan.copy.book.title if loan.copy and loan.copy.book else "",
            "accession_number": loan.copy.accession_number if loan.copy else "",
            "member_name": loan.member.full_name if loan.member else "",
            "issued_at": loan.issued_at,
            "due_at": loan.due_at,
            "returned_at": loan.returned_at,
            "overdue_days": loan.overdue_days,
        }
        for loan in session.execute(stmt).scalars().unique()
    ]


def member_borrowing_history(session: Session, params: dict[str, Any]) -> list[dict[str, Any]]:
    member_id = params.get("member_id")
    stmt = (
        select(Loan)
        .options(
            selectinload(Loan.copy).selectinload(BookCopy.book),
            selectinload(Loan.member),
        )
        .order_by(Loan.issued_at.desc())
    )
    if member_id:
        stmt = stmt.where(Loan.member_id == member_id)
    rows = []
    for loan in session.execute(stmt).scalars().unique():
        rows.append(
            {
                "loan_id": loan.id,
                "member_id": loan.member_id,
                "member_name": loan.member.full_name if loan.member else "",
                "book_title": loan.copy.book.title if loan.copy and loan.copy.book else "",
                "accession_number": loan.copy.accession_number if loan.copy else "",
                "issued_at": loan.issued_at,
                "due_at": loan.due_at,
                "returned_at": loan.returned_at,
                "status": loan.status.value,
                "renewal_count": loan.renewal_count,
            }
        )
    return rows





def fines_report(session: Session, params: dict[str, Any]) -> dict[str, Any]:
    from_date, to_date = _range(params)

    fines_stmt = select(
        Fine.member_id,
        User.first_name,
        User.last_name,
        func.count(Fine.id).label("assessed_count"),
        func.coalesce(func.sum(Fine.amount), 0).label("assessed_total"),
        func.coalesce(func.sum(Fine.amount_paid), 0).label("paid_total"),
        func.coalesce(func.sum(Fine.amount - Fine.amount_paid), 0).label("outstanding_total"),
    ).join(User, User.id == Fine.member_id).group_by(Fine.member_id, User.first_name, User.last_name)

    if from_date:
        fines_stmt = fines_stmt.where(Fine.assessed_at >= from_date)
    if to_date:
        fines_stmt = fines_stmt.where(Fine.assessed_at <= to_date)

    rows = []
    for row in session.execute(fines_stmt).all():
        rows.append(
            {
                "member_id": row.member_id,
                "member_name": f"{row.first_name} {row.last_name}".strip(),
                "assessed_count": int(row.assessed_count or 0),
                "assessed_total": float(money(row.assessed_total)),
                "paid_total": float(money(row.paid_total)),
                "outstanding_total": float(money(row.outstanding_total)),
            }
        )
    rows.sort(key=lambda item: item["outstanding_total"], reverse=True)

    outstanding = session.execute(
        select(func.coalesce(func.sum(Fine.amount - Fine.amount_paid), 0)).where(
            Fine.status.in_([FineStatus.PENDING, FineStatus.PARTIALLY_PAID])
        )
    ).scalar_one()
    collected = session.execute(
        select(func.coalesce(func.sum(FinePayment.amount), 0))
    ).scalar_one()
    assessed = session.execute(
        select(func.coalesce(func.sum(Fine.amount), 0))
    ).scalar_one()

    return {
        "rows": rows,
        "totals": {
            "assessed": float(money(assessed)),
            "collected": float(money(collected)),
            "outstanding": float(money(outstanding)),
        },
    }





def popular_books(session: Session, params: dict[str, Any], limit: int = 10) -> list[dict[str, Any]]:
    loan_counts = dict(
        session.execute(
            select(Loan.copy_id, func.count(Loan.id))
            .group_by(Loan.copy_id)
        ).all()
    )
    copy_to_book = dict(
        session.execute(select(BookCopy.id, BookCopy.book_id)).all()
    )
    book_loans: dict[int, int] = {}
    for copy_id, count in loan_counts.items():
        book_id = copy_to_book.get(copy_id)
        if book_id:
            book_loans[book_id] = book_loans.get(book_id, 0) + int(count)

    reservation_counts = dict(
        session.execute(
            select(Reservation.book_id, func.count(Reservation.id)).group_by(Reservation.book_id)
        ).all()
    )

    books = list(
        session.execute(
            select(Book)
            .options(selectinload(Book.authors))
            .where(Book.is_active.is_(True))
        ).scalars()
        .unique()
    )
    rows = [
        {
            "book_id": book.id,
            "title": book.title,
            "authors": [author.name for author in book.authors],
            "loan_count": book_loans.get(book.id, 0),
            "reservation_count": int(reservation_counts.get(book.id, 0)),
            "total_copies": book.total_copies,
        }
        for book in books
    ]
    rows.sort(key=lambda item: (item["loan_count"], item["reservation_count"]), reverse=True)
    return rows[:limit]


def members_report(session: Session, params: dict[str, Any]) -> dict[str, Any]:
    
    rows: list[dict[str, Any]] = []
    role_rows = session.execute(
        select(
            User.role,
            func.count(User.id),
            func.coalesce(func.sum(User.is_email_verified.cast(Integer)), 0),
        ).group_by(User.role)
    ).all()
    for role, total, verified in role_rows:
        rows.append(
            {
                "role": getattr(role, "value", role),
                "total": int(total or 0),
                "email_verified": int(verified or 0),
                "active": int(
                    session.execute(
                        select(func.count(User.id)).where(
                            User.role == role,
                            User.status == UserStatus.ACTIVE,
                        )
                    ).scalar_one()
                    or 0
                ),
                "suspended": int(
                    session.execute(
                        select(func.count(User.id)).where(
                            User.role == role,
                            User.status == UserStatus.SUSPENDED,
                        )
                    ).scalar_one()
                    or 0
                ),
                "pending": int(
                    session.execute(
                        select(func.count(User.id)).where(
                            User.role == role,
                            User.status == UserStatus.PENDING,
                        )
                    ).scalar_one()
                    or 0
                ),
            }
        )

    rows.sort(key=lambda row: str(row["role"]))

    active_loans = int(
        session.execute(
            select(func.count(Loan.id)).where(
                Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE])
            )
        ).scalar_one()
        or 0
    )
    expired_memberships = int(
        session.execute(
            select(func.count(User.id)).where(
                User.membership_expires.isnot(None),
                User.membership_expires < utcnow().date(),
            )
        ).scalar_one()
        or 0
    )

    return {
        "rows": rows,
        "totals": {
            "members": sum(int(row["total"]) for row in rows),
            "active_loans": active_loans,
            "expired_memberships": expired_memberships,
        },
    }


def department_circulation(session: Session, params: dict[str, Any]) -> list[dict[str, Any]]:
    departments = list(session.execute(select(Department).order_by(Department.name)).scalars())
    rows = []
    for department in departments:
        member_ids = set(
            session.execute(
                select(FacultyProfile.user_id).where(
                    FacultyProfile.department_id == department.id
                )
            ).scalars()
        )
        member_ids.update(
            session.execute(
                select(StudentProfile.user_id)
                .join(Course, Course.id == StudentProfile.course_id)
                .where(Course.department_id == department.id)
            ).scalars()
        )
        if not member_ids:
            rows.append(
                {
                    "department_name": department.name,
                    "member_count": 0,
                    "loan_count": 0,
                    "current_loans": 0,
                    "overdue_loans": 0,
                    "fine_total": 0.0,
                }
            )
            continue

        loan_count = int(
            session.execute(
                select(func.count(Loan.id)).where(Loan.member_id.in_(member_ids))
            ).scalar_one()
        )
        current_loans = int(
            session.execute(
                select(func.count(Loan.id)).where(
                    Loan.member_id.in_(member_ids),
                    Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
                )
            ).scalar_one()
        )
        overdue_loans = int(
            session.execute(
                select(func.count(Loan.id)).where(
                    Loan.member_id.in_(member_ids),
                    Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
                    Loan.due_at < utcnow(),
                )
            ).scalar_one()
        )
        fine_total = session.execute(
            select(func.coalesce(func.sum(Fine.amount - Fine.amount_paid), 0)).where(
                Fine.member_id.in_(member_ids),
                Fine.status.in_([FineStatus.PENDING, FineStatus.PARTIALLY_PAID]),
            )
        ).scalar_one()

        rows.append(
            {
                "department_name": department.name,
                "member_count": len(member_ids),
                "loan_count": loan_count,
                "current_loans": current_loans,
                "overdue_loans": overdue_loans,
                "fine_total": float(money(fine_total)),
            }
        )
    return rows


def reservation_activity(session: Session, params: dict[str, Any]) -> list[dict[str, Any]]:
    rows = session.execute(
        select(
            Reservation.book_id,
            Book.title,
            func.count(Reservation.id).label("total"),
            func.sum(case((Reservation.status == ReservationStatus.FULFILLED, 1), else_=0)).label(
                "fulfilled"
            ),
            func.sum(case((Reservation.status == ReservationStatus.CANCELLED, 1), else_=0)).label(
                "cancelled"
            ),
            func.sum(case((Reservation.status == ReservationStatus.EXPIRED, 1), else_=0)).label(
                "expired"
            ),
        )
        .join(Book, Book.id == Reservation.book_id)
        .group_by(Reservation.book_id, Book.title)
        .order_by(func.count(Reservation.id).desc())
    ).all()
    return [
        {
            "book_id": row.book_id,
            "title": row.title,
            "created_count": int(row.total or 0),
            "fulfilled_count": int(row.fulfilled or 0),
            "cancelled_count": int(row.cancelled or 0),
            "expired_count": int(row.expired or 0),
        }
        for row in rows
    ]


def email_failures(session: Session, params: dict[str, Any]) -> list[dict[str, Any]]:
    stmt = (
        select(Notification)
        .where(Notification.status == NotificationStatus.FAILED)
        .order_by(Notification.created_at.desc())
    )
    limit = params.get("limit", 100)
    rows = []
    for notification in session.execute(stmt.limit(limit)).scalars():
        rows.append(
            {
                "notification_id": notification.id,
                "recipient_email": notification.recipient_email,
                "subject": notification.subject,
                "type": notification.type.value,
                "attempts": notification.attempts,
                "last_error": notification.last_error,
                "created_at": notification.created_at,
                "last_attempt_at": notification.last_attempt_at,
            }
        )
    return rows





def dashboard_stats(session: Session) -> dict[str, Any]:
    now = utcnow()
    today = now.date()

    def scalar(stmt) -> int:
        return int(session.execute(stmt).scalar_one() or 0)

    total_books = scalar(select(func.count(Book.id)).where(Book.is_active.is_(True)))
    total_copies = scalar(select(func.count(BookCopy.id)))
    available_copies = scalar(
        select(func.count(BookCopy.id)).where(BookCopy.status == BookCopyStatus.AVAILABLE)
    )
    issued_copies = scalar(
        select(func.count(BookCopy.id)).where(BookCopy.status == BookCopyStatus.ISSUED)
    )
    total_members = scalar(
        select(func.count(User.id)).where(User.role.in_(["STUDENT", "FACULTY"]))
    )
    active_members = scalar(
        select(func.count(User.id)).where(
            User.role.in_(["STUDENT", "FACULTY"]), User.status == "ACTIVE"
        )
    )
    active_loans = scalar(
        select(func.count(Loan.id)).where(
            Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE])
        )
    )
    overdue_loans = scalar(
        select(func.count(Loan.id)).where(
            Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
            Loan.due_at < now,
        )
    )
    due_today = scalar(
        select(func.count(Loan.id)).where(
            Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
            Loan.due_at >= now,
            Loan.due_at < now + timedelta(days=1),
        )
    )
    pending_reservations = scalar(
        select(func.count(Reservation.id)).where(
            Reservation.status.in_([ReservationStatus.ACTIVE, ReservationStatus.READY])
        )
    )
    outstanding_fines = money(
        session.execute(
            select(func.coalesce(func.sum(Fine.amount - Fine.amount_paid), 0)).where(
                Fine.status.in_([FineStatus.PENDING, FineStatus.PARTIALLY_PAID])
            )
        ).scalar_one()
    )
    fines_collected = money(
        session.execute(select(func.coalesce(func.sum(FinePayment.amount), 0))).scalar_one()
    )
    notifications_queued = scalar(
        select(func.count(Notification.id)).where(Notification.status == NotificationStatus.QUEUED)
    )
    notifications_failed = scalar(
        select(func.count(Notification.id)).where(Notification.status == NotificationStatus.FAILED)
    )
    loans_issued_today = scalar(
        select(func.count(Loan.id)).where(func.date(Loan.issued_at) == today)
    )
    returns_today = scalar(
        select(func.count(Loan.id)).where(func.date(Loan.returned_at) == today)
    )

    return {
        "total_books": total_books,
        "total_copies": total_copies,
        "available_copies": available_copies,
        "issued_copies": issued_copies,
        "total_members": total_members,
        "active_members": active_members,
        "active_loans": active_loans,
        "overdue_loans": overdue_loans,
        "due_today": due_today,
        "pending_reservations": pending_reservations,
        "outstanding_fines": float(outstanding_fines),
        "fines_collected": float(fines_collected),
        "notifications_queued": notifications_queued,
        "notifications_failed": notifications_failed,
        "loans_issued_today": loans_issued_today,
        "returns_today": returns_today,
    }


def personal_dashboard(session: Session, member: User) -> dict[str, Any]:
    
    now = utcnow()
    current = list(
        session.execute(
            select(Loan)
            .options(selectinload(Loan.copy).selectinload(BookCopy.book))
            .where(
                Loan.member_id == member.id,
                Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
            )
            .order_by(Loan.due_at.asc())
        ).scalars()
        .unique()
    )
    reservations = list(
        session.execute(
            select(Reservation)
            .options(selectinload(Reservation.book), selectinload(Reservation.copy))
            .where(
                Reservation.member_id == member.id,
                Reservation.status.in_([ReservationStatus.ACTIVE, ReservationStatus.READY]),
            )
            .order_by(Reservation.reserved_at.desc())
        )
        .scalars()
        .unique()
    )
    outstanding = money(
        session.execute(
            select(func.coalesce(func.sum(Fine.amount - Fine.amount_paid), 0)).where(
                Fine.member_id == member.id,
                Fine.status.in_([FineStatus.PENDING, FineStatus.PARTIALLY_PAID]),
            )
        ).scalar_one()
    )
    return {
        "current_loans": [
            {
                "id": loan.id,
                "copy_id": loan.copy_id,
                "member_id": loan.member_id,
                "issued_at": loan.issued_at,
                "due_at": loan.due_at,
                "returned_at": None,
                "status": loan.status.value,
                "renewal_count": loan.renewal_count,
                "overdue_days": 0,
                "notes": None,
                "book_id": loan.copy.book.id if loan.copy and loan.copy.book else None,
                "book_title": loan.copy.book.title if loan.copy and loan.copy.book else None,
                "accession_number": loan.copy.accession_number if loan.copy else None,
                "member_name": member.full_name,
                "member_email": member.email,
                "issued_by_name": None,
                "returned_by_name": None,
                "days_overdue": max(0, (now - loan.due_at).days),
                "is_overdue": loan.due_at < now,
                "fine_amount": None,
            }
            for loan in current
        ],
        "reservations": [
            {
                "id": reservation.id,
                "book_id": reservation.book_id,
                "member_id": reservation.member_id,
                "status": reservation.status.value,
                "position": reservation.position,
                "queue_position": reservation.queue_position,
                "reserved_at": reservation.reserved_at,
                "pickup_deadline": reservation.pickup_deadline,
                "book_title": reservation.book.title if reservation.book else None,
                "accession_number": reservation.copy.accession_number if reservation.copy else None,
            }
            for reservation in reservations
        ],
        "outstanding_fines": float(outstanding),
        "overdue_count": sum(1 for loan in current if loan.due_at < now),
    }
