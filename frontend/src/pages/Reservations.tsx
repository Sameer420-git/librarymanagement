import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { BookMarked, XCircle } from "lucide-react"
import { useState } from "react"
import { Link } from "react-router-dom"

import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBlock,
  LoadingBlock,
  Modal,
  PageHeader,
  Pagination,
  StatusBadge,
  Table,
  Td,
  Th,
} from "../components/ui"
import { useAuth } from "../context/AuthContext"
import { api, getErrorMessage } from "../lib/api"
import { formatDateTime } from "../lib/format"
import type { Page, Reservation } from "../lib/types"

const filters = [
  { value: "ACTIVE", label: "Active" },
  { value: "READY", label: "Ready for pickup" },
  { value: "FULFILLED", label: "Fulfilled" },
  { value: "CANCELLED", label: "Cancelled" },
  { value: "EXPIRED", label: "Expired" },
  { value: "", label: "All" },
]

export function ReservationsPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState("ACTIVE")
  const [page, setPage] = useState(1)
  const [cancelTarget, setCancelTarget] = useState<Reservation | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reservationsQuery = useQuery({
    queryKey: ["reservations", { statusFilter, page }],
    queryFn: async () =>
      (
        await api.get<Page<Reservation>>("/reservations", {
          params: { status: statusFilter || undefined, page, page_size: 20 },
        })
      ).data,
  })

  const cancel = useMutation({
    mutationFn: async (id: number) =>
      (await api.post<Reservation>(`/reservations/${id}/cancel`)).data,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reservations"] })
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      setCancelTarget(null)
      setNotice("Reservation cancelled.")
    },
    onError: (mutationError) => setError(getErrorMessage(mutationError)),
  })

  const reservations = reservationsQuery.data?.items ?? []
  const pagination = reservationsQuery.data?.pagination
  const isStaff = user?.role === "SUPER_ADMIN" || user?.role === "LIBRARIAN"

  return (
    <>
      <PageHeader
        title="Reservations"
        description={
          isStaff
            ? "Holds placed by members, in queue order."
            : "Your holds. You will be e-mailed when a copy is ready."
        }
        actions={
          <Link to="/catalogue">
            <Button variant="secondary">
              <BookMarked className="h-4 w-4" /> Browse catalogue
            </Button>
          </Link>
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
        <div className="flex flex-wrap gap-2 border-b border-slate-100 p-4">
          {filters.map((filter) => (
            <button
              key={filter.label}
              type="button"
              onClick={() => {
                setStatusFilter(filter.value)
                setPage(1)
              }}
              className={
                statusFilter === filter.value
                  ? "rounded-full bg-slate-900 px-3.5 py-1.5 text-xs font-semibold text-white"
                  : "rounded-full bg-slate-100 px-3.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-200"
              }
            >
              {filter.label}
            </button>
          ))}
        </div>

        {reservationsQuery.isLoading ? (
          <LoadingBlock label="Loading reservations…" />
        ) : reservationsQuery.isError ? (
          <ErrorBlock
            message={getErrorMessage(reservationsQuery.error)}
            onRetry={() => void reservationsQuery.refetch()}
          />
        ) : reservations.length === 0 ? (
          <EmptyState
            title="No reservations"
            description={
              isStaff
                ? "No holds match this filter."
                : "Reserve a title from the catalogue when all copies are out."
            }
          />
        ) : (
          <>
            <Table>
              <thead>
                <tr>
                  <Th>Title</Th>
                  {isStaff ? <Th>Member</Th> : null}
                  <Th>Reserved</Th>
                  <Th>Queue</Th>
                  <Th>Pickup by</Th>
                  <Th>Status</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              </thead>
              <tbody>
                {reservations.map((reservation) => {
                  const cancellable =
                    reservation.status === "ACTIVE" || reservation.status === "READY"
                  return (
                    <tr key={reservation.id} className="hover:bg-slate-50/60">
                      <Td>
                        <Link
                          to={`/catalogue/${reservation.book_id}`}
                          className="font-medium text-slate-800 hover:text-brand-700"
                        >
                          {reservation.book_title}
                        </Link>
                        <p className="text-[11px] text-slate-500">
                          {reservation.book_authors.join(", ")}
                        </p>
                      </Td>
                      {isStaff ? (
                        <Td>
                          <Link
                            to={`/members/${reservation.member_id}`}
                            className="text-xs font-medium text-slate-700 hover:text-brand-700"
                          >
                            {reservation.member_name}
                          </Link>
                        </Td>
                      ) : null}
                      <Td className="text-xs text-slate-500">
                        {formatDateTime(reservation.reserved_at)}
                      </Td>
                      <Td className="text-xs text-slate-600">
                        {reservation.status === "READY" ? (
                          <Badge tone="green">Ready</Badge>
                        ) : (
                          `#${reservation.queue_position}`
                        )}
                      </Td>
                      <Td className="text-xs text-slate-500">
                        {formatDateTime(reservation.pickup_deadline)}
                      </Td>
                      <Td>
                        <StatusBadge status={reservation.status} />
                        {reservation.accession_number ? (
                          <p className="mt-0.5 font-mono text-[11px] text-slate-500">
                            {reservation.accession_number}
                          </p>
                        ) : null}
                      </Td>
                      <Td className="text-right">
                        {cancellable ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setError(null)
                              setCancelTarget(reservation)
                            }}
                          >
                            <XCircle className="h-3.5 w-3.5" /> Cancel
                          </Button>
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </Td>
                    </tr>
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
        open={cancelTarget !== null}
        onClose={() => {
          setCancelTarget(null)
          setError(null)
        }}
        title="Cancel reservation?"
        description={
          cancelTarget
            ? `"${cancelTarget.book_title}" will be released to the next member in the queue.`
            : undefined
        }
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setCancelTarget(null)
                setError(null)
              }}
            >
              Keep it
            </Button>
            <Button
              variant="danger"
              loading={cancel.isPending}
              onClick={() => cancelTarget && cancel.mutate(cancelTarget.id)}
            >
              Cancel reservation
            </Button>
          </>
        }
      >
        {error ? (
          <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </p>
        ) : (
          <p className="text-sm text-slate-600">
            Cancelling cannot be undone. Any queue position is lost.
          </p>
        )}
      </Modal>
    </>
  )
}
