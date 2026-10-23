import type { Role } from "./types"

export function isStaff(role: Role | undefined | null): boolean {
  return role === "LIBRARIAN" || role === "SUPER_ADMIN"
}

export function isAdmin(role: Role | undefined | null): boolean {
  return role === "SUPER_ADMIN"
}

export function isMember(role: Role | undefined | null): boolean {
  return role === "STUDENT" || role === "FACULTY"
}

export function roleLabel(role: Role): string {
  switch (role) {
    case "SUPER_ADMIN":
      return "Super administrator"
    case "LIBRARIAN":
      return "Librarian"
    case "FACULTY":
      return "Faculty"
    case "STUDENT":
      return "Student"
  }
}
