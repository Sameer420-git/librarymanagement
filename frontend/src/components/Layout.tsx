import {
  ArrowLeftRight,
  BarChart3,
  Bookmark,
  ChevronDown,
  LayoutDashboard,
  LibraryBig,
  LogOut,
  Mail,
  Menu,
  ScrollText,
  Settings,
  ShieldCheck,
  UserCircle2,
  Users,
  Wallet,
  X,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom"

import { useAuth } from "../context/AuthContext"
import { initials } from "../lib/format"
import { isAdmin, isStaff, roleLabel } from "../lib/permissions"
import type { Role } from "../lib/types"
import { cn } from "./ui"

const CURRENT_YEAR = new Date().getFullYear()

interface NavItem {
  to: string
  label: string
  icon: typeof LayoutDashboard
  roles?: Role[]
}

interface NavSection {
  title: string
  items: NavItem[]
}

const adminRoles: Role[] = ["SUPER_ADMIN"]

function sectionsFor(role: Role): NavSection[] {
  if (isStaff(role)) {
    return [
      {
        title: "Overview",
        items: [{ to: "/", label: "Dashboard", icon: LayoutDashboard }],
      },
      {
        title: "Operations",
        items: [
          { to: "/catalogue", label: "Catalogue", icon: LibraryBig },
          { to: "/circulation", label: "Circulation", icon: ArrowLeftRight },
          { to: "/reservations", label: "Reservations", icon: Bookmark },
          { to: "/fines", label: "Fines", icon: Wallet },
        ],
      },
      {
        title: "People",
        items: [
          { to: "/members", label: "Members", icon: Users },
          { to: "/users", label: "User accounts", icon: ShieldCheck, roles: adminRoles },
        ],
      },
      {
        title: "Insights",
        items: [
          { to: "/reports", label: "Reports", icon: BarChart3 },
          { to: "/notifications", label: "Notifications", icon: Mail },
        ],
      },
      {
        title: "Administration",
        items: [
          { to: "/settings", label: "Library settings", icon: Settings, roles: adminRoles },
          { to: "/audit", label: "Audit log", icon: ScrollText, roles: adminRoles },
        ],
      },
    ]
  }
  return [
    {
      title: "Overview",
      items: [{ to: "/", label: "Dashboard", icon: LayoutDashboard }],
    },
    {
      title: "Library",
      items: [
        { to: "/catalogue", label: "Catalogue", icon: LibraryBig },
        { to: "/circulation", label: "My loans", icon: ArrowLeftRight },
        { to: "/reservations", label: "My reservations", icon: Bookmark },
        { to: "/fines", label: "My fines", icon: Wallet },
        { to: "/notifications", label: "Notifications", icon: Mail },
      ],
    },
    {
      title: "Account",
      items: [{ to: "/profile", label: "My profile", icon: UserCircle2 }],
    },
  ]
}

export function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  const role = user?.role ?? "STUDENT"
  const sections = sectionsFor(role).filter(
    (section) => section.items.some((item) => !item.roles || item.roles.includes(role)),
  )

  const flatItems = sections.flatMap((section) => section.items)
  const activeItem = [...flatItems]
    .sort((a, b) => b.to.length - a.to.length)
    .find(
      (item) =>
        item.to === location.pathname ||
        (item.to !== "/" && location.pathname.startsWith(item.to)),
    )

  useEffect(() => {
    setSidebarOpen(false)
    setMenuOpen(false)
  }, [location.pathname])

  useEffect(() => {
    if (!menuOpen) return
    const onClick = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener("mousedown", onClick)
    return () => document.removeEventListener("mousedown", onClick)
  }, [menuOpen])

  const handleSignOut = async () => {
    await logout()
    navigate("/login", { replace: true })
  }

  return (
    <div className="min-h-screen bg-slate-100">
      {sidebarOpen ? (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-30 bg-slate-950/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      ) : null}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-slate-950 text-slate-300 transition-transform duration-200 lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center gap-2.5 px-5 py-5">
          <img src="/library.svg" alt="" className="h-9 w-9" />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-white">College Library</p>
            <p className="text-[11px] text-slate-400">Management System</p>
          </div>
          <button
            type="button"
            className="ml-auto rounded-md p-1 text-slate-400 hover:bg-white/10 hover:text-white lg:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close navigation"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex-1 space-y-5 overflow-y-auto px-3 pb-4">
          {sections.map((section) => (
            <div key={section.title}>
              <p className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                {section.title}
              </p>
              <div className="space-y-0.5">
                {section.items
                  .filter((item) => !item.roles || item.roles.includes(role))
                  .map((item) => {
                    const Icon = item.icon
                    return (
                      <NavLink
                        key={item.to}
                        to={item.to}
                        end={item.to === "/"}
                        className={({ isActive }) =>
                          cn(
                            "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition",
                            isActive
                              ? "bg-brand-600/15 text-brand-200"
                              : "text-slate-400 hover:bg-white/5 hover:text-slate-100",
                          )
                        }
                      >
                        <Icon className="h-4 w-4 shrink-0" />
                        <span className="truncate">{item.label}</span>
                      </NavLink>
                    )
                  })}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t border-white/10 p-3">
          <div className="flex items-center gap-2.5 rounded-lg px-2 py-2">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">
              {initials(user?.full_name || user?.email || "?")}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold text-white">
                {user?.full_name || user?.email}
              </p>
              <p className="truncate text-[11px] text-slate-400">
                {roleLabel(role)}
              </p>
            </div>
            <button
              type="button"
              onClick={handleSignOut}
              className="rounded-md p-1.5 text-slate-400 transition hover:bg-white/10 hover:text-white"
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      <div className="flex min-h-screen flex-col lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur sm:px-6">
          <button
            type="button"
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open navigation"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900">
              {activeItem?.label ?? "Dashboard"}
            </p>
            <p className="hidden text-[11px] text-slate-500 sm:block">
              {new Intl.DateTimeFormat("en-GB", {
                weekday: "long",
                day: "2-digit",
                month: "long",
                year: "numeric",
              }).format(new Date())}
            </p>
          </div>

          <div className="ml-auto flex items-center gap-2">
            {isAdmin(role) ? (
              <span className="hidden rounded-full bg-violet-50 px-2.5 py-1 text-[11px] font-semibold text-violet-700 ring-1 ring-violet-600/20 sm:inline-flex">
                Administrator
              </span>
            ) : isStaff(role) ? (
              <span className="hidden rounded-full bg-brand-50 px-2.5 py-1 text-[11px] font-semibold text-brand-700 ring-1 ring-brand-600/20 sm:inline-flex">
                Librarian
              </span>
            ) : null}

            <div className="relative" ref={menuRef}>
              <button
                type="button"
                onClick={() => setMenuOpen((open) => !open)}
                className="flex items-center gap-2 rounded-full border border-slate-200 bg-white py-1 pl-1 pr-2 text-sm transition hover:bg-slate-50"
              >
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-700 text-[11px] font-bold text-white">
                  {initials(user?.full_name || user?.email || "?")}
                </span>
                <span className="hidden max-w-32 truncate text-xs font-medium text-slate-700 sm:block">
                  {user?.first_name}
                </span>
                <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
              </button>

              {menuOpen ? (
                <div className="absolute right-0 mt-2 w-52 overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-lg">
                  <div className="border-b border-slate-100 px-3 py-2">
                    <p className="truncate text-xs font-semibold text-slate-800">
                      {user?.full_name}
                    </p>
                    <p className="truncate text-[11px] text-slate-500">{user?.email}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => navigate("/profile")}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-medium text-slate-600 hover:bg-slate-50"
                  >
                    <UserCircle2 className="h-4 w-4" /> My profile
                  </button>
                  <button
                    type="button"
                    onClick={handleSignOut}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-medium text-rose-600 hover:bg-rose-50"
                  >
                    <LogOut className="h-4 w-4" /> Sign out
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </header>

        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto w-full max-w-7xl space-y-6">
            <Outlet />
          </div>
        </main>

        <footer className="border-t border-slate-200 px-6 py-4 text-center text-[11px] text-slate-400">
          College Library Management System · {CURRENT_YEAR}
        </footer>
      </div>
    </div>
  )
}
