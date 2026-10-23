import { apiClient } from './client'
import type {
  Finding,
  FindingListResponse,
  FindingUpdatePayload,
  ConsistencyGraphResponse,
  ValidationRunResponse,
  RuleListResponse,
} from '../types'

export async function triggerValidation(
  applicationId: string,
): Promise<ValidationRunResponse> {
  const response = await apiClient.post<ValidationRunResponse>(
    `/applications/${applicationId}/validate`,
  )
  return response.data
}

export async function fetchFindings(
  applicationId: string,
  status?: string,
  severity?: string,
): Promise<FindingListResponse> {
  const params: Record<string, string> = {}
  if (status) params.status = status
  if (severity) params.severity = severity

  const response = await apiClient.get<FindingListResponse>(
    `/applications/${applicationId}/findings`,
    { params },
  )
  return response.data
}

export async function fetchConsistencyGraph(
  applicationId: string,
): Promise<ConsistencyGraphResponse> {
  const response = await apiClient.get<ConsistencyGraphResponse>(
    `/applications/${applicationId}/consistency-graph`,
  )
  return response.data
}

export async function updateFindingStatus(
  applicationId: string,
  findingId: string,
  payload: FindingUpdatePayload,
): Promise<Finding> {
  const response = await apiClient.patch<Finding>(
    `/applications/${applicationId}/findings/${findingId}`,
    payload,
  )
  return response.data
}

export async function fetchRules(): Promise<RuleListResponse> {
  const response = await apiClient.get<RuleListResponse>('/rules')
  return response.data
}
