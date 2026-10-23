import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios"

import type { TokenResponse } from "./types"

const API_BASE = import.meta.env.VITE_API_URL ?? "/api"

let accessToken: string | null = null
let refreshPromise: Promise<string> | null = null
let authFailureHandler: (() => void) | null = null

export class ApiError extends Error {
  status: number
  code: string
  details: unknown

  constructor(message: string, status: number, code = "error", details?: unknown) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.code = code
    this.details = details
  }
}

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

export function setAuthFailureHandler(handler: (() => void) | null): void {
  authFailureHandler = handler
}

function readCookie(name: string): string | null {
  const prefix = `${name}=`
  const match = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix))
  return match ? decodeURIComponent(match.slice(prefix.length)) : null
}

function csrfHeader(): Record<string, string> {
  const token = readCookie("library_csrf_token")
  return token ? { "X-CSRF-Token": token } : {}
}

export function hasCsrfCookie(): boolean {
  return readCookie("library_csrf_token") !== null
}

export const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  timeout: 30_000,
})

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  const url = config.url ?? ""
  if (url.startsWith("/auth/") && config.method !== "get") {
    Object.assign(config.headers, csrfHeader())
  }
  return config
})

type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean }

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetryConfig | undefined
    const status = error.response?.status ?? 0
    const url = config?.url ?? ""
    const isAuthCall =
      url.includes("/auth/login") ||
      url.includes("/auth/refresh") ||
      url.includes("/auth/logout")

    if (status === 401 && config && !config._retry && !isAuthCall) {
      config._retry = true
      try {
        const token = await refreshAccessToken()
        config.headers.Authorization = `Bearer ${token}`
        return api(config)
      } catch {
        accessToken = null
        authFailureHandler?.()
      }
    }

    throw toApiError(error)
  },
)

function toApiError(error: AxiosError): ApiError {
  if (error.response) {
    const body = error.response.data as
      | { error?: { code?: string; message?: string; details?: unknown } }
      | undefined
    const message =
      body?.error?.message ||
      (typeof error.response.data === "string" && error.response.data) ||
      `Request failed with status ${error.response.status}.`
    return new ApiError(
      message,
      error.response.status,
      body?.error?.code ?? "request_failed",
      body?.error?.details,
    )
  }
  if (error.code === "ECONNABORTED") {
    return new ApiError("The request timed out. Please try again.", 0, "timeout")
  }
  return new ApiError(
    "Cannot reach the server. Check your connection and try again.",
    0,
    "network_error",
  )
}

export async function refreshAccessToken(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const response = await axios.post<TokenResponse>(
        `${API_BASE}/auth/refresh`,
        null,
        { withCredentials: true, headers: csrfHeader(), timeout: 15_000 },
      )
      accessToken = response.data.access_token
      return accessToken
    })().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return "Something went wrong."
}

export function fieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError)) return {}
  const details = error.details as
    | { errors?: { field?: string; message?: string }[]; fields?: Record<string, string> }
    | undefined
  const result: Record<string, string> = {}
  for (const item of details?.errors ?? []) {
    if (item.field) result[item.field] = item.message ?? "Invalid value."
  }
  for (const [field, message] of Object.entries(details?.fields ?? {})) {
    result[field] = message
  }
  return result
}

function filenameFromHeader(header: unknown, fallback: string): string {
  if (typeof header !== "string") return fallback
  const match = /filename\*?=(?:UTF-8''|")?([^";]+)"?/i.exec(header)
  return match ? decodeURIComponent(match[1]) : fallback
}

export async function downloadFile(
  path: string,
  fallbackName: string,
  params?: Record<string, unknown>,
): Promise<void> {
  const response = await api.get(path, { params, responseType: "blob" })
  const blob = response.data as Blob
  const name = filenameFromHeader(
    response.headers["content-disposition"],
    fallbackName,
  )
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = name
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
