import { apiClient } from './client'

export interface HealthResponse {
  status: string
  version: string
  environment: string
  database: string
  disclaimer: string
}

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await apiClient.get<HealthResponse>('/health')
  return data
}
