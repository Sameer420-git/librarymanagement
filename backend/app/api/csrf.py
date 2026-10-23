

from __future__ import annotations

import secrets

from fastapi import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.exceptions import PermissionDeniedError

CSRF_COOKIE_NAME = "library_csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_auth_cookies(response: Response, refresh_token: str, csrf_token: str) -> None:
    
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/api/auth",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key=settings.REFRESH_COOKIE_NAME, path="/api/auth")
    response.delete_cookie(key=CSRF_COOKIE_NAME, path="/")


def validate_csrf(request: Request) -> None:
    
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if not cookie_token or not header_token:
        raise PermissionDeniedError(
            "Missing CSRF token. Refresh the page and try again.", code="csrf_failed"
        )
    if not secrets.compare_digest(cookie_token, header_token):
        raise PermissionDeniedError("Invalid CSRF token.", code="csrf_failed")

    origin = request.headers.get("origin")
    if origin and origin not in settings.cors_origins:
        raise PermissionDeniedError("Request origin is not allowed.", code="csrf_failed")
