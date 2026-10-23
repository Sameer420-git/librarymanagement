

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Iterable, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.models.catalogue import BookCopy
from app.models.circulation import Fine, Loan, Reservation
from app.models.enums import (
    AuditAction,
    FineStatus,
    LoanStatus,
    MembershipType,
    ReservationStatus,
    UserRole,
    UserStatus,
)
from app.models.member import Course, Department, FacultyProfile, StudentProfile
from app.models.user import User
from app.schemas.member import CourseCreate, DepartmentCreate, MemberCreate, MemberUpdate
from app.services.audit_service import log_action
from app.services.policy_service import (
    get_policy,
    loan_period_for,
    max_books_for,
    membership_validity_for,
)





def get_member(session: Session, member_id: int) -> User:
    member = session.execute(
        select(User)
        .where(User.id == member_id)
        .options(
            selectinload(User.student_profile).selectinload(StudentProfile.course),
            selectinload(User.faculty_profile).selectinload(FacultyProfile.department),
        )
    ).scalar_one_or_none()
    if member is None:
        raise NotFoundError("Member not found.")
    return member


def member_eligibility(session: Session, member: User) -> tuple[bool, str | None, int]:
    
    policy = get_policy(session)
    limit = max_books_for(policy, member.role)

    if member.status != UserStatus.ACTIVE:
        return False, "The account is not active.", limit
    if not member.is_email_verified:
        return False, "The e-mail address has not been verified.", limit
    if member.membership_expires is not None:
        expires = member.membership_expires
        if isinstance(expires, datetime):
            expires = expires.date()
        if expires < datetime.now(timezone.utc).date():
            return False, "The library membership has expired.", limit

    outstanding = session.execute(
        select(func.coalesce(func.sum(Fine.amount - Fine.amount_paid), 0)).where(
            Fine.member_id == member.id,
            Fine.status.in_([FineStatus.PENDING, FineStatus.PARTIALLY_PAID]),
        )
    ).scalar_one()
    if Decimal(str(outstanding)) > policy.max_fine_blocks_issue:
        return (
            False,
            f"Outstanding fines of {policy.currency_code} {Decimal(str(outstanding)):.2f} "
            "exceed the borrowing limit.",
            limit,
        )

    active_loans = session.execute(
        select(func.count(Loan.id)).where(
            Loan.member_id == member.id,
            Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
        )
    ).scalar_one()
    if active_loans >= limit:
        return False, f"The borrowing limit of {limit} book(s) has been reached.", limit

    return True, None, limit





def create_member(
    session: Session, payload: MemberCreate, actor: User | None = None
) -> User:
    email = payload.email.lower()
    if session.execute(select(User.id).where(User.email == email)).first():
        raise ConflictError("An account with this e-mail address already exists.")
    if payload.institutional_id:
        if session.execute(
            select(User.id).where(User.institutional_id == payload.institutional_id)
        ).first():
            raise ConflictError("An account with this institutional ID already exists.")
    if payload.role == UserRole.STUDENT and payload.enrollment_number:
        if session.execute(
            select(StudentProfile.id).where(
                StudentProfile.enrollment_number == payload.enrollment_number
            )
        ).first():
            raise ConflictError("This enrollment number is already registered.")

    policy = get_policy(session)
    membership_type = payload.membership_type or (
        MembershipType.FACULTY if payload.role == UserRole.FACULTY else MembershipType.STUDENT
    )
    membership_start = payload.membership_start or datetime.now(timezone.utc).date()
    membership_expires = payload.membership_expires
    if membership_expires is None:
        membership_expires = membership_start + timedelta(
            days=membership_validity_for(policy, membership_type)
        )

    user = User(
        email=email,
        institutional_id=payload.institutional_id,
        password_hash=hash_password(payload.password or _temporary_password()),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        phone=payload.phone,
        role=payload.role,
        status=payload.status,
        membership_type=membership_type,
        membership_start=membership_start,
        membership_expires=membership_expires,
        is_email_verified=bool(payload.password),
        avatar_url=payload.avatar_url,
        notes=payload.notes,
        created_by_id=actor.id if actor else None,
    )
    session.add(user)
    session.flush()

    if payload.role == UserRole.FACULTY:
        profile = FacultyProfile(
            user_id=user.id,
            employee_id=payload.employee_id,
            department_id=payload.department_id,
            designation=payload.designation,
            office_location=payload.office_location,
            office_phone=payload.office_phone,
            specialization=payload.specialization,
        )
    else:
        course_id = payload.course_id
        if course_id is None and payload.course_code:
            course = session.execute(
                select(Course).where(Course.code == payload.course_code)
            ).scalar_one_or_none()
            course_id = course.id if course else None
        profile = StudentProfile(
            user_id=user.id,
            enrollment_number=payload.enrollment_number,
            course_id=course_id,
            semester=payload.semester,
            section=payload.section,
            academic_year=payload.academic_year,
            guardian_name=payload.guardian_name,
            guardian_phone=payload.guardian_phone,
            address=payload.address,
        )
    session.add(profile)
    session.flush()

    log_action(
        session,
        AuditAction.MEMBER_CREATED,
        actor=actor,
        entity_type="user",
        entity_id=user.id,
        summary=f"Created member {user.full_name} ({user.email})",
    )
    session.flush()
    return get_member(session, user.id)


def _temporary_password() -> str:
    
    import secrets

    return secrets.token_urlsafe(16)


def update_member(
    session: Session, member_id: int, payload: MemberUpdate, actor: User | None = None
) -> User:
    member = get_member(session, member_id)
    data = payload.model_dump(exclude_unset=True)

    if "email" in data and data["email"]:
        email = data["email"].lower()
        clash = session.execute(
            select(User.id).where(User.email == email, User.id != member.id)
        ).first()
        if clash:
            raise ConflictError("An account with this e-mail address already exists.")
        data["email"] = email
    if "institutional_id" in data and data["institutional_id"]:
        clash = session.execute(
            select(User.id).where(
                User.institutional_id == data["institutional_id"], User.id != member.id
            )
        ).first()
        if clash:
            raise ConflictError("An account with this institutional ID already exists.")

    profile_fields = {
        "enrollment_number",
        "course_id",
        "semester",
        "section",
        "academic_year",
        "guardian_name",
        "guardian_phone",
        "address",
        "employee_id",
        "department_id",
        "designation",
        "office_location",
        "office_phone",
        "specialization",
    }
    user_data = {k: v for k, v in data.items() if k not in profile_fields}
    for key, value in user_data.items():
        if hasattr(member, key):
            setattr(member, key, value)

    profile_data = {k: v for k, v in data.items() if k in profile_fields}
    if profile_data:
        if member.student_profile is not None:
            for key, value in profile_data.items():
                if hasattr(member.student_profile, key):
                    setattr(member.student_profile, key, value)
        if member.faculty_profile is not None:
            for key, value in profile_data.items():
                if hasattr(member.faculty_profile, key):
                    setattr(member.faculty_profile, key, value)

    log_action(
        session,
        AuditAction.MEMBER_UPDATED,
        actor=actor,
        entity_type="user",
        entity_id=member.id,
        summary=f"Updated member {member.full_name}",
    )
    session.flush()
    return get_member(session, member.id)


def set_member_status(
    session: Session, member_id: int, status: UserStatus, actor: User | None = None
) -> User:
    member = get_member(session, member_id)
    if actor is not None and member.id == actor.id:
        raise ValidationError("You cannot change the status of your own account.")
    previous = member.status
    member.status = status
    log_action(
        session,
        AuditAction.USER_STATUS_CHANGED,
        actor=actor,
        entity_type="user",
        entity_id=member.id,
        summary=f"Status changed from {previous.value} to {status.value}",
    )
    session.flush()
    return member


def search_members(session: Session, params: dict[str, Any]) -> tuple[list[User], int]:
    stmt = select(User).options(
        selectinload(User.student_profile).selectinload(StudentProfile.course),
        selectinload(User.faculty_profile).selectinload(FacultyProfile.department),
    )
    roles = params.get("roles")
    if roles:
        stmt = stmt.where(User.role.in_(roles))
    if params.get("status"):
        stmt = stmt.where(User.status == params["status"])
    if params.get("department_id"):
        stmt = stmt.where(
            or_(
                User.faculty_profile.has(FacultyProfile.department_id == params["department_id"]),
                User.student_profile.has(
                    StudentProfile.course.has(Course.department_id == params["department_id"])
                ),
            )
        )
    search = (params.get("search") or "").strip()
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                User.first_name.like(pattern),
                User.last_name.like(pattern),
                User.email.like(pattern),
                User.institutional_id.like(pattern),
                User.student_profile.has(StudentProfile.enrollment_number.like(pattern)),
                User.faculty_profile.has(FacultyProfile.employee_id.like(pattern)),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = session.execute(count_stmt).scalar_one()
    page = params.get("page", 1)
    page_size = params.get("page_size", 20)
    stmt = stmt.order_by(User.first_name.asc(), User.last_name.asc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    return list(session.execute(stmt).scalars().unique()), total





def member_profile_payload(session: Session, member: User) -> dict[str, Any]:
    eligible, reason, limit = member_eligibility(session, member)

    active_loans = session.execute(
        select(func.count(Loan.id)).where(
            Loan.member_id == member.id,
            Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]),
        )
    ).scalar_one()
    overdue_loans = session.execute(
        select(func.count(Loan.id)).where(
            Loan.member_id == member.id, Loan.status == LoanStatus.OVERDUE
        )
    ).scalar_one()
    active_reservations = session.execute(
        select(func.count(Reservation.id)).where(
            Reservation.member_id == member.id,
            Reservation.status.in_([ReservationStatus.ACTIVE, ReservationStatus.READY]),
        )
    ).scalar_one()
    outstanding = session.execute(
        select(func.coalesce(func.sum(Fine.amount - Fine.amount_paid), 0)).where(
            Fine.member_id == member.id,
            Fine.status.in_([FineStatus.PENDING, FineStatus.PARTIALLY_PAID]),
        )
    ).scalar_one()

    department_name = None
    course_name = None
    enrollment_number = None
    employee_id = None
    designation = None
    semester = section = academic_year = None
    department_id = course_id = None
    office_location = None
    guardian_name = guardian_phone = address = None

    if member.student_profile is not None:
        profile = member.student_profile
        enrollment_number = profile.enrollment_number
        semester = profile.semester
        section = profile.section
        academic_year = profile.academic_year
        guardian_name = profile.guardian_name
        guardian_phone = profile.guardian_phone
        address = profile.address
        course_id = profile.course_id
        if profile.course is not None:
            course_name = profile.course.name
            if profile.course.department is not None:
                department_name = profile.course.department.name
                department_id = profile.course.department.id
    if member.faculty_profile is not None:
        profile = member.faculty_profile
        employee_id = profile.employee_id
        designation = profile.designation
        office_location = profile.office_location
        department_id = profile.department_id
        if profile.department is not None:
            department_name = profile.department.name

    return {
        "id": member.id,
        "email": member.email,
        "institutional_id": member.institutional_id,
        "first_name": member.first_name,
        "last_name": member.last_name,
        "full_name": member.full_name,
        "phone": member.phone,
        "role": member.role.value,
        "status": member.status.value,
        "membership_type": member.membership_type.value,
        "membership_start": member.membership_start,
        "membership_expires": member.membership_expires,
        "is_email_verified": member.is_email_verified,
        "last_login_at": member.last_login_at,
        "created_at": member.created_at,
        "avatar_url": member.avatar_url,
        "notes": member.notes,
        "department_id": department_id,
        "department_name": department_name,
        "course_id": course_id,
        "course_name": course_name,
        "enrollment_number": enrollment_number,
        "semester": semester,
        "section": section,
        "academic_year": academic_year,
        "employee_id": employee_id,
        "designation": designation,
        "office_location": office_location,
        "guardian_name": guardian_name,
        "guardian_phone": guardian_phone,
        "address": address,
        "active_loans": int(active_loans),
        "overdue_loans": int(overdue_loans),
        "active_reservations": int(active_reservations),
        "outstanding_fines": float(Decimal(str(outstanding))),
        "borrow_limit": limit,
        "eligible_to_borrow": eligible,
        "ineligibility_reason": reason,
    }


def member_list_item(session: Session, member: User) -> dict[str, Any]:
    profile = member_profile_payload(session, member)
    return {
        "id": profile["id"],
        "email": profile["email"],
        "institutional_id": profile["institutional_id"],
        "full_name": profile["full_name"],
        "role": profile["role"],
        "status": profile["status"],
        "membership_type": profile["membership_type"],
        "membership_expires": profile["membership_expires"],
        "department_name": profile["department_name"],
        "course_name": profile["course_name"],
        "enrollment_number": profile["enrollment_number"],
        "employee_id": profile["employee_id"],
        "active_loans": profile["active_loans"],
        "outstanding_fines": profile["outstanding_fines"],
    }





def create_department(session: Session, payload: DepartmentCreate) -> Department:
    if session.execute(
        select(Department.id).where(Department.code == payload.code)
    ).first():
        raise ConflictError("A department with this code already exists.")
    department = Department(code=payload.code, name=payload.name, description=payload.description)
    session.add(department)
    session.flush()
    return department


def create_course(session: Session, payload: CourseCreate) -> Course:
    if session.execute(select(Course.id).where(Course.code == payload.code)).first():
        raise ConflictError("A course with this code already exists.")
    course = Course(
        code=payload.code,
        name=payload.name,
        department_id=payload.department_id,
        duration_semesters=payload.duration_semesters,
    )
    session.add(course)
    session.flush()
    return course


def list_departments(session: Session) -> list[Department]:
    return list(session.execute(select(Department).order_by(Department.name)).scalars())


def list_courses(session: Session, department_id: int | None = None) -> list[Course]:
    stmt = select(Course).order_by(Course.name)
    if department_id:
        stmt = stmt.where(Course.department_id == department_id)
    return list(session.execute(stmt).scalars())





MEMBER_IMPORT_COLUMNS = [
    "email",
    "first_name",
    "last_name",
    "institutional_id",
    "role",
    "phone",
    "enrollment_number",
    "course_code",
    "semester",
    "section",
    "employee_id",
    "department_code",
    "designation",
    "membership_expires",
]


def preview_member_import(session: Session, content: str) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(content))
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(reader, start=2):
        errors: list[str] = []
        data = {k: (v or "").strip() for k, v in raw.items()}
        email = data.get("email", "").lower()
        if not email:
            errors.append("E-mail is required.")
        elif "@" not in email:
            errors.append("E-mail is not valid.")
        else:
            exists = session.execute(select(User.id).where(User.email == email)).first()
            if exists:
                errors.append("E-mail already exists.")
        if not data.get("first_name") or not data.get("last_name"):
            errors.append("First and last name are required.")
        role = (data.get("role") or "STUDENT").upper()
        if role not in ("STUDENT", "FACULTY"):
            errors.append("Role must be STUDENT or FACULTY.")
        rows.append(
            {
                "row_number": index,
                "data": data,
                "errors": errors,
                "duplicate": bool(errors and "already exists" in " ".join(errors)),
            }
        )
    return {
        "total_rows": len(rows),
        "valid_rows": sum(1 for r in rows if not r["errors"]),
        "rows": rows,
    }


def import_members_from_csv(
    session: Session, content: str, actor: User | None = None
) -> dict[str, Any]:
    preview = preview_member_import(session, content)
    created = 0
    updated = 0
    skipped = 0
    failed = 0
    errors: list[dict[str, Any]] = []
    created_ids: list[int] = []

    reader = csv.DictReader(io.StringIO(content))
    for index, raw in enumerate(reader, start=2):
        row = next((r for r in preview["rows"] if r["row_number"] == index), None)
        if row is None:
            continue
        if row["errors"]:
            failed += 1
            errors.append({"row_number": index, "errors": row["errors"]})
            continue
        data = row["data"]
        role = UserRole((data.get("role") or "STUDENT").upper())
        membership_type = (
            MembershipType.FACULTY if role == UserRole.FACULTY else MembershipType.STUDENT
        )

        department_id = None
        if data.get("department_code"):
            dept = session.execute(
                select(Department).where(Department.code == data["department_code"])
            ).scalar_one_or_none()
            if dept is None:
                failed += 1
                errors.append(
                    {
                        "row_number": index,
                        "errors": [f"Unknown department code '{data['department_code']}'."],
                    }
                )
                continue
            department_id = dept.id

        course_id = None
        if data.get("course_code"):
            course = session.execute(
                select(Course).where(Course.code == data["course_code"])
            ).scalar_one_or_none()
            if course is None:
                failed += 1
                errors.append(
                    {
                        "row_number": index,
                        "errors": [f"Unknown course code '{data['course_code']}'."],
                    }
                )
                continue
            course_id = course.id

        membership_expires = None
        if data.get("membership_expires"):
            try:
                membership_expires = datetime.strptime(
                    data["membership_expires"], "%Y-%m-%d"
                ).date()
            except ValueError:
                failed += 1
                errors.append(
                    {"row_number": index, "errors": ["membership_expires must be YYYY-MM-DD."]}
                )
                continue

        payload = MemberCreate(
            email=data["email"].lower(),
            first_name=data["first_name"],
            last_name=data["last_name"],
            institutional_id=data.get("institutional_id") or None,
            phone=data.get("phone") or None,
            role=role,
            membership_type=membership_type,
            membership_expires=membership_expires,
            enrollment_number=data.get("enrollment_number") or None,
            course_id=course_id,
            semester=int(data["semester"]) if data.get("semester") else None,
            section=data.get("section") or None,
            employee_id=data.get("employee_id") or None,
            department_id=department_id,
            designation=data.get("designation") or None,
        )
        try:
            member = create_member(session, payload, actor=actor)
            created += 1
            created_ids.append(member.id)
        except (ConflictError, ValidationError) as exc:
            failed += 1
            errors.append({"row_number": index, "errors": [exc.message]})

    log_action(
        session,
        AuditAction.CSV_IMPORT,
        actor=actor,
        entity_type="user",
        summary=f"Imported members from CSV: {created} created, {failed} failed",
        metadata={"created": created, "failed": failed},
    )
    session.flush()
    return {
        "total_rows": preview["total_rows"],
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
        "created_ids": created_ids,
    }


def export_members_csv(session: Session, member_ids: Iterable[int] | None = None) -> str:
    stmt = select(User).options(
        selectinload(User.student_profile).selectinload(StudentProfile.course),
        selectinload(User.faculty_profile).selectinload(FacultyProfile.department),
    )
    if member_ids:
        stmt = stmt.where(User.id.in_(list(member_ids)))
    members = list(session.execute(stmt.order_by(User.id)).scalars().unique())

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "email",
            "first_name",
            "last_name",
            "institutional_id",
            "role",
            "status",
            "membership_type",
            "department",
            "course",
            "enrollment_number",
            "employee_id",
        ]
    )
    for member in members:
        profile = member_profile_payload(session, member)
        writer.writerow(
            [
                member.id,
                member.email,
                member.first_name,
                member.last_name,
                member.institutional_id or "",
                member.role.value,
                member.status.value,
                member.membership_type.value,
                profile["department_name"] or "",
                profile["course_name"] or "",
                profile["enrollment_number"] or "",
                profile["employee_id"] or "",
            ]
        )
    return buffer.getvalue()
