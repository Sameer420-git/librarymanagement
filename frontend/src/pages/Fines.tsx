import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ChevronDown, ChevronRight, Receipt, SlidersHorizontal, Wallet } from "lucide-react"
import { Fragment, useState } from "react"
import { Link } from "react-router-dom"

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
import { useAuth } from "../context/AuthContext"
import { api, getErrorMessage } from "../lib/api"
import { formatDate, formatDateTime, formatMoney, humanize } from "../lib/format"
import { isStaff } from "../lib/permissions"
import type { Fine, Page, PaymentMethod } from "../lib/types"

const methods: PaymentMethod[] = [
  "CASH",
  "CARD",
  "UPI",
  "BANK_TRANSFER",
  "ONLINE",
  "OTHER",
]

export function FinesPage() {
  const { user } = useAuth()
  const staff = isStaff(user?.role)
  const queryClient = useQueryClient()

  const [status, setStatus] = useState("")
  const [outstandingOnly, setOutstandingOnly] = useState(false)
  const [page, setPage] = useState(1)
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const [payTarget, setPayTarget] = useState<Fine | null>(null)
  const [adjustTarget, setAdjustTarget] = useState<Fine | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const finesQuery = useQuery({
    queryKey: ["fines", { status, outstandingOnly, page }],
    queryFn: async () =>
      (
        await api.get<Page<Fine>>("/fines", {
          params: {
            status: status || undefined,
            outstanding_only: outstandingOnly || undefined,
            page,
            page_size: 20,
          },
        })
      ).data,
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["fines"] })
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    void queryClient.invalidateQueries({ queryKey: ["members"] })
  }

  const recordPayment = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: Record<string, unknown> }) =>
      (await api.post(`/fines/${id}/payments`, payload)).data,
    onSuccess: () => {
      invalidate()
      setPayTarget(null)
      setNotice("Payment recorded.")
    },
    onError: (mutationError) => setError(getErrorMessage(mutationError)),
  })

  const adjust = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: Record<string, unknown> }) =>
      (await api.post<Fine>(`/fines/${id}/adjust`, payload)).data,
    onSuccess: () => {
      invalidate()
      setAdjustTarget(null)
      setNotice("Fine adjusted.")
    },
    onError: (mutationError) => setError(getErrorMessage(mutationError)),
  })

  const fines = finesQuery.data?.items ?? []
  const pagination = finesQuery.data?.pagination

  const toggle = (id: number) =>
    setExpanded((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  return (
    <>
      <PageHeader
        title={staff ? "Fines" : "My fines"}
        description={
          staff
            ? "Payments, waivers and adjustments are recorded against each fine."
            : "Outstanding balances on your account."
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
        <div className="flex flex-wrap items-center gap-3 border-b border-slate-100 p-4">
          <Select
            className="w-44"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value)
              setPage(1)
            }}
          >
            <option value="">All statuses</option>
            <option value="PENDING">Pending</option>
            <option value="PARTIALLY_PAID">Partially paid</option>
            <option value="PAID">Paid</option>
            <option value="WAIVED">Waived</option>
          </Select>
          {staff ? (
            <label className="flex cursor-pointer items-center gap-2 text-xs font-medium text-slate-600">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-600"
                checked={outstandingOnly}
                onChange={(event) => {
                  setOutstandingOnly(event.target.checked)
                  setPage(1)
                }}
              />
              Outstanding only
            </label>
          ) : null}
          <span className="ml-auto text-xs text-slate-500">
            {pagination ? `${pagination.total} fine${pagination.total === 1 ? "" : "s"}` : ""}
          </span>
        </div>

        {finesQuery.isLoading ? (
          <LoadingBlock label="Loading fines…" />
        ) : finesQuery.isError ? (
          <ErrorBlock
            message={getErrorMessage(finesQuery.error)}
            onRetry={() => void finesQuery.refetch()}
          />
        ) : fines.length === 0 ? (
          <EmptyState
            title="No fines"
            description={
              staff ? "No fines match this filter." : "You have no fines on record."
            }
          />
        ) : (
          <>
            <Table>
              <thead>
                <tr>
                  <Th className="w-8" />
                  <Th>Member</Th>
                  <Th>Reason</Th>
                  <Th>Amount</Th>
                  <Th>Paid</Th>
                  <Th>Outstanding</Th>
                  <Th>Status</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              </thead>
              <tbody>
                {fines.map((fine) => {
                  const isOpen = expanded.has(fine.id)
                  return (
                    <Fragment key={fine.id}>
                      <tr className="hover:bg-slate-50/60">
                        <Td>
                          {fine.payments.length > 0 ? (
                            <button
                              type="button"
                              onClick={() => toggle(fine.id)}
                              className="rounded p-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                              aria-label="Toggle payments"
                            >
                              {isOpen ? (
                                <ChevronDown className="h-4 w-4" />
                              ) : (
                                <ChevronRight className="h-4 w-4" />
                              )}
                            </button>
                          ) : null}
                        </Td>
                        <Td>
                          <Link
                            to={`/members/${fine.member_id}`}
                            className="text-xs font-medium text-slate-700 hover:text-brand-700"
                          >
                            {fine.member_name}
                          </Link>
                          <p className="text-[11px] text-slate-500">{fine.member_email}</p>
                        </Td>
                        <Td>
                          <p className="text-xs text-slate-600">{fine.reason}</p>
                          <p className="text-[11px] text-slate-400">
                            {fine.book_title ?? "—"} · {formatDate(fine.assessed_at)}
                          </p>
                        </Td>
                        <Td className="text-sm text-slate-700">{formatMoney(fine.amount)}</Td>
                        <Td className="text-sm text-slate-500">
                          {formatMoney(fine.amount_paid)}
                        </Td>
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
                        <Td>
                          {staff && Number(fine.outstanding) > 0 ? (
                            <div className="flex justify-end gap-1">
                              <Button
                                size="sm"
                                onClick={() => {
                                  setError(null)
                                  setPayTarget(fine)
                                }}
                              >
                                <Wallet className="h-3.5 w-3.5" /> Pay
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setError(null)
                                  setAdjustTarget(fine)
                                }}
                              >
                                <SlidersHorizontal className="h-3.5 w-3.5" /> Adjust
                              </Button>
                            </div>
                          ) : (
                            <div className="text-right text-xs text-slate-400">
                              {fine.status === "WAIVED" && fine.waiver_reason
                                ? fine.waiver_reason
                                : "—"}
                            </div>
                          )}
                        </Td>
                      </tr>
                      {isOpen ? (
                        <tr className="bg-slate-50/70">
                          <td />
                          <td colSpan={7} className="px-4 py-3">
                            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                              Payment history
                            </p>
                            <div className="space-y-1.5">
                              {fine.payments.map((payment) => (
                                <div
                                  key={payment.id}
                                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-white px-3 py-2 text-xs shadow-sm"
                                >
                                  <span className="flex items-center gap-2 font-medium text-slate-700">
                                    <Receipt className="h-3.5 w-3.5 text-slate-400" />
                                    {formatMoney(payment.amount)} · {humanize(payment.method)}
                                  </span>
                                  <span className="text-slate-500">
                                    {formatDateTime(payment.paid_at)}
                                    {payment.reference ? ` · ${payment.reference}` : ""}
                                    {payment.recorded_by_name
                                      ? ` · by ${payment.recorded_by_name}`
                                      : ""}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  )
                })}
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
        open={payTarget !== null}
        onClose={() => {
          setPayTarget(null)
          setError(null)
        }}
        title="Record a payment"
        description={
          payTarget
            ? `${payTarget.member_name} · outstanding ${formatMoney(payTarget.outstanding)}`
            : undefined
        }
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setPayTarget(null)
                setError(null)
              }}
            >
              Cancel
            </Button>
            <Button type="submit" form="payment-form" loading={recordPayment.isPending}>
              Record payment
            </Button>
          </>
        }
      >
        <form
          id="payment-form"
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            if (!payTarget) return
            const data = new FormData(event.currentTarget)
            recordPayment.mutate({
              id: payTarget.id,
              payload: {
                amount: Number(data.get("amount")),
                method: data.get("method"),
                reference: String(data.get("reference") ?? "").trim() || null,
                notes: String(data.get("notes") ?? "").trim() || null,
              },
            })
          }}
        >
          {error ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </p>
          ) : null}
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Amount" required>
              <Input
                name="amount"
                type="number"
                min={0.01}
                step="0.01"
                max={payTarget ? Number(payTarget.outstanding) : undefined}
                defaultValue={payTarget ? Number(payTarget.outstanding).toFixed(2) : ""}
                required
              />
            </Field>
            <Field label="Method" required>
              <Select name="method" defaultValue="CASH">
                {methods.map((method) => (
                  <option key={method} value={method}>
                    {humanize(method)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Reference">
              <Input name="reference" placeholder="Receipt / transaction ID" />
            </Field>
          </div>
          <Field label="Notes">
            <Textarea name="notes" rows={2} />
          </Field>
        </form>
      </Modal>

      <Modal
        open={adjustTarget !== null}
        onClose={() => {
          setAdjustTarget(null)
          setError(null)
        }}
        title="Adjust fine"
        description={
          adjustTarget
            ? `Current total ${formatMoney(adjustTarget.amount)} · paid ${formatMoney(adjustTarget.amount_paid)}`
            : undefined
        }
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setAdjustTarget(null)
                setError(null)
              }}
            >
              Cancel
            </Button>
            <Button type="submit" form="adjust-form" loading={adjust.isPending}>
              Apply adjustment
            </Button>
          </>
        }
      >
        <form
          id="adjust-form"
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            if (!adjustTarget) return
            const data = new FormData(event.currentTarget)
            const waive = data.get("waive") === "on"
            adjust.mutate({
              id: adjustTarget.id,
              payload: {
                waive,
                amount: waive ? null : Number(data.get("amount")),
                reason: String(data.get("reason") ?? "").trim(),
              },
            })
          }}
        >
          {error ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </p>
          ) : null}
          <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700">
            <input
              id="waive-checkbox"
              name="waive"
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-600"
              onChange={(event) => {
                const amount = document.getElementById("adjust-amount") as HTMLInputElement | null
                if (amount) amount.disabled = event.target.checked
              }}
            />
            Waive this fine entirely
          </label>
          <Field label="New total amount" hint="This replaces the total, not a delta.">
            <Input
              id="adjust-amount"
              name="amount"
              type="number"
              min={0}
              step="0.01"
              defaultValue={adjustTarget ? Number(adjustTarget.amount).toFixed(2) : ""}
            />
          </Field>
          <Field label="Reason" required>
            <Textarea
              name="reason"
              rows={2}
              minLength={3}
              required
              placeholder="e.g. Overdue period waived due to medical leave"
            />
          </Field>
        </form>
      </Modal>
    </>
  )
}
