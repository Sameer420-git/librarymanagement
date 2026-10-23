

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationError, ConflictError, ValidationError
from app.core.security import (
    create_access_token,
    create_email_verification_jwt,
    create_refresh_token,
    decode_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.enums import AuditAction, UserRole, UserStatus
from app.models.user import (
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
    User,
)
from app.services.audit_service import log_action

logger = logging.getLogger(__name__)

GENERIC_AUTH_ERROR = "Invalid credentials. Please check your e-mail/ID and password."
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15


def _now() -> datetime:
    return datetime.now(timezone.utc)





def find_user_by_identifier(session: Session, identifier: str) -> Optional[User]:
    
    normalized = identifier.strip()
    return session.execute(
        select(User).where(
            or_(
                User.email == normalized.lower(),
                User.institutional_id == normalized,
            )
        )
    ).scalar_one_or_none()


def authenticate(
    session: Session,
    identifier: str,
    password: str,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> User:
    
    user = find_user_by_identifier(session, identifier)

    if user is None:
        
        
        verify_password(password, hash_password("dummy-password-for-timing"))
        log_action(
            session,
            AuditAction.LOGIN_FAILED,
            actor_email=identifier.lower()[:255],
            summary="Login failed for unknown identifier",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.commit()
        raise AuthenticationError(GENERIC_AUTH_ERROR)

    now = _now()
    if user.locked_until is not None:
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            raise AuthenticationError(
                "This account is temporarily locked after too many failed attempts. "
                f"Try again after {locked_until.astimezone(timezone.utc).strftime('%H:%M UTC')}."
            )

    if user.status == UserStatus.PENDING:
        raise AuthenticationError(
            "This account has not been activated yet. Please verify your e-mail address.",
            code="account_pending",
        )
    if user.status in (UserStatus.INACTIVE, UserStatus.SUSPENDED):
        raise AuthenticationError(
            "This account is not active. Please contact the library administrator.",
            code="account_inactive",
        )

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= MAX_FAILED_LOGINS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            user.failed_login_attempts = 0
        log_action(
            session,
            AuditAction.LOGIN_FAILED,
            actor=user,
            summary="Invalid password",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.commit()
        raise AuthenticationError(GENERIC_AUTH_ERROR)

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    log_action(
        session,
        AuditAction.LOGIN_SUCCESS,
        actor=user,
        summary="Login successful",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.commit()
    return user





def issue_tokens(
    session: Session,
    user: User,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    
    access_token, expires_in = create_access_token(user.id, user.role.value)
    refresh_token, jti, refresh_expires = create_refresh_token(user.id)

    record = RefreshToken(
        user_id=user.id,
        jti=jti,
        token_hash=hash_token(refresh_token),
        expires_at=_now() + timedelta(seconds=refresh_expires),
        created_at=_now(),
        user_agent=(user_agent or "")[:255] or None,
        ip_address=ip_address,
    )
    session.add(record)
    session.commit()

    return {
        "access_token": access_token,
        "expires_in": expires_in,
        "refresh_token": refresh_token,
        "refresh_expires_in": refresh_expires,
        "user": user,
    }


def rotate_refresh_token(
    session: Session,
    raw_token: str,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    
    try:
        payload = decode_token(raw_token, expected_type="refresh")
    except Exception as exc:
        raise AuthenticationError("Invalid or expired refresh token.") from exc

    jti = payload.get("jti")
    subject = payload.get("sub")
    if not jti or subject is None:
        raise AuthenticationError("Invalid refresh token.")

    record = session.execute(
        select(RefreshToken).where(RefreshToken.jti == jti)
    ).scalar_one_or_none()
    if record is None:
        raise AuthenticationError("Invalid refresh token.")

    if record.revoked_at is not None:
        
        session.query(RefreshToken).filter(
            RefreshToken.user_id == record.user_id, RefreshToken.revoked_at.is_(None)
        ).update({"revoked_at": _now(), "revoked_reason": "token_reuse_detected"})
        session.commit()
        log_action(
            session,
            AuditAction.LOGOUT,
            actor_id=record.user_id,
            summary="Refresh token reuse detected - all sessions revoked",
            ip_address=ip_address,
        )
        session.commit()
        raise AuthenticationError("Session expired. Please sign in again.")

    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= _now():
        raise AuthenticationError("Session expired. Please sign in again.")

    user = session.get(User, record.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise AuthenticationError("The account is not active.")

    access_token, access_expires = create_access_token(user.id, user.role.value)
    new_refresh, new_jti, refresh_expires = create_refresh_token(user.id)

    record.revoked_at = _now()
    record.revoked_reason = "rotated"
    record.replaced_by_jti = new_jti

    session.add(
        RefreshToken(
            user_id=user.id,
            jti=new_jti,
            token_hash=hash_token(new_refresh),
            expires_at=_now() + timedelta(seconds=refresh_expires),
            created_at=_now(),
            user_agent=(user_agent or "")[:255] or None,
            ip_address=ip_address,
        )
    )
    session.commit()

    return {
        "access_token": access_token,
        "expires_in": access_expires,
        "refresh_token": new_refresh,
        "refresh_expires_in": refresh_expires,
        "user": user,
    }


def revoke_refresh_token(
    session: Session,
    raw_token: str | None,
    *,
    user: User | None = None,
    all_sessions: bool = False,
    ip_address: str | None = None,
) -> None:
    
    if all_sessions and user is not None:
        session.query(RefreshToken).filter(
            RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
        ).update({"revoked_at": _now(), "revoked_reason": "logout_all"})
        log_action(
            session,
            AuditAction.LOGOUT,
            actor=user,
            summary="All sessions revoked",
            ip_address=ip_address,
        )
        session.commit()
        return

    if raw_token:
        try:
            payload = decode_token(raw_token, expected_type="refresh")
        except Exception:
            payload = {}
        jti = payload.get("jti")
        if jti:
            record = session.execute(
                select(RefreshToken).where(RefreshToken.jti == jti)
            ).scalar_one_or_none()
            if record is not None and record.revoked_at is None:
                record.revoked_at = _now()
                record.revoked_reason = "logout"
                log_action(
                    session,
                    AuditAction.LOGOUT,
                    actor_id=record.user_id,
                    summary="Session revoked",
                    ip_address=ip_address,
                )
                session.commit()
                return

    if user is not None:
        session.query(RefreshToken).filter(
            RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
        ).update({"revoked_at": _now(), "revoked_reason": "logout"})
        log_action(
            session,
            AuditAction.LOGOUT,
            actor=user,
            summary="Sessions revoked",
            ip_address=ip_address,
        )
        session.commit()


def revoke_all_sessions(session: Session, user: User, reason: str = "revoked") -> None:
    
    session.query(RefreshToken).filter(
        RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
    ).update({"revoked_at": _now(), "revoked_reason": reason})





def create_password_reset_token(
    session: Session, user: User, *, ip_address: str | None = None
) -> str:
    
    
    session.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)
    ).update({"used_at": _now()})

    raw_token = generate_opaque_token(32)
    record = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=_now() + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
        created_at=_now(),
        request_ip=ip_address,
    )
    session.add(record)
    session.commit()
    return raw_token


def consume_password_reset_token(session: Session, raw_token: str) -> User:
    
    token_hash = hash_token(raw_token)
    record = session.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    ).scalar_one_or_none()
    if record is None:
        raise ValidationError("This password reset link is invalid or has already been used.")
    if record.used_at is not None:
        raise ValidationError("This password reset link is invalid or has already been used.")
    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= _now():
        raise ValidationError("This password reset link has expired. Please request a new one.")

    user = session.get(User, record.user_id)
    if user is None:
        raise ValidationError("This password reset link is invalid.")

    record.used_at = _now()
    return user


def change_password(
    session: Session,
    user: User,
    current_password: str,
    new_password: str,
    *,
    ip_address: str | None = None,
    revoke_sessions: bool = True,
) -> None:
    
    if not verify_password(current_password, user.password_hash):
        raise AuthenticationError("Your current password is incorrect.")
    if current_password == new_password:
        raise ValidationError("The new password must be different from the current password.")
    user.password_hash = hash_password(new_password)
    if revoke_sessions:
        session.query(RefreshToken).filter(
            RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
        ).update({"revoked_at": _now(), "revoked_reason": "password_changed"})
    log_action(
        session,
        AuditAction.PASSWORD_CHANGED,
        actor=user,
        summary="Password changed by the account owner",
        ip_address=ip_address,
    )
    session.commit()





def create_email_verification_token(session: Session, user: User) -> tuple[str, int]:
    
    session.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id, EmailVerificationToken.used_at.is_(None)
    ).update({"used_at": _now()})

    raw, expires_in = create_email_verification_jwt(user.id)
    token_hash = hash_token(raw)
    record = EmailVerificationToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=_now() + timedelta(seconds=expires_in),
        created_at=_now(),
    )
    session.add(record)
    session.commit()
    return raw, expires_in


def consume_email_verification_token(session: Session, raw_token: str) -> User:
    from app.core.security import decode_token
    import jwt as _jwt

    try:
        payload = decode_token(raw_token, expected_type="email_verification")
    except _jwt.PyJWTError as exc:
        raise ValidationError("This verification link is invalid or has expired.") from exc

    token_hash = hash_token(raw_token)
    record = session.execute(
        select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
    ).scalar_one_or_none()
    if record is None or record.used_at is not None:
        raise ValidationError("This verification link is invalid or has already been used.")

    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= _now():
        raise ValidationError("This verification link has expired.")

    user = session.get(User, record.user_id)
    if user is None:
        raise ValidationError("This verification link is invalid.")

    record.used_at = _now()
    user.is_email_verified = True
    user.email_verified_at = _now()
    if user.status == UserStatus.PENDING:
        user.status = UserStatus.ACTIVE
    log_action(
        session,
        AuditAction.EMAIL_VERIFIED,
        actor=user,
        summary="E-mail address verified",
    )
    session.commit()
    return user





def build_user_profile(user: User) -> dict[str, Any]:
    
    department_name = None
    course_name = None
    enrollment_number = None
    employee_id = None
    designation = None
    semester = None
    section = None
    academic_year = None

    if user.student_profile is not None:
        enrollment_number = user.student_profile.enrollment_number
        semester = user.student_profile.semester
        section = user.student_profile.section
        academic_year = user.student_profile.academic_year
        if user.student_profile.course is not None:
            course_name = user.student_profile.course.name
            if user.student_profile.course.department is not None:
                department_name = user.student_profile.course.department.name
    if user.faculty_profile is not None:
        employee_id = user.faculty_profile.employee_id
        designation = user.faculty_profile.designation
        if user.faculty_profile.department is not None:
            department_name = user.faculty_profile.department.name

    return {
        "id": user.id,
        "email": user.email,
        "institutional_id": user.institutional_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "phone": user.phone,
        "role": user.role.value,
        "status": user.status.value,
        "membership_type": user.membership_type.value,
        "membership_start": user.membership_start,
        "membership_expires": user.membership_expires,
        "is_email_verified": user.is_email_verified,
        "last_login_at": user.last_login_at,
        "avatar_url": user.avatar_url,
        "department_name": department_name,
        "course_name": course_name,
        "enrollment_number": enrollment_number,
        "employee_id": employee_id,
        "designation": designation,
        "semester": semester,
        "section": section,
        "academic_year": academic_year,
    }


def ensure_user_can_be_created(session: Session, email: str, institutional_id: str | None) -> None:
    
    if session.execute(select(User.id).where(User.email == email.lower())).first():
        raise ConflictError("An account with this e-mail address already exists.")
    if institutional_id and session.execute(
        select(User.id).where(User.institutional_id == institutional_id)
    ).first():
        raise ConflictError("An account with this institutional ID already exists.")


def is_staff(user: User) -> bool:
    return user.role in (UserRole.SUPER_ADMIN, UserRole.LIBRARIAN)
