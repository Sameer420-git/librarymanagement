import { useMutation, useQuery } from "@tanstack/react-query"
import { BadgeCheck, KeyRound, LogOut, MailWarning } from "lucide-react"
import { useEffect, useState, type FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"

import {
  Badge,
  Button,
  Card,
  ErrorBlock,
  Field,
  Input,
  LoadingBlock,
  PageHeader,
  StatusBadge,
} from "../components/ui"
import { useAuth } from "../context/AuthContext"
import { api, getErrorMessage } from "../lib/api"
import { formatDate, formatDateTime, humanize } from "../lib/format"
import { isStaff } from "../lib/permissions"
import type { UserProfile } from "../lib/types"

export function ProfilePage() {
  const { user, setUser, logout } = useAuth()
  const navigate = useNavigate()
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: async () => (await api.get<UserProfile>("/auth/me")).data,
  })

  useEffect(() => {
    if (meQuery.data) setUser(meQuery.data)
  }, [meQuery.data, setUser])

  const changePassword = useMutation({
    mutationFn: async (payload: { current_password: string; new_password: string }) =>
      (await api.post<{ message: string }>("/auth/change-password", payload)).data,
    onSuccess: (result) => {
      setNotice(result.message)
      setError(null)
    },
    onError: (mutationError) => setError(getErrorMessage(mutationError)),
  })

  const resendVerification = useMutation({
    mutationFn: async () =>
      (await api.post<{ message: string }>("/auth/resend-verification")).data,
    onSuccess: (result) => setNotice(result.message),
    onError: (mutationError) => setError(getErrorMessage(mutationError)),
  })

  if (!user) return <LoadingBlock />
  if (meQuery.isError) {
    return (
      <ErrorBlock
        message={getErrorMessage(meQuery.error)}
        onRetry={() => void meQuery.refetch()}
      />
    )
  }

  const initials = `${user.first_name[0] ?? ""}${user.last_name[0] ?? ""}`.toUpperCase()

  return (
    <>
      <PageHeader
        title="My profile"
        description="Account details, security and membership information."
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
        <Card className="lg:col-span-1">
          <div className="flex flex-col items-center text-center">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-brand-100 text-2xl font-semibold text-brand-700">
              {initials}
            </div>
            <p className="mt-3 text-lg font-semibold text-slate-900">{user.full_name}</p>
            <p className="text-xs text-slate-500">{user.email}</p>
            <div className="mt-2 flex flex-wrap justify-center gap-1.5">
              <Badge tone="purple">{humanize(user.role)}</Badge>
              <StatusBadge status={user.status} />
              {user.is_email_verified ? (
                <Badge tone="green">
                  <BadgeCheck className="h-3 w-3" /> Verified
                </Badge>
              ) : (
                <Badge tone="amber">Unverified</Badge>
              )}
            </div>
          </div>

          <dl className="mt-6 space-y-2.5 text-sm">
            <Row label="Institutional ID" value={user.institutional_id} mono />
            <Row label="Membership" value={humanize(user.membership_type)} />
            <Row label="Phone" value={user.phone} />
            {user.role === "STUDENT" ? (
              <>
                <Row label="Enrollment" value={user.enrollment_number} mono />
                <Row label="Course" value={user.course_name} />
                <Row
                  label="Semester"
                  value={
                    user.semester
                      ? `${user.semester}${user.section ? ` · ${user.section}` : ""}`
                      : null
                  }
                />
              </>
            ) : (
              <>
                <Row label="Employee ID" value={user.employee_id} mono />
                <Row label="Department" value={user.department_name} />
                <Row label="Designation" value={user.designation} />
              </>
            )}
            <Row label="Member since" value={formatDate(user.membership_start)} />
            <Row
              label="Valid until"
              value={user.membership_expires ? formatDate(user.membership_expires) : "No expiry"}
            />
            <Row label="Last login" value={formatDateTime(user.last_login_at)} />
          </dl>

          {isStaff(user.role) ? (
            <Link to={`/members/${user.id}`} className="mt-4 block">
              <Button variant="secondary" className="w-full">
                Open member record
              </Button>
            </Link>
          ) : null}
        </Card>

        <div className="space-y-4 lg:col-span-2">
          {!user.is_email_verified ? (
            <Card title="Verify your e-mail">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-start gap-3">
                  <MailWarning className="mt-0.5 h-5 w-5 text-amber-500" />
                  <div>
                    <p className="text-sm text-slate-700">
                      Your e-mail address is not verified. Some notifications may be limited.
                    </p>
                    <p className="text-xs text-slate-500">{user.email}</p>
                  </div>
                </div>
                <Button
                  variant="secondary"
                  loading={resendVerification.isPending}
                  onClick={() => resendVerification.mutate()}
                >
                  Resend verification link
                </Button>
              </div>
            </Card>
          ) : null}

          <Card
            title="Change password"
            description="Use at least 8 characters with three of: lowercase, uppercase, digit, symbol."
          >
            {error ? (
              <p className="mb-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {error}
              </p>
            ) : null}
            <form
              className="grid gap-4 sm:grid-cols-2"
              onSubmit={(event: FormEvent<HTMLFormElement>) => {
                event.preventDefault()
                setError(null)
                const data = new FormData(event.currentTarget)
                const newPassword = String(data.get("new_password") ?? "")
                if (newPassword !== data.get("confirm_password")) {
                  setError("The new passwords do not match.")
                  return
                }
                changePassword.mutate({
                  current_password: String(data.get("current_password") ?? ""),
                  new_password: newPassword,
                })
                event.currentTarget.reset()
              }}
            >
              <Field label="Current password" required className="sm:col-span-2">
                <Input
                  name="current_password"
                  type="password"
                  autoComplete="current-password"
                  required
                />
              </Field>
              <Field label="New password" required>
                <Input
                  name="new_password"
                  type="password"
                  minLength={8}
                  autoComplete="new-password"
                  required
                />
              </Field>
              <Field label="Confirm new password" required>
                <Input
                  name="confirm_password"
                  type="password"
                  minLength={8}
                  autoComplete="new-password"
                  required
                />
              </Field>
              <div className="sm:col-span-2">
                <Button type="submit" loading={changePassword.isPending}>
                  <KeyRound className="h-4 w-4" /> Update password
                </Button>
              </div>
            </form>
          </Card>

          <Card title="Sessions" description="Signing out revokes the refresh cookie on this device.">
            <div className="flex flex-wrap items-center gap-3">
              <Button
                variant="secondary"
                onClick={async () => {
                  await logout(false)
                  navigate("/login", { replace: true })
                }}
              >
                <LogOut className="h-4 w-4" /> Sign out
              </Button>
              <Button
                variant="danger"
                onClick={async () => {
                  await logout(true)
                  navigate("/login", { replace: true })
                }}
              >
                Sign out everywhere
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </>
  )
}

function Row({
  label,
  value,
  mono,
}: {
  label: string
  value: string | null | undefined
  mono?: boolean
}) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="text-xs text-slate-400">{label}</dt>
      <dd className={`text-right text-xs text-slate-700 ${mono ? "font-mono" : ""}`}>
        {value || "—"}
      </dd>
    </div>
  )
}
