/**
 * TypeScript types for User authentication and roles.
 */

export type UserRole = 'admin' | 'officer' | 'viewer'

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at?: string
  updated_at?: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface AuthContextType {
  user: User | null
  token: string | null
  role: UserRole | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  hasRole: (roles: UserRole | UserRole[]) => boolean
}
