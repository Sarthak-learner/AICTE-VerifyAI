import { apiClient } from './client'
import type {
  Application,
  ApplicationCreatePayload,
  ApplicationListResponse,
  DocumentListResponse,
  AuditTrailResponse,
} from '../types'

export async function fetchApplications(skip = 0, limit = 50): Promise<ApplicationListResponse> {
  const response = await apiClient.get<ApplicationListResponse>('/applications', {
    params: { skip, limit },
  })
  return response.data
}

export async function fetchApplication(id: string): Promise<Application> {
  const response = await apiClient.get<Application>(`/applications/${id}`)
  return response.data
}

export async function createApplication(payload: ApplicationCreatePayload): Promise<Application> {
  const response = await apiClient.post<Application>('/applications', payload)
  return response.data
}

export async function fetchApplicationDocuments(applicationId: string): Promise<DocumentListResponse> {
  const response = await apiClient.get<DocumentListResponse>(`/applications/${applicationId}/documents`)
  return response.data
}

export async function fetchApplicationAuditTrail(applicationId: string): Promise<AuditTrailResponse> {
  const response = await apiClient.get<AuditTrailResponse>(`/applications/${applicationId}/audit-trail`)
  return response.data
}

