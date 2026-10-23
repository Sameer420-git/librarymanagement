import { useQuery } from "@tanstack/react-query"
import { Download, FileSpreadsheet, RefreshCw } from "lucide-react"
import { useState } from "react"

import {
  Button,
  Card,
  EmptyState,
  ErrorBlock,
  Field,
  Input,
  LoadingBlock,
  PageHeader,
  Select,
  Table,
  Td,
  Th,
} from "../components/ui"
import { api, downloadFile, getErrorMessage } from "../lib/api"
import { formatDateTime, formatMoney, humanize } from "../lib/format"
import type { ReportRow } from "../lib/types"

type ReportKind =
  | "inventory"
  | "circulation"
  | "overdue"
  | "fines"
  | "popular-books"
  | "members"
  | "departments"
  | "reservations"
  | "returns"
  | "member-history"
  | "email-failures"
  | "lost-damaged"

interface ReportConfig {
  value: ReportKind
  label: string
  description: string
  dates?: boolean
  granularity?: boolean
  limit?: boolean
  member?: boolean
}

const reports: ReportConfig[] = [
  {
    value: "inventory",
    label: "Inventory",
    description: "Titles, copies and availability by category.",
  },
  {
    value: "circulation",
    label: "Circulation",
    description: "Issues, returns and renewals grouped by period.",
    dates: true,
    granularity: true,
  },
  {
    value: "overdue",
    label: "Overdue loans",
    description: "Outstanding loans past their due date.",
  },
  {
    value: "fines",
    label: "Fines",
    description: "Assessed, collected and waived fines.",
    dates: true,
  },
  {
    value: "popular-books",
    label: "Popular titles",
    description: "Most borrowed titles in the collection.",
    limit: true,
  },
  {
    value: "members",
    label: "Members",
    description: "Membership counts by role and status.",
  },
  {
    value: "departments",
    label: "Departments",
    description: "Circulation activity by department.",
  },
  {
    value: "reservations",
    label: "Reservations",
    description: "Hold activity and conversion.",
  },
  {
    value: "returns",
    label: "Returns",
    description: "Returns within a date range.",
    dates: true,
  },
  {
    value: "member-history",
    label: "Member history",
    description: "Complete borrowing history, optionally for one member.",
    member: true,
  },
  {
    value: "email-failures",
    label: "E-mail failures",
    description: "Notifications that could not be delivered.",
    limit: true,
  },
  {
    value: "lost-damaged",
    label: "Lost & damaged",
    description: "Copies removed from circulation.",
  },
]

interface ReportResponse {
  rows: ReportRow[]
  totals?: Record<string, unknown>
}

const dateCols = ["date", "period", "month", "day", "week", "year"]

export function ReportsPage() {
  const [kind, setKind] = useState<ReportKind>("inventory")
  const [fromDate, setFromDate] = useState("")
  const [toDate, setToDate] = useState("")
  const [granularity, setGranularity] = useState("month")
  const [limit, setLimit] = useState("10")
  const [memberId, setMemberId] = useState("")

  const config = reports.find((report) => report.value === kind) ?? reports[0]

  const params: Record<string, unknown> = {}
  if (config.dates) {
    if (fromDate) params.from_date = fromDate
    if (toDate) params.to_date = toDate
  }
  if (config.granularity) params.granularity = granularity
  if (config.limit) params.limit = Number(limit) || undefined
  if (config.member) params.member_id = memberId ? Number(memberId) : undefined

  const reportQuery = useQuery({
    queryKey: ["report", kind, params],
    queryFn: async () =>
      (await api.get<ReportResponse>(`/reports/${kind}`, { params })).data,
    enabled: config.member ? memberId === "" || Number(memberId) > 0 : true,
  })

  const data = reportQuery.data
  const rows = data?.rows ?? []
  const columns = rows.length > 0 ? Object.keys(rows[0]) : []
  const totals = data?.totals

  const exportReport = () =>
    void downloadFile(`/reports/${kind}`, `${kind}-report.csv`, {
      ...params,
      export: true,
    })

  return (
    <>
      <PageHeader
        title="Reports"
        description="Operational reporting with CSV export for every report."
        actions={
          <>
            <Button variant="secondary" onClick={() => void reportQuery.refetch()}>
              <RefreshCw className="h-4 w-4" /> Refresh
            </Button>
            <Button onClick={exportReport} disabled={rows.length === 0}>
              <Download className="h-4 w-4" /> Export CSV
            </Button>
          </>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <Card title="Report" padded={false}>
          <ul className="max-h-[32rem] overflow-y-auto p-2">
            {reports.map((report) => (
              <li key={report.value}>
                <button
                  type="button"
                  onClick={() => setKind(report.value)}
                  className={
                    kind === report.value
                      ? "w-full rounded-lg bg-brand-50 px-3 py-2.5 text-left ring-1 ring-brand-200"
                      : "w-full rounded-lg px-3 py-2.5 text-left hover:bg-slate-50"
                  }
                >
                  <span
                    className={
                      kind === report.value
                        ? "block text-sm font-semibold text-brand-800"
                        : "block text-sm font-medium text-slate-700"
                    }
                  >
                    {report.label}
                  </span>
                  <span className="mt-0.5 block text-[11px] leading-snug text-slate-500">
                    {report.description}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <div className="space-y-4">
          {(config.dates || config.granularity || config.limit || config.member) && (
            <Card>
              <div className="flex flex-wrap items-end gap-3">
                {config.dates ? (
                  <>
                    <Field label="From">
                      <Input
                        type="date"
                        value={fromDate}
                        onChange={(event) => setFromDate(event.target.value)}
                      />
                    </Field>
                    <Field label="To">
                      <Input
                        type="date"
                        value={toDate}
                        onChange={(event) => setToDate(event.target.value)}
                      />
                    </Field>
                  </>
                ) : null}
                {config.granularity ? (
                  <Field label="Group by">
                    <Select
                      value={granularity}
                      onChange={(event) => setGranularity(event.target.value)}
                    >
                      <option value="day">Day</option>
                      <option value="week">Week</option>
                      <option value="month">Month</option>
                      <option value="year">Year</option>
                    </Select>
                  </Field>
                ) : null}
                {config.limit ? (
                  <Field label="Limit">
                    <Input
                      type="number"
                      min={1}
                      max={config.value === "email-failures" ? 1000 : 100}
                      value={limit}
                      onChange={(event) => setLimit(event.target.value)}
                      className="w-28"
                    />
                  </Field>
                ) : null}
                {config.member ? (
                  <Field label="Member ID" hint="Leave blank for all members.">
                    <Input
                      type="number"
                      min={1}
                      value={memberId}
                      onChange={(event) => setMemberId(event.target.value)}
                      className="w-36"
                    />
                  </Field>
                ) : null}
              </div>
            </Card>
          )}

          {totals && Object.keys(totals).length > 0 ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {Object.entries(totals).map(([key, value]) => (
                <div
                  key={key}
                  className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm"
                >
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                    {humanize(key)}
                  </p>
                  <p className="mt-0.5 text-lg font-semibold text-slate-800">
                    {typeof value === "number" &&
                    /(amount|fine|collected|outstanding|waived)/i.test(key)
                      ? formatMoney(value)
                      : typeof value === "number"
                        ? value.toLocaleString()
                        : String(value ?? "—")}
                  </p>
                </div>
              ))}
            </div>
          ) : null}

          <Card padded={false}>
            {reportQuery.isLoading ? (
              <LoadingBlock label="Building report…" />
            ) : reportQuery.isError ? (
              <ErrorBlock
                message={getErrorMessage(reportQuery.error)}
                onRetry={() => void reportQuery.refetch()}
              />
            ) : rows.length === 0 ? (
              <EmptyState
                title="No rows"
                description="There is no data for this report and filter combination."
              />
            ) : (
              <>
                <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                  <p className="text-sm font-semibold text-slate-800">
                    {config.label}
                    <span className="ml-2 text-xs font-normal text-slate-400">
                      {rows.length} row{rows.length === 1 ? "" : "s"}
                    </span>
                  </p>
                  <FileSpreadsheet className="h-4 w-4 text-slate-300" />
                </div>
                <div className="overflow-x-auto">
                  <Table>
                    <thead>
                      <tr>
                        {columns.map((column) => (
                          <Th key={column}>{humanize(column)}</Th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row, index) => (
                        <tr key={index} className="hover:bg-slate-50/60">
                          {columns.map((column) => (
                            <Td key={column} className="whitespace-nowrap">
                              {formatCell(column, row[column])}
                            </Td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </div>
              </>
            )}
          </Card>
        </div>
      </div>
    </>
  )
}

function formatCell(column: string, value: ReportRow[string]) {
  if (value === null || value === undefined) return "—"
  if (typeof value === "boolean") return value ? "Yes" : "No"
  if (typeof value === "number") {
    if (/(amount|fine|collected|outstanding|waived|price|revenue)/i.test(column)) {
      return formatMoney(value)
    }
    return value.toLocaleString()
  }
  if (
    typeof value === "string" &&
    (column.endsWith("_at") || dateCols.includes(column)) &&
    /^\d{4}-\d{2}-\d{2}/.test(value)
  ) {
    return formatDateTime(value)
  }
  return String(value)
}
