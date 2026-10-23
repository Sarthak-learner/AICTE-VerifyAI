/**
 * Authentication API calls.
 */
import { apiClient } from './client'
import { LoginResponse, User } from '../types/auth'

export async function loginApi(email: string, password: string): Promise<LoginResponse> {
  const resp = await apiClient.post<LoginResponse>('/auth/login', { email, password })
  return resp.data
}

export async function getMeApi(): Promise<User> {
  const resp = await apiClient.get<User>('/auth/me')
  return resp.data
}

export async function seedDemoUsersApi(): Promise<void> {
  await apiClient.post('/auth/seed')
}
