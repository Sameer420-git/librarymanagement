

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, DbSession, StaffUser
from app.core.exceptions import NotFoundError, ValidationError
from app.models.catalogue import Author, Category, Publisher
from app.schemas.book import (
    AuthorCreate,
    AuthorRead,
    BookCopyCreate,
    BookCopyRead,
    BookCopyUpdate,
    BookCreate,
    BookDetail,
    BookSearchParams,
    BookSummary,
    BookUpdate,
    CategoryCreate,
    CategoryRead,
    CopySearchParams,
    CopyStatusUpdate,
    PublisherCreate,
    PublisherRead,
)
from app.schemas.common import Page
from app.services import book_service
from app.services.book_service import (
    create_book,
    create_copy,
    export_books_csv,
    export_copies_csv,
    get_book,
    get_copy,
    import_books_from_csv,
    preview_book_import,
    recalculate_availability,
    retire_book,
    search_books,
    search_copies,
    update_book,
    update_copy_status,
)

router = APIRouter(tags=["Catalogue"])


def _author_names(book) -> list[str]:
    return [author.name for author in book.authors]


def _book_summary(book) -> BookSummary:
    return BookSummary(
        id=book.id,
        title=book.title,
        subtitle=book.subtitle,
        isbn=book.isbn,
        edition=book.edition,
        publication_year=book.publication_year,
        language=book.language,
        cover_image_url=book.cover_image_url,
        total_copies=book.total_copies,
        available_copies=book.available_copies,
        is_active=book.is_active,
        shelf_location=book.shelf_location,
        rack_number=book.rack_number,
        publisher_name=book.publisher.name if book.publisher else None,
        category_name=book.category.name if book.category else None,
        authors=_author_names(book),
    )


def _book_detail(book) -> BookDetail:
    summary = _book_summary(book)
    return BookDetail(
        **summary.model_dump(),
        isbn_10=book.isbn_10,
        description=book.description,
        keywords=book.keywords,
        subjects=book.subjects,
        department_id=book.department_id,
        is_reference_only=book.is_reference_only,
        created_at=book.created_at,
        updated_at=book.updated_at,
    )


def _copy_payload(copy) -> BookCopyRead:
    active_loan = session_copy_loan(copy)
    return BookCopyRead(
        id=copy.id,
        book_id=copy.book_id,
        accession_number=copy.accession_number,
        barcode=copy.barcode,
        status=copy.status,
        condition=copy.condition,
        acquisition_date=copy.acquisition_date,
        price=copy.price,
        shelf_location=copy.shelf_location,
        rack_number=copy.rack_number,
        notes=copy.notes,
        status_changed_at=copy.status_changed_at,
        book_title=copy.book.title if copy.book else None,
        active_loan_id=active_loan[0] if active_loan else None,
        active_loan_due_at=active_loan[1] if active_loan else None,
    )


def session_copy_loan(copy):
    
    from app.models.circulation import Loan
    from app.models.enums import LoanStatus

    for loan in copy.loans:
        if loan.status in (LoanStatus.ACTIVE, LoanStatus.OVERDUE):
            return loan.id, loan.due_at
    return None





@router.get("/books", response_model=Page[BookSummary], summary="Search the catalogue")
def list_books(
    session: DbSession,
    current_user: CurrentUser,
    search: Optional[str] = Query(default=None, description="Title, author, ISBN or keyword"),
    category_id: Optional[int] = Query(default=None),
    publisher_id: Optional[int] = Query(default=None),
    department_id: Optional[int] = Query(default=None),
    language: Optional[str] = Query(default=None),
    available_only: bool = Query(default=False),
    include_inactive: bool = Query(default=False),
    sort_by: str = Query(default="title"),
    sort_order: str = Query(default="asc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[BookSummary]:
    params = {
        "search": search,
        "category_id": category_id,
        "publisher_id": publisher_id,
        "department_id": department_id,
        "language": language,
        "available_only": available_only,
        "include_inactive": include_inactive,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "page": page,
        "page_size": page_size,
    }
    books, total = search_books(session, params)
    return Page.build([_book_summary(book) for book in books], page, page_size, total)


@router.get("/books/{book_id}", response_model=BookDetail, summary="Catalogue entry detail")
def get_book_detail(book_id: int, session: DbSession, current_user: CurrentUser) -> BookDetail:
    return _book_detail(get_book(session, book_id))


@router.post(
    "/books",
    response_model=BookDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Add a catalogue title",
)
def add_book(
    payload: BookCreate, session: DbSession, current_user: StaffUser
) -> BookDetail:
    book = create_book(session, payload, actor=current_user)
    session.commit()
    return _book_detail(book)


@router.put("/books/{book_id}", response_model=BookDetail, summary="Update a catalogue title")
def edit_book(
    book_id: int, payload: BookUpdate, session: DbSession, current_user: StaffUser
) -> BookDetail:
    book = update_book(session, book_id, payload, actor=current_user)
    session.commit()
    return _book_detail(book)


@router.delete(
    "/books/{book_id}", response_model=BookDetail, summary="Retire a catalogue title"
)
def remove_book(book_id: int, session: DbSession, current_user: StaffUser) -> BookDetail:
    book = retire_book(session, book_id, actor=current_user)
    session.commit()
    return _book_detail(book)


@router.get(
    "/books/{book_id}/copies",
    response_model=Page[BookCopyRead],
    summary="Physical copies of a title",
)
def list_book_copies(
    book_id: int,
    session: DbSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[BookCopyRead]:
    get_book(session, book_id)
    copies, total = search_copies(
        session, {"book_id": book_id, "page": 1, "page_size": 1000}
    )
    start = (page - 1) * page_size
    window = copies[start : start + page_size]
    return Page.build([_copy_payload(copy) for copy in window], page, page_size, total)





@router.post(
    "/books/{book_id}/copies",
    response_model=BookCopyRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a physical copy",
)
def add_copy(
    book_id: int, payload: BookCopyCreate, session: DbSession, current_user: StaffUser
) -> BookCopyRead:
    copy = create_copy(session, book_id, payload, actor=current_user)
    session.commit()
    return _copy_payload(copy)


@router.get("/copies", response_model=Page[BookCopyRead], summary="Search physical copies")
def list_copies(
    session: DbSession,
    current_user: CurrentUser,
    accession_number: Optional[str] = Query(default=None),
    barcode: Optional[str] = Query(default=None),
    book_id: Optional[int] = Query(default=None),
    copy_status: Optional[str] = Query(default=None, alias="status"),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[BookCopyRead]:
    from app.models.enums import BookCopyStatus

    status_value = None
    if copy_status:
        try:
            status_value = BookCopyStatus(copy_status.upper())
        except ValueError:
            raise ValidationError(f"Unknown copy status '{copy_status}'.")
    copies, total = search_copies(
        session,
        {
            "accession_number": accession_number,
            "barcode": barcode,
            "book_id": book_id,
            "status": status_value,
            "search": search,
            "page": page,
            "page_size": page_size,
        },
    )
    return Page.build([_copy_payload(copy) for copy in copies], page, page_size, total)


@router.get("/copies/{copy_id}", response_model=BookCopyRead, summary="Copy detail / barcode lookup")
def get_copy_detail(copy_id: int, session: DbSession, current_user: CurrentUser) -> BookCopyRead:
    return _copy_payload(get_copy(session, copy_id))


@router.patch(
    "/copies/{copy_id}/status", response_model=BookCopyRead, summary="Change a copy's status"
)
def change_copy_status(
    copy_id: int, payload: CopyStatusUpdate, session: DbSession, current_user: StaffUser
) -> BookCopyRead:
    copy = update_copy_status(session, copy_id, payload, actor=current_user)
    session.commit()
    return _copy_payload(copy)


@router.patch("/copies/{copy_id}", response_model=BookCopyRead, summary="Update copy details")
def edit_copy(
    copy_id: int, payload: BookCopyUpdate, session: DbSession, current_user: StaffUser
) -> BookCopyRead:
    copy = get_copy(session, copy_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if hasattr(copy, key):
            setattr(copy, key, value)
    session.commit()
    return _copy_payload(copy)





@router.get("/categories", response_model=list[CategoryRead], summary="List categories")
def list_categories(session: DbSession, current_user: CurrentUser) -> list[CategoryRead]:
    from sqlalchemy import select

    categories = session.execute(select(Category).order_by(Category.name)).scalars()
    return [CategoryRead.model_validate(category) for category in categories]


@router.post(
    "/categories",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
)
def add_category(
    payload: CategoryCreate, session: DbSession, current_user: StaffUser
) -> CategoryRead:
    from app.core.exceptions import ConflictError
    from sqlalchemy import select

    existing = session.execute(
        select(Category).where(Category.name == payload.name)
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("A category with this name already exists.")
    category = Category(name=payload.name, description=payload.description)
    session.add(category)
    session.commit()
    return CategoryRead.model_validate(category)


@router.get("/publishers", response_model=list[PublisherRead], summary="List publishers")
def list_publishers(session: DbSession, current_user: CurrentUser) -> list[PublisherRead]:
    from sqlalchemy import select

    publishers = session.execute(select(Publisher).order_by(Publisher.name)).scalars()
    return [PublisherRead.model_validate(publisher) for publisher in publishers]


@router.post(
    "/publishers",
    response_model=PublisherRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a publisher",
)
def add_publisher(
    payload: PublisherCreate, session: DbSession, current_user: StaffUser
) -> PublisherRead:
    from app.core.exceptions import ConflictError
    from sqlalchemy import select

    existing = session.execute(
        select(Publisher).where(Publisher.name == payload.name)
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("A publisher with this name already exists.")
    publisher = Publisher(**payload.model_dump())
    session.add(publisher)
    session.commit()
    return PublisherRead.model_validate(publisher)


@router.get("/authors", response_model=list[AuthorRead], summary="List authors")
def list_authors(session: DbSession, current_user: CurrentUser) -> list[AuthorRead]:
    from sqlalchemy import select

    authors = session.execute(select(Author).order_by(Author.name)).scalars()
    return [AuthorRead.model_validate(author) for author in authors]


@router.post(
    "/authors",
    response_model=AuthorRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an author",
)
def add_author(
    payload: AuthorCreate, session: DbSession, current_user: StaffUser
) -> AuthorRead:
    author = Author(**payload.model_dump())
    session.add(author)
    session.commit()
    return AuthorRead.model_validate(author)





@router.post(
    "/books/import/preview",
    summary="Validate a catalogue CSV without writing anything",
)
def preview_import(
    session: DbSession,
    current_user: StaffUser,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    content = _read_csv(file)
    return preview_book_import(session, content)


@router.post("/books/import", summary="Import books from CSV")
def import_books(
    session: DbSession,
    current_user: StaffUser,
    file: UploadFile = File(...),
    update_existing: bool = Query(default=False),
) -> dict[str, Any]:
    content = _read_csv(file)
    result = import_books_from_csv(session, content, actor=current_user, update_existing=update_existing)
    session.commit()
    return result


@router.get("/books/export/csv", summary="Export the catalogue as CSV")
def export_catalogue(
    session: DbSession,
    current_user: StaffUser,
    book_id: Optional[list[int]] = Query(default=None),
) -> PlainTextResponse:
    csv_text = export_books_csv(session, book_id)
    return PlainTextResponse(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=library_catalogue.csv"},
    )


@router.get("/copies/export/csv", summary="Export physical copies as CSV")
def export_copies(
    session: DbSession,
    current_user: StaffUser,
    copy_id: Optional[list[int]] = Query(default=None),
) -> PlainTextResponse:
    csv_text = export_copies_csv(session, copy_id)
    return PlainTextResponse(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=library_copies.csv"},
    )


def _read_csv(file: UploadFile) -> str:
    raw = file.file.read()
    if isinstance(raw, bytes):
        try:
            return raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            return raw.decode("latin-1")
    return raw
