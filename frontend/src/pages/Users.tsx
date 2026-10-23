import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Search, ShieldCheck, UserCog } from "lucide-react"
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
  StatusBadge,
  Table,
  Td,
  Textarea,
  Th,
} from "../components/ui"
import { api, getErrorMessage } from "../lib/api"
import { useDebounced } from "../lib/hooks"
import { formatMoney, humanize } from "../lib/format"
import type { MemberListItem, Page, Role, UserStatus } from "../lib/types"

const roles: Role[] = ["SUPER_ADMIN", "LIBRARIAN", "FACULTY", "STUDENT"]
const statuses: UserStatus[] = ["ACTIVE", "PENDING", "SUSPENDED", "INACTIVE"]

export function UsersPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState("")
  const debouncedSearch = useDebounced(search)
  const [role, setRole] = useState("")
  const [status, setStatus] = useState("")
  const [page, setPage] = useState(1)

  const [roleTarget, setRoleTarget] = useState<MemberListItem | null>(null)
  const [statusTarget, setStatusTarget] = useState<MemberListItem | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const usersQuery = useQuery({
    queryKey: ["admin-users", { search: debouncedSearch, role, status, page }],
    queryFn: async () =>
      (
        await api.get<Page<MemberListItem>>("/admin/users", {
          params: {
            search: debouncedSearch || undefined,
            role: role || undefined,
            status: status || undefined,
            page,
            page_size: 20,
          },
        })
      ).data,
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["admin-users"] })
    void queryClient.invalidateQueries({ queryKey: ["members"] })
  }

  const changeRole = useMutation({
    mutationFn: async ({ id, role: newRole }: { id: number; role: Role }) =>
      (
        await api.patch(`/admin/users/${id}/role`, null, {
          params: { role: newRole },
        })
      ).data,
    onSuccess: () => {
      invalidate()
      setRoleTarget(null)
      setNotice("Account role updated.")
    },
    onError: (mutationError) => setError(getErrorMessage(mutationError)),
  })

  const changeStatus = useMutation({
    mutationFn: async ({
      id,
      status: newStatus,
      reason,
    }: {
      id: number
      status: UserStatus
      reason: string
    }) =>
      (
        await api.patch(`/admin/users/${id}/status`, null, {
          params: { status: newStatus, reason: reason || undefined },
        })
      ).data,
    onSuccess: () => {
      invalidate()
      setStatusTarget(null)
      setNotice("Account status updated.")
    },
    onError: (mutationError) => setError(getErrorMessage(mutationError)),
  })

  const users = usersQuery.data?.items ?? []
  const pagination = usersQuery.data?.pagination

  return (
    <>
      <PageHeader
        title="User accounts"
        description="Roles and account status across the whole system."
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
          <div className="relative min-w-56 flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input
              className="pl-9"
              placeholder="Search name, e-mail or ID…"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                setPage(1)
              }}
            />
          </div>
          <Select
            className="w-44"
            value={role}
            onChange={(event) => {
              setRole(event.target.value)
              setPage(1)
            }}
          >
            <option value="">All roles</option>
            {roles.map((item) => (
              <option key={item} value={item}>
                {humanize(item)}
              </option>
            ))}
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
            {statuses.map((item) => (
              <option key={item} value={item}>
                {humanize(item)}
              </option>
            ))}
          </Select>
        </div>

        {usersQuery.isLoading ? (
          <LoadingBlock label="Loading users…" />
        ) : usersQuery.isError ? (
          <ErrorBlock
            message={getErrorMessage(usersQuery.error)}
            onRetry={() => void usersQuery.refetch()}
          />
        ) : users.length === 0 ? (
          <EmptyState title="No users found" description="Try a different search." />
        ) : (
          <>
            <Table>
              <thead>
                <tr>
                  <Th>Account</Th>
                  <Th>Role</Th>
                  <Th>Institutional ID</Th>
                  <Th>Status</Th>
                  <Th>Active loans</Th>
                  <Th>Fines</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              </thead>
              <tbody>
                {users.map((account) => (
                  <tr key={account.id} className="hover:bg-slate-50/60">
                    <Td>
                      <Link
                        to={`/members/${account.id}`}
                        className="font-medium text-slate-800 hover:text-brand-700"
                      >
                        {account.full_name}
                      </Link>
                      <p className="text-[11px] text-slate-500">{account.email}</p>
                    </Td>
                    <Td>
                      <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
                        <ShieldCheck className="h-3 w-3" />
                        {humanize(account.role)}
                      </span>
                    </Td>
                    <Td className="font-mono text-xs text-slate-500">
                      {account.institutional_id ?? "—"}
                    </Td>
                    <Td>
                      <StatusBadge status={account.status} />
                    </Td>
                    <Td className="text-sm text-slate-600">{account.active_loans}</Td>
                    <Td
                      className={
                        account.outstanding_fines > 0
                          ? "text-sm font-semibold text-rose-600"
                          : "text-sm text-slate-400"
                      }
                    >
                      {formatMoney(account.outstanding_fines)}
                    </Td>
                    <Td>
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setError(null)
                            setRoleTarget(account)
                          }}
                        >
                          <UserCog className="h-3.5 w-3.5" /> Role
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setError(null)
                            setStatusTarget(account)
                          }}
                        >
                          Status
                        </Button>
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

      <Modal
        open={roleTarget !== null}
        onClose={() => {
          setRoleTarget(null)
          setError(null)
        }}
        title="Change account role"
        description={
          roleTarget
            ? `${roleTarget.full_name} · currently ${humanize(roleTarget.role)}`
            : undefined
        }
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setRoleTarget(null)
                setError(null)
              }}
            >
              Cancel
            </Button>
            <Button type="submit" form="role-form" loading={changeRole.isPending}>
              Update role
            </Button>
          </>
        }
      >
        <form
          id="role-form"
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            if (!roleTarget) return
            const data = new FormData(event.currentTarget)
            changeRole.mutate({ id: roleTarget.id, role: data.get("role") as Role })
          }}
        >
          {error ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </p>
          ) : null}
          <Field label="Role" required>
            <Select name="role" defaultValue={roleTarget?.role}>
              {roles.map((item) => (
                <option key={item} value={item}>
                  {humanize(item)}
                </option>
              ))}
            </Select>
          </Field>
          <p className="text-xs text-slate-500">
            Super admins manage accounts and settings; librarians run circulation and
            catalogue operations.
          </p>
        </form>
      </Modal>

      <Modal
        open={statusTarget !== null}
        onClose={() => {
          setStatusTarget(null)
          setError(null)
        }}
        title="Change account status"
        description={
          statusTarget
            ? `${statusTarget.full_name} · currently ${humanize(statusTarget.status)}`
            : undefined
        }
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setStatusTarget(null)
                setError(null)
              }}
            >
              Cancel
            </Button>
            <Button type="submit" form="user-status-form" loading={changeStatus.isPending}>
              Update status
            </Button>
          </>
        }
      >
        <form
          id="user-status-form"
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            if (!statusTarget) return
            const data = new FormData(event.currentTarget)
            changeStatus.mutate({
              id: statusTarget.id,
              status: data.get("status") as UserStatus,
              reason: String(data.get("reason") ?? "").trim(),
            })
          }}
        >
          {error ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </p>
          ) : null}
          <Field label="Status" required>
            <Select name="status" defaultValue={statusTarget?.status}>
              {statuses.map((item) => (
                <option key={item} value={item}>
                  {humanize(item)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Reason" hint="Stored in the audit log.">
            <Textarea name="reason" rows={2} />
          </Field>
        </form>
      </Modal>
    </>
  )
}
