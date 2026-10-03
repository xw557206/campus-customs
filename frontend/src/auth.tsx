import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import {
  fetchMe,
  login as apiLogin,
  register as apiRegister,
  type RegisterInput,
  type User,
} from './api'

const TOKEN_KEY = 'cc.token'

interface AuthState {
  user: User | null
  /** The raw session token, needed for authenticated calls such as chat history. */
  token: string | null
  loading: boolean
  logIn: (email: string, password: string) => Promise<void>
  signUp: (input: RegisterInput) => Promise<void>
  logOut: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [loading, setLoading] = useState(true)

  // On load, ask the backend who the stored token belongs to. The token is
  // signed server-side, so a tampered one simply fails this check.
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      setLoading(false)
      return
    }
    let cancelled = false
    fetchMe(token)
      .then((u) => !cancelled && setUser(u))
      .catch(() => {
        if (cancelled) return
        localStorage.removeItem(TOKEN_KEY)
        setUser(null)
        setToken(null)
      })
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  const value = useMemo<AuthState>(
    () => ({
      user,
      token,
      loading,
      async logIn(email, password) {
        const res = await apiLogin(email, password)
        localStorage.setItem(TOKEN_KEY, res.token)
        setToken(res.token)
        setUser(res.user)
      },
      async signUp(input) {
        const res = await apiRegister(input)
        localStorage.setItem(TOKEN_KEY, res.token)
        setToken(res.token)
        setUser(res.user)
      },
      logOut() {
        localStorage.removeItem(TOKEN_KEY)
        setToken(null)
        setUser(null)
      },
    }),
    [user, token, loading],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
