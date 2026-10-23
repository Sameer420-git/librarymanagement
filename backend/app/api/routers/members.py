

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, File, Query, UploadFile, status
from fastapi.responses import PlainTextResponse

from app.api.dependencies import CurrentUser, DbSession, StaffUser
from app.core.exceptions import PermissionDeniedError, ValidationError
from app.models.enums import FineStatus, LoanStatus, UserRole, UserStatus
from app.schemas.circulation import FineRead, LoanRead, ReservationRead
from app.schemas.common import Page
from app.schemas.member import (
    CourseCreate,
    CourseRead,
    DepartmentCreate,
    DepartmentRead,
    MemberCreate,
    MemberImportResult,
    MemberListItem,
    MemberProfileRead,
    MemberUpdate,
)
from app.services import circulation_service, fine_service, reservation_service
from app.services.member_service import (
    create_course,
    create_department,
    create_member,
    export_members_csv,
    get_member,
    import_members_from_csv,
    list_courses,
    list_departments,
    member_list_item,
    member_profile_payload,
    preview_member_import,
    search_members,
    set_member_status,
    update_member,
)

router = APIRouter(prefix="/members", tags=["Members"])


def _is_staff(current_user) -> bool:
    return current_user.role in (UserRole.LIBRARIAN, UserRole.SUPER_ADMIN)


def _ensure_can_view(current_user, member_id: int) -> None:
    
    if current_user.id == member_id:
        return
    if not _is_staff(current_user):
        raise PermissionDeniedError("You may only access your own library record.")





@router.get("", response_model=Page[MemberListItem], summary="Search members")
def list_members(
    session: DbSession,
    current_user: StaffUser,
    search: Optional[str] = Query(default=None),
    role: Optional[str] = Query(default=None, description="STUDENT or FACULTY"),
    member_status: Optional[str] = Query(default=None, alias="status"),
    department_id: Optional[int] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[MemberListItem]:
    roles = None
    if role:
        try:
            roles = [UserRole(role.upper())]
        except ValueError:
            raise ValidationError(f"Unknown role '{role}'.")
    status_value = None
    if member_status:
        try:
            status_value = UserStatus(member_status.upper())
        except ValueError:
            raise ValidationError(f"Unknown status '{member_status}'.")

    members, total = search_members(
        session,
        {
            "search": search,
            "roles": roles,
            "status": status_value,
            "department_id": department_id,
            "page": page,
            "page_size": page_size,
        },
    )
    items = [MemberListItem(**member_list_item(session, member)) for member in members]
    return Page.build(items, page, page_size, total)


@router.post(
    "",
    response_model=MemberProfileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a member",
)
def add_member(
    payload: MemberCreate, session: DbSession, current_user: StaffUser
) -> MemberProfileRead:
    if payload.role not in (UserRole.STUDENT, UserRole.FACULTY):
        raise ValidationError("Members must be either STUDENT or FACULTY.")
    member = create_member(session, payload, actor=current_user)
    session.commit()
    return MemberProfileRead(**member_profile_payload(session, member))


@router.post(
    "/import",
    response_model=MemberImportResult,
    summary="Import members from CSV",
)
def import_members(
    session: DbSession,
    current_user: StaffUser,
    file: UploadFile = File(...),
) -> MemberImportResult:
    content = _read_csv(file)
    result = import_members_from_csv(session, content, actor=current_user)
    session.commit()
    return MemberImportResult(**result)


@router.post("/import/preview", summary="Validate a member CSV without writing anything")
def preview_members(
    session: DbSession,
    current_user: StaffUser,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    return preview_member_import(session, _read_csv(file))


@router.get("/export/csv", summary="Export members as CSV")
def export_members(
    session: DbSession,
    current_user: StaffUser,
    member_id: Optional[list[int]] = Query(default=None),
) -> PlainTextResponse:
    csv_text = export_members_csv(session, member_id)
    return PlainTextResponse(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=library_members.csv"},
    )


@router.get("/departments/all", response_model=list[DepartmentRead], summary="List departments")
def get_departments(session: DbSession, current_user: CurrentUser) -> list[DepartmentRead]:
    departments = list_departments(session)
    return [
        DepartmentRead(
            id=department.id,
            code=department.code,
            name=department.name,
            description=department.description,
            is_active=department.is_active,
            course_count=len(list_courses(session, department.id)),
        )
        for department in departments
    ]


@router.post(
    "/departments/all",
    response_model=DepartmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a department",
)
def add_department(
    payload: DepartmentCreate, session: DbSession, current_user: StaffUser
) -> DepartmentRead:
    department = create_department(session, payload)
    session.commit()
    return DepartmentRead(
        id=department.id,
        code=department.code,
        name=department.name,
        description=department.description,
        is_active=department.is_active,
        course_count=0,
    )


@router.get("/courses/all", response_model=list[CourseRead], summary="List courses")
def get_courses(
    session: DbSession,
    current_user: CurrentUser,
    department_id: Optional[int] = Query(default=None),
) -> list[CourseRead]:
    from app.models.member import Department

    courses = list_courses(session, department_id)
    items = []
    for course in courses:
        department = session.get(Department, course.department_id) if course.department_id else None
        items.append(
            CourseRead(
                id=course.id,
                code=course.code,
                name=course.name,
                department_id=course.department_id,
                department_name=department.name if department else None,
                duration_semesters=course.duration_semesters,
                is_active=course.is_active,
            )
        )
    return items


@router.post(
    "/courses/all",
    response_model=CourseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a course",
)
def add_course(
    payload: CourseCreate, session: DbSession, current_user: StaffUser
) -> CourseRead:
    course = create_course(session, payload)
    session.commit()
    return CourseRead(
        id=course.id,
        code=course.code,
        name=course.name,
        department_id=course.department_id,
        department_name=None,
        duration_semesters=course.duration_semesters,
        is_active=course.is_active,
    )





@router.get(
    "/{member_id}",
    response_model=MemberProfileRead,
    summary="Member profile with borrowing statistics",
)
def get_member_profile(
    member_id: int, session: DbSession, current_user: CurrentUser
) -> MemberProfileRead:
    _ensure_can_view(current_user, member_id)
    member = get_member(session, member_id)
    return MemberProfileRead(**member_profile_payload(session, member))


@router.put("/{member_id}", response_model=MemberProfileRead, summary="Update a member")
def edit_member(
    member_id: int, payload: MemberUpdate, session: DbSession, current_user: StaffUser
) -> MemberProfileRead:
    member = update_member(session, member_id, payload, actor=current_user)
    session.commit()
    return MemberProfileRead(**member_profile_payload(session, member))


@router.patch(
    "/{member_id}/status",
    response_model=MemberProfileRead,
    summary="Activate or deactivate a member",
)
def change_member_status(
    member_id: int,
    session: DbSession,
    current_user: StaffUser,
    status_value: UserStatus = Query(alias="status"),
) -> MemberProfileRead:
    member = set_member_status(session, member_id, status_value, actor=current_user)
    session.commit()
    return MemberProfileRead(**member_profile_payload(session, member))


@router.get(
    "/{member_id}/loans",
    response_model=Page[LoanRead],
    summary="Loans of a member",
)
def member_loans(
    member_id: int,
    session: DbSession,
    current_user: CurrentUser,
    loan_status: Optional[str] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[LoanRead]:
    _ensure_can_view(current_user, member_id)
    status_value = None
    if loan_status:
        try:
            status_value = LoanStatus(loan_status.upper())
        except ValueError:
            raise ValidationError(f"Unknown loan status '{loan_status}'.")

    loans, total = circulation_service.list_loans(
        session,
        {"member_id": member_id, "status": status_value, "page": page, "page_size": page_size},
        restrict_to_member=None if _is_staff(current_user) else member_id,
    )
    items = [LoanRead(**circulation_service.loan_payload(session, loan)) for loan in loans]
    return Page.build(items, page, page_size, total)


@router.get("/{member_id}/fines", response_model=Page[FineRead], summary="Fines of a member")
def member_fines(
    member_id: int,
    session: DbSession,
    current_user: CurrentUser,
    fine_status: Optional[str] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[FineRead]:
    _ensure_can_view(current_user, member_id)
    status_value = None
    if fine_status:
        try:
            status_value = FineStatus(fine_status.upper())
        except ValueError:
            raise ValidationError(f"Unknown fine status '{fine_status}'.")

    fines, total = fine_service.list_fines(
        session,
        {"member_id": member_id, "status": status_value, "page": page, "page_size": page_size},
        restrict_to_member=None if _is_staff(current_user) else member_id,
    )
    return Page.build(
        [FineRead(**fine_service.fine_payload(fine)) for fine in fines], page, page_size, total
    )


@router.get(
    "/{member_id}/reservations",
    response_model=Page[ReservationRead],
    summary="Reservations of a member",
)
def member_reservations(
    member_id: int,
    session: DbSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[ReservationRead]:
    _ensure_can_view(current_user, member_id)
    reservations, total = reservation_service.list_reservations(
        session,
        {"member_id": member_id, "page": page, "page_size": page_size},
        restrict_to_member=None if _is_staff(current_user) else member_id,
    )
    items = [
        ReservationRead(**reservation_service.reservation_payload(reservation))
        for reservation in reservations
    ]
    return Page.build(items, page, page_size, total)


def _read_csv(file: UploadFile) -> str:
    raw = file.file.read()
    if isinstance(raw, bytes):
        try:
            return raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            return raw.decode("latin-1")
    return raw
