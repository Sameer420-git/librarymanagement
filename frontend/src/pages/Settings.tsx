import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Save } from "lucide-react"
import { useState, type FormEvent } from "react"

import {
  Button,
  Card,
  ErrorBlock,
  Field,
  Input,
  LoadingBlock,
  PageHeader,
  Textarea,
} from "../components/ui"
import { api, getErrorMessage } from "../lib/api"
import type { Policy } from "../lib/types"

export function SettingsPage() {
  const queryClient = useQueryClient()
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const policyQuery = useQuery({
    queryKey: ["settings"],
    queryFn: async () => (await api.get<Policy>("/admin/settings")).data,
  })

  const save = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await api.put<Policy>("/admin/settings", payload)).data,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["settings"] })
      void queryClient.invalidateQueries({ queryKey: ["policy"] })
      setNotice("Library policy saved. New loans and renewals use these values.")
    },
    onError: (mutationError) => setError(getErrorMessage(mutationError)),
  })

  if (policyQuery.isLoading) return <LoadingBlock label="Loading policy…" />
  if (policyQuery.isError || !policyQuery.data) {
    return (
      <ErrorBlock
        message={getErrorMessage(policyQuery.error)}
        onRetry={() => void policyQuery.refetch()}
      />
    )
  }

  const policy = policyQuery.data

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    const data = new FormData(event.currentTarget)
    const text = (key: string) => String(data.get(key) ?? "").trim()
    const num = (key: string) => Number(data.get(key))
    const days = (key: string) =>
      text(key)
        .split(",")
        .map((part) => Number(part.trim()))
        .filter((value) => Number.isFinite(value) && value >= 0)

    save.mutate({
      institution_name: text("institution_name"),
      library_email: text("library_email"),
      library_phone: text("library_phone"),
      library_address: text("library_address"),
      opening_hours: text("opening_hours"),
      max_books_student: num("max_books_student"),
      max_books_faculty: num("max_books_faculty"),
      max_books_staff: num("max_books_staff"),
      loan_period_days_student: num("loan_period_days_student"),
      loan_period_days_faculty: num("loan_period_days_faculty"),
      max_renewals: num("max_renewals"),
      renewal_period_days: num("renewal_period_days"),
      max_fine_blocks_renewal: num("max_fine_blocks_renewal"),
      max_fine_blocks_issue: num("max_fine_blocks_issue"),
      fine_per_day: num("fine_per_day"),
      grace_period_days: num("grace_period_days"),
      max_fine_per_loan: num("max_fine_per_loan"),
      currency_code: text("currency_code").toUpperCase(),
      reservation_pickup_days: num("reservation_pickup_days"),
      max_active_reservations: num("max_active_reservations"),
      reservation_expiry_hours: num("reservation_expiry_hours"),
      due_reminder_days: days("due_reminder_days"),
      overdue_reminder_days: days("overdue_reminder_days"),
      membership_expiry_reminder_days: days("membership_expiry_reminder_days"),
      max_overdue_reminders: num("max_overdue_reminders"),
      membership_validity_days_student: num("membership_validity_days_student"),
      membership_validity_days_faculty: num("membership_validity_days_faculty"),
    })
  }

  return (
    <>
      <PageHeader
        title="Library settings"
        description="Policy values applied to new loans, renewals, fines and reservations."
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

      {error ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      <form onSubmit={onSubmit} className="space-y-4">
        <Card title="Institution" description="Shown on e-mails and receipts.">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Institution name">
              <Input name="institution_name" defaultValue={policy.institution_name} />
            </Field>
            <Field label="Library e-mail">
              <Input name="library_email" type="email" defaultValue={policy.library_email} />
            </Field>
            <Field label="Phone">
              <Input name="library_phone" defaultValue={policy.library_phone} />
            </Field>
            <Field label="Opening hours">
              <Input name="opening_hours" defaultValue={policy.opening_hours} />
            </Field>
            <Field label="Address" className="sm:col-span-2">
              <Textarea name="library_address" rows={2} defaultValue={policy.library_address} />
            </Field>
          </div>
        </Card>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Borrowing limits">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Books · students">
                <Input
                  name="max_books_student"
                  type="number"
                  min={1}
                  defaultValue={policy.max_books_student}
                />
              </Field>
              <Field label="Books · faculty">
                <Input
                  name="max_books_faculty"
                  type="number"
                  min={1}
                  defaultValue={policy.max_books_faculty}
                />
              </Field>
              <Field label="Books · staff">
                <Input
                  name="max_books_staff"
                  type="number"
                  min={1}
                  defaultValue={policy.max_books_staff}
                />
              </Field>
              <Field label="Max renewals">
                <Input
                  name="max_renewals"
                  type="number"
                  min={0}
                  defaultValue={policy.max_renewals}
                />
              </Field>
              <Field label="Loan days · students">
                <Input
                  name="loan_period_days_student"
                  type="number"
                  min={1}
                  defaultValue={policy.loan_period_days_student}
                />
              </Field>
              <Field label="Loan days · faculty">
                <Input
                  name="loan_period_days_faculty"
                  type="number"
                  min={1}
                  defaultValue={policy.loan_period_days_faculty}
                />
              </Field>
              <Field label="Renewal period (days)">
                <Input
                  name="renewal_period_days"
                  type="number"
                  min={1}
                  defaultValue={policy.renewal_period_days}
                />
              </Field>
            </div>
          </Card>

          <Card title="Fines">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Fine per day">
                <Input
                  name="fine_per_day"
                  type="number"
                  min={0}
                  step="0.01"
                  defaultValue={policy.fine_per_day}
                />
              </Field>
              <Field label="Grace period (days)">
                <Input
                  name="grace_period_days"
                  type="number"
                  min={0}
                  defaultValue={policy.grace_period_days}
                />
              </Field>
              <Field label="Max fine per loan">
                <Input
                  name="max_fine_per_loan"
                  type="number"
                  min={0}
                  step="0.01"
                  defaultValue={policy.max_fine_per_loan}
                />
              </Field>
              <Field label="Currency code">
                <Input name="currency_code" maxLength={3} defaultValue={policy.currency_code} />
              </Field>
              <Field label="Block renewal above">
                <Input
                  name="max_fine_blocks_renewal"
                  type="number"
                  min={0}
                  step="0.01"
                  defaultValue={policy.max_fine_blocks_renewal}
                />
              </Field>
              <Field label="Block issuing above">
                <Input
                  name="max_fine_blocks_issue"
                  type="number"
                  min={0}
                  step="0.01"
                  defaultValue={policy.max_fine_blocks_issue}
                />
              </Field>
            </div>
          </Card>

          <Card title="Reservations">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Pickup window (days)">
                <Input
                  name="reservation_pickup_days"
                  type="number"
                  min={1}
                  defaultValue={policy.reservation_pickup_days}
                />
              </Field>
              <Field label="Max active holds">
                <Input
                  name="max_active_reservations"
                  type="number"
                  min={1}
                  defaultValue={policy.max_active_reservations}
                />
              </Field>
              <Field label="Expiry (hours)">
                <Input
                  name="reservation_expiry_hours"
                  type="number"
                  min={1}
                  defaultValue={policy.reservation_expiry_hours}
                />
              </Field>
            </div>
          </Card>

          <Card title="Reminders & membership">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Due reminder days" hint="Comma separated, e.g. 3,1">
                <Input
                  name="due_reminder_days"
                  defaultValue={policy.due_reminder_days.join(",")}
                />
              </Field>
              <Field label="Overdue reminder days">
                <Input
                  name="overdue_reminder_days"
                  defaultValue={policy.overdue_reminder_days.join(",")}
                />
              </Field>
              <Field label="Membership reminder days">
                <Input
                  name="membership_expiry_reminder_days"
                  defaultValue={policy.membership_expiry_reminder_days.join(",")}
                />
              </Field>
              <Field label="Max overdue reminders">
                <Input
                  name="max_overdue_reminders"
                  type="number"
                  min={0}
                  defaultValue={policy.max_overdue_reminders}
                />
              </Field>
              <Field label="Student validity (days)">
                <Input
                  name="membership_validity_days_student"
                  type="number"
                  min={0}
                  defaultValue={policy.membership_validity_days_student}
                />
              </Field>
              <Field label="Faculty validity (days)">
                <Input
                  name="membership_validity_days_faculty"
                  type="number"
                  min={0}
                  defaultValue={policy.membership_validity_days_faculty}
                />
              </Field>
            </div>
          </Card>
        </div>

        <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3">
          <p className="text-xs text-slate-500">
            Last updated{" "}
            {policy.updated_at
              ? new Date(policy.updated_at).toLocaleString()
              : "—"}
          </p>
          <Button type="submit" loading={save.isPending}>
            <Save className="h-4 w-4" /> Save policy
          </Button>
        </div>
      </form>
    </>
  )
}
