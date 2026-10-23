

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.circulation import Fine, Loan, Reservation
from app.models.enums import FineStatus, ReservationStatus
from app.models.user import User
from app.utils.helpers import utcnow
from tests.conftest import auth_headers, login, make_user


def seed_book_with_copies(
    client: TestClient, token: str, *, copies: int = 2, isbn: str = "978-3333333333"
) -> tuple[int, list[int]]:
    book = client.post(
        "/api/books",
        headers=auth_headers(token),
        json={"title": "Reservation Test Book", "isbn": isbn},
    ).json()
    copy_ids: list[int] = []
    for index in range(copies):
        copy = client.post(
            f"/api/books/{book['id']}/copies",
            headers=auth_headers(token),
            json={"accession_number": f"ACC-RES-{isbn[-4:]}-{index}"},
        )
        assert copy.status_code == 201, copy.text
        copy_ids.append(copy.json()["id"])
    return book["id"], copy_ids


def token_for(client: TestClient, user: User) -> str:
    return login(client, user.email)["access_token"]





def test_member_can_reserve_a_book(
    client: TestClient, librarian_token: str, student_user: User
) -> None:
    book_id, _ = seed_book_with_copies(client, librarian_token, copies=1, isbn="978-4100000001")

    student_token = token_for(client, student_user)
    response = client.post(
        "/api/reservations",
        headers=auth_headers(student_token),
        json={"book_id": book_id},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == ReservationStatus.ACTIVE.value
    assert body["book_id"] == book_id
    assert body["member_id"] == student_user.id


def test_duplicate_active_reservation_is_rejected(
    client: TestClient, librarian_token: str, student_user: User
) -> None:
    book_id, _ = seed_book_with_copies(client, librarian_token, copies=1, isbn="978-4100000002")
    student_token = token_for(client, student_user)

    first = client.post(
        "/api/reservations", headers=auth_headers(student_token), json={"book_id": book_id}
    )
    assert first.status_code == 201

    second = client.post(
        "/api/reservations", headers=auth_headers(student_token), json={"book_id": book_id}
    )
    assert second.status_code in (400, 409, 422)


def test_reservation_queue_is_fifo(
    client: TestClient, librarian_token: str, db: Session
) -> None:
    book_id, _ = seed_book_with_copies(client, librarian_token, copies=1, isbn="978-4100000003")
    first_user = make_user(db, email="queue1@test.edu", role="STUDENT", institutional_id="Q1")
    second_user = make_user(db, email="queue2@test.edu", role="STUDENT", institutional_id="Q2")

    for user in (first_user, second_user):
        response = client.post(
            "/api/reservations",
            headers=auth_headers(token_for(client, user)),
            json={"book_id": book_id},
        )
        assert response.status_code == 201, response.text

    reservations = (
        db.query(Reservation)
        .filter(Reservation.book_id == book_id)
        .order_by(Reservation.reserved_at, Reservation.id)
        .all()
    )
    assert len(reservations) == 2
    assert reservations[0].member_id == first_user.id
    assert reservations[1].member_id == second_user.id


def test_cancelling_a_reservation(
    client: TestClient, librarian_token: str, student_user: User, db: Session
) -> None:
    book_id, _ = seed_book_with_copies(client, librarian_token, copies=1, isbn="978-4100000004")
    student_token = token_for(client, student_user)
    created = client.post(
        "/api/reservations",
        headers=auth_headers(student_token),
        json={"book_id": book_id},
    ).json()

    response = client.post(
        f"/api/reservations/{created['id']}/cancel",
        headers=auth_headers(student_token),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == ReservationStatus.CANCELLED.value

    db.expire_all()
    stored = db.get(Reservation, created["id"])
    assert stored is not None
    assert stored.status == ReservationStatus.CANCELLED


def test_members_only_see_their_own_reservations(
    client: TestClient, librarian_token: str, db: Session
) -> None:
    book_id, _ = seed_book_with_copies(client, librarian_token, copies=1, isbn="978-4100000005")
    owner = make_user(db, email="owner@test.edu", role="STUDENT", institutional_id="Q3")
    other = make_user(db, email="other@test.edu", role="STUDENT", institutional_id="Q4")

    created = client.post(
        "/api/reservations",
        headers=auth_headers(token_for(client, owner)),
        json={"book_id": book_id},
    ).json()

    other_token = token_for(client, other)
    listing = client.get("/api/reservations", headers=auth_headers(other_token)).json()
    assert all(item["member_id"] == other.id for item in listing["items"])

    detail = client.get(
        f"/api/reservations/{created['id']}", headers=auth_headers(other_token)
    )
    assert detail.status_code == 403





def assess_fine(
    client: TestClient,
    librarian_token: str,
    member: User,
    db: Session,
    *,
    days_overdue: int = 10,
) -> Fine:
    
    book = client.post(
        "/api/books",
        headers=auth_headers(librarian_token),
        json={
            "title": f"Fine Book {member.id}",
            "isbn": f"978-42{member.id:07d}",
        },
    ).json()
    copy = client.post(
        f"/api/books/{book['id']}/copies",
        headers=auth_headers(librarian_token),
        json={"accession_number": f"ACC-FINE-{member.id}"},
    ).json()

    loan = client.post(
        "/api/loans/issue",
        headers=auth_headers(librarian_token),
        json={"member_id": member.id, "copy_id": copy["id"]},
    ).json()

    db.expire_all()
    stored = db.get(Loan, loan["id"])
    assert stored is not None
    stored.due_at = utcnow() - timedelta(days=days_overdue)
    db.commit()

    returned = client.post(
        f"/api/loans/{loan['id']}/return", headers=auth_headers(librarian_token)
    )
    assert returned.status_code == 200, returned.text

    db.expire_all()
    fine = db.query(Fine).filter(Fine.member_id == member.id).one()
    return fine


def test_overdue_return_assesses_a_fine(
    client: TestClient, librarian_token: str, db: Session
) -> None:
    member = make_user(db, email="finee@test.edu", role="STUDENT", institutional_id="FIN-1")
    fine = assess_fine(client, librarian_token, member, db)

    assert fine.amount > 0
    assert fine.status == FineStatus.PENDING.value
    assert fine.days_overdue >= 10


def test_fine_can_be_paid_partially_and_fully(
    client: TestClient, librarian_token: str, db: Session
) -> None:
    member = make_user(db, email="payer@test.edu", role="STUDENT", institutional_id="FIN-2")
    fine = assess_fine(client, librarian_token, member, db)

    payment = client.post(
        f"/api/fines/{fine.id}/payments",
        headers=auth_headers(librarian_token),
        json={"amount": "20.00", "method": "CASH"},
    )
    assert payment.status_code == 201, payment.text

    detail = client.get(
        f"/api/fines/{fine.id}", headers=auth_headers(librarian_token)
    ).json()
    assert float(detail["amount_paid"]) == 20.0
    assert float(detail["outstanding"]) == float(detail["amount"]) - 20.0
    assert detail["status"] == FineStatus.PARTIALLY_PAID.value

    
    remainder = float(detail["outstanding"])
    settle = client.post(
        f"/api/fines/{fine.id}/payments",
        headers=auth_headers(librarian_token),
        json={"amount": f"{remainder:.2f}", "method": "UPI"},
    )
    assert settle.status_code == 201, settle.text
    assert settle.json()["status"] == FineStatus.PAID.value
    assert float(settle.json()["outstanding"]) == 0.0


def test_fine_can_be_waived(
    client: TestClient, librarian_token: str, db: Session
) -> None:
    member = make_user(db, email="waive@test.edu", role="STUDENT", institutional_id="FIN-3")
    fine = assess_fine(client, librarian_token, member, db)

    response = client.post(
        f"/api/fines/{fine.id}/adjust",
        headers=auth_headers(librarian_token),
        json={"waive": True, "reason": "First offence - goodwill waiver"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == FineStatus.WAIVED.value
    assert float(response.json()["outstanding"]) == 0.0


def test_overpayment_is_rejected(
    client: TestClient, librarian_token: str, db: Session
) -> None:
    member = make_user(db, email="overpay@test.edu", role="STUDENT", institutional_id="FIN-4")
    fine = assess_fine(client, librarian_token, member, db)

    response = client.post(
        f"/api/fines/{fine.id}/payments",
        headers=auth_headers(librarian_token),
        json={"amount": "9999.00", "method": "CASH"},
    )
    assert response.status_code in (400, 409, 422)


def test_students_cannot_manage_fines(
    client: TestClient, librarian_token: str, student_token: str, db: Session
) -> None:
    member = make_user(db, email="nostudent@test.edu", role="STUDENT", institutional_id="FIN-5")
    fine = assess_fine(client, librarian_token, member, db)

    response = client.post(
        f"/api/fines/{fine.id}/payments",
        headers=auth_headers(student_token),
        json={"amount": "1.00", "method": "CASH"},
    )
    assert response.status_code == 403
