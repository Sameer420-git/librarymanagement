import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { BookUp2, CornerDownLeft, RefreshCw, Search } from "lucide-react"
import { useState, type FormEvent } from "react"
import { Link } from "react-router-dom"

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
  Pagination,
  Select,
  StatusBadge,
  Table,
  Td,
  Textarea,
  Th,
} from "../components/ui"
import { api, getErrorMessage } from "../lib/api"
import { useAuth } from "../context/AuthContext"
import { isStaff } from "../lib/permissions"
import { formatDate, humanize } from "../lib/format"
import { useDebounced } from "../lib/hooks"
import type {
  BookCopy,
  CopyCondition,
  Loan,
  MemberListItem,
  Page,
} from "../lib/types"

const conditions: CopyCondition[] = ["NEW", "GOOD", "FAIR", "POOR", "DAMAGED"]

export function CirculationPage() {
  const { user } = useAuth()
  const staff = isStaff(user?.role)
  const queryClient = useQueryClient()
  const [status, setStatus] = useState("ACTIVE")
  const [page, setPage] = useState(1)
  const [notice, setNotice] = useState<string | null>(null)

  const [issueOpen, setIssueOpen] = useState(false)
  const [returnLoan, setReturnLoan] = useState<Loan | null>(null)
  const [renewLoan, setRenewLoan] = useState<Loan | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const loansQuery = useQuery({
    queryKey: ["loans", { status, page }],
    queryFn: async () =>
      (
        await api.get<Page<Loan>>("/loans", {
          params: { status: status || undefined, page, page_size: 20 },
        })
      ).data,
  })

  const invalidateLoans = () => {
    void queryClient.invalidateQueries({ queryKey: ["loans"] })
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    void queryClient.invalidateQueries({ queryKey: ["fines"] })
    void queryClient.invalidateQueries({ queryKey: ["books"] })
    void queryClient.invalidateQueries({ queryKey: ["copies"] })
  }

  const issue = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await api.post<Loan>("/loans/issue", payload)).data,
    onSuccess: (loan) => {
      invalidateLoans()
      setIssueOpen(false)
      setNotice(
        `Issued "${loan.book_title ?? "copy"}" to ${loan.member_name ?? "member"} — due ${formatDate(loan.due_at)}.`,
      )
    },
    onError: (error) => setFormError(getErrorMessage(error)),
  })

  const returnLoanMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: Record<string, unknown> }) =>
      (await api.post<Loan>(`/loans/${id}/return`, payload)).data,
    onSuccess: (loan) => {
      invalidateLoans()
      setReturnLoan(null)
      setNotice(
        `"${loan.book_title ?? "Copy"}" returned.${
          loan.fine_amount ? ` Fine assessed: ${loan.fine_amount}.` : ""
        }`,
      )
    },
    onError: (error) => setFormError(getErrorMessage(error)),
  })

  const renew = useMutation({
    mutationFn: async ({ id, notes }: { id: number; notes: string }) =>
      (
        await api.post<Loan>(`/loans/${id}/renew`, { notes: notes || null })
      ).data,
    onSuccess: (loan) => {
      invalidateLoans()
      setRenewLoan(null)
      setNotice(`Renewed. New due date: ${formatDate(loan.due_at)}.`)
    },
    onError: (error) => setFormError(getErrorMessage(error)),
  })

  const loans = loansQuery.data?.items ?? []
  const pagination = loansQuery.data?.pagination

  return (
    <>
      <PageHeader
        title="Circulation"
        description={
          staff
            ? "Issue, renew and return books. Fines are assessed automatically on return."
            : "Your current and past loans. Renew a loan when you need more time."
        }
        actions={
          staff ? (
            <Button
              onClick={() => {
                setFormError(null)
                setIssueOpen(true)
              }}
            >
              <BookUp2 className="h-4 w-4" /> Issue book
            </Button>
          ) : undefined
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
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-4">
          <div className="flex items-center gap-2">
            {[
              { value: "ACTIVE", label: "On loan" },
              { value: "OVERDUE", label: "Overdue" },
              { value: "RETURNED", label: "Returned" },
              { value: "LOST", label: "Lost" },
              { value: "", label: "All" },
            ].map((option) => (
              <button
                key={option.label}
                type="button"
                onClick={() => {
                  setStatus(option.value)
                  setPage(1)
                }}
                className={
                  status === option.value
                    ? "rounded-full bg-slate-900 px-3.5 py-1.5 text-xs font-semibold text-white"
                    : "rounded-full bg-slate-100 px-3.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-200"
                }
              >
                {option.label}
              </button>
            ))}
          </div>
          <p className="text-xs text-slate-500">
            {pagination ? `${pagination.total} loan${pagination.total === 1 ? "" : "s"}` : ""}
          </p>
        </div>

        {loansQuery.isLoading ? (
          <LoadingBlock label="Loading loans…" />
        ) : loansQuery.isError ? (
          <ErrorBlock
            message={getErrorMessage(loansQuery.error)}
            onRetry={() => void loansQuery.refetch()}
          />
        ) : loans.length === 0 ? (
          <EmptyState
            title={status === "OVERDUE" ? "No overdue loans" : "No loans here"}
            description={
              status === "OVERDUE"
                ? "Every borrowed title is within its due date."
                : staff
                  ? "Issue a book to get started."
                  : "You have no loans in this view."
            }
          />
        ) : (
          <>
            <Table>
              <thead>
                <tr>
                  {staff ? <Th>Member</Th> : null}
                  <Th>Title</Th>
                  <Th>Issued</Th>
                  <Th>Due</Th>
                  <Th>Status</Th>
                  <Th>Renewals</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              </thead>
              <tbody>
                {loans.map((loan) => (
                  <tr key={loan.id} className="hover:bg-slate-50/60">
                    {staff ? (
                      <Td>
                        <Link
                          to={`/members/${loan.member_id}`}
                          className="font-medium text-slate-800 hover:text-brand-700"
                        >
                          {loan.member_name}
                        </Link>
                        <p className="text-[11px] text-slate-500">{loan.member_email}</p>
                      </Td>
                    ) : null}
                    <Td>
                      {loan.book_id ? (
                        <Link
                          to={`/catalogue/${loan.book_id}`}
                          className="font-medium text-slate-700 hover:text-brand-700"
                        >
                          {loan.book_title}
                        </Link>
                      ) : (
                        <span className="text-slate-700">{loan.book_title ?? "—"}</span>
                      )}
                      <p className="font-mono text-[11px] text-slate-500">
                        {loan.accession_number}
                      </p>
                    </Td>
                    <Td className="text-xs text-slate-500">{formatDate(loan.issued_at)}</Td>
                    <Td className="text-xs">
                      <span
                        className={
                          loan.is_overdue
                            ? "font-semibold text-rose-600"
                            : "text-slate-600"
                        }
                      >
                        {formatDate(loan.due_at)}
                      </span>
                      {loan.is_overdue ? (
                        <p className="text-[11px] font-medium text-rose-500">
                          {loan.days_overdue} day{loan.days_overdue === 1 ? "" : "s"} late
                        </p>
                      ) : null}
                    </Td>
                    <Td>
                      <StatusBadge status={loan.status} />
                      {loan.returned_at ? (
                        <p className="mt-0.5 text-[11px] text-slate-500">
                          {formatDate(loan.returned_at)}
                        </p>
                      ) : null}
                    </Td>
                    <Td className="text-xs text-slate-500">{loan.renewal_count}</Td>
                    <Td>
                      <div className="flex justify-end gap-1">
                        {loan.status === "ACTIVE" || loan.status === "OVERDUE" ? (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setFormError(null)
                                setRenewLoan(loan)
                              }}
                            >
                              <RefreshCw className="h-3.5 w-3.5" /> Renew
                            </Button>
                            {staff ? (
                              <Button
                                size="sm"
                                onClick={() => {
                                  setFormError(null)
                                  setReturnLoan(loan)
                                }}
                              >
                                <CornerDownLeft className="h-3.5 w-3.5" /> Return
                              </Button>
                            ) : null}
                          </>
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </div>
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

      <IssueModal
        key={issueOpen ? "open" : "closed"}
        open={issueOpen}
        error={formError}
        saving={issue.isPending}
        onClose={() => {
          setIssueOpen(false)
          setFormError(null)
        }}
        onIssue={(payload) => {
          setFormError(null)
          issue.mutate(payload)
        }}
      />

      <Modal
        open={returnLoan !== null}
        onClose={() => {
          setReturnLoan(null)
          setFormError(null)
        }}
        title="Return book"
        description={
          returnLoan
            ? `"${returnLoan.book_title}" borrowed by ${returnLoan.member_name}. Due ${formatDate(returnLoan.due_at)}.`
            : undefined
        }
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setReturnLoan(null)
                setFormError(null)
              }}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              form="return-form"
              loading={returnLoanMutation.isPending}
            >
              Confirm return
            </Button>
          </>
        }
      >
        <form
          id="return-form"
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            if (!returnLoan) return
            const data = new FormData(event.currentTarget)
            returnLoanMutation.mutate({
              id: returnLoan.id,
              payload: {
                copy_condition: data.get("copy_condition") || null,
                notes: String(data.get("notes") ?? "").trim() || null,
              },
            })
          }}
        >
          {formError ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {formError}
            </p>
          ) : null}
          {returnLoan?.is_overdue ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              This loan is {returnLoan.days_overdue} day
              {returnLoan.days_overdue === 1 ? "" : "s"} overdue. An overdue fine will be
              calculated automatically.
            </div>
          ) : null}
          <Field label="Condition on return" hint="Record any damage observed at the desk.">
            <Select name="copy_condition" defaultValue="GOOD">
              {conditions.map((condition) => (
                <option key={condition} value={condition}>
                  {humanize(condition)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Notes">
            <Textarea name="notes" rows={2} />
          </Field>
        </form>
      </Modal>

      <Modal
        open={renewLoan !== null}
        onClose={() => {
          setRenewLoan(null)
          setFormError(null)
        }}
        title="Renew loan"
        description={
          renewLoan
            ? `Current due date: ${formatDate(renewLoan.due_at)}. Renewal ${renewLoan.renewal_count + 1}.`
            : undefined
        }
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setRenewLoan(null)
                setFormError(null)
              }}
            >
              Cancel
            </Button>
            <Button type="submit" form="renew-form" loading={renew.isPending}>
              Renew
            </Button>
          </>
        }
      >
        <form
          id="renew-form"
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            if (!renewLoan) return
            const data = new FormData(event.currentTarget)
            renew.mutate({
              id: renewLoan.id,
              notes: String(data.get("notes") ?? "").trim(),
            })
          }}
        >
          {formError ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {formError}
            </p>
          ) : null}
          <p className="text-sm text-slate-600">
            Renewals are subject to the policy limit, outstanding fines and reservations
            on this title.
          </p>
          <Field label="Notes">
            <Textarea name="notes" rows={2} placeholder="Optional renewal note" />
          </Field>
        </form>
      </Modal>
    </>
  )
}

function IssueModal({
  open,
  error,
  saving,
  onClose,
  onIssue,
}: {
  open: boolean
  error: string | null
  saving: boolean
  onClose: () => void
  onIssue: (payload: Record<string, unknown>) => void
}) {
  const [memberSearch, setMemberSearch] = useState("")
  const [copySearch, setCopySearch] = useState("")
  const debouncedMember = useDebounced(memberSearch)
  const debouncedCopy = useDebounced(copySearch)
  const [member, setMember] = useState<MemberListItem | null>(null)
  const [copy, setCopy] = useState<BookCopy | null>(null)

  const membersQuery = useQuery({
    queryKey: ["issue-members", debouncedMember],
    queryFn: async () =>
      (
        await api.get<Page<MemberListItem>>("/members", {
          params: { search: debouncedMember, page_size: 6 },
        })
      ).data.items,
    enabled: open && debouncedMember.trim().length >= 2,
  })

  const copiesQuery = useQuery({
    queryKey: ["issue-copies", debouncedCopy],
    queryFn: async () =>
      (
        await api.get<Page<BookCopy>>("/copies", {
          params: {
            search: debouncedCopy,
            status: "AVAILABLE",
            page_size: 6,
          },
        })
      ).data.items,
    enabled: open && debouncedCopy.trim().length >= 2,
  })

  if (!open) return null

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Issue a book"
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            form="issue-form"
            loading={saving}
            disabled={!member || !copy}
          >
            Issue
          </Button>
        </>
      }
    >
      <form
        id="issue-form"
        className="space-y-4"
        onSubmit={(event: FormEvent<HTMLFormElement>) => {
          event.preventDefault()
          if (!member || !copy) return
          const data = new FormData(event.currentTarget)
          const dueLocal = String(data.get("due_at") ?? "")
          onIssue({
            member_id: member.id,
            copy_id: copy.id,
            due_at: dueLocal ? new Date(dueLocal).toISOString() : null,
            notes: String(data.get("notes") ?? "").trim() || null,
          })
        }}
      >
        {error ? (
          <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </p>
        ) : null}

        <div>
          <Field label="Member" required>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                className="pl-9"
                placeholder="Search by name, e-mail, ID or enrollment number…"
                value={memberSearch}
                onChange={(event) => {
                  setMemberSearch(event.target.value)
                  setMember(null)
                }}
                autoFocus
              />
            </div>
          </Field>
          {member ? (
            <div className="mt-2 flex items-center justify-between rounded-lg border border-brand-200 bg-brand-50 px-3 py-2">
              <div>
                <p className="text-sm font-semibold text-slate-800">{member.full_name}</p>
                <p className="text-xs text-slate-500">
                  {member.email} · {humanize(member.role)} ·{" "}
                  {member.active_loans} active loan{member.active_loans === 1 ? "" : "s"}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={member.status} />
                <Button variant="ghost" size="sm" onClick={() => setMember(null)}>
                  Change
                </Button>
              </div>
            </div>
          ) : membersQuery.isFetching ? (
            <p className="mt-1 text-xs text-slate-400">Searching…</p>
          ) : debouncedMember.trim().length >= 2 && (membersQuery.data ?? []).length === 0 ? (
            <p className="mt-1 text-xs text-slate-500">No matching members.</p>
          ) : (
            <ul className="mt-1 max-h-44 divide-y divide-slate-100 overflow-y-auto rounded-lg border border-slate-200">
              {membersQuery.data?.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-slate-50"
                    onClick={() => {
                      setMember(item)
                      setMemberSearch(item.full_name)
                    }}
                  >
                    <span>
                      <span className="block text-sm font-medium text-slate-700">
                        {item.full_name}
                      </span>
                      <span className="block text-[11px] text-slate-500">
                        {item.email} · {item.institutional_id ?? item.enrollment_number ?? "—"}
                      </span>
                    </span>
                    <Badge tone={item.status === "ACTIVE" ? "green" : "amber"}>
                      {humanize(item.status)}
                    </Badge>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <Field label="Copy" required>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                className="pl-9"
                placeholder="Search available copies by accession, barcode or title…"
                value={copySearch}
                onChange={(event) => {
                  setCopySearch(event.target.value)
                  setCopy(null)
                }}
              />
            </div>
          </Field>
          {copy ? (
            <div className="mt-2 flex items-center justify-between rounded-lg border border-brand-200 bg-brand-50 px-3 py-2">
              <div>
                <p className="text-sm font-semibold text-slate-800">{copy.book_title}</p>
                <p className="font-mono text-xs text-slate-500">
                  {copy.accession_number} · {copy.shelf_location ?? "No shelf"}
                </p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setCopy(null)}>
                Change
              </Button>
            </div>
          ) : copiesQuery.isFetching ? (
            <p className="mt-1 text-xs text-slate-400">Searching…</p>
          ) : debouncedCopy.trim().length >= 2 && (copiesQuery.data ?? []).length === 0 ? (
            <p className="mt-1 text-xs text-slate-500">
              No available copies match that search.
            </p>
          ) : (
            <ul className="mt-1 max-h-44 divide-y divide-slate-100 overflow-y-auto rounded-lg border border-slate-200">
              {copiesQuery.data?.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-slate-50"
                    onClick={() => {
                      setCopy(item)
                      setCopySearch(item.accession_number)
                    }}
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium text-slate-700">
                        {item.book_title}
                      </span>
                      <span className="block font-mono text-[11px] text-slate-500">
                        {item.accession_number} · {item.condition}
                      </span>
                    </span>
                    <Badge tone="green">Available</Badge>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label="Due date override"
            hint="Leave blank to use the policy loan period."
          >
            <Input name="due_at" type="datetime-local" />
          </Field>
          <Field label="Notes">
            <Input name="notes" placeholder="Optional" />
          </Field>
        </div>

        {member && copy ? (
          <div className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
            <p>
              <strong>{member.full_name}</strong> will borrow{" "}
              <strong>{copy.book_title}</strong> ({copy.accession_number}).
            </p>
            {member.status !== "ACTIVE" ? (
              <p className="mt-1 font-medium text-amber-700">
                Warning: this member is {humanize(member.status).toLowerCase()}.
              </p>
            ) : null}
          </div>
        ) : null}
      </form>
    </Modal>
  )
}
