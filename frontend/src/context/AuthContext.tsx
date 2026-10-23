import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"

import {
  api,
  hasCsrfCookie,
  refreshAccessToken,
  setAccessToken,
  setAuthFailureHandler,
} from "../lib/api"
import type { TokenResponse, UserProfile } from "../lib/types"

interface AuthContextValue {
  user: UserProfile | null
  loading: boolean
  login: (identifier: string, password: string) => Promise<void>
  logout: (allSessions?: boolean) => Promise<void>
  setUser: (user: UserProfile | null) => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    setAuthFailureHandler(() => {
      if (mounted) setUser(null)
    })

    const bootstrap = async () => {
      if (!hasCsrfCookie()) {
        setLoading(false)
        return
      }
      try {
        await refreshAccessToken()
        const response = await api.get<UserProfile>("/auth/me")
        if (mounted) setUser(response.data)
      } catch {
        setAccessToken(null)
      } finally {
        if (mounted) setLoading(false)
      }
    }

    void bootstrap()
    return () => {
      mounted = false
      setAuthFailureHandler(null)
    }
  }, [])

  const login = useCallback(async (identifier: string, password: string) => {
    const response = await api.post<TokenResponse>("/auth/login", {
      identifier,
      password,
    })
    setAccessToken(response.data.access_token)
    setUser(response.data.user)
  }, [])

  const logout = useCallback(async (allSessions = false) => {
    try {
      await api.post("/auth/logout", { all_sessions: allSessions })
    } catch {
    } finally {
      setAccessToken(null)
      setUser(null)
    }
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({ user, loading, login, logout, setUser }),
    [user, loading, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error("useAuth must be used inside AuthProvider")
  return context
}
