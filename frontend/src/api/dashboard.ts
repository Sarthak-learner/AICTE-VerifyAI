import { apiClient } from './client'
import type { DashboardStats } from '../types'

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const response = await apiClient.get<DashboardStats>('/dashboard/stats')
  return response.data
}
