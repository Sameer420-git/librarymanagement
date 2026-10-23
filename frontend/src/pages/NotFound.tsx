import { BookX } from "lucide-react"
import { Link } from "react-router-dom"

export function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <BookX className="h-12 w-12 text-slate-300" />
      <h1 className="mt-4 text-2xl font-semibold text-slate-900">Page not found</h1>
      <p className="mt-1 max-w-md text-sm text-slate-500">
        The page you were looking for has been moved, retired, or never existed.
      </p>
      <Link
        to="/"
        className="mt-5 rounded-lg bg-brand-700 px-4 py-2 text-sm font-medium text-white hover:bg-brand-800"
      >
        Back to dashboard
      </Link>
    </div>
  )
}
