

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Iterable, Optional

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.catalogue import Author, Book, BookAuthor, BookCopy, Category, Publisher
from app.models.circulation import Loan, Reservation
from app.models.enums import AuditAction, BookCopyStatus, CopyCondition
from app.models.member import Department
from app.models.user import User
from app.schemas.book import BookCopyCreate, BookCreate, BookUpdate, CopyStatusUpdate
from app.services.audit_service import log_action





def get_book(session: Session, book_id: int) -> Book:
    book = session.execute(
        select(Book)
        .where(Book.id == book_id)
        .options(
            selectinload(Book.authors),
            selectinload(Book.publisher),
            selectinload(Book.category),
        )
    ).scalar_one_or_none()
    if book is None:
        raise NotFoundError("Book not found.")
    return book


def get_copy(session: Session, copy_id: int, *, for_update: bool = False) -> BookCopy:
    stmt = select(BookCopy).where(BookCopy.id == copy_id)
    if for_update:
        stmt = stmt.with_for_update()
    copy = session.execute(stmt).scalar_one_or_none()
    if copy is None:
        raise NotFoundError("Book copy not found.")
    return copy


def _resolve_publisher(
    session: Session, publisher_id: int | None, publisher_name: str | None
) -> int | None:
    if publisher_id is not None:
        if session.get(Publisher, publisher_id) is None:
            raise ValidationError(f"Publisher {publisher_id} does not exist.")
        return publisher_id
    if publisher_name:
        publisher = session.execute(
            select(Publisher).where(Publisher.name == publisher_name.strip())
        ).scalar_one_or_none()
        if publisher is None:
            publisher = Publisher(name=publisher_name.strip())
            session.add(publisher)
            session.flush()
        return publisher.id
    return None


def _resolve_category(
    session: Session, category_id: int | None, category_name: str | None
) -> int | None:
    if category_id is not None:
        if session.get(Category, category_id) is None:
            raise ValidationError(f"Category {category_id} does not exist.")
        return category_id
    if category_name:
        name = category_name.strip()
        category = session.execute(
            select(Category).where(Category.name == name)
        ).scalar_one_or_none()
        if category is None:
            category = Category(name=name)
            session.add(category)
            session.flush()
        return category.id
    return None


def _resolve_authors(
    session: Session, names: list[str], ids: list[int]
) -> list[int]:
    author_ids: list[int] = []
    for author_id in ids:
        if session.get(Author, author_id) is None:
            raise ValidationError(f"Author {author_id} does not exist.")
        author_ids.append(author_id)
    for name in names:
        clean = name.strip()
        if not clean:
            continue
        author = session.execute(
            select(Author).where(Author.name == clean)
        ).scalar_one_or_none()
        if author is None:
            author = Author(name=clean)
            session.add(author)
            session.flush()
        if author.id not in author_ids:
            author_ids.append(author.id)
    return author_ids





def create_book(
    session: Session, payload: BookCreate, actor: User | None = None
) -> Book:
    if payload.isbn:
        existing = session.execute(
            select(Book).where(Book.isbn == payload.isbn.strip())
        ).scalar_one_or_none()
        if existing is not None:
            raise ConflictError(f"A book with ISBN {payload.isbn} already exists.")

    book = Book(
        title=payload.title.strip(),
        subtitle=payload.subtitle,
        isbn=(payload.isbn or None),
        isbn_10=(payload.isbn_10 or None),
        publisher_id=_resolve_publisher(session, payload.publisher_id, payload.publisher_name),
        category_id=_resolve_category(session, payload.category_id, payload.category_name),
        edition=payload.edition,
        publication_year=payload.publication_year,
        language=payload.language or "English",
        description=payload.description,
        keywords=payload.keywords,
        subjects=payload.subjects,
        cover_image_url=payload.cover_image_url,
        department_id=payload.department_id,
        shelf_location=payload.shelf_location,
        rack_number=payload.rack_number,
        is_reference_only=payload.is_reference_only,
        created_by_id=actor.id if actor else None,
    )
    session.add(book)
    session.flush()

    author_ids = _resolve_authors(session, payload.author_names, payload.author_ids)
    for order, author_id in enumerate(author_ids):
        session.add(BookAuthor(book_id=book.id, author_id=author_id, author_order=order))

    log_action(
        session,
        AuditAction.BOOK_CREATED,
        actor=actor,
        entity_type="book",
        entity_id=book.id,
        summary=f"Created book '{book.title}'",
    )
    session.flush()
    return get_book(session, book.id)


def update_book(
    session: Session, book_id: int, payload: BookUpdate, actor: User | None = None
) -> Book:
    book = get_book(session, book_id)
    data = payload.model_dump(exclude_unset=True, exclude={"author_names", "author_ids"})

    if "isbn" in data and data["isbn"]:
        clash = session.execute(
            select(Book).where(Book.isbn == data["isbn"].strip(), Book.id != book.id)
        ).scalar_one_or_none()
        if clash is not None:
            raise ConflictError(f"A book with ISBN {data['isbn']} already exists.")

    if "publisher_id" in data or "publisher_name" in data:
        data["publisher_id"] = _resolve_publisher(
            session, data.get("publisher_id"), data.get("publisher_name")
        )
    if "category_id" in data or "category_name" in data:
        data["category_id"] = _resolve_category(
            session, data.get("category_id"), data.get("category_name")
        )

    for key, value in data.items():
        if hasattr(book, key):
            setattr(book, key, value)

    if payload.author_names is not None or payload.author_ids is not None:
        author_ids = _resolve_authors(
            session, payload.author_names or [], payload.author_ids or []
        )
        session.query(BookAuthor).filter(BookAuthor.book_id == book.id).delete()
        for order, author_id in enumerate(author_ids):
            session.add(BookAuthor(book_id=book.id, author_id=author_id, author_order=order))

    log_action(
        session,
        AuditAction.BOOK_UPDATED,
        actor=actor,
        entity_type="book",
        entity_id=book.id,
        summary=f"Updated book '{book.title}'",
    )
    session.flush()
    return get_book(session, book.id)


def retire_book(session: Session, book_id: int, actor: User | None = None) -> Book:
    
    book = get_book(session, book_id)

    copies = list(session.execute(select(BookCopy).where(BookCopy.book_id == book_id)).scalars())
    copy_ids = [copy.id for copy in copies]
    active_loans = 0
    if copy_ids:
        active_loans = session.execute(
            select(func.count(Loan.id)).where(
                Loan.copy_id.in_(copy_ids), Loan.status.in_(["ACTIVE", "OVERDUE"])
            )
        ).scalar_one()

    for copy in copies:
        if copy.status in (BookCopyStatus.ISSUED, BookCopyStatus.RESERVED):
            active_loans += 1

    if active_loans:
        raise ConflictError(
            "This book cannot be retired while copies are issued or reserved."
        )

    book.is_active = False
    for copy in copies:
        if copy.status not in (BookCopyStatus.LOST, BookCopyStatus.DAMAGED):
            copy.status = BookCopyStatus.RETIRED
            copy.status_changed_at = datetime.now(timezone.utc)
    recalculate_availability(session, book)
    log_action(
        session,
        AuditAction.BOOK_RETIRED,
        actor=actor,
        entity_type="book",
        entity_id=book.id,
        summary=f"Retired book '{book.title}'",
    )
    session.flush()
    return book


def recalculate_availability(session: Session, book: Book) -> None:
    
    counts = dict(
        session.execute(
            select(BookCopy.status, func.count(BookCopy.id))
            .where(BookCopy.book_id == book.id)
            .group_by(BookCopy.status)
        ).all()
    )
    book.total_copies = sum(counts.values())
    book.available_copies = counts.get(BookCopyStatus.AVAILABLE, 0)
    session.flush()





def create_copy(
    session: Session,
    book_id: int,
    payload: BookCopyCreate,
    actor: User | None = None,
) -> BookCopy:
    book = get_book(session, book_id)
    accession = payload.accession_number.strip()
    if session.execute(
        select(BookCopy.id).where(BookCopy.accession_number == accession)
    ).first():
        raise ConflictError(f"Accession number '{accession}' is already in use.")
    if payload.barcode:
        if session.execute(
            select(BookCopy.id).where(BookCopy.barcode == payload.barcode.strip())
        ).first():
            raise ConflictError(f"Barcode '{payload.barcode}' is already in use.")

    copy = BookCopy(
        book_id=book.id,
        accession_number=accession,
        barcode=(payload.barcode.strip() if payload.barcode else None),
        status=BookCopyStatus.AVAILABLE,
        condition=payload.condition,
        acquisition_date=payload.acquisition_date,
        price=payload.price,
        shelf_location=payload.shelf_location or book.shelf_location,
        rack_number=payload.rack_number or book.rack_number,
        notes=payload.notes,
    )
    session.add(copy)
    session.flush()
    recalculate_availability(session, book)
    log_action(
        session,
        AuditAction.COPY_CREATED,
        actor=actor,
        entity_type="book_copy",
        entity_id=copy.id,
        summary=f"Added copy {accession} of '{book.title}'",
    )
    session.flush()
    return copy


def update_copy_status(
    session: Session,
    copy_id: int,
    payload: CopyStatusUpdate,
    actor: User | None = None,
) -> BookCopy:
    
    copy = get_copy(session, copy_id, for_update=True)
    new_status = payload.status

    if new_status == copy.status:
        return copy

    if new_status in (BookCopyStatus.AVAILABLE, BookCopyStatus.ISSUED):
        raise ValidationError(
            "AVAILABLE and ISSUED statuses are managed by the circulation workflow."
        )
    if copy.status == BookCopyStatus.ISSUED:
        raise ConflictError("This copy is currently issued. Process a return first.")

    previous = copy.status
    copy.status = new_status
    copy.status_changed_at = datetime.now(timezone.utc)
    copy.status_changed_by_id = actor.id if actor else None

    from app.models.circulation import InventoryAdjustment

    session.add(
        InventoryAdjustment(
            copy_id=copy.id,
            previous_status=previous.value,
            new_status=new_status.value,
            reason=payload.reason,
            changed_by_id=actor.id if actor else None,
        )
    )
    recalculate_availability(session, session.get(Book, copy.book_id))
    log_action(
        session,
        AuditAction.COPY_STATUS_CHANGED,
        actor=actor,
        entity_type="book_copy",
        entity_id=copy.id,
        summary=f"Copy {copy.accession_number}: {previous.value} -> {new_status.value}",
    )
    session.flush()
    return copy





def search_books(session: Session, params: dict[str, Any]) -> tuple[list[Book], int]:
    
    stmt: Select = (
        select(Book)
        .options(selectinload(Book.authors), selectinload(Book.publisher), selectinload(Book.category))
    )

    if not params.get("include_inactive"):
        stmt = stmt.where(Book.is_active.is_(True))

    search = (params.get("search") or "").strip()
    if search:
        pattern = f"%{search}%"
        sub = select(BookAuthor.book_id).join(Author, Author.id == BookAuthor.author_id).where(
            Author.name.like(pattern)
        )
        stmt = stmt.where(
            or_(
                Book.title.like(pattern),
                Book.subtitle.like(pattern),
                Book.isbn.like(pattern),
                Book.isbn_10.like(pattern),
                Book.keywords.like(pattern),
                Book.subjects.like(pattern),
                Book.description.like(pattern),
                Book.id.in_(sub),
            )
        )

    if params.get("category_id"):
        stmt = stmt.where(Book.category_id == params["category_id"])
    if params.get("publisher_id"):
        stmt = stmt.where(Book.publisher_id == params["publisher_id"])
    if params.get("department_id"):
        stmt = stmt.where(Book.department_id == params["department_id"])
    if params.get("language"):
        stmt = stmt.where(Book.language == params["language"])

    if params.get("available_only"):
        stmt = stmt.where(Book.available_copies > 0)

    sort_by = (params.get("sort_by") or "title").lower()
    sort_order = (params.get("sort_order") or "asc").lower()
    sort_columns = {
        "title": Book.title,
        "publication_year": Book.publication_year,
        "available_copies": Book.available_copies,
        "total_copies": Book.total_copies,
        "created_at": Book.created_at,
        "popularity": Book.available_copies,
    }
    column = sort_columns.get(sort_by, Book.title)
    stmt = stmt.order_by(column.desc() if sort_order == "desc" else column.asc(), Book.id.asc())

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = session.execute(count_stmt).scalar_one()

    page = params.get("page", 1)
    page_size = params.get("page_size", 20)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    books = list(session.execute(stmt).scalars().unique())
    return books, total


def search_copies(session: Session, params: dict[str, Any]) -> tuple[list[BookCopy], int]:
    stmt = select(BookCopy).options(selectinload(BookCopy.book))
    if params.get("accession_number"):
        stmt = stmt.where(BookCopy.accession_number.like(f"%{params['accession_number']}%"))
    if params.get("barcode"):
        stmt = stmt.where(BookCopy.barcode == params["barcode"])
    if params.get("book_id"):
        stmt = stmt.where(BookCopy.book_id == params["book_id"])
    if params.get("status"):
        stmt = stmt.where(BookCopy.status == params["status"])
    if params.get("search"):
        pattern = f"%{params['search']}%"
        sub = select(Book.id).where(Book.title.like(pattern) | Book.isbn.like(pattern))
        stmt = stmt.where(
            or_(
                BookCopy.accession_number.like(pattern),
                BookCopy.barcode.like(pattern),
                BookCopy.book_id.in_(sub),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = session.execute(count_stmt).scalar_one()
    page = params.get("page", 1)
    page_size = params.get("page_size", 20)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    return list(session.execute(stmt).scalars().unique()), total





BOOK_IMPORT_COLUMNS = [
    "title",
    "isbn",
    "author_names",
    "publisher_name",
    "category_name",
    "edition",
    "publication_year",
    "language",
    "description",
    "shelf_location",
    "rack_number",
    "department_code",
    "copies",
    "accession_prefix",
    "price",
]


def _split_multi(value: str) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.replace(";", "|").split(",") if part.strip()]


def preview_book_import(session: Session, content: str) -> dict[str, Any]:
    
    reader = csv.DictReader(io.StringIO(content))
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for index, raw in enumerate(reader, start=2):
        title = (raw.get("title") or "").strip()
        row_errors: list[str] = []
        if not title:
            row_errors.append("Title is required.")
        isbn = (raw.get("isbn") or "").strip()
        duplicate = False
        if isbn:
            existing = session.execute(
                select(Book.id).where(Book.isbn == isbn)
            ).first()
            duplicate = existing is not None
            if duplicate:
                row_errors.append("ISBN already exists in the catalogue.")
        year_raw = (raw.get("publication_year") or "").strip()
        if year_raw:
            try:
                year = int(year_raw)
                if year < 1000 or year > 2200:
                    row_errors.append("publication_year is out of range.")
            except ValueError:
                row_errors.append("publication_year must be a number.")
        copies_raw = (raw.get("copies") or "1").strip()
        try:
            if int(copies_raw) < 1:
                row_errors.append("copies must be >= 1.")
        except ValueError:
            row_errors.append("copies must be a number.")

        rows.append(
            {
                "row_number": index,
                "data": {k: (v or "").strip() for k, v in raw.items()},
                "errors": row_errors,
                "duplicate": duplicate,
            }
        )
        if row_errors:
            errors.append({"row_number": index, "errors": row_errors})

    return {
        "total_rows": len(rows),
        "valid_rows": sum(1 for r in rows if not r["errors"]),
        "rows": rows,
        "errors": errors,
    }


def import_books_from_csv(
    session: Session, content: str, actor: User | None = None, *, update_existing: bool = False
) -> dict[str, Any]:
    
    preview = preview_book_import(session, content)
    created = 0
    updated = 0
    skipped = 0
    failed = 0
    errors: list[dict[str, Any]] = []
    created_ids: list[int] = []

    reader = csv.DictReader(io.StringIO(content))
    for index, raw in enumerate(reader, start=2):
        row = next((r for r in preview["rows"] if r["row_number"] == index), None)
        if row is None:
            continue
        if row["errors"] and not (update_existing and row["duplicate"]):
            failed += 1
            errors.append({"row_number": index, "errors": row["errors"]})
            continue

        data = row["data"]
        isbn = data.get("isbn") or None
        existing = None
        if isbn:
            existing = session.execute(
                select(Book).where(Book.isbn == isbn)
            ).scalar_one_or_none()

        department_id = None
        dept_code = data.get("department_code")
        if dept_code:
            dept = session.execute(
                select(Department).where(Department.code == dept_code)
            ).scalar_one_or_none()
            if dept is None:
                failed += 1
                errors.append(
                    {"row_number": index, "errors": [f"Unknown department code '{dept_code}'."]}
                )
                continue
            department_id = dept.id

        if existing is not None:
            if not update_existing:
                skipped += 1
                continue
            existing.title = data.get("title") or existing.title
            existing.edition = data.get("edition") or existing.edition
            existing.shelf_location = data.get("shelf_location") or existing.shelf_location
            existing.rack_number = data.get("rack_number") or existing.rack_number
            existing.language = data.get("language") or existing.language
            existing.department_id = department_id or existing.department_id
            session.flush()
            updated += 1
            book = existing
        else:
            price = data.get("price") or None
            book = Book(
                title=data["title"],
                isbn=isbn,
                edition=data.get("edition") or None,
                publication_year=int(data["publication_year"]) if data.get("publication_year") else None,
                language=data.get("language") or "English",
                description=data.get("description") or None,
                shelf_location=data.get("shelf_location") or None,
                rack_number=data.get("rack_number") or None,
                department_id=department_id,
                publisher_id=_resolve_publisher(session, None, data.get("publisher_name")),
                category_id=_resolve_category(session, None, data.get("category_name")),
            )
            session.add(book)
            session.flush()
            author_ids = _resolve_authors(session, _split_multi(data.get("author_names", "")), [])
            for order, author_id in enumerate(author_ids):
                session.add(BookAuthor(book_id=book.id, author_id=author_id, author_order=order))
            session.flush()
            created += 1
            created_ids.append(book.id)

        copies = int(data.get("copies") or 1)
        prefix = (data.get("accession_prefix") or "").strip()
        existing_accessions = {
            acc
            for (acc,) in session.execute(
                select(BookCopy.accession_number).where(BookCopy.book_id == book.id)
            ).all()
        }
        for copy_index in range(1, copies + 1):
            accession = f"{prefix}-{copy_index:03d}" if prefix else f"{book.id}-{copy_index:03d}"
            if accession in existing_accessions:
                continue
            session.add(
                BookCopy(
                    book_id=book.id,
                    accession_number=accession,
                    shelf_location=book.shelf_location,
                    rack_number=book.rack_number,
                )
            )
        session.flush()
        recalculate_availability(session, book)

    log_action(
        session,
        AuditAction.CSV_IMPORT,
        actor=actor,
        entity_type="book",
        summary=f"Imported books from CSV: {created} created, {updated} updated, {failed} failed",
        metadata={"created": created, "updated": updated, "failed": failed},
    )
    session.flush()
    return {
        "total_rows": preview["total_rows"],
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
        "created_ids": created_ids,
    }


def export_books_csv(session: Session, book_ids: Iterable[int] | None = None) -> str:
    
    stmt = select(Book).options(selectinload(Book.authors), selectinload(Book.publisher), selectinload(Book.category))
    if book_ids:
        stmt = stmt.where(Book.id.in_(list(book_ids)))
    books = list(session.execute(stmt.order_by(Book.id)).scalars().unique())

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "title",
            "isbn",
            "authors",
            "publisher",
            "category",
            "edition",
            "publication_year",
            "language",
            "shelf_location",
            "total_copies",
            "available_copies",
        ]
    )
    for book in books:
        writer.writerow(
            [
                book.id,
                book.title,
                book.isbn or "",
                "; ".join(author.name for author in book.authors),
                book.publisher.name if book.publisher else "",
                book.category.name if book.category else "",
                book.edition or "",
                book.publication_year or "",
                book.language,
                book.shelf_location or "",
                book.total_copies,
                book.available_copies,
            ]
        )
    return buffer.getvalue()


def export_copies_csv(session: Session, copy_ids: Iterable[int] | None = None) -> str:
    stmt = select(BookCopy).options(selectinload(BookCopy.book))
    if copy_ids:
        stmt = stmt.where(BookCopy.id.in_(list(copy_ids)))
    copies = list(session.execute(stmt.order_by(BookCopy.id)).scalars().unique())

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "copy_id",
            "accession_number",
            "barcode",
            "book_id",
            "title",
            "status",
            "condition",
            "acquisition_date",
            "price",
            "shelf_location",
            "rack_number",
        ]
    )
    for copy in copies:
        writer.writerow(
            [
                copy.id,
                copy.accession_number,
                copy.barcode or "",
                copy.book_id,
                copy.book.title if copy.book else "",
                copy.status.value,
                copy.condition.value,
                copy.acquisition_date or "",
                copy.price if copy.price is not None else "",
                copy.shelf_location or "",
                copy.rack_number or "",
            ]
        )
    return buffer.getvalue()
