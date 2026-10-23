

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.catalogue import BookCopy
from app.models.circulation import Loan
from app.models.enums import BookCopyStatus, LoanStatus
from app.models.user import User
from app.utils.helpers import utcnow
from tests.conftest import auth_headers, make_user


def seed_book_with_copies(
    client: TestClient, librarian_token: str, *, copies: int = 2, isbn: str = "978-1111111111"
) -> tuple[int, list[int]]:
    book = client.post(
        "/api/books",
        headers=auth_headers(librarian_token),
        json={"title": "Circulation Test Book", "isbn": isbn},
    ).json()

    copy_ids: list[int] = []
    for index in range(copies):
        copy = client.post(
            f"/api/books/{book['id']}/copies",
            headers=auth_headers(librarian_token),
            json={"accession_number": f"ACC-CIRC-{isbn[-4:]}-{index}"},
        )
        assert copy.status_code == 201, copy.text
        copy_ids.append(copy.json()["id"])
    return book["id"], copy_ids


def issue(
    client: TestClient,
    token: str,
    member_id: int,
    copy_id: int,
    **extra,
) -> dict:
    payload = {"member_id": member_id, "copy_id": copy_id}
    payload.update(extra)
    response = client.post(
        "/api/loans/issue", headers=auth_headers(token), json=payload
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_issue_requires_staff(
    client: TestClient, librarian_token: str, student_token: str, student_user: User
) -> None:
    _, copy_ids = seed_book_with_copies(
        client, librarian_token, copies=1, isbn="978-2222222222"
    )
    response = client.post(
        "/api/loans/issue",
        headers=auth_headers(student_token),
        json={"member_id": student_user.id, "copy_id": copy_ids[0]},
    )
    assert response.status_code == 403


def test_issue_and_return_a_book(
    client: TestClient, librarian_token: str, student_user: User, db: Session
) -> None:
    _, copy_ids = seed_book_with_copies(client, librarian_token, isbn="978-3333333333")

    loan = issue(client, librarian_token, student_user.id, copy_ids[0])
    assert loan["status"] == LoanStatus.ACTIVE.value
    assert loan["copy_id"] == copy_ids[0]
    assert loan["due_at"]

    db.expire_all()
    copy = db.get(BookCopy, copy_ids[0])
    assert copy is not None
    assert copy.status == BookCopyStatus.ISSUED

    returned = client.post(
        f"/api/loans/{loan['id']}/return", headers=auth_headers(librarian_token)
    )
    assert returned.status_code == 200, returned.text
    assert returned.json()["status"] == LoanStatus.RETURNED.value

    db.expire_all()
    copy = db.get(BookCopy, copy_ids[0])
    assert copy is not None
    assert copy.status == BookCopyStatus.AVAILABLE


def test_a_copy_cannot_be_issued_twice(
    client: TestClient, librarian_token: str, student_user: User, db: Session
) -> None:
    _, copy_ids = seed_book_with_copies(client, librarian_token, copies=1, isbn="978-4444444444")
    issue(client, librarian_token, student_user.id, copy_ids[0])

    duplicate = client.post(
        "/api/loans/issue",
        headers=auth_headers(librarian_token),
        json={"member_id": student_user.id, "copy_id": copy_ids[0]},
    )
    assert duplicate.status_code in (400, 409)

    db.expire_all()
    active = (
        db.query(Loan)
        .filter(Loan.copy_id == copy_ids[0], Loan.status == LoanStatus.ACTIVE)
        .count()
    )
    assert active == 1


def test_borrowing_limit_is_enforced(
    client: TestClient, librarian_token: str, student_user: User
) -> None:
    _, copy_ids = seed_book_with_copies(
        client, librarian_token, copies=6, isbn="978-5555555555"
    )
    
    for copy_id in copy_ids[:5]:
        issue(client, librarian_token, student_user.id, copy_id)

    response = client.post(
        "/api/loans/issue",
        headers=auth_headers(librarian_token),
        json={"member_id": student_user.id, "copy_id": copy_ids[5]},
    )
    assert response.status_code in (400, 409, 422)
    assert "error" in response.json()


def test_renewal_extends_the_due_date(
    client: TestClient, librarian_token: str, student_user: User
) -> None:
    _, copy_ids = seed_book_with_copies(client, librarian_token, copies=1, isbn="978-6666666666")
    loan = issue(client, librarian_token, student_user.id, copy_ids[0])
    original_due = loan["due_at"]

    renewed = client.post(
        f"/api/loans/{loan['id']}/renew", headers=auth_headers(librarian_token)
    )
    assert renewed.status_code == 200, renewed.text
    body = renewed.json()
    assert body["renewal_count"] == 1
    assert body["due_at"] > original_due


def test_members_can_renew_their_own_loans_only(
    client: TestClient, librarian_token: str, student_user: User, db: Session
) -> None:
    other = make_user(
        db, email="other@test.edu", role="STUDENT", institutional_id="STU-002"
    )
    _, copy_ids = seed_book_with_copies(client, librarian_token, copies=1, isbn="978-7777777777")
    loan = issue(client, librarian_token, student_user.id, copy_ids[0])

    other_token = client.post(
        "/api/auth/login",
        json={"identifier": other.email, "password": "Password@123"},
    ).json()["access_token"]

    response = client.post(
        f"/api/loans/{loan['id']}/renew", headers=auth_headers(other_token)
    )
    assert response.status_code == 403


def test_overdue_loan_gets_a_fine_on_return(
    client: TestClient, librarian_token: str, student_user: User, db: Session
) -> None:
    _, copy_ids = seed_book_with_copies(client, librarian_token, copies=1, isbn="978-8888888888")
    loan = issue(client, librarian_token, student_user.id, copy_ids[0])

    
    db.expire_all()
    stored = db.get(Loan, loan["id"])
    assert stored is not None
    stored.due_at = utcnow() - timedelta(days=10)
    db.commit()

    returned = client.post(
        f"/api/loans/{loan['id']}/return", headers=auth_headers(librarian_token)
    )
    assert returned.status_code == 200, returned.text
    body = returned.json()
    assert body["fine_amount"] is not None
    assert float(body["fine_amount"]) > 0

    db.expire_all()
    loans = db.get(Loan, loan["id"])
    assert loans is not None
    assert loans.fine_id is not None


def test_members_only_see_their_own_loans(
    client: TestClient, librarian_token: str, student_user: User, db: Session
) -> None:
    other = make_user(
        db, email="other2@test.edu", role="STUDENT", institutional_id="STU-003"
    )
    _, copy_ids = seed_book_with_copies(client, librarian_token, copies=1, isbn="978-9999999999")
    loan = issue(client, librarian_token, other.id, copy_ids[0])

    student_token = client.post(
        "/api/auth/login",
        json={"identifier": student_user.email, "password": "Password@123"},
    ).json()["access_token"]

    listing = client.get("/api/loans", headers=auth_headers(student_token)).json()
    assert all(item["member_id"] == student_user.id for item in listing["items"])

    detail = client.get(
        f"/api/loans/{loan['id']}", headers=auth_headers(student_token)
    )
    assert detail.status_code == 403


def test_overdue_listing(client: TestClient, librarian_token: str, student_user: User, db: Session) -> None:
    _, copy_ids = seed_book_with_copies(client, librarian_token, copies=1, isbn="978-1212121212")
    loan = issue(client, librarian_token, student_user.id, copy_ids[0])

    db.expire_all()
    stored = db.get(Loan, loan["id"])
    assert stored is not None
    stored.due_at = utcnow() - timedelta(days=5)
    db.commit()

    overdue = client.get("/api/loans/overdue", headers=auth_headers(librarian_token))
    assert overdue.status_code == 200
    assert overdue.json()["pagination"]["total"] >= 1
