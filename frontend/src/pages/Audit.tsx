import { useQuery } from "@tanstack/react-query"
import { ChevronDown, ChevronRight, ScrollText } from "lucide-react"
import { Fragment, useState } from "react"

import {
  Button,
  Card,
  EmptyState,
  ErrorBlock,
  Field,
  Input,
  LoadingBlock,
  PageHeader,
  Pagination,
  Table,
  Td,
  Th,
} from "../components/ui"
import { api, getErrorMessage } from "../lib/api"
import { formatDateTime, humanize } from "../lib/format"
import type { AuditLog, Page } from "../lib/types"

export function AuditPage() {
  const [action, setAction] = useState("")
  const [entityType, setEntityType] = useState("")
  const [actorId, setActorId] = useState("")
  const [fromDate, setFromDate] = useState("")
  const [page, setPage] = useState(1)
  const [expanded, setExpanded] = useState<Set<number>>(new Set())

  const auditQuery = useQuery({
    queryKey: ["audit-logs", { action, entityType, actorId, fromDate, page }],
    queryFn: async () =>
      (
        await api.get<Page<AuditLog>>("/admin/audit-logs", {
          params: {
            action: action || undefined,
            entity_type: entityType || undefined,
            actor_id: actorId ? Number(actorId) : undefined,
            from_date: fromDate || undefined,
            page,
            page_size: 25,
          },
        })
      ).data,
  })

  const logs = auditQuery.data?.items ?? []
  const pagination = auditQuery.data?.pagination

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
        title="Audit log"
        description="A tamper-evident record of staff actions, including metadata and source IP."
      />

      <Card padded={false}>
        <div className="flex flex-wrap items-end gap-3 border-b border-slate-100 p-4">
          <Field label="Action">
            <Input
              placeholder="e.g. LOAN_ISSUED"
              value={action}
              onChange={(event) => {
                setAction(event.target.value)
                setPage(1)
              }}
              className="w-52"
            />
          </Field>
          <Field label="Entity type">
            <Input
              placeholder="loan, user, book…"
              value={entityType}
              onChange={(event) => {
                setEntityType(event.target.value)
                setPage(1)
              }}
              className="w-44"
            />
          </Field>
          <Field label="Actor ID">
            <Input
              type="number"
              min={1}
              value={actorId}
              onChange={(event) => {
                setActorId(event.target.value)
                setPage(1)
              }}
              className="w-28"
            />
          </Field>
          <Field label="Since">
            <Input
              type="date"
              value={fromDate}
              onChange={(event) => {
                setFromDate(event.target.value)
                setPage(1)
              }}
            />
          </Field>
          <Button
            variant="ghost"
            onClick={() => {
              setAction("")
              setEntityType("")
              setActorId("")
              setFromDate("")
              setPage(1)
            }}
          >
            Clear
          </Button>
          <span className="ml-auto flex items-center gap-1.5 text-xs text-slate-400">
            <ScrollText className="h-3.5 w-3.5" />
            {pagination ? `${pagination.total} entries` : ""}
          </span>
        </div>

        {auditQuery.isLoading ? (
          <LoadingBlock label="Loading audit log…" />
        ) : auditQuery.isError ? (
          <ErrorBlock
            message={getErrorMessage(auditQuery.error)}
            onRetry={() => void auditQuery.refetch()}
          />
        ) : logs.length === 0 ? (
          <EmptyState title="No audit entries" description="No actions match these filters." />
        ) : (
          <>
            <Table>
              <thead>
                <tr>
                  <Th className="w-8" />
                  <Th>When</Th>
                  <Th>Actor</Th>
                  <Th>Action</Th>
                  <Th>Entity</Th>
                  <Th>Summary</Th>
                  <Th>IP</Th>
                </tr>
              </thead>
              <tbody>
                {logs.map((entry) => {
                  const isOpen = expanded.has(entry.id)
                  return (
                    <Fragment key={entry.id}>
                      <tr className="hover:bg-slate-50/60">
                        <Td>
                          <button
                            type="button"
                            onClick={() => toggle(entry.id)}
                            className="rounded p-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                            aria-label="Toggle details"
                          >
                            {isOpen ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                          </button>
                        </Td>
                        <Td className="whitespace-nowrap text-xs text-slate-500">
                          {formatDateTime(entry.created_at)}
                        </Td>
                        <Td>
                          <p className="text-xs font-medium text-slate-700">
                            {entry.actor_email ?? "system"}
                          </p>
                          <p className="text-[11px] text-slate-400">
                            {entry.actor_role ? humanize(entry.actor_role) : "—"}
                          </p>
                        </Td>
                        <Td>
                          <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] font-medium text-slate-600">
                            {entry.action}
                          </span>
                        </Td>
                        <Td className="text-xs text-slate-500">
                          {entry.entity_type
                            ? `${entry.entity_type}${entry.entity_id ? ` #${entry.entity_id}` : ""}`
                            : "—"}
                        </Td>
                        <Td className="max-w-sm text-xs text-slate-600">{entry.summary}</Td>
                        <Td className="font-mono text-[11px] text-slate-400">
                          {entry.ip_address ?? "—"}
                        </Td>
                      </tr>
                      {isOpen ? (
                        <tr className="bg-slate-50/70">
                          <td />
                          <td colSpan={6} className="px-4 py-3">
                            <div className="space-y-2">
                              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                                Metadata
                              </p>
                              <pre className="max-h-64 overflow-auto rounded-lg bg-slate-900 p-3 text-[11px] leading-relaxed text-slate-100">
                                {JSON.stringify(entry.metadata ?? {}, null, 2)}
                              </pre>
                              {entry.user_agent ? (
                                <p className="break-all text-[11px] text-slate-500">
                                  User agent: {entry.user_agent}
                                </p>
                              ) : null}
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
    </>
  )
}
