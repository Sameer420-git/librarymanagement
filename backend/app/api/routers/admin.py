

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from app.api.dependencies import AdminUser, CurrentUser, DbSession
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.core.permissions import ROLE_PERMISSIONS, Role
from app.models.enums import AuditAction, UserRole, UserStatus
from app.models.settings import AuditLog, LibraryPolicy
from app.models.user import User
from app.schemas.common import Page
from app.services import report_service
from app.services.audit_service import log_action
from app.services.member_service import member_list_item
from app.schemas.member import MemberListItem

router = APIRouter(prefix="/admin", tags=["Administration"])





@router.get("/dashboard", summary="Administrative dashboard statistics")
def dashboard(session: DbSession, current_user: AdminUser) -> dict[str, Any]:
    stats = report_service.dashboard_stats(session)
    from sqlalchemy import func as sql_func

    from app.models.notification import Notification
    from app.models.enums import NotificationStatus

    recent_audit = list(
        session.execute(
            select(AuditLog).order_by(AuditLog.created_at.desc()).limit(10)
        ).scalars()
    )
    recent_loans = int(
        session.execute(
            select(sql_func.count(AuditLog.id)).where(
                AuditLog.action == AuditAction.LOAN_ISSUED.value
            )
        ).scalar_one()
    )
    return {
        "stats": stats,
        "recent_activity": [
            {
                "id": entry.id,
                "action": entry.action,
                "actor_email": entry.actor_email,
                "summary": entry.summary,
                "created_at": entry.created_at,
            }
            for entry in recent_audit
        ],
        "total_loan_events": recent_loans,
    }


@router.get("/me/dashboard", summary="Dashboard for the signed-in member")
def my_dashboard(session: DbSession, current_user: CurrentUser) -> dict[str, Any]:
    if current_user.role.value in ("SUPER_ADMIN", "LIBRARIAN"):
        return report_service.dashboard_stats(session)
    return report_service.personal_dashboard(session, current_user)





@router.get("/users", response_model=Page[MemberListItem], summary="List user accounts")
def list_users(
    session: DbSession,
    current_user: AdminUser,
    search: Optional[str] = Query(default=None),
    role: Optional[str] = Query(default=None),
    user_status: Optional[str] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[MemberListItem]:
    from app.services.member_service import search_members

    roles = None
    if role:
        try:
            roles = [UserRole(role.upper())]
        except ValueError:
            raise ValidationError(f"Unknown role '{role}'.")
    status_value = None
    if user_status:
        try:
            status_value = UserStatus(user_status.upper())
        except ValueError:
            raise ValidationError(f"Unknown status '{user_status}'.")

    users, total = search_members(
        session,
        {
            "search": search,
            "roles": roles,
            "status": status_value,
            "page": page,
            "page_size": page_size,
        },
    )
    items = [MemberListItem(**member_list_item(session, user)) for user in users]
    return Page.build(items, page, page_size, total)


@router.patch("/users/{user_id}/status", summary="Activate or deactivate an account")
def change_user_status(
    user_id: int,
    session: DbSession,
    current_user: AdminUser,
    new_status: UserStatus = Query(alias="status"),
    reason: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    user = session.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    if user.id == current_user.id:
        raise ValidationError("You cannot change the status of your own account.")

    previous = user.status
    user.status = new_status
    if new_status in (UserStatus.INACTIVE, UserStatus.SUSPENDED):
        from app.services.auth_service import revoke_all_sessions

        revoke_all_sessions(session, user, reason=f"account_{new_status.value.lower()}")
    log_action(
        session,
        AuditAction.USER_STATUS_CHANGED,
        actor=current_user,
        entity_type="user",
        entity_id=user.id,
        summary=f"Status changed from {previous.value} to {new_status.value}",
        metadata={"reason": reason},
    )
    session.commit()
    return {"id": user.id, "status": user.status.value}


@router.patch("/users/{user_id}/role", summary="Change a user's role")
def change_user_role(
    user_id: int,
    session: DbSession,
    current_user: AdminUser,
    new_role: UserRole = Query(alias="role"),
) -> dict[str, Any]:
    user = session.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    if user.id == current_user.id:
        raise ValidationError("You cannot change your own role.")
    previous = user.role
    if previous == new_role:
        return {"id": user.id, "role": user.role.value}

    user.role = new_role
    if new_role == UserRole.FACULTY:
        user.membership_type = "FACULTY"
    log_action(
        session,
        AuditAction.ROLE_CHANGED,
        actor=current_user,
        entity_type="user",
        entity_id=user.id,
        summary=f"Role changed from {previous.value} to {new_role.value}",
    )
    session.commit()
    return {"id": user.id, "role": user.role.value}


@router.get("/roles", summary="Roles and their permissions")
def list_roles(current_user: AdminUser) -> list[dict[str, Any]]:
    return [
        {
            "role": role.value,
            "permissions": sorted(permission.value for permission in permissions),
        }
        for role, permissions in ROLE_PERMISSIONS.items()
    ]





@router.get("/settings", summary="Library policy settings")
def get_settings(session: DbSession, current_user: AdminUser) -> dict[str, Any]:
    policy = LibraryPolicy.get_current(session)
    session.commit()
    return _policy_payload(policy)


@router.put("/settings", summary="Update library policy settings")
def update_settings(
    payload: dict[str, Any], session: DbSession, current_user: AdminUser
) -> dict[str, Any]:
    policy = LibraryPolicy.get_current(session)
    editable = {
        "institution_name",
        "library_email",
        "library_phone",
        "library_address",
        "opening_hours",
        "max_books_student",
        "max_books_faculty",
        "max_books_staff",
        "loan_period_days_student",
        "loan_period_days_faculty",
        "max_renewals",
        "renewal_period_days",
        "max_fine_blocks_renewal",
        "max_fine_blocks_issue",
        "fine_per_day",
        "grace_period_days",
        "max_fine_per_loan",
        "currency_code",
        "reservation_pickup_days",
        "max_active_reservations",
        "reservation_expiry_hours",
        "due_reminder_days",
        "overdue_reminder_days",
        "membership_expiry_reminder_days",
        "max_overdue_reminders",
        "membership_validity_days_student",
        "membership_validity_days_faculty",
    }
    changes: dict[str, Any] = {}
    for key, value in payload.items():
        if key not in editable:
            continue
        changes[key] = value

    for key, value in changes.items():
        setattr(policy, key, value)
    policy.updated_by_id = current_user.id

    log_action(
        session,
        AuditAction.SETTINGS_UPDATED,
        actor=current_user,
        entity_type="library_policy",
        entity_id=policy.id,
        summary="Library policy updated",
        metadata={"keys": sorted(changes.keys())},
    )
    session.commit()
    return _policy_payload(policy)


def _policy_payload(policy: LibraryPolicy) -> dict[str, Any]:
    return {
        "id": policy.id,
        "institution_name": policy.institution_name,
        "library_email": policy.library_email,
        "library_phone": policy.library_phone,
        "library_address": policy.library_address,
        "opening_hours": policy.opening_hours,
        "max_books_student": policy.max_books_student,
        "max_books_faculty": policy.max_books_faculty,
        "max_books_staff": policy.max_books_staff,
        "loan_period_days_student": policy.loan_period_days_student,
        "loan_period_days_faculty": policy.loan_period_days_faculty,
        "max_renewals": policy.max_renewals,
        "renewal_period_days": policy.renewal_period_days,
        "max_fine_blocks_renewal": float(policy.max_fine_blocks_renewal),
        "max_fine_blocks_issue": float(policy.max_fine_blocks_issue),
        "fine_per_day": float(policy.fine_per_day),
        "grace_period_days": policy.grace_period_days,
        "max_fine_per_loan": float(policy.max_fine_per_loan),
        "currency_code": policy.currency_code,
        "reservation_pickup_days": policy.reservation_pickup_days,
        "max_active_reservations": policy.max_active_reservations,
        "reservation_expiry_hours": policy.reservation_expiry_hours,
        "due_reminder_days": list(policy.due_reminder_days or []),
        "overdue_reminder_days": list(policy.overdue_reminder_days or []),
        "membership_expiry_reminder_days": list(policy.membership_expiry_reminder_days or []),
        "max_overdue_reminders": policy.max_overdue_reminders,
        "membership_validity_days_student": policy.membership_validity_days_student,
        "membership_validity_days_faculty": policy.membership_validity_days_faculty,
        "updated_at": policy.updated_at,
    }





@router.get("/audit-logs", response_model=Page[dict[str, Any]], summary="Audit log")
def audit_logs(
    session: DbSession,
    current_user: AdminUser,
    action: Optional[str] = Query(default=None),
    actor_id: Optional[int] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    from_date: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> Page[dict[str, Any]]:
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)

    total = session.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()
    stmt = stmt.order_by(AuditLog.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = list(session.execute(stmt).scalars())
    items = [
        {
            "id": entry.id,
            "actor_id": entry.actor_id,
            "actor_email": entry.actor_email,
            "actor_role": entry.actor_role,
            "action": entry.action,
            "entity_type": entry.entity_type,
            "entity_id": entry.entity_id,
            "summary": entry.summary,
            "metadata": entry.metadata_json,
            "ip_address": entry.ip_address,
            "user_agent": entry.user_agent,
            "created_at": entry.created_at,
        }
        for entry in rows
    ]
    return Page.build(items, page, page_size, total)
