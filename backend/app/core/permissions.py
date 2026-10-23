

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    LIBRARIAN = "LIBRARIAN"
    FACULTY = "FACULTY"
    STUDENT = "STUDENT"


class Permission(str, Enum):
    
    BOOKS_READ = "books:read"
    BOOKS_WRITE = "books:write"
    BOOKS_DELETE = "books:delete"
    COPIES_READ = "copies:read"
    COPIES_WRITE = "copies:write"

    
    MEMBERS_READ = "members:read"
    MEMBERS_WRITE = "members:write"
    MEMBERS_READ_ANY = "members:read_any"

    
    ISSUE_BOOK = "circulation:issue"
    RETURN_BOOK = "circulation:return"
    RENEW_BOOK = "circulation:renew"
    LOANS_READ_ANY = "loans:read_any"

    
    RESERVATIONS_CREATE = "reservations:create"
    RESERVATIONS_READ_ANY = "reservations:read_any"
    RESERVATIONS_MANAGE = "reservations:manage"

    
    FINES_READ_ANY = "fines:read_any"
    FINES_ADJUST = "fines:adjust"
    FINES_PAY = "fines:pay"

    
    NOTIFICATIONS_READ_ANY = "notifications:read_any"
    NOTIFICATIONS_MANAGE = "notifications:manage"

    
    REPORTS_READ = "reports:read"
    AUDIT_READ = "audit:read"
    SETTINGS_MANAGE = "settings:manage"
    USERS_MANAGE = "users:manage"
    DASHBOARD_ADMIN = "dashboard:admin"


_ALL: frozenset[Permission] = frozenset(Permission)

STUDENT_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.BOOKS_READ,
        Permission.COPIES_READ,
        Permission.RESERVATIONS_CREATE,
    }
)

FACULTY_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.BOOKS_READ,
        Permission.COPIES_READ,
        Permission.RESERVATIONS_CREATE,
    }
)

LIBRARIAN_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.BOOKS_READ,
        Permission.BOOKS_WRITE,
        Permission.BOOKS_DELETE,
        Permission.COPIES_READ,
        Permission.COPIES_WRITE,
        Permission.MEMBERS_READ,
        Permission.MEMBERS_WRITE,
        Permission.MEMBERS_READ_ANY,
        Permission.ISSUE_BOOK,
        Permission.RETURN_BOOK,
        Permission.RENEW_BOOK,
        Permission.LOANS_READ_ANY,
        Permission.RESERVATIONS_CREATE,
        Permission.RESERVATIONS_READ_ANY,
        Permission.RESERVATIONS_MANAGE,
        Permission.FINES_READ_ANY,
        Permission.FINES_ADJUST,
        Permission.FINES_PAY,
        Permission.NOTIFICATIONS_READ_ANY,
        Permission.REPORTS_READ,
        Permission.DASHBOARD_ADMIN,
    }
)

SUPER_ADMIN_PERMISSIONS: frozenset[Permission] = _ALL

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.STUDENT: STUDENT_PERMISSIONS,
    Role.FACULTY: FACULTY_PERMISSIONS,
    Role.LIBRARIAN: LIBRARIAN_PERMISSIONS,
    Role.SUPER_ADMIN: SUPER_ADMIN_PERMISSIONS,
}


ADMIN_ROLES: frozenset[Role] = frozenset({Role.SUPER_ADMIN})


STAFF_ROLES: frozenset[Role] = frozenset({Role.LIBRARIAN, Role.SUPER_ADMIN})


def permissions_for_role(role: Role | str) -> frozenset[Permission]:
    try:
        role_enum = Role(role)
    except ValueError:
        return frozenset()
    return ROLE_PERMISSIONS.get(role_enum, frozenset())


def role_has_permission(role: Role | str, permission: Permission) -> bool:
    return permission in permissions_for_role(role)
