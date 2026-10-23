

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.enums import MembershipType, UserRole
from app.models.settings import LibraryPolicy
from app.models.user import User


def get_policy(session: Session) -> LibraryPolicy:
    
    return LibraryPolicy.get_current(session)


def max_books_for(policy: LibraryPolicy, role: UserRole | str) -> int:
    role_value = role.value if isinstance(role, UserRole) else str(role)
    if role_value == UserRole.FACULTY.value:
        return policy.max_books_faculty
    if role_value in (UserRole.LIBRARIAN.value, UserRole.SUPER_ADMIN.value):
        return policy.max_books_staff
    return policy.max_books_student


def loan_period_for(policy: LibraryPolicy, role: UserRole | str) -> int:
    role_value = role.value if isinstance(role, UserRole) else str(role)
    if role_value == UserRole.FACULTY.value:
        return policy.loan_period_days_faculty
    return policy.loan_period_days_student


def membership_validity_for(policy: LibraryPolicy, membership_type: MembershipType | str) -> int:
    value = (
        membership_type.value
        if isinstance(membership_type, MembershipType)
        else str(membership_type)
    )
    if value == MembershipType.FACULTY.value:
        return policy.membership_validity_days_faculty
    return policy.membership_validity_days_student


def role_from_membership(membership_type: MembershipType | str) -> UserRole:
    value = (
        membership_type.value
        if isinstance(membership_type, MembershipType)
        else str(membership_type)
    )
    return UserRole.FACULTY if value == MembershipType.FACULTY.value else UserRole.STUDENT


def currency_code(policy: LibraryPolicy) -> str:
    return policy.currency_code or "INR"


def as_decimal(value: object) -> Decimal:
    from app.utils.helpers import money

    return money(value)
