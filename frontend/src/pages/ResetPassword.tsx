import { CheckCircle2 } from "lucide-react"
import { useState, type FormEvent } from "react"
import { Link, useSearchParams } from "react-router-dom"

import { Button, Field, Input } from "../components/ui"
import { api, getErrorMessage } from "../lib/api"

export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const token = params.get("token") ?? ""
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    if (password !== confirm) {
      setError("The passwords do not match.")
      return
    }
    setSubmitting(true)
    try {
      const response = await api.post<{ message: string }>("/auth/reset-password", {
        token,
        new_password: password,
      })
      setMessage(response.data.message)
    } catch (caught) {
      setError(getErrorMessage(caught))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 px-6 py-12">
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
        <h1 className="text-xl font-semibold text-slate-900">Choose a new password</h1>
        <p className="mt-1 text-sm text-slate-500">
          Passwords must be at least 8 characters long.
        </p>

        {!token ? (
          <p className="mt-5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            This reset link is missing its token. Request a new link from the{" "}
            <Link to="/forgot-password" className="font-semibold underline">
              forgot password
            </Link>{" "}
            page.
          </p>
        ) : message ? (
          <div className="mt-5 space-y-5">
            <div className="flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm text-emerald-800">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{message}</span>
            </div>
            <Link
              to="/login"
              className="inline-flex w-full items-center justify-center rounded-lg bg-brand-700 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-800"
            >
              Go to sign in
            </Link>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="mt-5 space-y-4">
            {error ? (
              <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {error}
              </p>
            ) : null}
            <Field label="New password" htmlFor="password" required>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                minLength={8}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </Field>
            <Field label="Confirm password" htmlFor="confirm" required>
              <Input
                id="confirm"
                type="password"
                autoComplete="new-password"
                minLength={8}
                value={confirm}
                onChange={(event) => setConfirm(event.target.value)}
                required
              />
            </Field>
            <Button type="submit" className="w-full" loading={submitting}>
              Reset password
            </Button>
          </form>
        )}
      </div>
    </div>
  )
}
