import { apiClient } from './client'
import type { ExtractionResult, ProcessingStatusResponse } from '../types'

export async function triggerProcessing(
  applicationId: string,
  documentId: string,
): Promise<ProcessingStatusResponse> {
  const response = await apiClient.post<ProcessingStatusResponse>(
    `/applications/${applicationId}/documents/${documentId}/process`,
  )
  return response.data
}

export async function fetchExtraction(
  applicationId: string,
  documentId: string,
): Promise<ExtractionResult> {
  const response = await apiClient.get<ExtractionResult>(
    `/applications/${applicationId}/documents/${documentId}/extraction`,
  )
  return response.data
}
