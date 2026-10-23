import { ShieldAlert } from "lucide-react"
import type { ReactNode } from "react"
import { Link, Navigate, Outlet, useLocation } from "react-router-dom"

import { useAuth } from "../context/AuthContext"
import type { Role } from "../lib/types"
import { Spinner } from "./ui"

export function FullPageLoader() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-slate-100 text-slate-500">
      <Spinner className="h-7 w-7 text-brand-700" />
      <p className="text-sm font-medium">Preparing your library…</p>
    </div>
  )
}

export function RequireAuth() {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return <FullPageLoader />
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}

export function PublicOnly({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <FullPageLoader />
  if (user) return <Navigate to="/" replace />
  return <>{children}</>
}

export function RequireRole({
  roles,
  children,
}: {
  roles: Role[]
  children: ReactNode
}) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (!roles.includes(user.role)) {
    return (
      <div className="mx-auto max-w-lg rounded-xl border border-amber-200 bg-amber-50 p-8 text-center">
        <ShieldAlert className="mx-auto h-8 w-8 text-amber-500" />
        <h1 className="mt-3 text-lg font-semibold text-amber-900">Access restricted</h1>
        <p className="mt-1 text-sm text-amber-800">
          You do not have permission to view this page. Contact a librarian or the
          system administrator if you believe this is a mistake.
        </p>
        <Link
          to="/"
          className="mt-4 inline-flex rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700"
        >
          Back to dashboard
        </Link>
      </div>
    )
  }
  return <>{children}</>
}
