

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.permissions import Permission, permissions_for_role
from app.core.security import decode_token
from app.db.session import get_db
from app.models.enums import UserStatus
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")

DbSession = Annotated[Session, Depends(get_db)]


def get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
    session: DbSession = None,  
) -> User:
    
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Authentication credentials were not provided.")

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Your session has expired. Please sign in again.") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid authentication token.") from exc

    subject = payload.get("sub")
    if subject is None:
        raise AuthenticationError("Invalid authentication token.")

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("Invalid authentication token.") from exc

    user = session.get(User, user_id)
    if user is None:
        raise AuthenticationError("The account associated with this token no longer exists.")
    if user.status != UserStatus.ACTIVE:
        raise PermissionDeniedError("This account is not active.")

    request.state.user = user
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: str) -> Callable[..., User]:
    

    allowed = {r.upper() for r in roles}

    def _dependency(current_user: CurrentUser) -> User:
        if current_user.role.value.upper() not in allowed:
            raise PermissionDeniedError(
                "Your role does not permit this operation."
            )
        return current_user

    return _dependency


def require_permissions(*permissions: Permission) -> Callable[..., User]:
    

    required = set(permissions)

    def _dependency(current_user: CurrentUser) -> User:
        granted = permissions_for_role(current_user.role)
        if not required.issubset(granted):
            raise PermissionDeniedError(
                "Your role does not permit this operation."
            )
        return current_user

    return _dependency


def require_self_or_permission(
    member_id: int, permission: Permission
) -> Callable[..., User]:
    

    def _dependency(current_user: CurrentUser) -> User:
        if current_user.id == member_id:
            return current_user
        granted = permissions_for_role(current_user.role)
        if permission not in granted:
            raise PermissionDeniedError("You may only access your own records.")
        return current_user

    return _dependency


def require_staff(current_user: CurrentUser) -> User:
    if current_user.role.value not in ("LIBRARIAN", "SUPER_ADMIN"):
        raise PermissionDeniedError("Only library staff can perform this action.")
    return current_user


StaffUser = Annotated[User, Depends(require_staff)]
AdminUser = Annotated[User, Depends(require_roles("SUPER_ADMIN"))]


def optional_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
    session: DbSession = None,  
) -> User | None:
    
    if credentials is None or not credentials.credentials:
        return None
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        user_id = int(payload.get("sub", "0"))
    except (jwt.PyJWTError, TypeError, ValueError):
        return None
    user = session.get(User, user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        return None
    return user


def has_any_permission(user: User, permissions: Iterable[Permission]) -> bool:
    granted = permissions_for_role(user.role)
    return any(p in granted for p in permissions)
