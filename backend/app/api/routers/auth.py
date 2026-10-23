

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status
from sqlalchemy.orm import Session

from app.api.csrf import (
    clear_auth_cookies,
    new_csrf_token,
    set_auth_cookies,
    validate_csrf,
)
from app.api.dependencies import CurrentUser, DbSession, get_client_ip
from app.core.config import settings
from app.core.exceptions import AuthenticationError, RateLimitError, ValidationError
from app.models.enums import AuditAction, NotificationType, UserStatus
from app.schemas.auth import (
    ChangePasswordRequest,
    EmailVerificationRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserProfile,
)
from app.services import auth_service
from app.services.audit_service import log_action
from app.services.notification_service import queue_notification
from app.services.rate_limit import get_rate_limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_refresh_cookie(response: Response, tokens: dict) -> str:
    csrf_token = new_csrf_token()
    set_auth_cookies(response, tokens["refresh_token"], csrf_token)
    return csrf_token


def _token_response(tokens: dict) -> TokenResponse:
    return TokenResponse(
        access_token=tokens["access_token"],
        token_type="bearer",
        expires_in=tokens["expires_in"],
        refresh_token=None,  
        user=UserProfile(**auth_service.build_user_profile(tokens["user"])),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Sign in with e-mail or institutional ID",
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: DbSession,
) -> TokenResponse:
    ip_address = get_client_ip(request)
    limiter = get_rate_limiter()
    identifier_key = f"login:id:{payload.identifier.strip().lower()}"
    ip_key = f"login:ip:{ip_address or 'unknown'}"

    if not limiter.is_allowed(identifier_key) or not limiter.is_allowed(ip_key):
        raise RateLimitError(
            "Too many sign-in attempts. Please wait a few minutes and try again."
        )

    user = auth_service.authenticate(
        session,
        payload.identifier,
        payload.password,
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent"),
    )
    limiter.reset(identifier_key)
    limiter.reset(ip_key)

    tokens = auth_service.issue_tokens(
        session,
        user,
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent"),
    )
    _set_refresh_cookie(response, tokens)
    return _token_response(tokens)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate the refresh token and obtain a new access token",
)
def refresh(
    request: Request,
    response: Response,
    session: DbSession,
    body: RefreshRequest | None = None,
) -> TokenResponse:
    validate_csrf(request)
    raw_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not raw_token and body is not None:
        raw_token = body.refresh_token
    if not raw_token:
        raise AuthenticationError("No refresh token was supplied.")

    tokens = auth_service.rotate_refresh_token(
        session,
        raw_token,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    _set_refresh_cookie(response, tokens)
    return _token_response(tokens)


@router.post("/logout", response_model=MessageResponse, summary="Revoke the current session")
def logout(
    request: Request,
    response: Response,
    session: DbSession,
    body: LogoutRequest | None = None,
) -> MessageResponse:
    try:
        validate_csrf(request)
    except Exception:
        
        
        pass

    raw_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not raw_token and body is not None:
        raw_token = body.refresh_token

    current_user: object | None = None
    try:
        from app.api.dependencies import optional_user

        current_user = optional_user(request, None, session)
    except Exception:
        current_user = None

    auth_service.revoke_refresh_token(
        session,
        raw_token,
        user=current_user,  
        all_sessions=bool(body and body.all_sessions),
        ip_address=get_client_ip(request),
    )
    clear_auth_cookies(response)
    return MessageResponse(message="Signed out successfully.")


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Request a password reset link",
)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    session: DbSession,
) -> ForgotPasswordResponse:
    ip_address = get_client_ip(request)
    limiter = get_rate_limiter()
    if not limiter.is_allowed(f"forgot:{payload.email.lower()}"):
        raise RateLimitError("Too many password reset requests. Please try again later.")

    user = auth_service.find_user_by_identifier(session, payload.email)
    generic = ForgotPasswordResponse(
        message=(
            "If an account exists for that e-mail address, a password reset link "
            "has been sent."
        )
    )
    if user is None or user.status in (UserStatus.INACTIVE, UserStatus.SUSPENDED):
        
        log_action(
            session,
            AuditAction.PASSWORD_RESET_REQUESTED,
            actor_email=payload.email.lower(),
            summary="Password reset requested for an unknown or inactive account",
            ip_address=ip_address,
        )
        session.commit()
        return generic

    raw_token = auth_service.create_password_reset_token(session, user, ip_address=ip_address)
    reset_url = f"{settings.APP_BASE_URL.rstrip('/')}/reset-password?token={raw_token}"
    queue_notification(
        session,
        user=user,
        notification_type=NotificationType.PASSWORD_RESET,
        template_name="password_reset",
        context={
            "name": user.first_name,
            "email": user.email,
            "reset_url": reset_url,
            "expiry_minutes": settings.PASSWORD_RESET_EXPIRE_MINUTES,
        },
        dedupe_key=f"password_reset:{user.id}:{raw_token[:16]}",
    )
    log_action(
        session,
        AuditAction.PASSWORD_RESET_REQUESTED,
        actor=user,
        summary="Password reset link issued",
        ip_address=ip_address,
    )
    session.commit()
    return generic


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset a password using a single-use token",
)
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    session: DbSession,
) -> MessageResponse:
    user = auth_service.consume_password_reset_token(session, payload.token)
    user.password_hash = auth_service.hash_password(payload.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    auth_service.revoke_all_sessions(session, user, reason="password_reset")
    log_action(
        session,
        AuditAction.PASSWORD_RESET_COMPLETED,
        actor=user,
        summary="Password reset completed",
        ip_address=get_client_ip(request),
    )
    session.commit()
    return MessageResponse(message="Your password has been reset. You can now sign in.")


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change the password of the signed-in account",
)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    session: DbSession,
    current_user: CurrentUser,
) -> MessageResponse:
    auth_service.change_password(
        session,
        current_user,
        payload.current_password,
        payload.new_password,
        ip_address=get_client_ip(request),
    )
    return MessageResponse(
        message="Password changed successfully. Please sign in again on other devices."
    )


@router.get("/me", response_model=UserProfile, summary="Current account profile")
def me(current_user: CurrentUser) -> UserProfile:
    return UserProfile(**auth_service.build_user_profile(current_user))


@router.post(
    "/verify-email",
    response_model=UserProfile,
    summary="Verify an e-mail address and activate the account",
)
def verify_email(
    payload: EmailVerificationRequest,
    request: Request,
    session: DbSession,
) -> UserProfile:
    user = auth_service.consume_email_verification_token(session, payload.token)
    queue_notification(
        session,
        user=user,
        notification_type=NotificationType.WELCOME,
        template_name="welcome",
        context={
            "name": user.first_name,
            "email": user.email,
            "role": user.role.value,
            "institutional_id": user.institutional_id,
        },
        dedupe_key=f"welcome:{user.id}",
    )
    session.commit()
    return UserProfile(**auth_service.build_user_profile(user))


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Send a new e-mail verification link",
)
def resend_verification(
    request: Request,
    session: DbSession,
    current_user: CurrentUser,
) -> MessageResponse:
    if current_user.is_email_verified:
        raise ValidationError("This e-mail address is already verified.")
    raw_token, expires_in = auth_service.create_email_verification_token(session, current_user)
    verification_url = (
        f"{settings.APP_BASE_URL.rstrip('/')}/verify-email?token={raw_token}"
    )
    queue_notification(
        session,
        user=current_user,
        notification_type=NotificationType.EMAIL_VERIFICATION,
        template_name="email_verification",
        context={
            "name": current_user.first_name,
            "verification_url": verification_url,
            "expiry_hours": max(1, expires_in // 3600),
        },
        dedupe_key=f"verify_email:{current_user.id}:{raw_token[:16]}",
    )
    session.commit()
    return MessageResponse(message="A verification link has been sent to your e-mail address.")
