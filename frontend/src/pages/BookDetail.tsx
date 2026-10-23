import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  ArrowLeft,
  BookmarkPlus,
  CopyPlus,
  Pencil,
  Trash2,
} from "lucide-react"
import { useState } from "react"
import { useNavigate, useParams } from "react-router-dom"

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
  Select,
  StatusBadge,
  Table,
  Td,
  Textarea,
  Th,
} from "../components/ui"
import { useAuth } from "../context/AuthContext"
import { api, getErrorMessage } from "../lib/api"
import { formatDate, formatMoney } from "../lib/format"
import { isStaff } from "../lib/permissions"
import type {
  BookCopy,
  BookDetail,
  BookInput,
  CopyCondition,
  CopyStatus,
} from "../lib/types"

const conditions: CopyCondition[] = ["NEW", "GOOD", "FAIR", "POOR", "DAMAGED"]
const copyStatuses: CopyStatus[] = [
  "AVAILABLE",
  "ISSUED",
  "RESERVED",
  "LOST",
  "DAMAGED",
  "RETIRED",
]

export function BookDetailPage() {
  const { id } = useParams<{ id: string }>()
  const bookId = Number(id)
  const { user } = useAuth()
  const staff = isStaff(user?.role)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [notice, setNotice] = useState<string | null>(null)
  const [editOpen, setEditOpen] = useState(false)
  const [addCopyOpen, setAddCopyOpen] = useState(false)
  const [retireOpen, setRetireOpen] = useState(false)
  const [statusCopy, setStatusCopy] = useState<BookCopy | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const bookQuery = useQuery({
    queryKey: ["book", bookId],
    queryFn: async () => (await api.get<BookDetail>(`/books/${bookId}`)).data,
    enabled: Number.isFinite(bookId),
  })

  const copiesQuery = useQuery({
    queryKey: ["copies", bookId],
    queryFn: async () =>
      (
        await api.get<{ items: BookCopy[] }>(`/books/${bookId}/copies`, {
          params: { page_size: 100 },
        })
      ).data.items,
    enabled: Number.isFinite(bookId),
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["book", bookId] })
    void queryClient.invalidateQueries({ queryKey: ["copies", bookId] })
    void queryClient.invalidateQueries({ queryKey: ["books"] })
  }

  const updateBook = useMutation({
    mutationFn: async (payload: BookInput) =>
      (await api.put<BookDetail>(`/books/${bookId}`, payload)).data,
    onSuccess: () => {
      invalidate()
      setEditOpen(false)
      setNotice("Catalogue details updated.")
    },
    onError: (error) => setFormError(getErrorMessage(error)),
  })

  const addCopy = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await api.post<BookCopy>(`/books/${bookId}/copies`, payload)).data,
    onSuccess: () => {
      invalidate()
      setAddCopyOpen(false)
      setNotice("Physical copy added.")
    },
    onError: (error) => setFormError(getErrorMessage(error)),
  })

  const changeStatus = useMutation({
    mutationFn: async ({ copyId, status, reason }: { copyId: number; status: CopyStatus; reason: string }) =>
      (
        await api.patch<BookCopy>(`/copies/${copyId}/status`, {
          status,
          reason: reason || null,
        })
      ).data,
    onSuccess: () => {
      invalidate()
      setStatusCopy(null)
      setNotice("Copy status updated.")
    },
    onError: (error) => setFormError(getErrorMessage(error)),
  })

  const retire = useMutation({
    mutationFn: async () => (await api.delete<BookDetail>(`/books/${bookId}`)).data,
    onSuccess: () => {
      invalidate()
      setRetireOpen(false)
      setNotice("The title has been retired. Existing loans are unaffected.")
    },
    onError: (error) => setFormError(getErrorMessage(error)),
  })

  const reserve = useMutation({
    mutationFn: async () => (await api.post("/reservations", { book_id: bookId })).data,
    onSuccess: () => {
      setNotice("Reservation placed. You will be notified when a copy is ready.")
      void queryClient.invalidateQueries({ queryKey: ["reservations"] })
    },
    onError: (error) => setNotice(getErrorMessage(error)),
  })

  if (bookQuery.isLoading) return <LoadingBlock label="Loading title…" />
  if (bookQuery.isError || !bookQuery.data) {
    return (
      <ErrorBlock
        message={getErrorMessage(bookQuery.error)}
        onRetry={() => void bookQuery.refetch()}
      />
    )
  }

  const book = bookQuery.data
  const copies = copiesQuery.data ?? []

  return (
    <>
      <button
        type="button"
        onClick={() => navigate("/catalogue")}
        className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-800"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back to catalogue
      </button>

      <PageHeader
        title={book.title}
        description={
          book.authors.length > 0 ? book.authors.join(", ") : "Author not recorded"
        }
        actions={
          <>
            {!staff && book.is_active && !book.is_reference_only && book.available_copies === 0 ? (
              <Button
                variant="secondary"
                loading={reserve.isPending}
                onClick={() => reserve.mutate()}
              >
                <BookmarkPlus className="h-4 w-4" /> Reserve
              </Button>
            ) : null}
            {staff ? (
              <>
                <Button variant="secondary" onClick={() => setEditOpen(true)}>
                  <Pencil className="h-4 w-4" /> Edit
                </Button>
                <Button onClick={() => setAddCopyOpen(true)}>
                  <CopyPlus className="h-4 w-4" /> Add copy
                </Button>
                {book.is_active ? (
                  <Button variant="danger" onClick={() => setRetireOpen(true)}>
                    <Trash2 className="h-4 w-4" /> Retire
                  </Button>
                ) : null}
              </>
            ) : null}
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

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="About this title" className="lg:col-span-2">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Badge tone={book.is_active ? "green" : "slate"}>
              {book.is_active ? "Active" : "Retired"}
            </Badge>
            {book.is_reference_only ? <Badge tone="purple">Reference only</Badge> : null}
            <Badge tone={book.available_copies > 0 ? "teal" : "amber"}>
              {book.available_copies} of {book.total_copies} available
            </Badge>
            {book.category_name ? <Badge tone="slate">{book.category_name}</Badge> : null}
          </div>
          <p className="whitespace-pre-line text-sm leading-relaxed text-slate-600">
            {book.description || "No description has been recorded for this title."}
          </p>
          <dl className="mt-5 grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
            <Detail label="ISBN" value={book.isbn} mono />
            <Detail label="Publisher" value={book.publisher_name} />
            <Detail label="Edition" value={book.edition} />
            <Detail label="Published" value={book.publication_year?.toString()} />
            <Detail label="Language" value={book.language} />
            <Detail
              label="Shelf"
              value={
                book.shelf_location
                  ? `${book.shelf_location}${book.rack_number ? ` · ${book.rack_number}` : ""}`
                  : null
              }
            />
            <Detail label="Keywords" value={book.keywords} />
            <Detail label="Subjects" value={book.subjects} />
          </dl>
        </Card>

        <Card title="Availability" description="Copies currently held by the library.">
          <div className="space-y-3">
            <div className="flex items-center justify-between rounded-lg bg-emerald-50 px-4 py-3">
              <span className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
                Available
              </span>
              <span className="text-2xl font-semibold text-emerald-800">
                {book.available_copies}
              </span>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-sky-50 px-4 py-3">
              <span className="text-xs font-semibold uppercase tracking-wide text-sky-700">
                On loan
              </span>
              <span className="text-2xl font-semibold text-sky-800">
                {copies.filter((copy) => copy.status === "ISSUED").length}
              </span>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                Total copies
              </span>
              <span className="text-2xl font-semibold text-slate-800">
                {book.total_copies}
              </span>
            </div>
          </div>
          {!staff ? (
            <p className="mt-4 text-xs text-slate-500">
              Ask at the circulation desk if you need help locating this title.
            </p>
          ) : null}
        </Card>
      </div>

      <Card
        title="Physical copies"
        description={`${copies.length} cop${copies.length === 1 ? "y" : "ies"} recorded`}
        padded={false}
      >
        {copiesQuery.isLoading ? (
          <LoadingBlock />
        ) : copies.length === 0 ? (
          <EmptyState
            title="No physical copies yet"
            description="Add a copy so this title can be issued."
            action={
              staff ? (
                <Button size="sm" onClick={() => setAddCopyOpen(true)}>
                  Add copy
                </Button>
              ) : undefined
            }
          />
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Accession</Th>
                <Th>Barcode</Th>
                <Th>Status</Th>
                <Th>Condition</Th>
                <Th>Location</Th>
                <Th>Acquired</Th>
                <Th>Price</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </thead>
            <tbody>
              {copies.map((copy) => (
                <tr key={copy.id} className="hover:bg-slate-50/60">
                  <Td className="font-mono text-xs font-medium text-slate-700">
                    {copy.accession_number}
                  </Td>
                  <Td className="font-mono text-xs text-slate-500">
                    {copy.barcode ?? "—"}
                  </Td>
                  <Td>
                    <StatusBadge status={copy.status} />
                    {copy.active_loan_due_at ? (
                      <p className="mt-0.5 text-[11px] text-slate-500">
                        Due {formatDate(copy.active_loan_due_at)}
                      </p>
                    ) : null}
                  </Td>
                  <Td className="text-xs text-slate-600">{copy.condition}</Td>
                  <Td className="text-xs text-slate-500">
                    {copy.shelf_location ?? "—"}
                    {copy.rack_number ? ` · ${copy.rack_number}` : ""}
                  </Td>
                  <Td className="text-xs text-slate-500">
                    {formatDate(copy.acquisition_date)}
                  </Td>
                  <Td className="text-xs text-slate-500">{formatMoney(copy.price)}</Td>
                  <Td className="text-right">
                    {staff ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setFormError(null)
                          setStatusCopy(copy)
                        }}
                      >
                        Change status
                      </Button>
                    ) : (
                      <span className="text-xs text-slate-400">—</span>
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <EditBookModal
        open={editOpen}
        book={book}
        error={formError}
        saving={updateBook.isPending}
        onClose={() => {
          setEditOpen(false)
          setFormError(null)
        }}
        onSave={(payload) => {
          setFormError(null)
          updateBook.mutate(payload)
        }}
      />

      <AddCopyModal
        open={addCopyOpen}
        error={formError}
        saving={addCopy.isPending}
        defaults={{
          shelf_location: book.shelf_location ?? "",
          rack_number: book.rack_number ?? "",
        }}
        onClose={() => {
          setAddCopyOpen(false)
          setFormError(null)
        }}
        onSave={(payload) => {
          setFormError(null)
          addCopy.mutate(payload)
        }}
      />

      <Modal
        open={statusCopy !== null}
        onClose={() => {
          setStatusCopy(null)
          setFormError(null)
        }}
        title={`Change status · ${statusCopy?.accession_number ?? ""}`}
        description="Status changes are audited. Issued copies must be returned through circulation."
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setStatusCopy(null)
                setFormError(null)
              }}
            >
              Cancel
            </Button>
            <Button
              loading={changeStatus.isPending}
              onClick={() => {
                const form = document.getElementById("copy-status-form") as HTMLFormElement | null
                form?.requestSubmit()
              }}
            >
              Save status
            </Button>
          </>
        }
      >
        <form
          id="copy-status-form"
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            const data = new FormData(event.currentTarget)
            if (!statusCopy) return
            changeStatus.mutate({
              copyId: statusCopy.id,
              status: data.get("status") as CopyStatus,
              reason: String(data.get("reason") ?? ""),
            })
          }}
        >
          {formError ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {formError}
            </p>
          ) : null}
          <Field label="New status" required>
            <Select name="status" defaultValue={statusCopy?.status ?? "AVAILABLE"}>
              {copyStatuses.map((status) => (
                <option key={status} value={status}>
                  {status.charAt(0) + status.slice(1).toLowerCase()}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Reason" hint="Required for lost, damaged or retired copies.">
            <Textarea name="reason" rows={2} placeholder="e.g. Water damage reported by member" />
          </Field>
        </form>
      </Modal>

      <Modal
        open={retireOpen}
        onClose={() => setRetireOpen(false)}
        title="Retire this title?"
        description="The title will be hidden from the catalogue and cannot be issued. Existing loans remain valid."
        footer={
          <>
            <Button variant="secondary" onClick={() => setRetireOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" loading={retire.isPending} onClick={() => retire.mutate()}>
              Retire title
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-600">
          <strong className="font-semibold text-slate-800">{book.title}</strong> has{" "}
          {book.total_copies} recorded cop{book.total_copies === 1 ? "y" : "ies"} and{" "}
          {book.available_copies} currently available.
        </p>
        {formError ? (
          <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {formError}
          </p>
        ) : null}
      </Modal>
    </>
  )
}

function Detail({
  label,
  value,
  mono,
}: {
  label: string
  value: string | null | undefined
  mono?: boolean
}) {
  return (
    <div>
      <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
        {label}
      </dt>
      <dd className={mono ? "font-mono text-xs text-slate-700" : "text-slate-700"}>
        {value || "—"}
      </dd>
    </div>
  )
}

function EditBookModal({
  open,
  book,
  error,
  saving,
  onClose,
  onSave,
}: {
  open: boolean
  book: BookDetail
  error: string | null
  saving: boolean
  onClose: () => void
  onSave: (payload: BookInput) => void
}) {
  const [values, setValues] = useState(() => initialValues(book))

  if (!open) return null

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Edit catalogue details"
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="edit-book-form" loading={saving}>
            Save changes
          </Button>
        </>
      }
    >
      <form
        id="edit-book-form"
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault()
          onSave({
            title: values.title.trim(),
            subtitle: values.subtitle.trim() || null,
            isbn: values.isbn.trim() || null,
            publisher_name: values.publisher_name.trim() || null,
            category_name: values.category_name.trim() || null,
            edition: values.edition.trim() || null,
            publication_year: values.publication_year
              ? Number(values.publication_year)
              : null,
            language: values.language || "English",
            shelf_location: values.shelf_location.trim() || null,
            rack_number: values.rack_number.trim() || null,
            description: values.description.trim() || null,
            is_reference_only: values.is_reference_only,
            author_names: values.authors
              .split(",")
              .map((name) => name.trim())
              .filter(Boolean),
          })
        }}
      >
        {error ? (
          <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </p>
        ) : null}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Title" required className="sm:col-span-2">
            <Input
              value={values.title}
              onChange={(event) => setValues({ ...values, title: event.target.value })}
              required
            />
          </Field>
          <Field label="Subtitle" className="sm:col-span-2">
            <Input
              value={values.subtitle}
              onChange={(event) => setValues({ ...values, subtitle: event.target.value })}
            />
          </Field>
          <Field label="Authors" hint="Comma separated" className="sm:col-span-2">
            <Input
              value={values.authors}
              onChange={(event) => setValues({ ...values, authors: event.target.value })}
            />
          </Field>
          <Field label="ISBN">
            <Input
              value={values.isbn}
              onChange={(event) => setValues({ ...values, isbn: event.target.value })}
            />
          </Field>
          <Field label="Publisher">
            <Input
              value={values.publisher_name}
              onChange={(event) =>
                setValues({ ...values, publisher_name: event.target.value })
              }
            />
          </Field>
          <Field label="Category">
            <Input
              value={values.category_name}
              onChange={(event) =>
                setValues({ ...values, category_name: event.target.value })
              }
            />
          </Field>
          <Field label="Edition">
            <Input
              value={values.edition}
              onChange={(event) => setValues({ ...values, edition: event.target.value })}
            />
          </Field>
          <Field label="Publication year">
            <Input
              type="number"
              min={1000}
              max={2200}
              value={values.publication_year}
              onChange={(event) =>
                setValues({ ...values, publication_year: event.target.value })
              }
            />
          </Field>
          <Field label="Language">
            <Input
              value={values.language}
              onChange={(event) => setValues({ ...values, language: event.target.value })}
            />
          </Field>
          <Field label="Shelf location">
            <Input
              value={values.shelf_location}
              onChange={(event) =>
                setValues({ ...values, shelf_location: event.target.value })
              }
            />
          </Field>
          <Field label="Rack number">
            <Input
              value={values.rack_number}
              onChange={(event) =>
                setValues({ ...values, rack_number: event.target.value })
              }
            />
          </Field>
          <Field label="Description" className="sm:col-span-2">
            <Textarea
              rows={3}
              value={values.description}
              onChange={(event) =>
                setValues({ ...values, description: event.target.value })
              }
            />
          </Field>
          <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600 sm:col-span-2">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-600"
              checked={values.is_reference_only}
              onChange={(event) =>
                setValues({ ...values, is_reference_only: event.target.checked })
              }
            />
            Reference only
          </label>
        </div>
      </form>
    </Modal>
  )
}

function initialValues(book: BookDetail) {
  return {
    title: book.title,
    subtitle: book.subtitle ?? "",
    authors: book.authors.join(", "),
    isbn: book.isbn ?? "",
    publisher_name: book.publisher_name ?? "",
    category_name: book.category_name ?? "",
    edition: book.edition ?? "",
    publication_year: book.publication_year?.toString() ?? "",
    language: book.language ?? "English",
    shelf_location: book.shelf_location ?? "",
    rack_number: book.rack_number ?? "",
    description: book.description ?? "",
    is_reference_only: book.is_reference_only,
  }
}

function AddCopyModal({
  open,
  error,
  saving,
  defaults,
  onClose,
  onSave,
}: {
  open: boolean
  error: string | null
  saving: boolean
  defaults: { shelf_location: string; rack_number: string }
  onClose: () => void
  onSave: (payload: Record<string, unknown>) => void
}) {
  if (!open) return null
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add a physical copy"
      description="Accession numbers must be unique across the entire library."
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="add-copy-form" loading={saving}>
            Add copy
          </Button>
        </>
      }
    >
      <form
        id="add-copy-form"
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault()
          const data = new FormData(event.currentTarget)
          onSave({
            accession_number: String(data.get("accession_number") ?? "").trim(),
            barcode: String(data.get("barcode") ?? "").trim() || null,
            condition: data.get("condition"),
            acquisition_date: data.get("acquisition_date") || null,
            price: data.get("price") ? Number(data.get("price")) : null,
            shelf_location:
              String(data.get("shelf_location") ?? "").trim() || null,
            rack_number: String(data.get("rack_number") ?? "").trim() || null,
            notes: String(data.get("notes") ?? "").trim() || null,
          })
        }}
      >
        {error ? (
          <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </p>
        ) : null}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Accession number" required>
            <Input name="accession_number" placeholder="ACC00042" required autoFocus />
          </Field>
          <Field label="Barcode">
            <Input name="barcode" placeholder="BC00042" />
          </Field>
          <Field label="Condition">
            <Select name="condition" defaultValue="GOOD">
              {conditions.map((condition) => (
                <option key={condition} value={condition}>
                  {condition.charAt(0) + condition.slice(1).toLowerCase()}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Acquisition date">
            <Input name="acquisition_date" type="date" />
          </Field>
          <Field label="Price">
            <Input name="price" type="number" min={0} step="0.01" />
          </Field>
          <Field label="Shelf location">
            <Input name="shelf_location" defaultValue={defaults.shelf_location} />
          </Field>
          <Field label="Rack number">
            <Input name="rack_number" defaultValue={defaults.rack_number} />
          </Field>
          <Field label="Notes" className="sm:col-span-2">
            <Textarea name="notes" rows={2} />
          </Field>
        </div>
      </form>
    </Modal>
  )
}
