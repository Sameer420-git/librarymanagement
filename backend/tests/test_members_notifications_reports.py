

from __future__ import annotations

import io

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import NotificationStatus, UserStatus
from app.models.notification import Notification
from app.models.user import User
from tests.conftest import auth_headers





def test_librarian_registers_a_student(client: TestClient, librarian_token: str) -> None:
    response = client.post(
        "/api/members",
        headers=auth_headers(librarian_token),
        json={
            "email": "new.student@example.edu",
            "first_name": "Nina",
            "last_name": "Student",
            "role": "STUDENT",
            "institutional_id": "STU-2026-001",
            "password": "Student@123",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "new.student@example.edu"
    assert body["role"] == "STUDENT"


def test_students_cannot_register_members(client: TestClient, student_token: str) -> None:
    response = client.post(
        "/api/members",
        headers=auth_headers(student_token),
        json={
            "email": "sneaky@example.edu",
            "first_name": "Sneaky",
            "last_name": "Student",
            "role": "STUDENT",
            "password": "Student@123",
        },
    )
    assert response.status_code == 403


def test_duplicate_email_is_rejected(client: TestClient, librarian_token: str) -> None:
    payload = {
        "email": "duplicate@example.edu",
        "first_name": "Dup",
        "last_name": "Licate",
        "role": "STUDENT",
        "institutional_id": "STU-2026-002",
        "password": "Student@123",
    }
    first = client.post("/api/members", headers=auth_headers(librarian_token), json=payload)
    assert first.status_code == 201

    second = client.post("/api/members", headers=auth_headers(librarian_token), json=payload)
    assert second.status_code in (400, 409, 422)


def test_member_search_and_profile(client: TestClient, librarian_token: str) -> None:
    client.post(
        "/api/members",
        headers=auth_headers(librarian_token),
        json={
            "email": "searchable@example.edu",
            "first_name": "Sara",
            "last_name": "Searchable",
            "role": "STUDENT",
            "institutional_id": "STU-2026-003",
            "password": "Student@123",
        },
    )

    listing = client.get(
        "/api/members",
        headers=auth_headers(librarian_token),
        params={"search": "Searchable"},
    )
    assert listing.status_code == 200
    body = listing.json()
    assert body["pagination"]["total"] == 1

    member_id = body["items"][0]["id"]
    profile = client.get(
        f"/api/members/{member_id}", headers=auth_headers(librarian_token)
    )
    assert profile.status_code == 200
    assert profile.json()["full_name"] == "Sara Searchable"


def test_members_can_read_their_own_profile(
    client: TestClient, student_token: str, student_user: User
) -> None:
    response = client.get(
        f"/api/members/{student_user.id}", headers=auth_headers(student_token)
    )
    assert response.status_code == 200
    assert response.json()["email"] == student_user.email


def test_members_cannot_read_other_profiles(
    client: TestClient, student_token: str, db: Session
) -> None:
    other = User(
        email="other.member@example.edu",
        institutional_id="STU-2026-004",
        password_hash="x",
        first_name="Other",
        last_name="Member",
        role="STUDENT",
        status=UserStatus.ACTIVE,
    )
    db.add(other)
    db.commit()
    db.refresh(other)

    response = client.get(
        f"/api/members/{other.id}", headers=auth_headers(student_token)
    )
    assert response.status_code == 403


def test_member_status_can_be_changed(
    client: TestClient, librarian_token: str, student_user: User
) -> None:
    response = client.patch(
        f"/api/members/{student_user.id}/status",
        headers=auth_headers(librarian_token),
        params={"status": "SUSPENDED"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "SUSPENDED"


def test_member_csv_export(client: TestClient, librarian_token: str) -> None:
    client.post(
        "/api/members",
        headers=auth_headers(librarian_token),
        json={
            "email": "exported@example.edu",
            "first_name": "Exported",
            "last_name": "Member",
            "role": "FACULTY",
            "institutional_id": "FAC-2026-001",
            "password": "Faculty@123",
        },
    )
    response = client.get("/api/members/export/csv", headers=auth_headers(librarian_token))
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "exported@example.edu" in response.text


def test_member_csv_import(client: TestClient, librarian_token: str) -> None:
    csv_payload = (
        "email,first_name,last_name,role,institutional_id,password\n"
        "imported@example.edu,Imported,Member,STUDENT,STU-2026-005,Student@123\n"
    )
    response = client.post(
        "/api/members/import",
        headers=auth_headers(librarian_token),
        files={"file": ("members.csv", io.BytesIO(csv_payload.encode()), "text/csv")},
    )
    assert response.status_code in (200, 201), response.text
    assert response.json()["created"] == 1


def test_departments_and_courses_can_be_created(
    client: TestClient, librarian_token: str
) -> None:
    department = client.post(
        "/api/members/departments/all",
        headers=auth_headers(librarian_token),
        json={"code": "CSE", "name": "Computer Science & Engineering"},
    )
    assert department.status_code == 201, department.text
    department_id = department.json()["id"]

    course = client.post(
        "/api/members/courses/all",
        headers=auth_headers(librarian_token),
        json={
            "code": "BTECH-CSE",
            "name": "B.Tech Computer Science",
            "department_id": department_id,
            "duration_semesters": 8,
        },
    )
    assert course.status_code == 201, course.text

    listing = client.get(
        "/api/members/courses/all", headers=auth_headers(librarian_token)
    ).json()
    assert any(item["code"] == "BTECH-CSE" for item in listing)





def test_notification_is_queued_when_a_book_is_issued(
    client: TestClient, librarian_token: str, student_user: User, db: Session
) -> None:
    book = client.post(
        "/api/books",
        headers=auth_headers(librarian_token),
        json={"title": "Notification Book", "isbn": "978-7000000001"},
    ).json()
    copy = client.post(
        f"/api/books/{book['id']}/copies",
        headers=auth_headers(librarian_token),
        json={"accession_number": "ACC-NOTIF-1"},
    ).json()

    client.post(
        "/api/loans/issue",
        headers=auth_headers(librarian_token),
        json={"member_id": student_user.id, "copy_id": copy["id"]},
    )

    db.expire_all()
    notifications = db.query(Notification).filter(Notification.user_id == student_user.id).all()
    assert notifications
    assert notifications[0].type.value == "BOOK_ISSUED"
    assert notifications[0].status == NotificationStatus.QUEUED


def test_queued_notifications_are_delivered(
    client: TestClient, librarian_token: str, student_user: User, db: Session
) -> None:
    book = client.post(
        "/api/books",
        headers=auth_headers(librarian_token),
        json={"title": "Deliverable Book", "isbn": "978-7000000002"},
    ).json()
    copy = client.post(
        f"/api/books/{book['id']}/copies",
        headers=auth_headers(librarian_token),
        json={"accession_number": "ACC-NOTIF-2"},
    ).json()
    client.post(
        "/api/loans/issue",
        headers=auth_headers(librarian_token),
        json={"member_id": student_user.id, "copy_id": copy["id"]},
    )

    from app.services.notification_service import process_pending

    stats = process_pending(db)
    assert stats["claimed"] >= 1
    assert stats["sent"] >= 1

    db.expire_all()
    delivered = (
        db.query(Notification)
        .filter(Notification.user_id == student_user.id)
        .filter(Notification.status == NotificationStatus.SENT)
        .all()
    )
    assert delivered


def test_notification_history_is_scoped_to_the_owner(
    client: TestClient, librarian_token: str, student_user: User, db: Session
) -> None:
    book = client.post(
        "/api/books",
        headers=auth_headers(librarian_token),
        json={"title": "Scoped Book", "isbn": "978-7000000003"},
    ).json()
    copy = client.post(
        f"/api/books/{book['id']}/copies",
        headers=auth_headers(librarian_token),
        json={"accession_number": "ACC-NOTIF-3"},
    ).json()
    client.post(
        "/api/loans/issue",
        headers=auth_headers(librarian_token),
        json={"member_id": student_user.id, "copy_id": copy["id"]},
    )

    student_token = client.post(
        "/api/auth/login",
        json={"identifier": student_user.email, "password": "Password@123"},
    ).json()["access_token"]

    history = client.get("/api/notifications", headers=auth_headers(student_token))
    assert history.status_code == 200
    assert history.json()["pagination"]["total"] >= 1

    queue = client.get("/api/admin/notifications", headers=auth_headers(librarian_token))
    assert queue.status_code == 200
    assert queue.json()["pagination"]["total"] >= 1

    stats = client.get(
        "/api/admin/notifications/stats", headers=auth_headers(librarian_token)
    )
    assert stats.status_code == 200
    assert stats.json()["total"] >= 1





def test_reports_are_available_to_staff(client: TestClient, librarian_token: str) -> None:
    for endpoint in (
        "/api/reports/inventory",
        "/api/reports/circulation",
        "/api/reports/fines",
        "/api/reports/popular-books",
        "/api/reports/overdue",
        "/api/reports/members",
    ):
        response = client.get(endpoint, headers=auth_headers(librarian_token))
        assert response.status_code == 200, f"{endpoint}: {response.text}"
        assert isinstance(response.json(), dict)


def test_reports_are_not_available_to_students(
    client: TestClient, student_token: str
) -> None:
    response = client.get("/api/reports/inventory", headers=auth_headers(student_token))
    assert response.status_code == 403
