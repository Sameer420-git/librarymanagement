import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { MailCheck, RefreshCw, Send, Search } from "lucide-react"
import { useState } from "react"
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
  StatCard,
  StatusBadge,
  Table,
  Td,
  Th,
} from "../components/ui"
import { useAuth } from "../context/AuthContext"
import { api, getErrorMessage } from "../lib/api"
import { formatDateTime, humanize } from "../lib/format"
import { useDebounced } from "../lib/hooks"
import { isStaff } from "../lib/permissions"
import type {
  NotificationItem,
  NotificationStats,
  Page,
} from "../lib/types"

const types = [
  "WELCOME",
  "EMAIL_VERIFICATION",
  "PASSWORD_RESET",
  "BOOK_ISSUED",
  "BOOK_RETURNED",
  "BOOK_DUE_SOON",
  "BOOK_OVERDUE",
  "RESERVATION_AVAILABLE",
  "RESERVATION_EXPIRED",
  "FINE_ASSESSED",
  "FINE_PAYMENT",
  "MEMBERSHIP_EXPIRING",
  "MEMBERSHIP_EXPIRED",
  "SYSTEM",
]

export function NotificationsPage() {
  const { user } = useAuth()
  const staff = isStaff(user?.role)
  const queryClient = useQueryClient()

  const [scope, setScope] = useState<"mine" | "all">("mine")
  const [status, setStatus] = useState("")
  const [type, setType] = useState("")
  const [search, setSearch] = useState("")
  const debouncedSearch = useDebounced(search)
  const [page, setPage] = useState(1)
  const [testOpen, setTestOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const endpoint = staff && scope === "all" ? "/admin/notifications" : "/notifications"

  const notificationsQuery = useQuery({
    queryKey: ["notifications", { endpoint, status, type, search: debouncedSearch, page }],
    queryFn: async () =>
      (
        await api.get<Page<NotificationItem>>(endpoint, {
          params: {
            status: status || undefined,
            type: type || undefined,
            search: scope === "all" ? debouncedSearch || undefined : undefined,
            page,
            page_size: 20,
          },
        })
      ).data,
  })

  const statsQuery = useQuery({
    queryKey: ["notification-stats"],
    queryFn: async () =>
      (await api.get<NotificationStats>("/admin/notifications/stats")).data,
    enabled: staff,
    refetchInterval: 30_000,
  })

  const retry = useMutation({
    mutationFn: async (id: number) =>
      (await api.post<NotificationItem>(`/admin/notifications/${id}/retry`)).data,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] })
      void queryClient.invalidateQueries({ queryKey: ["notification-stats"] })
      setNotice("Notification re-queued for delivery.")
    },
    onError: (mutationError) => setError(getErrorMessage(mutationError)),
  })

  const sendTest = useMutation({
    mutationFn: async (payload: { to_email?: string; subject?: string }) =>
      (
        await api.post<{ success: boolean; message: string; recipient: string; error?: string }>(
          "/admin/notifications/test",
          payload,
        )
      ).data,
    onSuccess: (result) => {
      setTestOpen(false)
      setNotice(
        result.success
          ? `Test e-mail delivered to ${result.recipient}.`
          : `${result.message}${result.error ? ` (${result.error})` : ""}`,
      )
    },
    onError: (mutationError) => setError(getErrorMessage(mutationError)),
  })

  const notifications = notificationsQuery.data?.items ?? []
  const pagination = notificationsQuery.data?.pagination
  const stats = statsQuery.data

  return (
    <>
      <PageHeader
        title="Notifications"
        description={
          staff
            ? "Monitor the outbox and troubleshoot delivery failures."
            : "Messages the library has sent to you."
        }
        actions={
          staff ? (
            <Button variant="secondary" onClick={() => setTestOpen(true)}>
              <Send className="h-4 w-4" /> Send test e-mail
            </Button>
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

      {staff && scope === "all" && stats ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Queued"
            value={stats.queued}
            hint="Waiting to be sent"
            icon={<RefreshCw className="h-5 w-5" />}
            tone="amber"
          />
          <StatCard
            label="Sent"
            value={stats.sent}
            hint="Delivered successfully"
            icon={<MailCheck className="h-5 w-5" />}
            tone="emerald"
          />
          <StatCard
            label="Failed"
            value={stats.failed}
            hint={`Failure rate ${(stats.failure_rate * 100).toFixed(1)}%`}
            icon={<Send className="h-5 w-5" />}
            tone={stats.failed > 0 ? "rose" : "slate"}
          />
          <StatCard
            label="Total"
            value={stats.total}
            hint="All notifications"
            icon={<MailCheck className="h-5 w-5" />}
            tone="brand"
          />
        </div>
      ) : null}

      <Card padded={false}>
        <div className="flex flex-wrap items-center gap-3 border-b border-slate-100 p-4">
          {staff ? (
            <div className="flex rounded-lg bg-slate-100 p-0.5">
              {[
                { value: "mine" as const, label: "My inbox" },
                { value: "all" as const, label: "Delivery log" },
              ].map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => {
                    setScope(option.value)
                    setPage(1)
                  }}
                  className={
                    scope === option.value
                      ? "rounded-md bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 shadow-sm"
                      : "rounded-md px-3 py-1.5 text-xs font-medium text-slate-500 hover:text-slate-700"
                  }
                >
                  {option.label}
                </button>
              ))}
            </div>
          ) : null}
          {scope === "all" ? (
            <div className="relative min-w-48 flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                className="pl-9"
                placeholder="Search subject or recipient…"
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value)
                  setPage(1)
                }}
              />
            </div>
          ) : null}
          <Select
            className="w-36"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value)
              setPage(1)
            }}
          >
            <option value="">All statuses</option>
            <option value="QUEUED">Queued</option>
            <option value="SENDING">Sending</option>
            <option value="SENT">Sent</option>
            <option value="FAILED">Failed</option>
            <option value="CANCELLED">Cancelled</option>
          </Select>
          <Select
            className="w-48"
            value={type}
            onChange={(event) => {
              setType(event.target.value)
              setPage(1)
            }}
          >
            <option value="">All types</option>
            {types.map((item) => (
              <option key={item} value={item}>
                {humanize(item)}
              </option>
            ))}
          </Select>
        </div>

        {notificationsQuery.isLoading ? (
          <LoadingBlock label="Loading notifications…" />
        ) : notificationsQuery.isError ? (
          <ErrorBlock
            message={getErrorMessage(notificationsQuery.error)}
            onRetry={() => void notificationsQuery.refetch()}
          />
        ) : notifications.length === 0 ? (
          <EmptyState
            title="No notifications"
            description={
              scope === "all"
                ? "The outbox is empty for this filter."
                : "You have no messages yet."
            }
          />
        ) : (
          <>
            <Table>
              <thead>
                <tr>
                  <Th>Subject</Th>
                  {scope === "all" ? <Th>Recipient</Th> : null}
                  <Th>Type</Th>
                  <Th>Status</Th>
                  <Th>Attempts</Th>
                  <Th>Created</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              </thead>
              <tbody>
                {notifications.map((notification) => (
                  <tr key={notification.id} className="hover:bg-slate-50/60">
                    <Td>
                      <p className="max-w-md truncate text-sm font-medium text-slate-700">
                        {notification.subject}
                      </p>
                      {notification.last_error ? (
                        <p className="max-w-md truncate text-[11px] text-rose-500">
                          {notification.last_error}
                        </p>
                      ) : null}
                    </Td>
                    {scope === "all" ? (
                      <Td>
                        {notification.user_id ? (
                          <Link
                            to={`/members/${notification.user_id}`}
                            className="text-xs text-slate-600 hover:text-brand-700"
                          >
                            {notification.recipient_email}
                          </Link>
                        ) : (
                          <span className="text-xs text-slate-600">
                            {notification.recipient_email}
                          </span>
                        )}
                      </Td>
                    ) : null}
                    <Td className="text-xs text-slate-500">
                      {humanize(notification.type)}
                    </Td>
                    <Td>
                      <StatusBadge status={notification.status} />
                    </Td>
                    <Td className="text-xs text-slate-500">{notification.attempts}</Td>
                    <Td className="text-xs text-slate-500">
                      {formatDateTime(notification.created_at)}
                    </Td>
                    <Td className="text-right">
                      {scope === "all" && notification.status === "FAILED" ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          loading={retry.isPending}
                          onClick={() => {
                            setError(null)
                            retry.mutate(notification.id)
                          }}
                        >
                          <RefreshCw className="h-3.5 w-3.5" /> Retry
                        </Button>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
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
        open={testOpen}
        onClose={() => {
          setTestOpen(false)
          setError(null)
        }}
        title="Send a test e-mail"
        description="Uses the configured SMTP transport. Useful after changing mail settings."
        footer={
          <>
            <Button variant="secondary" onClick={() => setTestOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="test-email-form" loading={sendTest.isPending}>
              Send
            </Button>
          </>
        }
      >
        <form
          id="test-email-form"
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            const data = new FormData(event.currentTarget)
            sendTest.mutate({
              to_email: String(data.get("to_email") ?? "").trim() || undefined,
              subject: String(data.get("subject") ?? "").trim() || undefined,
            })
          }}
        >
          {error ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </p>
          ) : null}
          <Field label="Recipient" hint={`Leave blank to use ${user?.email}.`}>
            <Input name="to_email" type="email" />
          </Field>
          <Field label="Subject">
            <Input name="subject" defaultValue="College Library - SMTP test" />
          </Field>
        </form>
      </Modal>
    </>
  )
}
