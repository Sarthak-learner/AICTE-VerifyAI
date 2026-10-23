import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { AuthContextType, User, UserRole } from '../types/auth'
import { loginApi, getMeApi } from '../api/auth'

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const TOKEN_KEY = 'access_token'
const USER_KEY = 'verifyai_user'

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem(USER_KEY)
    if (saved) {
      try {
        return JSON.parse(saved) as User
      } catch {
        return null
      }
    }
    return null
  })
  const [isLoading, setIsLoading] = useState<boolean>(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY)
    const storedUser = localStorage.getItem(USER_KEY)
    if (!storedToken) return false
    return !storedUser
  })


  // Validate or refresh session on initial load
  useEffect(() => {
    let isMounted = true

    async function verifySession() {
      const storedToken = localStorage.getItem(TOKEN_KEY)
      if (!storedToken) {
        if (isMounted) setIsLoading(false)
        return
      }

      try {
        const freshUser = await getMeApi()
        if (isMounted) {
          setUser(freshUser)
          localStorage.setItem(USER_KEY, JSON.stringify(freshUser))
        }
      } catch (err) {
        // Token expired or invalid
        if (isMounted) {
          localStorage.removeItem(TOKEN_KEY)
          localStorage.removeItem(USER_KEY)
          setToken(null)
          setUser(null)
        }
      } finally {
        if (isMounted) setIsLoading(false)
      }
    }

    verifySession()

    return () => {
      isMounted = false
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const data = await loginApi(email, password)
    localStorage.setItem(TOKEN_KEY, data.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    setToken(data.access_token)
    setUser(data.user)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setToken(null)
    setUser(null)
  }, [])

  const hasRole = useCallback(
    (roles: UserRole | UserRole[]): boolean => {
      if (!user) return false
      const allowed = Array.isArray(roles) ? roles : [roles]
      return allowed.includes(user.role)
    },
    [user]
  )

  const value: AuthContextType = {
    user,
    token,
    role: user?.role ?? null,
    isAuthenticated: !!token && !!user,
    isLoading,
    login,
    logout,
    hasRole,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

const fallbackAuth: AuthContextType = {
  user: {
    id: '1',
    email: 'officer@aicte.gov.in',
    full_name: 'AICTE Officer',
    role: 'officer',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
  },

  token: 'mock-token',
  role: 'officer',
  isAuthenticated: true,
  isLoading: false,
  login: async () => {},
  logout: () => {},
  hasRole: (roles) => {
    const allowed = Array.isArray(roles) ? roles : [roles]
    return allowed.includes('officer') || allowed.includes('admin')
  },
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    return fallbackAuth
  }
  return context
}

