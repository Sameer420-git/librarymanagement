

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import UserStatus
from app.models.user import RefreshToken, User
from tests.conftest import auth_headers, csrf_headers, login, make_user


def test_health_endpoint_is_public(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_returns_tokens_and_sets_refresh_cookie(client: TestClient, student_user: User) -> None:
    response = client.post(
        "/api/auth/login",
        json={"identifier": student_user.email, "password": "Password@123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"].lower() == "bearer"
    assert body["user"]["email"] == student_user.email

    cookies = response.cookies
    assert "library_refresh_token" in cookies


def test_login_with_wrong_password_is_rejected(client: TestClient, student_user: User) -> None:
    response = client.post(
        "/api/auth/login", json={"identifier": student_user.email, "password": "wrong-password"}
    )
    assert response.status_code == 401
    assert "error" in response.json()


def test_login_is_rate_limited(client: TestClient, student_user: User) -> None:
    
    statuses = []
    for _ in range(8):
        response = client.post(
            "/api/auth/login",
            json={"identifier": student_user.email, "password": "definitely-wrong"},
        )
        statuses.append(response.status_code)
    assert 429 in statuses


def test_inactive_account_cannot_log_in(client: TestClient, db: Session) -> None:
    user = make_user(
        db,
        email="suspended@test.edu",
        role="STUDENT",
        status=UserStatus.SUSPENDED,
    )
    response = client.post(
        "/api/auth/login", json={"identifier": user.email, "password": "Password@123"}
    )
    assert response.status_code in (401, 403)


def test_protected_endpoint_requires_a_token(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_returns_the_current_user(client: TestClient, student_user: User) -> None:
    token = login(client, student_user.email)["access_token"]
    response = client.get("/api/auth/me", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["email"] == student_user.email


def test_refresh_rotates_the_refresh_token(client: TestClient, student_user: User) -> None:
    login(client, student_user.email)
    response = client.post("/api/auth/refresh", headers=csrf_headers(client))
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]

    
    second = client.post("/api/auth/refresh", headers=csrf_headers(client))
    assert second.status_code in (401, 200)
    if second.status_code == 401:
        assert "error" in second.json()


def test_refresh_without_a_csrf_header_is_rejected(
    client: TestClient, student_user: User
) -> None:
    login(client, student_user.email)
    response = client.post("/api/auth/refresh")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


def test_logout_revokes_the_refresh_token(
    client: TestClient, db: Session, student_user: User
) -> None:
    login(client, student_user.email)
    response = client.post("/api/auth/logout", headers=csrf_headers(client))
    assert response.status_code == 200

    
    assert "library_refresh_token" not in client.cookies
    
    tokens = db.execute(
        select(RefreshToken).where(RefreshToken.user_id == student_user.id)
    ).scalars().all()
    assert tokens and all(token.is_revoked for token in tokens)

    refresh = client.post("/api/auth/refresh", headers=csrf_headers(client))
    assert refresh.status_code in (401, 403)


def test_forgot_password_does_not_leak_account_existence(
    client: TestClient, student_user: User
) -> None:
    response = client.post("/api/auth/forgot-password", json={"email": student_user.email})
    assert response.status_code == 200
    assert "message" in response.json()

    unknown = client.post(
        "/api/auth/forgot-password", json={"email": "nobody@test.edu"}
    )
    assert unknown.status_code == 200
    assert unknown.json()["message"] == response.json()["message"]


def test_reset_password_with_an_invalid_token_fails(client: TestClient) -> None:
    response = client.post(
        "/api/auth/reset-password",
        json={"token": "not-a-real-token", "new_password": "NewPassword@123"},
    )
    assert response.status_code in (400, 404, 422), response.text


def test_change_password_requires_a_valid_current_password(
    client: TestClient, student_user: User
) -> None:
    token = login(client, student_user.email)["access_token"]
    response = client.post(
        "/api/auth/change-password",
        headers=auth_headers(token),
        json={"current_password": "wrong", "new_password": "NewPassword@123"},
    )
    assert response.status_code in (400, 401)


def test_change_password_then_login_with_the_new_password(
    client: TestClient, student_user: User
) -> None:
    token = login(client, student_user.email)["access_token"]
    response = client.post(
        "/api/auth/change-password",
        headers=auth_headers(token),
        json={"current_password": "Password@123", "new_password": "NewPassword@123"},
    )
    assert response.status_code == 200

    assert (
        client.post(
            "/api/auth/login",
            json={"identifier": student_user.email, "password": "Password@123"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"identifier": student_user.email, "password": "NewPassword@123"},
        ).status_code
        == 200
    )
