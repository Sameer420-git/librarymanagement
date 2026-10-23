

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any


os.environ.setdefault("EMAIL_BACKEND", "mock")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault(
    "SECRET_KEY", "test-secret-key-that-is-long-enough-for-the-test-suite-0123456789"
)
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import pytest  
from fastapi.testclient import TestClient  
from sqlalchemy import create_engine  
from sqlalchemy.orm import Session, sessionmaker  
from sqlalchemy.pool import StaticPool  

from app.core.security import hash_password  
from app.db.base import Base  
from app.db.session import configure_engine, get_db  
from app.main import app  
from app.models.enums import MembershipType, UserRole, UserStatus  
from app.models.user import User  

BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def engine():
    
    test_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture()
def session_factory(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


@pytest.fixture(autouse=True)
def _configure_engine(session_factory) -> None:
    configure_engine(engine=session_factory.kw["bind"], session_factory=session_factory)


@pytest.fixture()
def db(session_factory) -> Iterator[Session]:
    
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client(session_factory) -> Iterator[TestClient]:
    

    def _get_override() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_override
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    
    from app.services.rate_limit import reset_rate_limiter

    reset_rate_limiter()





def make_user(
    session: Session,
    *,
    email: str,
    role: UserRole,
    first_name: str = "Test",
    last_name: str = "User",
    password: str = "Password@123",
    status: UserStatus = UserStatus.ACTIVE,
    membership_type: MembershipType | None = None,
    institutional_id: str | None = None,
    verified: bool = True,
) -> User:
    if membership_type is None:
        membership_type = {
            UserRole.STUDENT: MembershipType.STUDENT,
            UserRole.FACULTY: MembershipType.FACULTY,
        }.get(role, MembershipType.STAFF)

    user = User(
        email=email,
        institutional_id=institutional_id,
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        role=role,
        status=status,
        membership_type=membership_type,
        is_email_verified=verified,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture()
def admin_user(db: Session) -> User:
    return make_user(
        db,
        email="admin@test.edu",
        role=UserRole.SUPER_ADMIN,
        first_name="Ada",
        last_name="Admin",
        institutional_id="ADM-001",
    )


@pytest.fixture()
def librarian_user(db: Session) -> User:
    return make_user(
        db,
        email="librarian@test.edu",
        role=UserRole.LIBRARIAN,
        first_name="Lee",
        last_name="Librarian",
        institutional_id="LIB-001",
    )


@pytest.fixture()
def faculty_user(db: Session) -> User:
    return make_user(
        db,
        email="faculty@test.edu",
        role=UserRole.FACULTY,
        first_name="Fiona",
        last_name="Faculty",
        institutional_id="FAC-001",
    )


@pytest.fixture()
def student_user(db: Session) -> User:
    return make_user(
        db,
        email="student@test.edu",
        role=UserRole.STUDENT,
        first_name="Sam",
        last_name="Student",
        institutional_id="STU-001",
    )





def login(client: TestClient, email: str, password: str = "Password@123") -> dict[str, Any]:
    
    response = client.post(
        "/api/auth/login", json={"identifier": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def csrf_headers(client: TestClient) -> dict[str, str]:
    
    token = client.cookies.get("library_csrf_token")
    return {"X-CSRF-Token": token} if token else {}


@pytest.fixture()
def admin_token(client: TestClient, admin_user: User) -> str:
    return login(client, admin_user.email)["access_token"]


@pytest.fixture()
def librarian_token(client: TestClient, librarian_user: User) -> str:
    return login(client, librarian_user.email)["access_token"]


@pytest.fixture()
def student_token(client: TestClient, student_user: User) -> str:
    return login(client, student_user.email)["access_token"]


@pytest.fixture()
def faculty_token(client: TestClient, faculty_user: User) -> str:
    return login(client, faculty_user.email)["access_token"]
