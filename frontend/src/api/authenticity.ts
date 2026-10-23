import { apiClient } from './client'
import type {
  AuthenticityCheck,
  AuthenticityCheckUpdatePayload,
  AuthenticityScreeningResponse,
} from '../types'

export async function runAuthenticityScreening(
  applicationId: string,
): Promise<AuthenticityScreeningResponse> {
  const response = await apiClient.post<AuthenticityScreeningResponse>(
    `/applications/${applicationId}/authenticity-screen`,
  )
  return response.data
}

export async function fetchAuthenticityChecks(
  applicationId: string,
  params?: {
    document_id?: string
    result?: string
    status?: string
  },
): Promise<AuthenticityScreeningResponse> {
  const queryParams: Record<string, string> = {}
  if (params?.document_id) queryParams.document_id = params.document_id
  if (params?.result) queryParams.result = params.result
  if (params?.status) queryParams.status = params.status

  const response = await apiClient.get<AuthenticityScreeningResponse>(
    `/applications/${applicationId}/authenticity-checks`,
    { params: queryParams },
  )
  return response.data
}

export async function updateAuthenticityCheckStatus(
  applicationId: string,
  checkId: string,
  payload: AuthenticityCheckUpdatePayload,
): Promise<AuthenticityCheck> {
  const response = await apiClient.patch<AuthenticityCheck>(
    `/applications/${applicationId}/authenticity-checks/${checkId}`,
    payload,
  )
  return response.data
}
