

from __future__ import annotations

import io

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.catalogue import Book, BookCopy
from app.models.enums import BookCopyStatus
from tests.conftest import auth_headers


def create_book(
    client: TestClient,
    token: str,
    *,
    title: str = "Clean Code",
    isbn: str = "978-0132350884",
) -> dict:
    response = client.post(
        "/api/books",
        headers=auth_headers(token),
        json={
            "title": title,
            "isbn": isbn,
            "author_names": ["Robert C. Martin"],
            "publisher_name": "Prentice Hall",
            "category_name": "Software Engineering",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def add_copy(
    client: TestClient,
    token: str,
    book_id: int,
    accession_number: str,
    **extra,
) -> dict:
    payload = {"accession_number": accession_number, "shelf_location": "A-1"}
    payload.update(extra)
    response = client.post(
        f"/api/books/{book_id}/copies", headers=auth_headers(token), json=payload
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_book_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/books", json={"title": "Nope"})
    assert response.status_code == 401


def test_student_cannot_create_a_book(client: TestClient, student_token: str) -> None:
    response = client.post(
        "/api/books", headers=auth_headers(student_token), json={"title": "Nope"}
    )
    assert response.status_code == 403


def test_librarian_can_create_a_book(client: TestClient, librarian_token: str) -> None:
    body = create_book(client, librarian_token)
    assert body["title"] == "Clean Code"
    assert body["total_copies"] == 0
    assert body["authors"] == ["Robert C. Martin"]
    assert body["publisher_name"] == "Prentice Hall"
    assert body["category_name"] == "Software Engineering"


def test_book_detail_and_search(client: TestClient, librarian_token: str) -> None:
    created = create_book(client, librarian_token)

    detail = client.get(
        f"/api/books/{created['id']}", headers=auth_headers(librarian_token)
    )
    assert detail.status_code == 200
    assert detail.json()["isbn"] == "978-0132350884"

    search = client.get(
        "/api/books", headers=auth_headers(librarian_token), params={"search": "Clean"}
    )
    assert search.status_code == 200
    body = search.json()
    assert body["pagination"]["total"] >= 1
    assert any(item["id"] == created["id"] for item in body["items"])


def test_duplicate_isbn_is_rejected(client: TestClient, librarian_token: str) -> None:
    create_book(client, librarian_token)
    duplicate = client.post(
        "/api/books",
        headers=auth_headers(librarian_token),
        json={"title": "Another Book", "isbn": "978-0132350884"},
    )
    assert duplicate.status_code in (400, 409)


def test_copies_can_be_added_and_listed(client: TestClient, librarian_token: str) -> None:
    created = create_book(client, librarian_token)
    copy = add_copy(client, librarian_token, created["id"], "ACC-0001")
    assert copy["status"] == BookCopyStatus.AVAILABLE.value
    assert copy["accession_number"] == "ACC-0001"

    copies = client.get(
        f"/api/books/{created['id']}/copies", headers=auth_headers(librarian_token)
    )
    assert copies.status_code == 200
    body = copies.json()
    assert body["pagination"]["total"] == 1
    assert body["items"][0]["accession_number"] == "ACC-0001"

    
    detail = client.get(
        f"/api/books/{created['id']}", headers=auth_headers(librarian_token)
    ).json()
    assert detail["total_copies"] == 1
    assert detail["available_copies"] == 1


def test_duplicate_accession_number_is_rejected(
    client: TestClient, librarian_token: str
) -> None:
    created = create_book(client, librarian_token)
    add_copy(client, librarian_token, created["id"], "ACC-0001")
    duplicate = client.post(
        f"/api/books/{created['id']}/copies",
        headers=auth_headers(librarian_token),
        json={"accession_number": "ACC-0001"},
    )
    assert duplicate.status_code in (400, 409)


def test_deleting_a_book_retires_it_and_its_copies(
    client: TestClient, librarian_token: str, db: Session
) -> None:
    created = create_book(client, librarian_token)
    add_copy(client, librarian_token, created["id"], "ACC-0002")

    response = client.delete(
        f"/api/books/{created['id']}", headers=auth_headers(librarian_token)
    )
    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False

    db.expire_all()
    book = db.get(Book, created["id"])
    assert book is not None
    assert book.is_active is False

    copies = db.query(BookCopy).filter(BookCopy.book_id == created["id"]).all()
    assert copies
    assert all(copy.status == BookCopyStatus.RETIRED for copy in copies)


def test_copy_status_can_be_changed(
    client: TestClient, librarian_token: str, db: Session
) -> None:
    created = create_book(client, librarian_token)
    copy = add_copy(client, librarian_token, created["id"], "ACC-0003")

    response = client.patch(
        f"/api/copies/{copy['id']}/status",
        headers=auth_headers(librarian_token),
        json={"status": "DAMAGED", "reason": "Spine broken"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == BookCopyStatus.DAMAGED.value

    db.expire_all()
    stored = db.get(BookCopy, copy["id"])
    assert stored is not None
    assert stored.status == BookCopyStatus.DAMAGED


def test_csv_export_of_the_catalogue(client: TestClient, librarian_token: str) -> None:
    create_book(client, librarian_token, title="Exported Book", isbn="978-0000000001")
    response = client.get("/api/books/export/csv", headers=auth_headers(librarian_token))
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    body = response.text
    assert "Exported Book" in body
    assert "978-0000000001" in body


def test_csv_import_creates_books(client: TestClient, librarian_token: str) -> None:
    csv_payload = (
        "title,isbn,publisher_name,category_name,author_names\n"
        "Imported Book,978-0000000002,Acme Press,Computing,\"Ada Lovelace,Alan Turing\"\n"
    )
    response = client.post(
        "/api/books/import",
        headers=auth_headers(librarian_token),
        files={"file": ("books.csv", io.BytesIO(csv_payload.encode()), "text/csv")},
    )
    assert response.status_code in (200, 201), response.text
    assert response.json()["created"] == 1

    search = client.get(
        "/api/books",
        headers=auth_headers(librarian_token),
        params={"search": "Imported Book"},
    )
    assert search.json()["pagination"]["total"] == 1


def test_csv_import_preview_does_not_write(
    client: TestClient, librarian_token: str
) -> None:
    csv_payload = (
        "title,isbn,publisher_name,category_name,author_names\n"
        "Preview Only,978-0000000003,Acme Press,Computing,Ada Lovelace\n"
    )
    response = client.post(
        "/api/books/import/preview",
        headers=auth_headers(librarian_token),
        files={"file": ("books.csv", io.BytesIO(csv_payload.encode()), "text/csv")},
    )
    assert response.status_code == 200, response.text

    search = client.get(
        "/api/books",
        headers=auth_headers(librarian_token),
        params={"search": "Preview Only"},
    )
    assert search.json()["pagination"]["total"] == 0


def test_students_can_browse_the_catalogue(client: TestClient, student_token: str) -> None:
    response = client.get("/api/books", headers=auth_headers(student_token))
    assert response.status_code == 200
    assert "items" in response.json()
