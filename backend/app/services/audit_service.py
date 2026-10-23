

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.enums import AuditAction
from app.models.settings import AuditLog
from app.models.user import User

logger = logging.getLogger(__name__)


_SENSITIVE_KEYS = {
    "password",
    "new_password",
    "current_password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "smtp_password",
    "authorization",
    "cookie",
}


def _sanitize(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not metadata:
        return None
    cleaned: dict[str, Any] = {}
    for key, value in metadata.items():
        if key.lower() in _SENSITIVE_KEYS:
            cleaned[key] = "***"
        elif isinstance(value, str) and len(value) > 500:
            cleaned[key] = value[:500] + "..."
        else:
            cleaned[key] = value
    return cleaned


def log_action(
    session: Session,
    action: AuditAction | str,
    *,
    actor: User | None = None,
    actor_id: int | None = None,
    actor_email: str | None = None,
    actor_role: str | None = None,
    entity_type: str | None = None,
    entity_id: Any | None = None,
    summary: str | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    commit: bool = False,
) -> AuditLog:
    
    try:
        if actor is not None:
            actor_id = actor.id
            actor_email = actor.email
            actor_role = actor.role.value if hasattr(actor.role, "value") else str(actor.role)
        entry = AuditLog(
            actor_id=actor_id,
            actor_email=actor_email,
            actor_role=actor_role,
            action=action.value if isinstance(action, AuditAction) else str(action),
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            summary=summary,
            metadata_json=_sanitize(metadata),
            ip_address=ip_address,
            user_agent=(user_agent or "")[:255] or None,
        )
        session.add(entry)
        if commit:
            session.commit()
        else:
            session.flush()
    except Exception:  
        logger.exception("Failed to write audit log for action %s", action)
    return entry  
