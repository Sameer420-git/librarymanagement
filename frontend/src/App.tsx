import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"

import { Layout } from "./components/Layout"
import { PublicOnly, RequireAuth, RequireRole } from "./components/guards"
import { AuthProvider } from "./context/AuthContext"
import { AuditPage } from "./pages/Audit"
import { BookDetailPage } from "./pages/BookDetail"
import { CataloguePage } from "./pages/Catalogue"
import { CirculationPage } from "./pages/Circulation"
import { DashboardPage } from "./pages/Dashboard"
import { FinesPage } from "./pages/Fines"
import { ForgotPasswordPage } from "./pages/ForgotPassword"
import { LoginPage } from "./pages/Login"
import { MemberDetailPage } from "./pages/MemberDetail"
import { MembersPage } from "./pages/Members"
import { NotFoundPage } from "./pages/NotFound"
import { NotificationsPage } from "./pages/Notifications"
import { ProfilePage } from "./pages/Profile"
import { ReportsPage } from "./pages/Reports"
import { ReservationsPage } from "./pages/Reservations"
import { ResetPasswordPage } from "./pages/ResetPassword"
import { SettingsPage } from "./pages/Settings"
import { UsersPage } from "./pages/Users"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 15_000,
    },
  },
})

const staff = ["SUPER_ADMIN", "LIBRARIAN"] as const
const admins = ["SUPER_ADMIN"] as const

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route
              path="/login"
              element={
                <PublicOnly>
                  <LoginPage />
                </PublicOnly>
              }
            />
            <Route
              path="/forgot-password"
              element={
                <PublicOnly>
                  <ForgotPasswordPage />
                </PublicOnly>
              }
            />
            <Route
              path="/reset-password"
              element={
                <PublicOnly>
                  <ResetPasswordPage />
                </PublicOnly>
              }
            />

            <Route element={<RequireAuth />}>
              <Route element={<Layout />}>
                <Route index element={<DashboardPage />} />
                <Route path="catalogue" element={<CataloguePage />} />
                <Route path="catalogue/:id" element={<BookDetailPage />} />

                <Route
                  path="members"
                  element={
                    <RequireRole roles={[...staff]}>
                      <MembersPage />
                    </RequireRole>
                  }
                />
                <Route path="members/:id" element={<MemberDetailPage />} />

                <Route path="circulation" element={<CirculationPage />} />
                <Route path="reservations" element={<ReservationsPage />} />
                <Route path="fines" element={<FinesPage />} />
                <Route
                  path="reports"
                  element={
                    <RequireRole roles={[...staff]}>
                      <ReportsPage />
                    </RequireRole>
                  }
                />
                <Route path="notifications" element={<NotificationsPage />} />
                <Route path="profile" element={<ProfilePage />} />

                <Route
                  path="users"
                  element={
                    <RequireRole roles={[...admins]}>
                      <UsersPage />
                    </RequireRole>
                  }
                />
                <Route
                  path="settings"
                  element={
                    <RequireRole roles={[...admins]}>
                      <SettingsPage />
                    </RequireRole>
                  }
                />
                <Route
                  path="audit"
                  element={
                    <RequireRole roles={[...admins]}>
                      <AuditPage />
                    </RequireRole>
                  }
                />

                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
