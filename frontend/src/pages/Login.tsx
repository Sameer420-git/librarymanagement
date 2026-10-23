import { AlertCircle, BookOpen, Lock, Mail } from "lucide-react"
import { useState, type FormEvent } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"

import { Button, Field, Input } from "../components/ui"
import { useAuth } from "../context/AuthContext"
import { getErrorMessage } from "../lib/api"

const CURRENT_YEAR = new Date().getFullYear()

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [identifier, setIdentifier] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const from = (location.state as { from?: string } | null)?.from ?? "/"

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(identifier.trim(), password)
      navigate(from, { replace: true })
    } catch (caught) {
      setError(getErrorMessage(caught))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-slate-950">
      <div className="relative hidden w-1/2 overflow-hidden lg:block">
        <div className="absolute inset-0 bg-gradient-to-br from-brand-800 via-brand-900 to-slate-950" />
        <div className="absolute -left-24 top-1/3 h-96 w-96 rounded-full bg-brand-500/20 blur-3xl" />
        <div className="absolute -right-16 bottom-0 h-80 w-80 rounded-full bg-teal-400/10 blur-3xl" />
        <div className="relative flex h-full flex-col justify-between p-12">
          <div className="flex items-center gap-3">
            <img src="/library.svg" alt="" className="h-11 w-11" />
            <div>
              <p className="text-sm font-semibold text-white">College Library</p>
              <p className="text-xs text-brand-200/80">Management System</p>
            </div>
          </div>

          <div className="max-w-md">
            <h1 className="text-3xl font-semibold leading-tight text-white">
              Every title, every copy, every borrower — in one place.
            </h1>
            <p className="mt-4 text-sm leading-relaxed text-brand-100/80">
              Search the catalogue, manage circulation, track reservations and fines,
              and keep members informed with reliable e-mail reminders.
            </p>
            <div className="mt-8 grid gap-3 text-sm text-brand-50/90">
              <div className="flex items-center gap-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/10">
                  <BookOpen className="h-4 w-4" />
                </span>
                Catalogue and copy-level inventory
              </div>
              <div className="flex items-center gap-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/10">
                  <Lock className="h-4 w-4" />
                </span>
                Role-based access for staff and members
              </div>
              <div className="flex items-center gap-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/10">
                  <Mail className="h-4 w-4" />
                </span>
                Durable reminders with delivery tracking
              </div>
            </div>
          </div>

          <p className="text-xs text-brand-200/60">
            © {CURRENT_YEAR} College Library. All rights reserved.
          </p>
        </div>
      </div>

      <div className="flex w-full items-center justify-center bg-slate-100 px-6 py-12 lg:w-1/2">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <img src="/library.svg" alt="" className="h-10 w-10" />
            <div>
              <p className="text-sm font-semibold text-slate-900">College Library</p>
              <p className="text-xs text-slate-500">Management System</p>
            </div>
          </div>

          <h2 className="text-2xl font-semibold tracking-tight text-slate-900">
            Welcome back
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Sign in with your e-mail address or institutional ID.
          </p>

          <form onSubmit={onSubmit} className="mt-7 space-y-4">
            {error ? (
              <div className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-sm text-rose-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            ) : null}

            <Field label="E-mail or institutional ID" htmlFor="identifier" required>
              <Input
                id="identifier"
                autoComplete="username"
                autoFocus
                value={identifier}
                onChange={(event) => setIdentifier(event.target.value)}
                placeholder="you@college.edu"
                required
              />
            </Field>

            <Field label="Password" htmlFor="password" required>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••"
                required
              />
            </Field>

            <div className="flex items-center justify-between">
              <Link
                to="/forgot-password"
                className="text-xs font-medium text-brand-700 hover:text-brand-800"
              >
                Forgot your password?
              </Link>
            </div>

            <Button type="submit" className="w-full" loading={submitting}>
              Sign in
            </Button>
          </form>

          <p className="mt-6 text-center text-xs text-slate-400">
            Accounts are created by the library staff.
          </p>
        </div>
      </div>
    </div>
  )
}
