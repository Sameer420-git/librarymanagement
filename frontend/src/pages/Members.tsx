import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Download, Search, Upload, UserPlus } from "lucide-react"
import { useRef, useState, type ChangeEvent, type FormEvent } from "react"
import { Link, useSearchParams } from "react-router-dom"

import {
  Button,
  Card,
  EmptyState,
  ErrorBlock,
  Field,
  Input,
  LoadingBlock,
  Modal,
  PageHeader,
  Pagination,
  Select,
  StatusBadge,
  Table,
  Td,
  Textarea,
  Th,
} from "../components/ui"
import { api, downloadFile, getErrorMessage } from "../lib/api"
import { useDebounced } from "../lib/hooks"
import { formatMoney } from "../lib/format"
import type {
  Course,
  Department,
  ImportResult,
  MemberListItem,
  Page,
} from "../lib/types"

interface MemberFormState {
  first_name: string
  last_name: string
  email: string
  institutional_id: string
  phone: string
  role: "STUDENT" | "FACULTY"
  password: string
  membership_expires: string
  notes: string
  enrollment_number: string
  course_id: string
  semester: string
  section: string
  academic_year: string
  employee_id: string
  department_id: string
  designation: string
}

const emptyMember: MemberFormState = {
  first_name: "",
  last_name: "",
  email: "",
  institutional_id: "",
  phone: "",
  role: "STUDENT",
  password: "",
  membership_expires: "",
  notes: "",
  enrollment_number: "",
  course_id: "",
  semester: "",
  section: "",
  academic_year: "",
  employee_id: "",
  department_id: "",
  designation: "",
}

export function MembersPage() {
  const queryClient = useQueryClient()
  const [params, setParams] = useSearchParams()

  const [search, setSearch] = useState("")
  const debouncedSearch = useDebounced(search)
  const [role, setRole] = useState("")
  const [status, setStatus] = useState("")
  const [departmentId, setDepartmentId] = useState("")
  const [page, setPage] = useState(1)

  const [modalOpen, setModalOpen] = useState(params.get("new") === "1")
  const [form, setForm] = useState<MemberFormState>(emptyMember)
  const [formError, setFormError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [importOpen, setImportOpen] = useState(false)
  const [importResult, setImportResult] = useState<ImportResult | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const membersQuery = useQuery({
    queryKey: ["members", { search: debouncedSearch, role, status, departmentId, page }],
    queryFn: async () =>
      (
        await api.get<Page<MemberListItem>>("/members", {
          params: {
            search: debouncedSearch || undefined,
            role: role || undefined,
            status: status || undefined,
            department_id: departmentId || undefined,
            page,
            page_size: 20,
          },
        })
      ).data,
  })

  const departmentsQuery = useQuery({
    queryKey: ["departments"],
    queryFn: async () => (await api.get<Department[]>("/members/departments/all")).data,
  })

  const coursesQuery = useQuery({
    queryKey: ["courses"],
    queryFn: async () => (await api.get<Course[]>("/members/courses/all")).data,
  })

  const createMember = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await api.post("/members", payload)).data,
    onSuccess: (member: { full_name?: string; email?: string }) => {
      void queryClient.invalidateQueries({ queryKey: ["members"] })
      setModalOpen(false)
      setForm(emptyMember)
      setParams({})
      setNotice(`Member ${member.full_name ?? member.email ?? ""} registered.`)
    },
    onError: (error) => setFormError(getErrorMessage(error)),
  })

  const importMembers = useMutation({
    mutationFn: async (file: File) => {
      const data = new FormData()
      data.append("file", file)
      return (await api.post<ImportResult>("/members/import", data)).data
    },
    onSuccess: (result) => {
      setImportResult(result)
      void queryClient.invalidateQueries({ queryKey: ["members"] })
    },
    onError: (error) =>
      setImportResult({
        total_rows: 0,
        created: 0,
        updated: 0,
        skipped: 0,
        failed: 1,
        errors: [{ message: getErrorMessage(error) }],
      }),
  })

  const update = <K extends keyof MemberFormState>(key: K, value: MemberFormState[K]) =>
    setForm((current) => ({ ...current, [key]: value }))

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    setFormError(null)
    const payload: Record<string, unknown> = {
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      email: form.email.trim(),
      institutional_id: form.institutional_id.trim() || null,
      phone: form.phone.trim() || null,
      role: form.role,
      password: form.password || null,
      membership_expires: form.membership_expires || null,
      notes: form.notes.trim() || null,
    }
    if (form.role === "STUDENT") {
      payload.enrollment_number = form.enrollment_number.trim() || null
      payload.course_id = form.course_id || null
      payload.semester = form.semester ? Number(form.semester) : null
      payload.section = form.section.trim() || null
      payload.academic_year = form.academic_year.trim() || null
    } else {
      payload.employee_id = form.employee_id.trim() || null
      payload.department_id = form.department_id || null
      payload.designation = form.designation.trim() || null
    }
    createMember.mutate(payload)
  }

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) importMembers.mutate(file)
    event.target.value = ""
  }

  const members = membersQuery.data?.items ?? []
  const pagination = membersQuery.data?.pagination

  return (
    <>
      <PageHeader
        title="Members"
        description="Students and faculty registered with the library."
        actions={
          <>
            <Button variant="secondary" onClick={() => setImportOpen(true)}>
              <Upload className="h-4 w-4" /> Import
            </Button>
            <Button
              variant="secondary"
              onClick={() => void downloadFile("/members/export/csv", "members.csv")}
            >
              <Download className="h-4 w-4" /> Export
            </Button>
            <Button
              onClick={() => {
                setFormError(null)
                setModalOpen(true)
              }}
            >
              <UserPlus className="h-4 w-4" /> Register member
            </Button>
          </>
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

      <Card padded={false}>
        <div className="flex flex-wrap items-end gap-3 border-b border-slate-100 p-4">
          <div className="relative min-w-56 flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input
              className="pl-9"
              placeholder="Search name, e-mail, ID or enrollment numberâ€¦"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                setPage(1)
              }}
            />
          </div>
          <Select
            className="w-36"
            value={role}
            onChange={(event) => {
              setRole(event.target.value)
              setPage(1)
            }}
          >
            <option value="">All roles</option>
            <option value="STUDENT">Students</option>
            <option value="FACULTY">Faculty</option>
          </Select>
          <Select
            className="w-40"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value)
              setPage(1)
            }}
          >
            <option value="">All statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="PENDING">Pending</option>
            <option value="SUSPENDED">Suspended</option>
            <option value="INACTIVE">Inactive</option>
          </Select>
          <Select
            className="w-48"
            value={departmentId}
            onChange={(event) => {
              setDepartmentId(event.target.value)
              setPage(1)
            }}
          >
            <option value="">All departments</option>
            {departmentsQuery.data?.map((department) => (
              <option key={department.id} value={department.id}>
                {department.name}
              </option>
            ))}
          </Select>
        </div>

        {membersQuery.isLoading ? (
          <LoadingBlock label="Loading membersâ€¦" />
        ) : membersQuery.isError ? (
          <ErrorBlock
            message={getErrorMessage(membersQuery.error)}
            onRetry={() => void membersQuery.refetch()}
          />
        ) : members.length === 0 ? (
          <EmptyState
            title="No members found"
            description="Adjust the filters or register a new member."
            action={
              <Button size="sm" onClick={() => setModalOpen(true)}>
                Register member
              </Button>
            }
          />
        ) : (
          <>
            <Table>
              <thead>
                <tr>
                  <Th>Member</Th>
                  <Th>Role</Th>
                  <Th>ID</Th>
                  <Th>Department / course</Th>
                  <Th>Loans</Th>
                  <Th>Fines</Th>
                  <Th>Status</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              </thead>
              <tbody>
                {members.map((member) => (
                  <tr key={member.id} className="hover:bg-slate-50/60">
                    <Td>
                      <Link
                        to={`/members/${member.id}`}
                        className="font-medium text-slate-800 hover:text-brand-700"
                      >
                        {member.full_name}
                      </Link>
                      <p className="text-[11px] text-slate-500">{member.email}</p>
                    </Td>
                    <Td className="text-xs font-medium text-slate-600">
                      {member.role === "FACULTY" ? "Faculty" : "Student"}
                    </Td>
                    <Td className="font-mono text-xs text-slate-500">
                      {member.institutional_id ?? member.enrollment_number ?? "â€”"}
                    </Td>
                    <Td className="text-xs text-slate-500">
                      {member.department_name ?? member.course_name ?? "â€”"}
                    </Td>
                    <Td className="text-sm font-semibold text-slate-700">
                      {member.active_loans}
                    </Td>
                    <Td
                      className={
                        member.outstanding_fines > 0
                          ? "text-sm font-semibold text-rose-600"
                          : "text-sm text-slate-400"
                      }
                    >
                      {formatMoney(member.outstanding_fines)}
                    </Td>
                    <Td>
                      <StatusBadge status={member.status} />
                    </Td>
                    <Td className="text-right">
                      <Link to={`/members/${member.id}`}>
                        <Button variant="ghost" size="sm">
                          View
                        </Button>
                      </Link>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
            {pagination ? (
              <div className="px-4">
                <Pagination
                  page={pagination.page}
                  pageSize={pagination.page_size}
                  total={pagination.total}
                  onPageChange={setPage}
                />
              </div>
            ) : null}
          </>
        )}
      </Card>

      <Modal
        open={modalOpen}
        onClose={() => {
          setModalOpen(false)
          setFormError(null)
          setParams({})
        }}
        title="Register a member"
        description="Members can sign in as soon as an initial password is set."
        size="lg"
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setModalOpen(false)
                setFormError(null)
                setParams({})
              }}
            >
              Cancel
            </Button>
            <Button type="submit" form="member-form" loading={createMember.isPending}>
              Register member
            </Button>
          </>
        }
      >
        <form id="member-form" onSubmit={onSubmit} className="space-y-4">
          {formError ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {formError}
            </p>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Role" required>
              <Select
                value={form.role}
                onChange={(event) => update("role", event.target.value as "STUDENT" | "FACULTY")}
              >
                <option value="STUDENT">Student</option>
                <option value="FACULTY">Faculty</option>
              </Select>
            </Field>
            <Field label="Institutional ID">
              <Input
                value={form.institutional_id}
                onChange={(event) => update("institutional_id", event.target.value)}
                placeholder={form.role === "STUDENT" ? "STU-2026-001" : "FAC-2026-001"}
              />
            </Field>
            <Field label="First name" required>
              <Input
                value={form.first_name}
                onChange={(event) => update("first_name", event.target.value)}
                required
              />
            </Field>
            <Field label="Last name" required>
              <Input
                value={form.last_name}
                onChange={(event) => update("last_name", event.target.value)}
                required
              />
            </Field>
            <Field label="E-mail address" required>
              <Input
                type="email"
                value={form.email}
                onChange={(event) => update("email", event.target.value)}
                required
              />
            </Field>
            <Field label="Phone">
              <Input
                value={form.phone}
                onChange={(event) => update("phone", event.target.value)}
              />
            </Field>
            <Field
              label="Initial password"
              hint="Leave blank to generate a temporary password."
            >
              <Input
                type="password"
                minLength={8}
                value={form.password}
                onChange={(event) => update("password", event.target.value)}
                placeholder="At least 8 characters"
              />
            </Field>
            <Field label="Membership expires">
              <Input
                type="date"
                value={form.membership_expires}
                onChange={(event) => update("membership_expires", event.target.value)}
              />
            </Field>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
              {form.role === "STUDENT" ? "Student details" : "Faculty details"}
            </p>
            {form.role === "STUDENT" ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Enrollment number">
                  <Input
                    value={form.enrollment_number}
                    onChange={(event) => update("enrollment_number", event.target.value)}
                  />
                </Field>
                <Field label="Course">
                  <Select
                    value={form.course_id}
                    onChange={(event) => update("course_id", event.target.value)}
                  >
                    <option value="">Not assigned</option>
                    {coursesQuery.data?.map((course) => (
                      <option key={course.id} value={course.id}>
                        {course.name}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Semester">
                  <Input
                    type="number"
                    min={1}
                    max={12}
                    value={form.semester}
                    onChange={(event) => update("semester", event.target.value)}
                  />
                </Field>
                <Field label="Section">
                  <Input
                    value={form.section}
                    onChange={(event) => update("section", event.target.value)}
                    placeholder="A"
                  />
                </Field>
                <Field label="Academic year">
                  <Input
                    value={form.academic_year}
                    onChange={(event) => update("academic_year", event.target.value)}
                    placeholder="2026-27"
                  />
                </Field>
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Employee ID">
                  <Input
                    value={form.employee_id}
                    onChange={(event) => update("employee_id", event.target.value)}
                  />
                </Field>
                <Field label="Department">
                  <Select
                    value={form.department_id}
                    onChange={(event) => update("department_id", event.target.value)}
                  >
                    <option value="">Not assigned</option>
                    {departmentsQuery.data?.map((department) => (
                      <option key={department.id} value={department.id}>
                        {department.name}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Designation">
                  <Input
                    value={form.designation}
                    onChange={(event) => update("designation", event.target.value)}
                    placeholder="Assistant Professor"
                  />
                </Field>
              </div>
            )}
          </div>

          <Field label="Notes">
            <Textarea
              rows={2}
              value={form.notes}
              onChange={(event) => update("notes", event.target.value)}
            />
          </Field>
        </form>
      </Modal>

      <Modal
        open={importOpen}
        onClose={() => {
          setImportOpen(false)
          setImportResult(null)
        }}
        title="Import members from CSV"
        description="Columns: email, first_name, last_name, role, institutional_id, password, enrollment_number, course_code, semester, section, academic_year, employee_id, department_code, designation, phone, membership_expires."
        footer={
          <>
            <Button variant="secondary" onClick={() => setImportOpen(false)}>
              Close
            </Button>
            <Button onClick={() => fileRef.current?.click()} loading={importMembers.isPending}>
              <Upload className="h-4 w-4" /> Choose file
            </Button>
          </>
        }
      >
        <input
          ref={fileRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={onFileChange}
        />
        {importResult ? (
          <div className="space-y-3 text-sm">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {[
                ["Rows", importResult.total_rows],
                ["Created", importResult.created],
                ["Skipped", importResult.skipped],
                ["Failed", importResult.failed],
              ].map(([label, value]) => (
                <div key={String(label)} className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-[11px] font-semibold uppercase text-slate-500">
                    {label}
                  </p>
                  <p className="text-lg font-semibold text-slate-800">{value}</p>
                </div>
              ))}
            </div>
            {importResult.errors.length > 0 ? (
              <ul className="max-h-48 space-y-1 overflow-y-auto rounded-lg border border-rose-100 bg-rose-50 p-3 text-xs text-rose-700">
                {importResult.errors.map((error, index) => (
                  <li key={index}>
                    {error.row_number ? `Row ${error.row_number}: ` : ""}
                    {error.message ?? error.errors?.join(", ")}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-slate-500">
            Each row is validated before writing. Existing e-mail addresses are updated
            when possible; invalid rows are reported.
          </p>
        )}
      </Modal>
    </>
  )
}
