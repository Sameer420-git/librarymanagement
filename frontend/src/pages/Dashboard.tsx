import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  AlertTriangle,
  ArrowLeftRight,
  BookMarked,
  BookOpen,
  CalendarClock,
  CircleDollarSign,
  RotateCw,
  Users,
  Wallet,
} from "lucide-react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Link, useNavigate } from "react-router-dom"

import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBlock,
  LoadingBlock,
  PageHeader,
  StatCard,
  StatusBadge,
  Table,
  Td,
  Th,
} from "../components/ui"
import { useAuth } from "../context/AuthContext"
import { api, getErrorMessage } from "../lib/api"
import { formatDate, formatDateTime, formatMoney } from "../lib/format"
import { isStaff } from "../lib/permissions"
import type {
  DashboardStats,
  Loan,
  Page,
  PersonalDashboard,
  ReportRow,
} from "../lib/types"

interface CirculationReport {
  rows: {
    period: string
    issued_count: number
    returned_count: number
    renewed_count: number
    overdue_count: number
  }[]
  totals: { issued: number; returned: number; renewed: number; overdue: number }
}

export function DashboardPage() {
  const { user } = useAuth()
  if (!user) return null
  return isStaff(user.role) ? <StaffDashboard /> : <MemberDashboard />
}

function StaffDashboard() {
  const { user } = useAuth()
  const isSuperAdmin = user?.role === "SUPER_ADMIN"

  const statsQuery = useQuery({
    queryKey: ["dashboard", "staff"],
    queryFn: async () => (await api.get<DashboardStats>("/admin/me/dashboard")).data,
  })

  const circulationQuery = useQuery({
    queryKey: ["reports", "circulation", "month"],
    queryFn: async () =>
      (
        await api.get<CirculationReport>("/reports/circulation", {
          params: { granularity: "month" },
        })
      ).data,
  })

  const popularQuery = useQuery({
    queryKey: ["reports", "popular-books", 5],
    queryFn: async () =>
      (
        await api.get<{ rows: ReportRow[] }>("/reports/popular-books", {
          params: { limit: 5 },
        })
      ).data.rows,
  })

  const activityQuery = useQuery({
    queryKey: ["audit", "recent"],
    enabled: isSuperAdmin,
    queryFn: async () =>
      (
        await api.get<Page<{ id: number; summary: string; actor_email: string | null; created_at: string }>>(
          "/admin/audit-logs",
          { params: { page_size: 8 } },
        )
      ).data,
  })

  if (statsQuery.isLoading) return <LoadingBlock label="Loading dashboard…" />
  if (statsQuery.isError || !statsQuery.data) {
    return (
      <ErrorBlock
        message={getErrorMessage(statsQuery.error)}
        onRetry={() => void statsQuery.refetch()}
      />
    )
  }

  const stats = statsQuery.data
  const chartData = circulationQuery.data?.rows.slice(-8) ?? []

  return (
    <>
      <PageHeader
        title="Library overview"
        description="Live circulation, inventory and membership indicators."
        actions={
          <>
            <Link to="/reports">
              <Button variant="secondary">View reports</Button>
            </Link>
            <Link to="/circulation?issue=1">
              <Button>Issue a book</Button>
            </Link>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <StatCard
          label="Catalogue titles"
          value={stats.total_books}
          hint={`${stats.total_copies} physical copies`}
          icon={<BookOpen className="h-5 w-5" />}
        />
        <StatCard
          label="Available copies"
          value={stats.available_copies}
          hint={`${stats.issued_copies} currently issued`}
          icon={<BookMarked className="h-5 w-5" />}
          tone="sky"
        />
        <StatCard
          label="Active loans"
          value={stats.active_loans}
          hint={`${stats.due_today} due today · ${stats.loans_issued_today} issued today`}
          icon={<ArrowLeftRight className="h-5 w-5" />}
        />
        <StatCard
          label="Overdue loans"
          value={stats.overdue_loans}
          hint={stats.overdue_loans > 0 ? "Reminders are queued automatically" : "Nothing overdue"}
          icon={<AlertTriangle className="h-5 w-5" />}
          tone="rose"
        />
        <StatCard
          label="Members"
          value={stats.total_members}
          hint={`${stats.active_members} active accounts`}
          icon={<Users className="h-5 w-5" />}
          tone="violet"
        />
        <StatCard
          label="Outstanding fines"
          value={formatMoney(stats.outstanding_fines)}
          hint={`${formatMoney(stats.fines_collected)} collected to date`}
          icon={<CircleDollarSign className="h-5 w-5" />}
          tone="amber"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <Card
          title="Circulation trend"
          description="Issued and returned copies per month."
          className="lg:col-span-3"
        >
          {circulationQuery.isLoading ? (
            <LoadingBlock label="Loading chart…" />
          ) : chartData.length === 0 ? (
            <EmptyState
              title="No circulation activity yet"
              description="Issue a book to start building the trend."
            />
          ) : (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 4, right: 8, left: -18, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                  <XAxis
                    dataKey="period"
                    tick={{ fontSize: 11, fill: "#64748b" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fontSize: 11, fill: "#64748b" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      fontSize: 12,
                      borderRadius: 8,
                      border: "1px solid #e2e8f0",
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar
                    dataKey="issued_count"
                    name="Issued"
                    fill="#0f766e"
                    radius={[4, 4, 0, 0]}
                    maxBarSize={26}
                  />
                  <Bar
                    dataKey="returned_count"
                    name="Returned"
                    fill="#5eead4"
                    radius={[4, 4, 0, 0]}
                    maxBarSize={26}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card
          title="Most borrowed"
          description="Top titles by lifetime loans."
          className="lg:col-span-2"
        >
          {popularQuery.isLoading ? (
            <LoadingBlock label="Loading titles…" />
          ) : (popularQuery.data?.length ?? 0) === 0 ? (
            <EmptyState title="No loans recorded yet" />
          ) : (
            <ol className="space-y-3">
              {popularQuery.data?.map((row, index) => (
                <li key={String(row.book_id ?? index)} className="flex items-center gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[11px] font-bold text-slate-500">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-800">
                      {String(row.title ?? "Untitled")}
                    </p>
                    <p className="text-[11px] text-slate-500">
                      {String(row.author ?? "Unknown author")}
                    </p>
                  </div>
                  <Badge tone="teal">{String(row.loan_count ?? 0)} loans</Badge>
                </li>
              ))}
            </ol>
          )}
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {isSuperAdmin ? (
          <Card
            title="Recent activity"
            description="Latest audited actions across the system."
            action={
              <Link
                to="/audit"
                className="text-xs font-semibold text-brand-700 hover:text-brand-800"
              >
                View all
              </Link>
            }
          >
            {activityQuery.isLoading ? (
              <LoadingBlock />
            ) : (activityQuery.data?.items.length ?? 0) === 0 ? (
              <EmptyState title="No activity recorded" />
            ) : (
              <ul className="divide-y divide-slate-100">
                {activityQuery.data?.items.map((entry) => (
                  <li key={entry.id} className="flex gap-3 py-2.5">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />
                    <div className="min-w-0">
                      <p className="text-sm text-slate-700">{entry.summary}</p>
                      <p className="text-[11px] text-slate-400">
                        {entry.actor_email ?? "System"} · {formatDateTime(entry.created_at)}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        ) : (
          <Card title="Notification queue" description="E-mail delivery status.">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-amber-50 px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-700">
                  Queued
                </p>
                <p className="mt-1 text-xl font-semibold text-amber-800">
                  {stats.notifications_queued}
                </p>
              </div>
              <div className="rounded-lg bg-rose-50 px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-rose-700">
                  Failed
                </p>
                <p className="mt-1 text-xl font-semibold text-rose-800">
                  {stats.notifications_failed}
                </p>
              </div>
            </div>
            <p className="mt-3 text-xs text-slate-500">
              Undelivered messages retry automatically with backoff. Review the queue in{" "}
              <Link to="/notifications" className="font-semibold text-brand-700">
                Notifications
              </Link>
              .
            </p>
          </Card>
        )}

        <Card title="Quick actions" description="Common circulation desk tasks.">
          <div className="grid gap-2 sm:grid-cols-2">
            <Link
              to="/circulation?issue=1"
              className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-medium text-slate-700 transition hover:border-brand-300 hover:bg-brand-50/40"
            >
              <ArrowLeftRight className="h-4 w-4 text-brand-600" /> Issue a book
            </Link>
            <Link
              to="/members?new=1"
              className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-medium text-slate-700 transition hover:border-brand-300 hover:bg-brand-50/40"
            >
              <Users className="h-4 w-4 text-brand-600" /> Register a member
            </Link>
            <Link
              to="/catalogue?new=1"
              className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-medium text-slate-700 transition hover:border-brand-300 hover:bg-brand-50/40"
            >
              <BookOpen className="h-4 w-4 text-brand-600" /> Add a title
            </Link>
            <Link
              to="/circulation?overdue=1"
              className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-medium text-slate-700 transition hover:border-brand-300 hover:bg-brand-50/40"
            >
              <CalendarClock className="h-4 w-4 text-brand-600" /> Review overdue loans
            </Link>
          </div>
        </Card>
      </div>
    </>
  )
}

function MemberDashboard() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const dashboardQuery = useQuery({
    queryKey: ["dashboard", "member"],
    queryFn: async () =>
      (await api.get<PersonalDashboard>("/admin/me/dashboard")).data,
  })

  const renew = useMutation({
    mutationFn: async (loanId: number) =>
      (await api.post<Loan>(`/loans/${loanId}/renew`)).data,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["dashboard", "member"] })
      void queryClient.invalidateQueries({ queryKey: ["loans"] })
    },
  })

  if (dashboardQuery.isLoading) return <LoadingBlock label="Loading your dashboard…" />
  if (dashboardQuery.isError || !dashboardQuery.data) {
    return (
      <ErrorBlock
        message={getErrorMessage(dashboardQuery.error)}
        onRetry={() => void dashboardQuery.refetch()}
      />
    )
  }

  const data = dashboardQuery.data
  const loans = data.current_loans ?? []
  const reservations = data.reservations ?? []

  return (
    <>
      <PageHeader
        title="My library"
        description="Your current loans, reservations and outstanding balance."
        actions={
          <Link to="/catalogue">
            <Button>Browse the catalogue</Button>
          </Link>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Books on loan"
          value={loans.length}
          hint={`${data.overdue_count} overdue`}
          icon={<BookOpen className="h-5 w-5" />}
        />
        <StatCard
          label="Reservations"
          value={reservations.length}
          hint="Active or ready for pickup"
          icon={<BookMarked className="h-5 w-5" />}
          tone="sky"
        />
        <StatCard
          label="Outstanding fines"
          value={formatMoney(data.outstanding_fines)}
          hint={data.outstanding_fines > 0 ? "Please settle at the circulation desk" : "No dues"}
          icon={<Wallet className="h-5 w-5" />}
          tone={data.outstanding_fines > 0 ? "rose" : "brand"}
        />
        <StatCard
          label="Overdue"
          value={data.overdue_count}
          hint={data.overdue_count > 0 ? "Return items to avoid further fines" : "All items on time"}
          icon={<AlertTriangle className="h-5 w-5" />}
          tone={data.overdue_count > 0 ? "rose" : "brand"}
        />
      </div>

      <Card
        title="Currently on loan"
        description="Renew items before their due date, subject to policy limits."
        padded={false}
      >
        {loans.length === 0 ? (
          <EmptyState
            title="You have no books on loan"
            description="Search the catalogue to find your next read."
            action={
              <Link to="/catalogue">
                <Button variant="secondary" size="sm">
                  Browse catalogue
                </Button>
              </Link>
            }
          />
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Title</Th>
                <Th>Accession</Th>
                <Th>Issued</Th>
                <Th>Due</Th>
                <Th>Status</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </thead>
            <tbody>
              {loans.map((loan) => (
                <tr key={loan.id} className="hover:bg-slate-50/60">
                  <Td>
                    <Link
                      to={`/catalogue/${loan.book_id}`}
                      className="font-medium text-slate-800 hover:text-brand-700"
                    >
                      {loan.book_title ?? "Unknown title"}
                    </Link>
                  </Td>
                  <Td className="font-mono text-xs text-slate-500">
                    {loan.accession_number ?? "—"}
                  </Td>
                  <Td className="text-slate-500">{formatDate(loan.issued_at)}</Td>
                  <Td className={loan.is_overdue ? "font-semibold text-rose-600" : "text-slate-600"}>
                    {formatDate(loan.due_at)}
                  </Td>
                  <Td>
                    <StatusBadge status={loan.is_overdue ? "OVERDUE" : loan.status} />
                  </Td>
                  <Td className="text-right">
                    <Button
                      variant="secondary"
                      size="sm"
                      loading={renew.isPending && renew.variables === loan.id}
                      onClick={() => renew.mutate(loan.id)}
                      disabled={loan.is_overdue}
                      title={loan.is_overdue ? "Overdue loans cannot be renewed" : "Renew for another period"}
                    >
                      <RotateCw className="h-3.5 w-3.5" /> Renew
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
        {renew.isError ? (
          <p className="border-t border-rose-100 bg-rose-50 px-4 py-2 text-xs text-rose-700">
            {getErrorMessage(renew.error)}
          </p>
        ) : null}
      </Card>

      <Card title="My reservations" description="Your position in the waiting list.">
        {reservations.length === 0 ? (
          <EmptyState
            title="No active reservations"
            description="Reserve a title from the catalogue when all copies are on loan."
          />
        ) : (
          <ul className="divide-y divide-slate-100">
            {reservations.map((reservation) => (
              <li
                key={reservation.id}
                className="flex flex-wrap items-center justify-between gap-3 py-3"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-800">
                    {reservation.book_title ?? "Unknown title"}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    Reserved {formatDate(reservation.reserved_at)}
                    {reservation.pickup_deadline
                      ? ` · collect by ${formatDate(reservation.pickup_deadline)}`
                      : ""}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone="slate">Queue #{reservation.queue_position}</Badge>
                  <StatusBadge status={reservation.status} />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => navigate("/reservations")}
                  >
                    Manage
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  )
}
