

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from pwdlib import PasswordHash

from app.core.config import settings


password_hasher = PasswordHash.recommended()

TokenType = Literal["access", "refresh", "email_verification", "password_reset"]





def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    if not password or not hashed_password:
        return False
    try:
        return password_hasher.verify(password, hashed_password)
    except Exception:
        return False


def needs_rehash(hashed_password: str) -> bool:
    try:
        return password_hasher.verify_and_update("dummy-never-used", hashed_password)[1] is not None
    except Exception:
        return False





def generate_opaque_token(nbytes: int = 32) -> str:
    
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_equals(left: str, right: str) -> bool:
    return secrets.compare_digest(left, right)





def _create_jwt(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    user_id: int | str, role: str, extra_claims: dict[str, Any] | None = None
) -> tuple[str, int]:
    
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    claims = {"role": role}
    if extra_claims:
        claims.update(extra_claims)
    token = _create_jwt(str(user_id), "access", expires, claims)
    return token, int(expires.total_seconds())


def create_refresh_token(user_id: int | str, extra_claims: dict[str, Any] | None = None) -> tuple[str, str, int]:
    
    expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    token = _create_jwt(str(user_id), "refresh", expires, extra_claims)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    return token, payload["jti"], int(expires.total_seconds())


def create_email_verification_jwt(user_id: int | str) -> tuple[str, int]:
    expires = timedelta(hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS)
    token = _create_jwt(str(user_id), "email_verification", expires)
    return token, int(expires.total_seconds())


def decode_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any]:
    
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if expected_type and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"Expected token type '{expected_type}'")
    return payload
