

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

import app.db.types

revision = '0a07f24e08cf'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    
    op.create_table('authors',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('biography', sa.Text(), nullable=True),
    sa.Column('nationality', sa.String(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_authors'))
    )
    with op.batch_alter_table('authors', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_authors_name'), ['name'], unique=False)

    op.create_table('categories',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_categories'))
    )
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_categories_name'), ['name'], unique=True)

    op.create_table('departments',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('code', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_departments')),
    sa.UniqueConstraint('name', name=op.f('uq_departments_name'))
    )
    with op.batch_alter_table('departments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_departments_code'), ['code'], unique=True)

    op.create_table('publishers',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('address', sa.Text(), nullable=True),
    sa.Column('contact_email', sa.String(length=255), nullable=True),
    sa.Column('website', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_publishers'))
    )
    with op.batch_alter_table('publishers', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_publishers_name'), ['name'], unique=True)

    op.create_table('users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('institutional_id', sa.String(length=64), nullable=True),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('first_name', sa.String(length=120), nullable=False),
    sa.Column('last_name', sa.String(length=120), nullable=False),
    sa.Column('phone', sa.String(length=32), nullable=True),
    sa.Column('role', sa.Enum('SUPER_ADMIN', 'LIBRARIAN', 'FACULTY', 'STUDENT', name='userrole', native_enum=False, length=32), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'ACTIVE', 'INACTIVE', 'SUSPENDED', name='userstatus', native_enum=False, length=32), nullable=False),
    sa.Column('membership_type', sa.Enum('STUDENT', 'FACULTY', 'STAFF', 'ALUMNI', 'EXTERNAL', name='membershiptype', native_enum=False, length=32), nullable=False),
    sa.Column('membership_start', sa.Date(), nullable=True),
    sa.Column('membership_expires', sa.Date(), nullable=True),
    sa.Column('is_email_verified', sa.Boolean(), nullable=False),
    sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('failed_login_attempts', sa.Integer(), nullable=False),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('avatar_url', sa.String(length=512), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_users_created_by_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)
        batch_op.create_index(batch_op.f('ix_users_institutional_id'), ['institutional_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_users_membership_expires'), ['membership_expires'], unique=False)
        batch_op.create_index(batch_op.f('ix_users_role'), ['role'], unique=False)
        batch_op.create_index('ix_users_role_status', ['role', 'status'], unique=False)
        batch_op.create_index(batch_op.f('ix_users_status'), ['status'], unique=False)

    op.create_table('audit_logs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=True),
    sa.Column('actor_email', sa.String(length=255), nullable=True),
    sa.Column('actor_role', sa.String(length=32), nullable=True),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('entity_type', sa.String(length=64), nullable=True),
    sa.Column('entity_id', sa.String(length=64), nullable=True),
    sa.Column('summary', sa.String(length=255), nullable=True),
    sa.Column('metadata_json', app.db.types.JSONPayload(), nullable=True),
    sa.Column('ip_address', sa.String(length=64), nullable=True),
    sa.Column('user_agent', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], name=op.f('fk_audit_logs_actor_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs'))
    )
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_audit_logs_action'), ['action'], unique=False)
        batch_op.create_index('ix_audit_logs_action_created', ['action', 'created_at'], unique=False)
        batch_op.create_index('ix_audit_logs_actor_created', ['actor_id', 'created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_actor_id'), ['actor_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_entity_type'), ['entity_type'], unique=False)

    op.create_table('books',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('subtitle', sa.String(length=300), nullable=True),
    sa.Column('isbn', sa.String(length=32), nullable=True),
    sa.Column('isbn_10', sa.String(length=32), nullable=True),
    sa.Column('publisher_id', sa.Integer(), nullable=True),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.Column('edition', sa.String(length=80), nullable=True),
    sa.Column('publication_year', sa.Integer(), nullable=True),
    sa.Column('language', sa.String(length=48), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('keywords', sa.String(length=512), nullable=True),
    sa.Column('subjects', sa.String(length=512), nullable=True),
    sa.Column('cover_image_url', sa.String(length=512), nullable=True),
    sa.Column('department_id', sa.Integer(), nullable=True),
    sa.Column('shelf_location', sa.String(length=80), nullable=True),
    sa.Column('rack_number', sa.String(length=32), nullable=True),
    sa.Column('total_copies', sa.Integer(), nullable=False),
    sa.Column('available_copies', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_reference_only', sa.Boolean(), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_books_category_id_categories'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_books_created_by_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name=op.f('fk_books_department_id_departments'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['publisher_id'], ['publishers.id'], name=op.f('fk_books_publisher_id_publishers'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_books'))
    )
    with op.batch_alter_table('books', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_books_category_id'), ['category_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_books_department_id'), ['department_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_books_is_active'), ['is_active'], unique=False)
        batch_op.create_index(batch_op.f('ix_books_isbn'), ['isbn'], unique=True)
        batch_op.create_index(batch_op.f('ix_books_isbn_10'), ['isbn_10'], unique=False)
        batch_op.create_index(batch_op.f('ix_books_language'), ['language'], unique=False)
        batch_op.create_index(batch_op.f('ix_books_publication_year'), ['publication_year'], unique=False)
        batch_op.create_index('ix_books_publisher_category', ['publisher_id', 'category_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_books_publisher_id'), ['publisher_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_books_shelf_location'), ['shelf_location'], unique=False)
        batch_op.create_index(batch_op.f('ix_books_title'), ['title'], unique=False)

    op.create_table('courses',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('code', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('department_id', sa.Integer(), nullable=True),
    sa.Column('duration_semesters', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name=op.f('fk_courses_department_id_departments'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_courses')),
    sa.UniqueConstraint('code', 'name', name='uq_courses_code_name')
    )
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_courses_code'), ['code'], unique=True)
        batch_op.create_index(batch_op.f('ix_courses_department_id'), ['department_id'], unique=False)

    op.create_table('email_verification_tokens',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=128), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_email_verification_tokens_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_email_verification_tokens'))
    )
    with op.batch_alter_table('email_verification_tokens', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_email_verification_tokens_token_hash'), ['token_hash'], unique=True)
        batch_op.create_index(batch_op.f('ix_email_verification_tokens_user_id'), ['user_id'], unique=False)
        batch_op.create_index('ix_email_verification_user_active', ['user_id', 'used_at'], unique=False)

    op.create_table('faculty_profiles',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('employee_id', sa.String(length=64), nullable=True),
    sa.Column('department_id', sa.Integer(), nullable=True),
    sa.Column('designation', sa.String(length=120), nullable=True),
    sa.Column('office_location', sa.String(length=120), nullable=True),
    sa.Column('office_phone', sa.String(length=32), nullable=True),
    sa.Column('specialization', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name=op.f('fk_faculty_profiles_department_id_departments'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_faculty_profiles_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_faculty_profiles'))
    )
    with op.batch_alter_table('faculty_profiles', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_faculty_profiles_department_id'), ['department_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_faculty_profiles_employee_id'), ['employee_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_faculty_profiles_user_id'), ['user_id'], unique=True)

    op.create_table('library_policies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('institution_name', sa.String(length=200), nullable=False),
    sa.Column('library_email', sa.String(length=255), nullable=True),
    sa.Column('library_phone', sa.String(length=64), nullable=True),
    sa.Column('library_address', sa.Text(), nullable=True),
    sa.Column('opening_hours', sa.String(length=255), nullable=True),
    sa.Column('max_books_student', sa.Integer(), nullable=False),
    sa.Column('max_books_faculty', sa.Integer(), nullable=False),
    sa.Column('max_books_staff', sa.Integer(), nullable=False),
    sa.Column('loan_period_days_student', sa.Integer(), nullable=False),
    sa.Column('loan_period_days_faculty', sa.Integer(), nullable=False),
    sa.Column('max_renewals', sa.Integer(), nullable=False),
    sa.Column('renewal_period_days', sa.Integer(), nullable=False),
    sa.Column('max_fine_blocks_renewal', app.db.types.Money(precision=12, scale=2), nullable=False),
    sa.Column('max_fine_blocks_issue', app.db.types.Money(precision=12, scale=2), nullable=False),
    sa.Column('fine_per_day', app.db.types.Money(precision=12, scale=2), nullable=False),
    sa.Column('grace_period_days', sa.Integer(), nullable=False),
    sa.Column('max_fine_per_loan', app.db.types.Money(precision=12, scale=2), nullable=False),
    sa.Column('currency_code', sa.String(length=8), nullable=False),
    sa.Column('reservation_pickup_days', sa.Integer(), nullable=False),
    sa.Column('max_active_reservations', sa.Integer(), nullable=False),
    sa.Column('reservation_expiry_hours', sa.Integer(), nullable=False),
    sa.Column('due_reminder_days', sa.JSON(), nullable=False),
    sa.Column('overdue_reminder_days', sa.JSON(), nullable=False),
    sa.Column('membership_expiry_reminder_days', sa.JSON(), nullable=False),
    sa.Column('max_overdue_reminders', sa.Integer(), nullable=False),
    sa.Column('membership_validity_days_student', sa.Integer(), nullable=False),
    sa.Column('membership_validity_days_faculty', sa.Integer(), nullable=False),
    sa.Column('updated_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_library_policies_updated_by_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_library_policies'))
    )
    op.create_table('notifications',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('type', sa.Enum('WELCOME', 'EMAIL_VERIFICATION', 'PASSWORD_RESET', 'BOOK_ISSUED', 'BOOK_RETURNED', 'BOOK_DUE_SOON', 'BOOK_OVERDUE', 'RESERVATION_AVAILABLE', 'RESERVATION_EXPIRED', 'FINE_ASSESSED', 'FINE_PAYMENT', 'MEMBERSHIP_EXPIRING', 'MEMBERSHIP_EXPIRED', 'SYSTEM', name='notificationtype', native_enum=False, length=48), nullable=False),
    sa.Column('channel', sa.Enum('EMAIL', name='notificationchannel', native_enum=False, length=16), nullable=False),
    sa.Column('status', sa.Enum('QUEUED', 'SENDING', 'SENT', 'FAILED', 'CANCELLED', name='notificationstatus', native_enum=False, length=16), nullable=False),
    sa.Column('subject', sa.String(length=255), nullable=False),
    sa.Column('body_html', sa.Text(), nullable=False),
    sa.Column('body_text', sa.Text(), nullable=False),
    sa.Column('template_name', sa.String(length=64), nullable=False),
    sa.Column('recipient_email', sa.String(length=255), nullable=False),
    sa.Column('dedupe_key', sa.String(length=191), nullable=False),
    sa.Column('payload', app.db.types.JSONPayload(), nullable=True),
    sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('max_attempts', sa.Integer(), nullable=False),
    sa.Column('last_error', sa.String(length=512), nullable=True),
    sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('locked_by', sa.String(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_notifications_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications')),
    sa.UniqueConstraint('dedupe_key', name='uq_notifications_dedupe_key')
    )
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.create_index('ix_notifications_queue', ['status', 'scheduled_for'], unique=False)
        batch_op.create_index(batch_op.f('ix_notifications_scheduled_for'), ['scheduled_for'], unique=False)
        batch_op.create_index(batch_op.f('ix_notifications_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_notifications_type'), ['type'], unique=False)
        batch_op.create_index(batch_op.f('ix_notifications_user_id'), ['user_id'], unique=False)
        batch_op.create_index('ix_notifications_user_type', ['user_id', 'type'], unique=False)

    op.create_table('password_reset_tokens',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=128), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('request_ip', sa.String(length=64), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_password_reset_tokens_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_password_reset_tokens'))
    )
    with op.batch_alter_table('password_reset_tokens', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_password_reset_tokens_token_hash'), ['token_hash'], unique=True)
        batch_op.create_index(batch_op.f('ix_password_reset_tokens_user_id'), ['user_id'], unique=False)
        batch_op.create_index('ix_password_reset_user_active', ['user_id', 'used_at'], unique=False)

    op.create_table('refresh_tokens',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('jti', sa.String(length=64), nullable=False),
    sa.Column('token_hash', sa.String(length=128), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_reason', sa.String(length=128), nullable=True),
    sa.Column('replaced_by_jti', sa.String(length=64), nullable=True),
    sa.Column('user_agent', sa.String(length=255), nullable=True),
    sa.Column('ip_address', sa.String(length=64), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_refresh_tokens_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_tokens'))
    )
    with op.batch_alter_table('refresh_tokens', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_refresh_tokens_jti'), ['jti'], unique=True)
        batch_op.create_index(batch_op.f('ix_refresh_tokens_user_id'), ['user_id'], unique=False)

    op.create_table('book_authors',
    sa.Column('book_id', sa.Integer(), nullable=False),
    sa.Column('author_id', sa.Integer(), nullable=False),
    sa.Column('author_order', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['authors.id'], name=op.f('fk_book_authors_author_id_authors'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['book_id'], ['books.id'], name=op.f('fk_book_authors_book_id_books'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('book_id', 'author_id', name=op.f('pk_book_authors'))
    )
    op.create_table('book_copies',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('book_id', sa.Integer(), nullable=False),
    sa.Column('accession_number', sa.String(length=64), nullable=False),
    sa.Column('barcode', sa.String(length=64), nullable=True),
    sa.Column('status', sa.Enum('AVAILABLE', 'ISSUED', 'RESERVED', 'LOST', 'DAMAGED', 'RETIRED', name='bookcopystatus', native_enum=False, length=24), nullable=False),
    sa.Column('condition', sa.Enum('NEW', 'GOOD', 'FAIR', 'POOR', 'DAMAGED', name='copycondition', native_enum=False, length=24), nullable=False),
    sa.Column('acquisition_date', sa.Date(), nullable=True),
    sa.Column('price', app.db.types.Money(precision=12, scale=2), nullable=True),
    sa.Column('shelf_location', sa.String(length=80), nullable=True),
    sa.Column('rack_number', sa.String(length=32), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('status_changed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status_changed_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['book_id'], ['books.id'], name=op.f('fk_book_copies_book_id_books'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['status_changed_by_id'], ['users.id'], name=op.f('fk_book_copies_status_changed_by_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_book_copies'))
    )
    with op.batch_alter_table('book_copies', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_book_copies_accession_number'), ['accession_number'], unique=True)
        batch_op.create_index(batch_op.f('ix_book_copies_barcode'), ['barcode'], unique=True)
        batch_op.create_index(batch_op.f('ix_book_copies_book_id'), ['book_id'], unique=False)
        batch_op.create_index('ix_book_copies_book_status', ['book_id', 'status'], unique=False)
        batch_op.create_index(batch_op.f('ix_book_copies_shelf_location'), ['shelf_location'], unique=False)
        batch_op.create_index(batch_op.f('ix_book_copies_status'), ['status'], unique=False)

    op.create_table('notification_attempts',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('notification_id', sa.Integer(), nullable=False),
    sa.Column('attempt_number', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=24), nullable=False),
    sa.Column('error_message', sa.String(length=512), nullable=True),
    sa.Column('error_type', sa.String(length=128), nullable=True),
    sa.Column('duration_ms', sa.Integer(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('was_retry', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['notification_id'], ['notifications.id'], name=op.f('fk_notification_attempts_notification_id_notifications'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notification_attempts')),
    sa.UniqueConstraint('notification_id', 'attempt_number', name='uq_notification_attempt_number')
    )
    with op.batch_alter_table('notification_attempts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_notification_attempts_notification_id'), ['notification_id'], unique=False)

    op.create_table('student_profiles',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('enrollment_number', sa.String(length=64), nullable=True),
    sa.Column('course_id', sa.Integer(), nullable=True),
    sa.Column('semester', sa.Integer(), nullable=True),
    sa.Column('section', sa.String(length=32), nullable=True),
    sa.Column('academic_year', sa.String(length=32), nullable=True),
    sa.Column('guardian_name', sa.String(length=160), nullable=True),
    sa.Column('guardian_phone', sa.String(length=32), nullable=True),
    sa.Column('address', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], name=op.f('fk_student_profiles_course_id_courses'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_student_profiles_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_student_profiles'))
    )
    with op.batch_alter_table('student_profiles', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_student_profiles_course_id'), ['course_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_student_profiles_enrollment_number'), ['enrollment_number'], unique=False)
        batch_op.create_index(batch_op.f('ix_student_profiles_user_id'), ['user_id'], unique=True)

    op.create_table('inventory_adjustments',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('copy_id', sa.Integer(), nullable=False),
    sa.Column('previous_status', sa.String(length=24), nullable=False),
    sa.Column('new_status', sa.String(length=24), nullable=False),
    sa.Column('reason', sa.String(length=255), nullable=True),
    sa.Column('changed_by_id', sa.Integer(), nullable=True),
    sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['changed_by_id'], ['users.id'], name=op.f('fk_inventory_adjustments_changed_by_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['copy_id'], ['book_copies.id'], name=op.f('fk_inventory_adjustments_copy_id_book_copies'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_inventory_adjustments'))
    )
    with op.batch_alter_table('inventory_adjustments', schema=None) as batch_op:
        batch_op.create_index('ix_inventory_adjustments_copy', ['copy_id', 'changed_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_inventory_adjustments_copy_id'), ['copy_id'], unique=False)

    op.create_table('loans',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('copy_id', sa.Integer(), nullable=False),
    sa.Column('member_id', sa.Integer(), nullable=False),
    sa.Column('issued_by_id', sa.Integer(), nullable=True),
    sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('returned_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('returned_by_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.Enum('ACTIVE', 'RETURNED', 'OVERDUE', 'LOST', name='loanstatus', native_enum=False, length=24), nullable=False),
    sa.Column('renewal_count', sa.Integer(), nullable=False),
    sa.Column('due_date_version', sa.Integer(), nullable=False),
    sa.Column('active_copy_id', sa.Integer(), nullable=True),
    sa.Column('overdue_days', sa.Integer(), nullable=False),
    sa.Column('fine_id', sa.Integer(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['active_copy_id'], ['book_copies.id'], name=op.f('fk_loans_active_copy_id_book_copies'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['copy_id'], ['book_copies.id'], name=op.f('fk_loans_copy_id_book_copies'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['fine_id'], ['fines.id'], name=op.f('fk_loans_fine_id_fines'), ondelete='SET NULL', use_alter=True),
    sa.ForeignKeyConstraint(['issued_by_id'], ['users.id'], name=op.f('fk_loans_issued_by_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['member_id'], ['users.id'], name=op.f('fk_loans_member_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['returned_by_id'], ['users.id'], name=op.f('fk_loans_returned_by_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_loans')),
    sa.UniqueConstraint('active_copy_id', name=op.f('uq_loans_active_copy_id')),
    sa.UniqueConstraint('fine_id', name=op.f('uq_loans_fine_id'))
    )
    with op.batch_alter_table('loans', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_loans_copy_id'), ['copy_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_loans_due_at'), ['due_at'], unique=False)
        batch_op.create_index('ix_loans_due_status', ['due_at', 'status'], unique=False)
        batch_op.create_index('ix_loans_issued_at', ['issued_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_loans_member_id'), ['member_id'], unique=False)
        batch_op.create_index('ix_loans_member_status', ['member_id', 'status'], unique=False)
        batch_op.create_index(batch_op.f('ix_loans_status'), ['status'], unique=False)

    op.create_table('reservations',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('book_id', sa.Integer(), nullable=False),
    sa.Column('member_id', sa.Integer(), nullable=False),
    sa.Column('copy_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.Enum('ACTIVE', 'READY', 'FULFILLED', 'CANCELLED', 'EXPIRED', name='reservationstatus', native_enum=False, length=24), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('queue_position', sa.Integer(), nullable=False),
    sa.Column('reserved_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ready_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('pickup_deadline', sa.DateTime(timezone=True), nullable=True),
    sa.Column('fulfilled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('expired_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('active_key', sa.String(length=64), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['book_id'], ['books.id'], name=op.f('fk_reservations_book_id_books'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['copy_id'], ['book_copies.id'], name=op.f('fk_reservations_copy_id_book_copies'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['member_id'], ['users.id'], name=op.f('fk_reservations_member_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_reservations')),
    sa.UniqueConstraint('active_key', name=op.f('uq_reservations_active_key'))
    )
    with op.batch_alter_table('reservations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_reservations_book_id'), ['book_id'], unique=False)
        batch_op.create_index('ix_reservations_book_status', ['book_id', 'status'], unique=False)
        batch_op.create_index(batch_op.f('ix_reservations_copy_id'), ['copy_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_reservations_member_id'), ['member_id'], unique=False)
        batch_op.create_index('ix_reservations_member_status', ['member_id', 'status'], unique=False)
        batch_op.create_index(batch_op.f('ix_reservations_pickup_deadline'), ['pickup_deadline'], unique=False)
        batch_op.create_index('ix_reservations_queue', ['book_id', 'status', 'reserved_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_reservations_status'), ['status'], unique=False)

    op.create_table('fines',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('member_id', sa.Integer(), nullable=False),
    sa.Column('loan_id', sa.Integer(), nullable=True),
    sa.Column('amount', app.db.types.Money(precision=12, scale=2), nullable=False),
    sa.Column('amount_paid', app.db.types.Money(precision=12, scale=2), nullable=False),
    sa.Column('days_overdue', sa.Integer(), nullable=False),
    sa.Column('rate_per_day', app.db.types.Money(precision=12, scale=2), nullable=False),
    sa.Column('reason', sa.String(length=255), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'PARTIALLY_PAID', 'PAID', 'WAIVED', 'CANCELLED', name='finestatus', native_enum=False, length=24), nullable=False),
    sa.Column('assessed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('assessed_by_id', sa.Integer(), nullable=True),
    sa.Column('waived_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('waived_by_id', sa.Integer(), nullable=True),
    sa.Column('waiver_reason', sa.String(length=255), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['assessed_by_id'], ['users.id'], name=op.f('fk_fines_assessed_by_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['loan_id'], ['loans.id'], name=op.f('fk_fines_loan_id_loans'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['member_id'], ['users.id'], name=op.f('fk_fines_member_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['waived_by_id'], ['users.id'], name=op.f('fk_fines_waived_by_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_fines'))
    )
    with op.batch_alter_table('fines', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_fines_loan_id'), ['loan_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_fines_member_id'), ['member_id'], unique=False)
        batch_op.create_index('ix_fines_member_status', ['member_id', 'status'], unique=False)
        batch_op.create_index(batch_op.f('ix_fines_status'), ['status'], unique=False)

    op.create_table('loan_renewals',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('loan_id', sa.Integer(), nullable=False),
    sa.Column('renewed_by_id', sa.Integer(), nullable=True),
    sa.Column('previous_due_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('new_due_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('renewal_number', sa.Integer(), nullable=False),
    sa.Column('renewed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('note', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['loan_id'], ['loans.id'], name=op.f('fk_loan_renewals_loan_id_loans'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['renewed_by_id'], ['users.id'], name=op.f('fk_loan_renewals_renewed_by_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_loan_renewals'))
    )
    with op.batch_alter_table('loan_renewals', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_loan_renewals_loan_id'), ['loan_id'], unique=False)

    op.create_table('fine_payments',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('fine_id', sa.Integer(), nullable=False),
    sa.Column('amount', app.db.types.Money(precision=12, scale=2), nullable=False),
    sa.Column('method', sa.Enum('CASH', 'CARD', 'UPI', 'BANK_TRANSFER', 'ONLINE', 'OTHER', name='paymentmethod', native_enum=False, length=32), nullable=False),
    sa.Column('reference', sa.String(length=120), nullable=True),
    sa.Column('paid_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('recorded_by_id', sa.Integer(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['fine_id'], ['fines.id'], name=op.f('fk_fine_payments_fine_id_fines'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['recorded_by_id'], ['users.id'], name=op.f('fk_fine_payments_recorded_by_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_fine_payments'))
    )
    with op.batch_alter_table('fine_payments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_fine_payments_fine_id'), ['fine_id'], unique=False)

    


def downgrade() -> None:
    
    with op.batch_alter_table('fine_payments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_fine_payments_fine_id'))

    op.drop_table('fine_payments')
    with op.batch_alter_table('loan_renewals', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_loan_renewals_loan_id'))

    op.drop_table('loan_renewals')
    with op.batch_alter_table('fines', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_fines_status'))
        batch_op.drop_index('ix_fines_member_status')
        batch_op.drop_index(batch_op.f('ix_fines_member_id'))
        batch_op.drop_index(batch_op.f('ix_fines_loan_id'))

    op.drop_table('fines')
    with op.batch_alter_table('reservations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_reservations_status'))
        batch_op.drop_index('ix_reservations_queue')
        batch_op.drop_index(batch_op.f('ix_reservations_pickup_deadline'))
        batch_op.drop_index('ix_reservations_member_status')
        batch_op.drop_index(batch_op.f('ix_reservations_member_id'))
        batch_op.drop_index(batch_op.f('ix_reservations_copy_id'))
        batch_op.drop_index('ix_reservations_book_status')
        batch_op.drop_index(batch_op.f('ix_reservations_book_id'))

    op.drop_table('reservations')
    with op.batch_alter_table('loans', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_loans_status'))
        batch_op.drop_index('ix_loans_member_status')
        batch_op.drop_index(batch_op.f('ix_loans_member_id'))
        batch_op.drop_index('ix_loans_issued_at')
        batch_op.drop_index('ix_loans_due_status')
        batch_op.drop_index(batch_op.f('ix_loans_due_at'))
        batch_op.drop_index(batch_op.f('ix_loans_copy_id'))

    op.drop_table('loans')
    with op.batch_alter_table('inventory_adjustments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_inventory_adjustments_copy_id'))
        batch_op.drop_index('ix_inventory_adjustments_copy')

    op.drop_table('inventory_adjustments')
    with op.batch_alter_table('student_profiles', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_student_profiles_user_id'))
        batch_op.drop_index(batch_op.f('ix_student_profiles_enrollment_number'))
        batch_op.drop_index(batch_op.f('ix_student_profiles_course_id'))

    op.drop_table('student_profiles')
    with op.batch_alter_table('notification_attempts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_notification_attempts_notification_id'))

    op.drop_table('notification_attempts')
    with op.batch_alter_table('book_copies', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_book_copies_status'))
        batch_op.drop_index(batch_op.f('ix_book_copies_shelf_location'))
        batch_op.drop_index('ix_book_copies_book_status')
        batch_op.drop_index(batch_op.f('ix_book_copies_book_id'))
        batch_op.drop_index(batch_op.f('ix_book_copies_barcode'))
        batch_op.drop_index(batch_op.f('ix_book_copies_accession_number'))

    op.drop_table('book_copies')
    op.drop_table('book_authors')
    with op.batch_alter_table('refresh_tokens', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_refresh_tokens_user_id'))
        batch_op.drop_index(batch_op.f('ix_refresh_tokens_jti'))

    op.drop_table('refresh_tokens')
    with op.batch_alter_table('password_reset_tokens', schema=None) as batch_op:
        batch_op.drop_index('ix_password_reset_user_active')
        batch_op.drop_index(batch_op.f('ix_password_reset_tokens_user_id'))
        batch_op.drop_index(batch_op.f('ix_password_reset_tokens_token_hash'))

    op.drop_table('password_reset_tokens')
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.drop_index('ix_notifications_user_type')
        batch_op.drop_index(batch_op.f('ix_notifications_user_id'))
        batch_op.drop_index(batch_op.f('ix_notifications_type'))
        batch_op.drop_index(batch_op.f('ix_notifications_status'))
        batch_op.drop_index(batch_op.f('ix_notifications_scheduled_for'))
        batch_op.drop_index('ix_notifications_queue')

    op.drop_table('notifications')
    op.drop_table('library_policies')
    with op.batch_alter_table('faculty_profiles', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_faculty_profiles_user_id'))
        batch_op.drop_index(batch_op.f('ix_faculty_profiles_employee_id'))
        batch_op.drop_index(batch_op.f('ix_faculty_profiles_department_id'))

    op.drop_table('faculty_profiles')
    with op.batch_alter_table('email_verification_tokens', schema=None) as batch_op:
        batch_op.drop_index('ix_email_verification_user_active')
        batch_op.drop_index(batch_op.f('ix_email_verification_tokens_user_id'))
        batch_op.drop_index(batch_op.f('ix_email_verification_tokens_token_hash'))

    op.drop_table('email_verification_tokens')
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_courses_department_id'))
        batch_op.drop_index(batch_op.f('ix_courses_code'))

    op.drop_table('courses')
    with op.batch_alter_table('books', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_books_title'))
        batch_op.drop_index(batch_op.f('ix_books_shelf_location'))
        batch_op.drop_index(batch_op.f('ix_books_publisher_id'))
        batch_op.drop_index('ix_books_publisher_category')
        batch_op.drop_index(batch_op.f('ix_books_publication_year'))
        batch_op.drop_index(batch_op.f('ix_books_language'))
        batch_op.drop_index(batch_op.f('ix_books_isbn_10'))
        batch_op.drop_index(batch_op.f('ix_books_isbn'))
        batch_op.drop_index(batch_op.f('ix_books_is_active'))
        batch_op.drop_index(batch_op.f('ix_books_department_id'))
        batch_op.drop_index(batch_op.f('ix_books_category_id'))

    op.drop_table('books')
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_audit_logs_entity_type'))
        batch_op.drop_index(batch_op.f('ix_audit_logs_created_at'))
        batch_op.drop_index(batch_op.f('ix_audit_logs_actor_id'))
        batch_op.drop_index('ix_audit_logs_actor_created')
        batch_op.drop_index('ix_audit_logs_action_created')
        batch_op.drop_index(batch_op.f('ix_audit_logs_action'))

    op.drop_table('audit_logs')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_status'))
        batch_op.drop_index('ix_users_role_status')
        batch_op.drop_index(batch_op.f('ix_users_role'))
        batch_op.drop_index(batch_op.f('ix_users_membership_expires'))
        batch_op.drop_index(batch_op.f('ix_users_institutional_id'))
        batch_op.drop_index(batch_op.f('ix_users_email'))

    op.drop_table('users')
    with op.batch_alter_table('publishers', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_publishers_name'))

    op.drop_table('publishers')
    with op.batch_alter_table('departments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_departments_code'))

    op.drop_table('departments')
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_categories_name'))

    op.drop_table('categories')
    with op.batch_alter_table('authors', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_authors_name'))

    op.drop_table('authors')
    
