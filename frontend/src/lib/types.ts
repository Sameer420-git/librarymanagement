export type Role = "SUPER_ADMIN" | "LIBRARIAN" | "FACULTY" | "STUDENT"
export type UserStatus = "PENDING" | "ACTIVE" | "INACTIVE" | "SUSPENDED"
export type LoanStatus = "ACTIVE" | "RETURNED" | "OVERDUE" | "LOST"
export type ReservationStatus = "ACTIVE" | "READY" | "FULFILLED" | "CANCELLED" | "EXPIRED"
export type FineStatus = "PENDING" | "PARTIALLY_PAID" | "PAID" | "WAIVED" | "CANCELLED"
export type CopyStatus = "AVAILABLE" | "ISSUED" | "RESERVED" | "LOST" | "DAMAGED" | "RETIRED"
export type CopyCondition = "NEW" | "GOOD" | "FAIR" | "POOR" | "DAMAGED"
export type PaymentMethod = "CASH" | "CARD" | "UPI" | "BANK_TRANSFER" | "ONLINE" | "OTHER"
export type NotificationStatus = "QUEUED" | "SENDING" | "SENT" | "FAILED" | "CANCELLED"

export interface Pagination {
  page: number
  page_size: number
  total: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

export interface Page<T> {
  items: T[]
  pagination: Pagination
}

export interface UserProfile {
  id: number
  email: string
  institutional_id: string | null
  first_name: string
  last_name: string
  full_name: string
  phone: string | null
  role: Role
  status: UserStatus
  membership_type: string
  membership_start: string | null
  membership_expires: string | null
  is_email_verified: boolean
  last_login_at: string | null
  avatar_url: string | null
  department_name: string | null
  course_name: string | null
  enrollment_number: string | null
  employee_id: string | null
  designation: string | null
  semester: number | null
  section: string | null
  academic_year: string | null
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  refresh_token: string | null
  user: UserProfile
}

export interface Author {
  id: number
  name: string
  biography: string | null
  nationality: string | null
}

export interface Publisher {
  id: number
  name: string
  address: string | null
  contact_email: string | null
  website: string | null
}

export interface Category {
  id: number
  name: string
  description: string | null
}

export interface BookSummary {
  id: number
  title: string
  subtitle: string | null
  isbn: string | null
  edition: string | null
  publication_year: number | null
  language: string
  cover_image_url: string | null
  total_copies: number
  available_copies: number
  is_active: boolean
  shelf_location: string | null
  rack_number: string | null
  publisher_name: string | null
  category_name: string | null
  authors: string[]
}

export interface BookDetail extends BookSummary {
  description: string | null
  keywords: string | null
  subjects: string | null
  department_id: number | null
  is_reference_only: boolean
  created_at: string | null
  updated_at: string | null
}

export interface BookCopy {
  id: number
  book_id: number
  accession_number: string
  barcode: string | null
  status: CopyStatus
  condition: CopyCondition
  acquisition_date: string | null
  price: string | number | null
  shelf_location: string | null
  rack_number: string | null
  notes: string | null
  status_changed_at: string | null
  book_title: string | null
  active_loan_id: number | null
  active_loan_due_at: string | null
}

export interface BookCopyInput {
  accession_number: string
  barcode?: string | null
  condition?: CopyCondition
  acquisition_date?: string | null
  price?: number | null
  shelf_location?: string | null
  rack_number?: string | null
  notes?: string | null
}

export interface BookInput {
  title: string
  subtitle?: string | null
  isbn?: string | null
  publisher_id?: number | null
  publisher_name?: string | null
  category_id?: number | null
  category_name?: string | null
  edition?: string | null
  publication_year?: number | null
  language?: string
  description?: string | null
  keywords?: string | null
  subjects?: string | null
  department_id?: number | null
  shelf_location?: string | null
  rack_number?: string | null
  is_reference_only?: boolean
  author_names?: string[]
}

export interface MemberListItem {
  id: number
  email: string
  institutional_id: string | null
  full_name: string
  role: Role
  status: UserStatus
  membership_type: string
  membership_expires: string | null
  department_name: string | null
  course_name: string | null
  enrollment_number: string | null
  employee_id: string | null
  active_loans: number
  outstanding_fines: number
}

export interface MemberProfile extends MemberListItem {
  first_name: string
  last_name: string
  phone: string | null
  membership_start: string | null
  is_email_verified: boolean
  last_login_at: string | null
  created_at: string | null
  avatar_url: string | null
  notes: string | null
  department_id: number | null
  course_id: number | null
  semester: number | null
  section: string | null
  academic_year: string | null
  designation: string | null
  office_location: string | null
  guardian_name: string | null
  guardian_phone: string | null
  address: string | null
  overdue_loans: number
  active_reservations: number
  borrow_limit: number
  eligible_to_borrow: boolean
  ineligibility_reason: string | null
}

export interface Department {
  id: number
  code: string
  name: string
  description: string | null
  is_active: boolean
  course_count: number
}

export interface Course {
  id: number
  code: string
  name: string
  department_id: number | null
  department_name: string | null
  duration_semesters: number | null
  is_active: boolean
}

export interface Loan {
  id: number
  copy_id: number
  member_id: number
  issued_at: string
  due_at: string
  returned_at: string | null
  status: LoanStatus
  renewal_count: number
  overdue_days: number
  notes: string | null
  book_id: number | null
  book_title: string | null
  accession_number: string | null
  member_name: string | null
  member_email: string | null
  issued_by_name: string | null
  returned_by_name: string | null
  days_overdue: number
  is_overdue: boolean
  fine_amount: number | null
}

export interface LoanRenewal {
  id: number
  loan_id: number
  previous_due_at: string
  new_due_at: string
  renewal_number: number
  renewed_at: string
  note: string | null
  renewed_by_name: string | null
}

export interface LoanDetail extends Loan {
  renewals: LoanRenewal[]
  fine_id: number | null
}

export interface Reservation {
  id: number
  book_id: number
  member_id: number
  copy_id: number | null
  status: ReservationStatus
  position: number
  queue_position: number
  reserved_at: string
  ready_at: string | null
  pickup_deadline: string | null
  fulfilled_at: string | null
  cancelled_at: string | null
  expired_at: string | null
  book_title: string | null
  book_authors: string[]
  member_name: string | null
  accession_number: string | null
  shelf_location: string | null
}

export interface FinePayment {
  id: number
  fine_id: number
  amount: string
  method: PaymentMethod
  reference: string | null
  paid_at: string
  notes: string | null
  recorded_by_name: string | null
}

export interface Fine {
  id: number
  member_id: number
  loan_id: number | null
  amount: string
  amount_paid: string
  outstanding: string
  days_overdue: number
  rate_per_day: string
  reason: string
  status: FineStatus
  assessed_at: string
  waived_at: string | null
  waiver_reason: string | null
  notes: string | null
  member_name: string | null
  member_email: string | null
  book_title: string | null
  payments: FinePayment[]
}

export interface NotificationItem {
  id: number
  user_id: number
  recipient_email: string
  type: string
  channel: string
  status: NotificationStatus
  subject: string
  attempts: number
  last_error: string | null
  created_at: string
  sent_at: string | null
  last_attempt_at: string | null
}

export interface NotificationStats {
  queued: number
  sending: number
  sent: number
  failed: number
  cancelled: number
  total: number
  failure_rate: number
}

export interface DashboardStats {
  total_books: number
  total_copies: number
  available_copies: number
  issued_copies: number
  total_members: number
  active_members: number
  active_loans: number
  overdue_loans: number
  due_today: number
  pending_reservations: number
  outstanding_fines: number
  fines_collected: number
  notifications_queued: number
  notifications_failed: number
  loans_issued_today: number
  returns_today: number
}

export interface AuditEntry {
  id: number
  actor_email: string | null
  action: string
  summary: string
  created_at: string
}

export interface AdminDashboard {
  stats: DashboardStats
  recent_activity: AuditEntry[]
  total_loan_events: number
}

export interface PersonalDashboard {
  current_loans: Loan[]
  reservations: Reservation[]
  outstanding_fines: number
  overdue_count: number
  [key: string]: unknown
}

export interface Policy {
  id: number
  institution_name: string
  library_email: string
  library_phone: string
  library_address: string
  opening_hours: string
  max_books_student: number
  max_books_faculty: number
  max_books_staff: number
  loan_period_days_student: number
  loan_period_days_faculty: number
  max_renewals: number
  renewal_period_days: number
  max_fine_blocks_renewal: number
  max_fine_blocks_issue: number
  fine_per_day: number
  grace_period_days: number
  max_fine_per_loan: number
  currency_code: string
  reservation_pickup_days: number
  max_active_reservations: number
  reservation_expiry_hours: number
  due_reminder_days: number[]
  overdue_reminder_days: number[]
  membership_expiry_reminder_days: number[]
  max_overdue_reminders: number
  membership_validity_days_student: number
  membership_validity_days_faculty: number
  updated_at: string | null
}

export interface RoleInfo {
  role: Role
  permissions: string[]
}

export interface AuditLog {
  id: number
  actor_id: number | null
  actor_email: string | null
  actor_role: string | null
  action: string
  entity_type: string | null
  entity_id: number | null
  summary: string
  metadata: Record<string, unknown> | null
  ip_address: string | null
  user_agent: string | null
  created_at: string
}

export interface ImportResult {
  total_rows: number
  created: number
  updated: number
  skipped: number
  failed: number
  errors: { row_number?: number; message?: string; errors?: string[] }[]
}

export interface ReportRow {
  [key: string]: string | number | boolean | null
}
