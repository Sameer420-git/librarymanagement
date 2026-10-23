

from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import get_session_factory  
from app.models.circulation import Fine, Loan, LoanRenewal  
from app.models.enums import (  
    CopyCondition,
    BookCopyStatus,
    FineStatus,
    LoanStatus,
    UserRole,
    UserStatus,
)
from app.models.notification import Notification  
from app.models.user import User  
from app.schemas.book import BookCopyCreate, BookCreate  
from app.schemas.member import CourseCreate, DepartmentCreate, MemberCreate  
from app.services import book_service, circulation_service, member_service  
from app.services import reservation_service  
from app.core.security import hash_password  
from app.utils.helpers import utcnow  

TABLES_IN_DELETE_ORDER = [
    "fine_payments",
    "fines",
    "loan_renewals",
    "notifications",
    "notification_attempts",
    "reservations",
    "loans",
    "inventory_adjustments",
    "book_copies",
    "book_authors",
    "books",
    "authors",
    "categories",
    "publishers",
    "student_profiles",
    "faculty_profiles",
    "courses",
    "departments",
    "password_reset_tokens",
    "email_verification_tokens",
    "refresh_tokens",
    "audit_logs",
    "users",
    "library_policies",
]


def truncate_all(session) -> None:
    for table in TABLES_IN_DELETE_ORDER:
        session.execute(_text(f"DELETE FROM {table}"))
    session.commit()


def _text(statement: str):
    from sqlalchemy import text

    return text(statement)


def seed_users(session) -> dict[str, User]:
    
    people = [
        ("admin", "Aarav", "Sharma", "admin@college.edu", UserRole.SUPER_ADMIN, "ADM-001"),
        ("librarian", "Sushil", "Yadav", "librarian@college.edu", UserRole.LIBRARIAN, "LIB-001"),
        ("librarian2", "Rohit", "Nair", "librarian2@college.edu", UserRole.LIBRARIAN, "LIB-002"),
        ("faculty", "Dr. Kavita", "Singh", "faculty@college.edu", UserRole.FACULTY, "FAC-001"),
        ("faculty2", "Dr. Anil", "Kumar", "faculty2@college.edu", UserRole.FACULTY, "FAC-002"),
    ]
    created: dict[str, User] = {}

    for key, first, last, email, role, inst_id in people:
        payload = MemberCreate(
            email=email,
            institutional_id=inst_id,
            first_name=first,
            last_name=last,
            role=role,
            status=UserStatus.ACTIVE,
            password="Demo@12345",
        )
        user = member_service.create_member(session, payload)
        user.is_email_verified = True
        session.commit()
        created[key] = user

    student_names = [
        ("Sameer", "Kumar"),
        ("Anup", "Singh"),
        ("Priyanshu", "Sharma"),
        ("Rudra", "Patel"),
        ("Harshita", "Yadav"),
        ("Raj", "Verma"),
    ]
    for index, (first, last) in enumerate(student_names, start=1):
        email = f"student{index}@college.edu"
        payload = MemberCreate(
            email=email,
            institutional_id=f"STU-{index:04d}",
            first_name=first,
            last_name=last,
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
            enrollment_number=f"ENR-{index:05d}",
            semester=(index % 8) + 1,
            section="A",
            academic_year="2025-26",
            password="Student@123",
        )
        user = member_service.create_member(session, payload)
        user.is_email_verified = True
        session.commit()
        created[f"student{index}"] = user

    return created


def seed_academic_structure(session) -> tuple[list, list]:
    departments = [
        ("CSE", "Computer Science & Engineering"),
        ("ECE", "Electronics & Communication"),
        ("ME", "Mechanical Engineering"),
        ("MAT", "Mathematics"),
        ("PHY", "Physics"),
    ]
    dept_objects = [
        member_service.create_department(
            session, DepartmentCreate(code=code, name=name)
        )
        for code, name in departments
    ]
    session.commit()

    courses = [
        ("BTECH-CSE", "B.Tech Computer Science & Engineering", dept_objects[0].id, 8),
        ("MTECH-CSE", "M.Tech Computer Science & Engineering", dept_objects[0].id, 4),
        ("BTECH-ECE", "B.Tech Electronics & Communication", dept_objects[1].id, 8),
        ("BTECH-ME", "B.Tech Mechanical Engineering", dept_objects[2].id, 8),
        ("BSC-MAT", "B.Sc Mathematics", dept_objects[3].id, 6),
    ]
    course_objects = [
        member_service.create_course(
            session,
            CourseCreate(
                code=code,
                name=name,
                department_id=dept_id,
                duration_semesters=terms,
            ),
        )
        for code, name, dept_id, terms in courses
    ]
    session.commit()
    return dept_objects, course_objects


def seed_catalogue(session, actor: User, departments: list) -> list:
    catalogue = [
        {
            "title": "Introduction to Algorithms",
            "subtitle": "The definitive guide",
            "isbn": "978-0-262-03384-8",
            "publisher_name": "MIT Press",
            "category_name": "Computer Science",
            "edition": "3rd",
            "publication_year": 2009,
            "description": "A comprehensive introduction to modern algorithms.",
            "author_names": ["Thomas H. Cormen", "Charles E. Leiserson"],
            "shelf_location": "A-01",
            "rack_number": "A1.1",
        },
        {
            "title": "Clean Code",
            "isbn": "978-0-13-235088-4",
            "publisher_name": "Prentice Hall",
            "category_name": "Software Engineering",
            "edition": "1st",
            "publication_year": 2008,
            "description": "Principles and patterns for writing maintainable code.",
            "author_names": ["Robert C. Martin"],
            "shelf_location": "A-02",
            "rack_number": "A2.3",
        },
        {
            "title": "Database System Concepts",
            "isbn": "978-0-07-802956-3",
            "publisher_name": "McGraw-Hill",
            "category_name": "Computer Science",
            "edition": "6th",
            "publication_year": 2008,
            "description": "The classic reference on relational database systems.",
            "author_names": ["Abraham Silberschatz", "Henry F. Korth"],
            "shelf_location": "A-03",
            "rack_number": "A3.2",
        },
        {
            "title": "Digital Design and Computer Architecture",
            "isbn": "978-0-12-374064-1",
            "publisher_name": "Morgan Kaufmann",
            "category_name": "Electronics",
            "edition": "1st",
            "publication_year": 2007,
            "description": "Digital logic design and the RISC-V architecture.",
            "author_names": ["Harris & Harris"],
            "shelf_location": "B-01",
            "rack_number": "B1.1",
        },
        {
            "title": "Fluid Mechanics",
            "isbn": "978-0-07-339774-2",
            "publisher_name": "McGraw-Hill",
            "category_name": "Mechanical",
            "edition": "7th",
            "publication_year": 2015,
            "description": "Fundamentals of fluid flow, with worked examples.",
            "author_names": ["Frank M. White"],
            "shelf_location": "C-01",
            "rack_number": "C1.4",
        },
        {
            "title": "Linear Algebra and Its Applications",
            "isbn": "978-0-547-75015-5",
            "publisher_name": "Wiley",
            "category_name": "Mathematics",
            "edition": "5th",
            "publication_year": 2015,
            "description": "An accessible introduction to linear algebra.",
            "author_names": ["Gilbert Strang"],
            "shelf_location": "D-01",
            "rack_number": "D1.1",
        },
        {
            "title": "Introduction to Algorithms - Python Edition",
            "isbn": "978-0-13-461099-3",
            "publisher_name": "Addison-Wesley",
            "category_name": "Computer Science",
            "edition": "1st",
            "publication_year": 2016,
            "description": "Algorithm design and analysis with Python.",
            "author_names": ["Prabhakar Raghavan"],
            "shelf_location": "A-03",
            "rack_number": "A3.5",
        },
        {
            "title": "Fundamentals of Physics",
            "isbn": "978-0-13-325698-5",
            "publisher_name": "Pearson",
            "category_name": "Physics",
            "edition": "10th",
            "publication_year": 2013,
            "description": "A three-volume foundation for undergraduate physics.",
            "author_names": ["Halliday, Resnick and Walker"],
            "shelf_location": "E-01",
            "rack_number": "E1.2",
        },
        {
            "title": "Artificial Intelligence: A Modern Approach",
            "isbn": "978-0-13-604399-1",
            "publisher_name": "Pearson",
            "category_name": "Computer Science",
            "edition": "3rd",
            "publication_year": 2016,
            "description": "The standard textbook on intelligent agents.",
            "author_names": ["Stuart Russell", "Peter Norvig"],
            "shelf_location": "A-04",
            "rack_number": "A4.1",
        },
        {
            "title": "The Pragmatic Programmer",
            "isbn": "978-0-201-61622-4",
            "publisher_name": "Addison-Wesley",
            "category_name": "Software Engineering",
            "edition": "2nd",
            "publication_year": 2019,
            "description": "Practical guides to software craftsmanship.",
            "author_names": ["David Thomas", "Andrew Hunt"],
            "shelf_location": "A-02",
            "rack_number": "A2.6",
        },
        {
            "title": "Operating System Concepts",
            "isbn": "978-0-470-34407-9",
            "publisher_name": "Wiley",
            "category_name": "Computer Science",
            "edition": "9th",
            "publication_year": 2012,
            "description": "Core operating-system principles and internals.",
            "author_names": ["Silberschatz, Galvin and Gagne"],
            "shelf_location": "A-05",
            "rack_number": "A5.3",
        },
        {
            "title": "Heat and Mass Transfer",
            "isbn": "978-0-07-339774-3",
            "publisher_name": "McGraw-Hill",
            "category_name": "Mechanical",
            "edition": "6th",
            "publication_year": 2017,
            "description": "Conduction, convection and radiation.",
            "author_names": ["Yunus A. Cengel"],
            "shelf_location": "C-02",
            "rack_number": "C2.2",
        },
    ]

    books = []
    for entry in catalogue:
        payload = BookCreate(
            title=entry["title"],
            subtitle=entry.get("subtitle"),
            isbn=entry["isbn"],
            publisher_name=entry["publisher_name"],
            category_name=entry["category_name"],
            edition=entry.get("edition"),
            publication_year=entry.get("publication_year"),
            description=entry.get("description"),
            author_names=entry.get("author_names", []),
            shelf_location=entry.get("shelf_location"),
            rack_number=entry.get("rack_number"),
        )
        book = book_service.create_book(session, payload, actor=actor)
        books.append(book)
    session.commit()

    
    counter = 1
    for book in books:
        copies = random.choice([2, 2, 3, 3, 4])
        for _ in range(copies):
            accession = f"ACC{counter:05d}"
            book_service.create_copy(
                session,
                book.id,
                BookCopyCreate(
                    accession_number=accession,
                    barcode=f"BC{counter:05d}",
                    condition=random.choice(list(CopyCondition)),
                    acquisition_date=date.today() - timedelta(days=random.randint(30, 1500)),
                    price=round(random.uniform(250, 4500), 2),
                ),
                actor=actor,
            )
            counter += 1
    session.commit()
    return books


def seed_circulation(session, actor: User, books: list, users: dict[str, User]) -> None:
    
    students = [users[f"student{i}"] for i in range(1, 21)]
    faculty = [users["faculty"], users["faculty2"]]

    from app.models.catalogue import BookCopy

    copies = list(session.query(BookCopy).order_by(BookCopy.id).all())
    demo_fine_examples = [
        ("student1", 12),
        ("student2", 8),
        ("student3", 5),
    ]
    available_copies = [
        copy for copy in copies if copy.status == BookCopyStatus.AVAILABLE
    ]
    if len(available_copies) < len(demo_fine_examples):
        raise RuntimeError("Not enough available copies to create demo fine examples.")

    for (student_key, overdue_days), copy in zip(
        demo_fine_examples, available_copies
    ):
        loan = circulation_service.issue_book(
            session,
            member_id=users[student_key].id,
            copy_id=copy.id,
            actor=actor,
        )
        loan.due_at = utcnow() - timedelta(days=overdue_days)
        session.flush()
        circulation_service.return_book(
            session,
            loan.id,
            actor,
            notes="Demo overdue return",
        )
    print("  demo fines: student1, student2 and student3 have outstanding fines")

    random.shuffle(copies)

    issued = 0
    returned = 0
    overdue = 0
    renewed = 0

    for copy in copies:
        member = random.choice(students + faculty)
        try:
            loan = circulation_service.issue_book(
                session,
                member_id=member.id,
                copy_id=copy.id,
                actor=actor,
            )
        except Exception:  
            session.rollback()
            continue

        issued += 1
        bucket = random.random()

        if bucket < 0.45:
            
            late_days = random.choice([0, 0, 0, 3, 6, 11])
            loan.due_at = utcnow() - timedelta(days=late_days)
            session.commit()
            try:
                circulation_service.return_book(session, loan.id, actor)
                session.commit()
                returned += 1
            except Exception:  
                session.rollback()
        elif bucket < 0.7:
            
            loan.due_at = utcnow() - timedelta(days=random.randint(2, 18))
            loan.status = LoanStatus.OVERDUE
            loan.overdue_days = random.randint(2, 18)
            session.commit()
            overdue += 1
        else:
            
            if random.random() < 0.4:
                try:
                    circulation_service.renew_loan(session, loan.id, actor, notes="Renewal")
                    session.commit()
                    renewed += 1
                except Exception:  
                    session.rollback()

    session.commit()
    print(
        f"  circulation: {issued} loans issued, {returned} returned, "
        f"{overdue} overdue, {renewed} renewed"
    )


def seed_reservations(session, actor: User, books: list, users: dict[str, User]) -> None:
    students = [users[f"student{i}"] for i in range(1, 21)]
    created = 0
    for book in books[:5]:
        for member in random.sample(students, 2):
            try:
                reservation_service.create_reservation(
                    session,
                    member_id=member.id,
                    book_id=book.id,
                    actor=actor,
                )
                created += 1
            except Exception:  
                session.rollback()
    session.commit()
    print(f"  reservations: {created} queued")


def summarise(session) -> None:
    from app.models.catalogue import Book, BookCopy

    counts = {
        "users": session.query(User).count(),
        "books": session.query(Book).count(),
        "copies": session.query(BookCopy).count(),
        "loans": session.query(Loan).count(),
        "renewals": session.query(LoanRenewal).count(),
        "fines": session.query(Fine).count(),
        "notifications": session.query(Notification).count(),
    }
    outstanding = (
        session.query(Fine).filter(Fine.status.in_([FineStatus.PENDING, FineStatus.PARTIALLY_PAID])).count()
    )
    print("Summary")
    for key, value in counts.items():
        print(f"  {key:14}: {value}")
    print(f"  {'open fines':14}: {outstanding}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed demonstration data.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing domain data before seeding.",
    )
    args = parser.parse_args()

    session = get_session_factory()()
    try:
        if args.reset:
            print("Clearing existing data ...")
            truncate_all(session)
        elif session.query(User).count() > 0:
            print(
                "The database already contains users. Re-run with --reset to "
                "replace the demo data."
            )
            return 1

        print("Seeding users ...")
        users = seed_users(session)
        print("Seeding academic structure ...")
        departments, _courses = seed_academic_structure(session)
        print("Seeding catalogue ...")
        books = seed_catalogue(session, users["librarian"], departments)
        print("Seeding circulation ...")
        seed_circulation(session, users["librarian"], books, users)
        print("Seeding reservations ...")
        seed_reservations(session, users["librarian"], books, users)

        summarise(session)
        print("\nDemo accounts (password in brackets):")
        print("  Super admin  admin@college.edu      [Demo@12345]")
        print("  Librarian   librarian@college.edu   [Demo@12345]")
        print("  Faculty     faculty@college.edu     [Demo@12345]")
        print("  Student     student1@college.edu    [Student@123]")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
