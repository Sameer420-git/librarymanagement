import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  AlertTriangle,
  ArrowLeft,
  BadgeCheck,
  BookOpen,
  CalendarClock,
  Pencil,
  ShieldAlert,
  Wallet,
} from "lucide-react"
import { useState, type FormEvent, type ReactNode } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"

import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBlock,
  Field,
  Input,
  LoadingBlock,
  Modal,
  PageHeader,
  Select,
  StatCard,
  StatusBadge,
  Table,
  Tabs,
  Td,
  Textarea,
  Th,
} from "../components/ui"
import { useAuth } from "../context/AuthContext"
import { api, getErrorMessage } from "../lib/api"
import { formatDate, formatDateTime, formatMoney, humanize } from "../lib/format"
import { isStaff } from "../lib/permissions"
import type {
  Course,
  Department,
  Fine,
  Loan,
  MemberProfile,
  Page,
  Reservation,
  UserStatus,
} from "../lib/types"

type TabKey = "loans" | "fines" | "reservations"

const statusOptions: UserStatus[] = ["ACTIVE", "PENDING", "SUSPENDED", "INACTIVE"]

export function MemberDetailPage() {
  const { id } = useParams<{ id: string }>()
  const memberId = Number(id)
  const { user } = useAuth()
  const staff = isStaff(user?.role)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [tab, setTab] = useState<TabKey>("loans")
  const [editOpen, setEditOpen] = useState(false)
  const [statusOpen, setStatusOpen] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const memberQuery = useQuery({
    queryKey: ["member", memberId],
    queryFn: async () => (await api.get<MemberProfile>(`/members/${memberId}`)).data,
    enabled: Number.isFinite(memberId),
  })

  const loansQuery = useQuery({
    queryKey: ["member-loans", memberId],
    queryFn: async () =>
      (
        await api.get<Page<Loan>>(`/members/${memberId}/loans`, {
          params: { page_size: 50 },
        })
      ).data,
    enabled: Number.isFinite(memberId) && tab === "loans",
  })

  const finesQuery = useQuery({
    queryKey: ["member-fines", memberId],
    queryFn: async () =>
      (
        await api.get<Page<Fine>>(`/members/${memberId}/fines`, {
          params: { page_size: 50 },
        })
      ).data,
    enabled: Number.isFinite(memberId) && tab === "fines",
  })

  const reservationsQuery = useQuery({
    queryKey: ["member-reservations", memberId],
    queryFn: async () =>
      (
        await api.get<Page<Reservation>>(`/members/${memberId}/reservations`, {
          params: { page_size: 50 },
        })
      ).data,
    enabled: Number.isFinite(memberId) && tab === "reservations",
  })

  const departmentsQuery = useQuery({
    queryKey: ["departments"],
    queryFn: async () => (await api.get<Department[]>("/members/departments/all")).data,
    enabled: staff && editOpen,
  })

  const coursesQuery = useQuery({
    queryKey: ["courses"],
    queryFn: async () => (await api.get<Course[]>("/members/courses/all")).data,
    enabled: staff && editOpen,
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["member", memberId] })
    void queryClient.invalidateQueries({ queryKey: ["members"] })
    void queryClient.invalidateQueries({ queryKey: ["member-loans", memberId] })
    void queryClient.invalidateQueries({ queryKey: ["member-fines", memberId] })
    void queryClient.invalidateQueries({ queryKey: ["member-reservations", memberId] })
  }

  const updateMember = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await api.put<MemberProfile>(`/members/${memberId}`, payload)).data,
    onSuccess: () => {
      invalidate()
      setEditOpen(false)
      setNotice("Member profile updated.")
    },
    onError: (error) => setFormError(getErrorMessage(error)),
  })

  const changeStatus = useMutation({
    mutationFn: async (status: UserStatus) =>
      (
        await api.patch<MemberProfile>(`/members/${memberId}/status`, null, {
          params: { status },
        })
      ).data,
    onSuccess: (member) => {
      invalidate()
      setStatusOpen(false)
      setNotice(`Membership status set to ${humanize(member.status)}.`)
    },
    onError: (error) => setFormError(getErrorMessage(error)),
  })

  if (memberQuery.isLoading) return <LoadingBlock label="Loading member…" />
  if (memberQuery.isError || !memberQuery.data) {
    return (
      <ErrorBlock
        message={getErrorMessage(memberQuery.error)}
        onRetry={() => void memberQuery.refetch()}
      />
    )
  }

  const member = memberQuery.data
  const initials = `${member.first_name[0] ?? ""}${member.last_name[0] ?? ""}`.toUpperCase()
  const isStudent = member.role === "STUDENT"

  return (
    <>
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-800"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back
      </button>

      <PageHeader
        title={member.full_name}
        description={`${isStudent ? "Student" : "Faculty"} · ${member.email}`}
        actions={
          staff ? (
            <>
              <Button
                variant="secondary"
                onClick={() => {
                  setFormError(null)
                  setStatusOpen(true)
                }}
              >
                <ShieldAlert className="h-4 w-4" /> Change status
              </Button>
              <Button
                onClick={() => {
                  setFormError(null)
                  setEditOpen(true)
                }}
              >
                <Pencil className="h-4 w-4" /> Edit profile
              </Button>
            </>
          ) : null
        }
      />

      {notice ? (
        <div className="flex items-start justify-between gap-3 rounded-lg border border-brand-200 bg-brand-50 px-4 py-2.5 text-sm text-brand-800">
          <span>{notice}</span>
          <button
            type="button"
            className="text-xs font-semibold underline"
            onClick={() => setNotice(null)}
          >
            Dismiss
          </button>
        </div>
      ) : null}

      {!member.eligible_to_borrow && staff ? (
        <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-semibold">Borrowing is currently blocked</p>
            <p className="text-xs text-amber-700">
              {member.ineligibility_reason ?? "This member cannot borrow at the moment."}
            </p>
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <div className="flex items-center gap-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-100 text-xl font-semibold text-brand-700">
              {initials}
            </div>
            <div className="min-w-0">
              <p className="truncate text-base font-semibold text-slate-900">
                {member.full_name}
              </p>
              <p className="truncate text-xs text-slate-500">{member.email}</p>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                <StatusBadge status={member.status} />
                <Badge tone="slate">{member.membership_type}</Badge>
                {member.is_email_verified ? (
                  <Badge tone="green">
                    <BadgeCheck className="h-3 w-3" /> Verified
                  </Badge>
                ) : (
                  <Badge tone="amber">Unverified</Badge>
                )}
              </div>
            </div>
          </div>

          <dl className="mt-5 space-y-3 text-sm">
            <Row label="Institutional ID" value={member.institutional_id} mono />
            <Row label="Phone" value={member.phone} />
            {isStudent ? (
              <>
                <Row label="Enrollment" value={member.enrollment_number} mono />
                <Row label="Course" value={member.course_name} />
                <Row
                  label="Semester"
                  value={
                    member.semester
                      ? `${member.semester}${member.section ? ` · Section ${member.section}` : ""}`
                      : null
                  }
                />
                <Row label="Academic year" value={member.academic_year} />
              </>
            ) : (
              <>
                <Row label="Employee ID" value={member.employee_id} mono />
                <Row label="Department" value={member.department_name} />
                <Row label="Designation" value={member.designation} />
                <Row label="Office" value={member.office_location} />
              </>
            )}
            <Row label="Joined" value={formatDate(member.created_at)} />
            <Row
              label="Membership expires"
              value={member.membership_expires ? formatDate(member.membership_expires) : "No expiry"}
            />
            <Row label="Last login" value={formatDateTime(member.last_login_at)} />
            {member.guardian_name ? (
              <Row
                label="Guardian"
                value={`${member.guardian_name}${member.guardian_phone ? ` · ${member.guardian_phone}` : ""}`}
              />
            ) : null}
          </dl>

          {member.notes ? (
            <div className="mt-5 rounded-lg bg-slate-50 p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                Notes
              </p>
              <p className="mt-1 whitespace-pre-line text-xs text-slate-600">
                {member.notes}
              </p>
            </div>
          ) : null}
        </Card>

        <div className="grid gap-4 lg:col-span-2 lg:grid-cols-2">
          <StatCard
            label="Active loans"
            value={member.active_loans}
            hint={`Borrow limit ${member.borrow_limit}`}
            icon={<BookOpen className="h-5 w-5" />}
            tone="brand"
          />
          <StatCard
            label="Overdue"
            value={member.overdue_loans}
            hint={member.overdue_loans ? "Needs follow-up" : "Nothing overdue"}
            icon={<CalendarClock className="h-5 w-5" />}
            tone={member.overdue_loans ? "rose" : "emerald"}
          />
          <StatCard
            label="Outstanding fines"
            value={formatMoney(member.outstanding_fines)}
            hint="Unpaid balance"
            icon={<Wallet className="h-5 w-5" />}
            tone={member.outstanding_fines > 0 ? "amber" : "slate"}
          />
          <StatCard
            label="Reservations"
            value={member.active_reservations}
            hint="Active holds"
            icon={<CalendarClock className="h-5 w-5" />}
            tone="sky"
          />
          <Card title="Borrowing allowance" className="lg:col-span-2">
            <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
              <span>
                {member.active_loans} of {member.borrow_limit} slots in use
              </span>
              <span>{Math.max(member.borrow_limit - member.active_loans, 0)} remaining</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className={
                  member.active_loans >= member.borrow_limit
                    ? "h-full rounded-full bg-rose-500"
                    : "h-full rounded-full bg-brand-500"
                }
                style={{
                  width: `${
                    member.borrow_limit > 0
                      ? Math.min((member.active_loans / member.borrow_limit) * 100, 100)
                      : 0
                  }%`,
                }}
              />
            </div>
            <p className="mt-3 text-xs text-slate-500">
              {member.eligible_to_borrow
                ? "This member is eligible to borrow."
                : member.ineligibility_reason ?? "This member is currently ineligible."}
            </p>
          </Card>
        </div>
      </div>

      <Card padded={false}>
        <div className="border-b border-slate-100 px-4 pt-4">
          <Tabs
            value={tab}
            onChange={(value) => setTab(value as TabKey)}
            items={[
              { key: "loans", label: "Loans" },
              { key: "fines", label: "Fines" },
              { key: "reservations", label: "Reservations" },
            ]}
          />
        </div>

        {tab === "loans" ? (
          <TabBody
            loading={loansQuery.isLoading}
            error={loansQuery.error}
            onRetry={() => void loansQuery.refetch()}
            empty={!loansQuery.data || loansQuery.data.items.length === 0}
            emptyTitle="No loans recorded"
          >
            <Table>
              <thead>
                <tr>
                  <Th>Title</Th>
                  <Th>Accession</Th>
                  <Th>Issued</Th>
                  <Th>Due</Th>
                  <Th>Status</Th>
                  <Th>Renewals</Th>
                </tr>
              </thead>
              <tbody>
                {loansQuery.data?.items.map((loan) => (
                  <tr key={loan.id} className="hover:bg-slate-50/60">
                    <Td>
                      {loan.book_id ? (
                        <Link
                          to={`/catalogue/${loan.book_id}`}
                          className="font-medium text-slate-800 hover:text-brand-700"
                        >
                          {loan.book_title}
                        </Link>
                      ) : (
                        loan.book_title ?? "—"
                      )}
                    </Td>
                    <Td className="font-mono text-xs text-slate-500">
                      {loan.accession_number ?? "—"}
                    </Td>
                    <Td className="text-xs text-slate-500">{formatDate(loan.issued_at)}</Td>
                    <Td className="text-xs text-slate-500">
                      {formatDate(loan.due_at)}
                      {loan.is_overdue ? (
                        <span className="ml-1 font-semibold text-rose-600">
                          +{loan.days_overdue}d
                        </span>
                      ) : null}
                    </Td>
                    <Td>
                      <StatusBadge status={loan.status} />
                    </Td>
                    <Td className="text-xs text-slate-500">{loan.renewal_count}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TabBody>
        ) : null}

        {tab === "fines" ? (
          <TabBody
            loading={finesQuery.isLoading}
            error={finesQuery.error}
            onRetry={() => void finesQuery.refetch()}
            empty={!finesQuery.data || finesQuery.data.items.length === 0}
            emptyTitle="No fines on record"
          >
            <Table>
              <thead>
                <tr>
                  <Th>Reason</Th>
                  <Th>Book</Th>
                  <Th>Assessed</Th>
                  <Th>Amount</Th>
                  <Th>Outstanding</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {finesQuery.data?.items.map((fine) => (
                  <tr key={fine.id} className="hover:bg-slate-50/60">
                    <Td className="text-xs text-slate-600">{fine.reason}</Td>
                    <Td className="text-xs text-slate-600">{fine.book_title ?? "—"}</Td>
                    <Td className="text-xs text-slate-500">{formatDate(fine.assessed_at)}</Td>
                    <Td className="text-sm text-slate-700">{formatMoney(fine.amount)}</Td>
                    <Td
                      className={
                        Number(fine.outstanding) > 0
                          ? "text-sm font-semibold text-rose-600"
                          : "text-sm text-slate-400"
                      }
                    >
                      {formatMoney(fine.outstanding)}
                    </Td>
                    <Td>
                      <StatusBadge status={fine.status} />
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TabBody>
        ) : null}

        {tab === "reservations" ? (
          <TabBody
            loading={reservationsQuery.isLoading}
            error={reservationsQuery.error}
            onRetry={() => void reservationsQuery.refetch()}
            empty={!reservationsQuery.data || reservationsQuery.data.items.length === 0}
            emptyTitle="No reservations"
          >
            <Table>
              <thead>
                <tr>
                  <Th>Title</Th>
                  <Th>Reserved</Th>
                  <Th>Queue</Th>
                  <Th>Pickup by</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {reservationsQuery.data?.items.map((reservation) => (
                  <tr key={reservation.id} className="hover:bg-slate-50/60">
                    <Td>
                      <Link
                        to={`/catalogue/${reservation.book_id}`}
                        className="font-medium text-slate-800 hover:text-brand-700"
                      >
                        {reservation.book_title}
                      </Link>
                    </Td>
                    <Td className="text-xs text-slate-500">
                      {formatDate(reservation.reserved_at)}
                    </Td>
                    <Td className="text-xs text-slate-500">
                      {reservation.status === "READY" ? "Ready" : `#${reservation.queue_position}`}
                    </Td>
                    <Td className="text-xs text-slate-500">
                      {formatDate(reservation.pickup_deadline)}
                    </Td>
                    <Td>
                      <StatusBadge status={reservation.status} />
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TabBody>
        ) : null}
      </Card>

      <EditMemberModal
        key={editOpen ? "open" : "closed"}
        open={editOpen}
        member={member}
        departments={departmentsQuery.data ?? []}
        courses={coursesQuery.data ?? []}
        error={formError}
        saving={updateMember.isPending}
        onClose={() => {
          setEditOpen(false)
          setFormError(null)
        }}
        onSave={(payload) => {
          setFormError(null)
          updateMember.mutate(payload)
        }}
      />

      <Modal
        open={statusOpen}
        onClose={() => {
          setStatusOpen(false)
          setFormError(null)
        }}
        title="Change membership status"
        description="Suspending a member stops new loans and reservations but keeps their history."
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setStatusOpen(false)
                setFormError(null)
              }}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              form="member-status-form"
              loading={changeStatus.isPending}
            >
              Update status
            </Button>
          </>
        }
      >
        <form
          id="member-status-form"
          className="space-y-4"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault()
            const data = new FormData(event.currentTarget)
            changeStatus.mutate(data.get("status") as UserStatus)
          }}
        >
          {formError ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {formError}
            </p>
          ) : null}
          <Field label="Status" required>
            <Select name="status" defaultValue={member.status}>
              {statusOptions.map((status) => (
                <option key={status} value={status}>
                  {humanize(status)}
                </option>
              ))}
            </Select>
          </Field>
          <p className="text-xs text-slate-500">
            Current status: <strong>{humanize(member.status)}</strong>
          </p>
        </form>
      </Modal>
    </>
  )
}

function Row({
  label,
  value,
  mono,
}: {
  label: string
  value: string | null | undefined
  mono?: boolean
}) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="text-xs text-slate-400">{label}</dt>
      <dd
        className={`text-right text-xs text-slate-700 ${mono ? "font-mono" : ""}`}
      >
        {value || "—"}
      </dd>
    </div>
  )
}

function TabBody({
  loading,
  error,
  onRetry,
  empty,
  emptyTitle,
  children,
}: {
  loading: boolean
  error: unknown
  onRetry: () => void
  empty: boolean
  emptyTitle: string
  children: ReactNode
}) {
  if (loading) return <LoadingBlock />
  if (error) return <ErrorBlock message={getErrorMessage(error)} onRetry={onRetry} />
  if (empty) return <EmptyState title={emptyTitle} />
  return <>{children}</>
}

function EditMemberModal({
  open,
  member,
  departments,
  courses,
  error,
  saving,
  onClose,
  onSave,
}: {
  open: boolean
  member: MemberProfile
  departments: Department[]
  courses: Course[]
  error: string | null
  saving: boolean
  onClose: () => void
  onSave: (payload: Record<string, unknown>) => void
}) {
  const isStudent = member.role === "STUDENT"
  if (!open) return null

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Edit member profile"
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="edit-member-form" loading={saving}>
            Save changes
          </Button>
        </>
      }
    >
      <form
        id="edit-member-form"
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault()
          const data = new FormData(event.currentTarget)
          const text = (key: string) => {
            const value = String(data.get(key) ?? "").trim()
            return value || null
          }
          const payload: Record<string, unknown> = {
            first_name: text("first_name"),
            last_name: text("last_name"),
            email: text("email"),
            phone: text("phone"),
            institutional_id: text("institutional_id"),
            membership_expires: text("membership_expires"),
            notes: text("notes"),
          }
          if (isStudent) {
            payload.enrollment_number = text("enrollment_number")
            payload.course_id = data.get("course_id") ? Number(data.get("course_id")) : null
            payload.semester = data.get("semester") ? Number(data.get("semester")) : null
            payload.section = text("section")
            payload.academic_year = text("academic_year")
          } else {
            payload.employee_id = text("employee_id")
            payload.department_id = data.get("department_id")
              ? Number(data.get("department_id"))
              : null
            payload.designation = text("designation")
            payload.office_location = text("office_location")
          }
          onSave(payload)
        }}
      >
        {error ? (
          <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </p>
        ) : null}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="First name" required>
            <Input name="first_name" defaultValue={member.first_name} required />
          </Field>
          <Field label="Last name" required>
            <Input name="last_name" defaultValue={member.last_name} required />
          </Field>
          <Field label="E-mail" required>
            <Input name="email" type="email" defaultValue={member.email} required />
          </Field>
          <Field label="Phone">
            <Input name="phone" defaultValue={member.phone ?? ""} />
          </Field>
          <Field label="Institutional ID">
            <Input name="institutional_id" defaultValue={member.institutional_id ?? ""} />
          </Field>
          <Field label="Membership expires">
            <Input
              name="membership_expires"
              type="date"
              defaultValue={member.membership_expires ?? ""}
            />
          </Field>
          {isStudent ? (
            <>
              <Field label="Enrollment number">
                <Input
                  name="enrollment_number"
                  defaultValue={member.enrollment_number ?? ""}
                />
              </Field>
              <Field label="Course">
                <Select name="course_id" defaultValue={member.course_id ?? ""}>
                  <option value="">Not assigned</option>
                  {courses.map((course) => (
                    <option key={course.id} value={course.id}>
                      {course.name}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Semester">
                <Input
                  name="semester"
                  type="number"
                  min={1}
                  max={12}
                  defaultValue={member.semester ?? ""}
                />
              </Field>
              <Field label="Section">
                <Input name="section" defaultValue={member.section ?? ""} />
              </Field>
              <Field label="Academic year">
                <Input name="academic_year" defaultValue={member.academic_year ?? ""} />
              </Field>
            </>
          ) : (
            <>
              <Field label="Employee ID">
                <Input name="employee_id" defaultValue={member.employee_id ?? ""} />
              </Field>
              <Field label="Department">
                <Select name="department_id" defaultValue={member.department_id ?? ""}>
                  <option value="">Not assigned</option>
                  {departments.map((department) => (
                    <option key={department.id} value={department.id}>
                      {department.name}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Designation">
                <Input name="designation" defaultValue={member.designation ?? ""} />
              </Field>
              <Field label="Office location">
                <Input name="office_location" defaultValue={member.office_location ?? ""} />
              </Field>
            </>
          )}
          <Field label="Notes" className="sm:col-span-2">
            <Textarea name="notes" rows={3} defaultValue={member.notes ?? ""} />
          </Field>
        </div>
      </form>
    </Modal>
  )
}
