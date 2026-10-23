

from __future__ import annotations

import argparse
import getpass
import os
import secrets
import string
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import get_session_factory
from app.models.enums import MembershipType, UserRole, UserStatus
from app.models.user import User


def generate_password(length: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(not c.isalnum() for c in password)
        ):
            return password


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap the super administrator account.")
    parser.add_argument("--email", default=settings.BOOTSTRAP_ADMIN_EMAIL)
    parser.add_argument("--password", default=settings.BOOTSTRAP_ADMIN_PASSWORD or None)
    parser.add_argument("--name", default="Library Administrator")
    parser.add_argument(
        "--reset", action="store_true", help="Reset the password of an existing account."
    )
    args = parser.parse_args(argv)

    email = (args.email or "").strip().lower()
    if not email or "@" not in email:
        print("A valid administrator e-mail address is required.", file=sys.stderr)
        return 2

    password = args.password
    generated = False
    if not password:
        if os.isatty(sys.stdin):
            password = getpass.getpass("Administrator password: ")
        if not password:
            password = generate_password()
            generated = True

    if len(password) < 8:
        print("The password must be at least 8 characters long.", file=sys.stderr)
        return 2

    session = get_session_factory()()
    try:
        user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            parts = args.name.strip().split(" ", 1)
            user = User(
                email=email,
                institutional_id="ADMIN-001",
                password_hash=hash_password(password),
                first_name=parts[0],
                last_name=parts[1] if len(parts) > 1 else "Administrator",
                role=UserRole.SUPER_ADMIN,
                status=UserStatus.ACTIVE,
                membership_type=MembershipType.STAFF,
                is_email_verified=True,
            )
            session.add(user)
            action = "created"
        else:
            user.password_hash = hash_password(password)
            user.role = UserRole.SUPER_ADMIN
            user.status = UserStatus.ACTIVE
            user.is_email_verified = True
            action = "updated"
        session.commit()
    finally:
        session.close()

    print(f"Super administrator {action}: {email}")
    if generated:
        print("Generated password (shown once):")
        print(password)
    else:
        print("Password updated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
