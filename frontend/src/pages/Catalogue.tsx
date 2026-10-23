import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  BookPlus,
  BookmarkPlus,
  Download,
  Search,
  Upload,
} from "lucide-react"
import { useRef, useState, type ChangeEvent, type FormEvent } from "react"
import { Link, useSearchParams } from "react-router-dom"

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
  Table,
  Td,
  Textarea,
  Th,
  cn,
} from "../components/ui"
import { useAuth } from "../context/AuthContext"
import { api, downloadFile, getErrorMessage } from "../lib/api"
import { useDebounced } from "../lib/hooks"
import { isStaff } from "../lib/permissions"
import type {
  BookInput,
  BookSummary,
  Category,
  ImportResult,
  Page,
} from "../lib/types"

interface BookFormState {
  title: string
  subtitle: string
  authors: string
  isbn: string
  publisher_name: string
  category_name: string
  edition: string
  publication_year: string
  language: string
  shelf_location: string
  rack_number: string
  description: string
  is_reference_only: boolean
}

const emptyForm: BookFormState = {
  title: "",
  subtitle: "",
  authors: "",
  isbn: "",
  publisher_name: "",
  category_name: "",
  edition: "",
  publication_year: "",
  language: "English",
  shelf_location: "",
  rack_number: "",
  description: "",
  is_reference_only: false,
}

export function CataloguePage() {
  const { user } = useAuth()
  const staff = isStaff(user?.role)
  const queryClient = useQueryClient()
  const [params, setParams] = useSearchParams()

  const [search, setSearch] = useState("")
  const debouncedSearch = useDebounced(search)
  const [categoryId, setCategoryId] = useState("")
  const [availableOnly, setAvailableOnly] = useState(false)
  const [includeInactive, setIncludeInactive] = useState(false)
  const [page, setPage] = useState(1)
  const [modalOpen, setModalOpen] = useState(params.get("new") === "1")
  const [form, setForm] = useState<BookFormState>(emptyForm)
  const [formError, setFormError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [importOpen, setImportOpen] = useState(false)
  const [importResult, setImportResult] = useState<ImportResult | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const booksQuery = useQuery({
    queryKey: [
      "books",
      { search: debouncedSearch, categoryId, availableOnly, includeInactive, page },
    ],
    queryFn: async () =>
      (
        await api.get<Page<BookSummary>>("/books", {
          params: {
            search: debouncedSearch || undefined,
            category_id: categoryId || undefined,
            available_only: availableOnly || undefined,
            include_inactive: staff && includeInactive ? true : undefined,
            page,
            page_size: 20,
            sort_by: "title",
            sort_order: "asc",
          },
        })
      ).data,
  })

  const categoriesQuery = useQuery({
    queryKey: ["categories"],
    queryFn: async () => (await api.get<Category[]>("/categories")).data,
  })

  const createBook = useMutation({
    mutationFn: async (payload: BookInput) =>
      (await api.post<BookSummary>("/books", payload)).data,
    onSuccess: (book) => {
      void queryClient.invalidateQueries({ queryKey: ["books"] })
      setModalOpen(false)
      setForm(emptyForm)
      setParams({})
      setNotice(`"${book.title}" was added to the catalogue.`)
    },
    onError: (error) => setFormError(getErrorMessage(error)),
  })

  const reserve = useMutation({
    mutationFn: async (bookId: number) =>
      (await api.post("/reservations", { book_id: bookId })).data,
    onSuccess: () => {
      setNotice("Reservation placed. You will be notified when a copy is ready.")
      void queryClient.invalidateQueries({ queryKey: ["reservations"] })
    },
    onError: (error) => setNotice(getErrorMessage(error)),
  })

  const importBooks = useMutation({
    mutationFn: async (file: File) => {
      const data = new FormData()
      data.append("file", file)
      return (await api.post<ImportResult>("/books/import", data)).data
    },
    onSuccess: (result) => {
      setImportResult(result)
      void queryClient.invalidateQueries({ queryKey: ["books"] })
    },
    onError: (error) => setImportResult({ total_rows: 0, created: 0, updated: 0, skipped: 0, failed: 1, errors: [{ message: getErrorMessage(error) }] }),
  })

  const openCreate = () => {
    setFormError(null)
    setModalOpen(true)
  }

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    setFormError(null)
    const payload: BookInput = {
      title: form.title.trim(),
      subtitle: form.subtitle.trim() || null,
      isbn: form.isbn.trim() || null,
      publisher_name: form.publisher_name.trim() || null,
      category_name: form.category_name.trim() || null,
      edition: form.edition.trim() || null,
      publication_year: form.publication_year ? Number(form.publication_year) : null,
      language: form.language || "English",
      shelf_location: form.shelf_location.trim() || null,
      rack_number: form.rack_number.trim() || null,
      description: form.description.trim() || null,
      is_reference_only: form.is_reference_only,
      author_names: form.authors
        .split(",")
        .map((name) => name.trim())
        .filter(Boolean),
    }
    createBook.mutate(payload)
  }

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) importBooks.mutate(file)
    event.target.value = ""
  }

  const update = <K extends keyof BookFormState>(key: K, value: BookFormState[K]) => {
    setForm((current) => ({ ...current, [key]: value }))
  }

  const books = booksQuery.data?.items ?? []
  const pagination = booksQuery.data?.pagination

  return (
    <>
      <PageHeader
        title="Catalogue"
        description="Titles and physical copies held by the library."
        actions={
          staff ? (
            <>
              <Button variant="secondary" onClick={() => setImportOpen(true)}>
                <Upload className="h-4 w-4" /> Import
              </Button>
              <Button
                variant="secondary"
                onClick={() => void downloadFile("/books/export/csv", "catalogue.csv")}
              >
                <Download className="h-4 w-4" /> Export
              </Button>
              <Button onClick={openCreate}>
                <BookPlus className="h-4 w-4" /> Add title
              </Button>
            </>
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

      <Card padded={false}>
        <div className="flex flex-wrap items-end gap-3 border-b border-slate-100 p-4">
          <div className="relative min-w-56 flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input
              className="pl-9"
              placeholder="Search title, author, ISBN or keyword…"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                setPage(1)
              }}
            />
          </div>
          <Select
            className="w-44"
            value={categoryId}
            onChange={(event) => {
              setCategoryId(event.target.value)
              setPage(1)
            }}
          >
            <option value="">All categories</option>
            {categoriesQuery.data?.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </Select>
          <label className="flex h-10 cursor-pointer items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 text-xs font-medium text-slate-600">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-600"
              checked={availableOnly}
              onChange={(event) => {
                setAvailableOnly(event.target.checked)
                setPage(1)
              }}
            />
            Available only
          </label>
          {staff ? (
            <label className="flex h-10 cursor-pointer items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 text-xs font-medium text-slate-600">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-600"
                checked={includeInactive}
                onChange={(event) => {
                  setIncludeInactive(event.target.checked)
                  setPage(1)
                }}
              />
              Include retired
            </label>
          ) : null}
        </div>

        {booksQuery.isLoading ? (
          <LoadingBlock label="Searching the catalogue…" />
        ) : booksQuery.isError ? (
          <ErrorBlock
            message={getErrorMessage(booksQuery.error)}
            onRetry={() => void booksQuery.refetch()}
          />
        ) : books.length === 0 ? (
          <EmptyState
            title="No titles match your search"
            description="Try a different keyword or clear the filters."
            action={
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setSearch("")
                  setCategoryId("")
                  setAvailableOnly(false)
                }}
              >
                Clear filters
              </Button>
            }
          />
        ) : (
          <>
            <Table>
              <thead>
                <tr>
                  <Th>Title</Th>
                  <Th>Category</Th>
                  <Th>ISBN</Th>
                  <Th>Copies</Th>
                  <Th>Shelf</Th>
                  <Th>Status</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              </thead>
              <tbody>
                {books.map((book) => (
                  <tr key={book.id} className="hover:bg-slate-50/60">
                    <Td>
                      <Link
                        to={`/catalogue/${book.id}`}
                        className="font-medium text-slate-800 hover:text-brand-700"
                      >
                        {book.title}
                      </Link>
                      <p className="text-[11px] text-slate-500">
                        {book.authors.length > 0 ? book.authors.join(", ") : "Unknown author"}
                        {book.edition ? ` · ${book.edition} ed.` : ""}
                      </p>
                    </Td>
                    <Td className="text-slate-600">{book.category_name ?? "—"}</Td>
                    <Td className="font-mono text-xs text-slate-500">{book.isbn ?? "—"}</Td>
                    <Td>
                      <span
                        className={cn(
                          "text-sm font-semibold",
                          book.available_copies > 0 ? "text-emerald-600" : "text-rose-600",
                        )}
                      >
                        {book.available_copies}
                      </span>
                      <span className="text-xs text-slate-400"> / {book.total_copies}</span>
                    </Td>
                    <Td className="text-xs text-slate-500">
                      {book.shelf_location ?? "—"}
                      {book.rack_number ? ` · ${book.rack_number}` : ""}
                    </Td>
                    <Td>
                      {book.is_active ? (
                        <Badge tone={book.available_copies > 0 ? "green" : "amber"}>
                          {book.available_copies > 0 ? "Available" : "All on loan"}
                        </Badge>
                      ) : (
                        <Badge tone="slate">Retired</Badge>
                      )}
                    </Td>
                    <Td>
                      <div className="flex items-center justify-end gap-1.5">
                        {!staff && book.available_copies === 0 && book.is_active ? (
                          <Button
                            size="sm"
                            variant="secondary"
                            loading={reserve.isPending && reserve.variables === book.id}
                            onClick={() => reserve.mutate(book.id)}
                          >
                            <BookmarkPlus className="h-3.5 w-3.5" /> Reserve
                          </Button>
                        ) : null}
                        <Link to={`/catalogue/${book.id}`}>
                          <Button size="sm" variant="ghost">
                            View
                          </Button>
                        </Link>
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
        open={modalOpen}
        onClose={() => {
          setModalOpen(false)
          setFormError(null)
          setParams({})
        }}
        title="Add a catalogue title"
        description="Physical copies are added separately after the title is saved."
        size="lg"
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setModalOpen(false)
                setFormError(null)
                setParams({})
              }}
            >
              Cancel
            </Button>
            <Button type="submit" form="book-form" loading={createBook.isPending}>
              Save title
            </Button>
          </>
        }
      >
        <form id="book-form" onSubmit={onSubmit} className="space-y-4">
          {formError ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {formError}
            </p>
          ) : null}
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Title" required className="sm:col-span-2">
              <Input
                value={form.title}
                onChange={(event) => update("title", event.target.value)}
                required
              />
            </Field>
            <Field label="Subtitle" className="sm:col-span-2">
              <Input
                value={form.subtitle}
                onChange={(event) => update("subtitle", event.target.value)}
              />
            </Field>
            <Field label="Authors" hint="Separate multiple authors with commas." className="sm:col-span-2">
              <Input
                value={form.authors}
                onChange={(event) => update("authors", event.target.value)}
                placeholder="Thomas H. Cormen, Charles E. Leiserson"
              />
            </Field>
            <Field label="ISBN">
              <Input
                value={form.isbn}
                onChange={(event) => update("isbn", event.target.value)}
              />
            </Field>
            <Field label="Publisher">
              <Input
                value={form.publisher_name}
                onChange={(event) => update("publisher_name", event.target.value)}
              />
            </Field>
            <Field label="Category">
              <Input
                value={form.category_name}
                onChange={(event) => update("category_name", event.target.value)}
                placeholder="Computer Science"
                list="category-options"
              />
              <datalist id="category-options">
                {categoriesQuery.data?.map((category) => (
                  <option key={category.id} value={category.name} />
                ))}
              </datalist>
            </Field>
            <Field label="Edition">
              <Input
                value={form.edition}
                onChange={(event) => update("edition", event.target.value)}
                placeholder="3rd"
              />
            </Field>
            <Field label="Publication year">
              <Input
                type="number"
                min={1000}
                max={2200}
                value={form.publication_year}
                onChange={(event) => update("publication_year", event.target.value)}
              />
            </Field>
            <Field label="Language">
              <Input
                value={form.language}
                onChange={(event) => update("language", event.target.value)}
              />
            </Field>
            <Field label="Shelf location">
              <Input
                value={form.shelf_location}
                onChange={(event) => update("shelf_location", event.target.value)}
                placeholder="A-01"
              />
            </Field>
            <Field label="Rack number">
              <Input
                value={form.rack_number}
                onChange={(event) => update("rack_number", event.target.value)}
                placeholder="A1.1"
              />
            </Field>
            <Field label="Description" className="sm:col-span-2">
              <Textarea
                value={form.description}
                onChange={(event) => update("description", event.target.value)}
                rows={3}
              />
            </Field>
            <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600 sm:col-span-2">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-600"
                checked={form.is_reference_only}
                onChange={(event) => update("is_reference_only", event.target.checked)}
              />
              Reference only — this title cannot be issued or reserved.
            </label>
          </div>
        </form>
      </Modal>

      <Modal
        open={importOpen}
        onClose={() => {
          setImportOpen(false)
          setImportResult(null)
        }}
        title="Import catalogue from CSV"
        description="Columns: title, authors, isbn, publisher, category, edition, publication_year, language, shelf_location, rack_number, description, is_reference_only."
        footer={
          <>
            <Button variant="secondary" onClick={() => setImportOpen(false)}>
              Close
            </Button>
            <Button
              onClick={() => fileRef.current?.click()}
              loading={importBooks.isPending}
            >
              <Upload className="h-4 w-4" /> Choose file
            </Button>
          </>
        }
      >
        <input
          ref={fileRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={onFileChange}
        />
        {importResult ? (
          <div className="space-y-3 text-sm">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {[
                ["Rows", importResult.total_rows],
                ["Created", importResult.created],
                ["Skipped", importResult.skipped],
                ["Failed", importResult.failed],
              ].map(([label, value]) => (
                <div key={String(label)} className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="text-[11px] font-semibold uppercase text-slate-500">
                    {label}
                  </p>
                  <p className="text-lg font-semibold text-slate-800">{value}</p>
                </div>
              ))}
            </div>
            {importResult.errors.length > 0 ? (
              <ul className="max-h-48 space-y-1 overflow-y-auto rounded-lg border border-rose-100 bg-rose-50 p-3 text-xs text-rose-700">
                {importResult.errors.map((error, index) => (
                  <li key={index}>
                    {error.row_number ? `Row ${error.row_number}: ` : ""}
                    {error.message ?? error.errors?.join(", ")}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-slate-500">
            The import validates each row before writing. Duplicate ISBNs are skipped
            and reported. Download the export to see the expected format.
          </p>
        )}
      </Modal>
    </>
  )
}
