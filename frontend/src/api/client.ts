/**
 * Axios base client.
 * All API calls go through this instance so base URL and headers
 * can be configured from a single place.
 */
import axios from 'axios'

export const apiClient = axios.create({
  baseURL: (import.meta.env.VITE_API_BASE_URL as string) || '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

// Attach auth token when present (token-based auth will be added later)
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
