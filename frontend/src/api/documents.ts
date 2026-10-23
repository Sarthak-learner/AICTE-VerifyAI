import { apiClient } from './client'
import type { Document, UploadResponse } from '../types'

export async function uploadDocument(
  applicationId: string,
  file: File,
  documentType?: string,
): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  if (documentType) {
    formData.append('document_type', documentType)
  }

  const response = await apiClient.post<UploadResponse>(
    `/applications/${applicationId}/documents`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    },
  )
  return response.data
}

export async function fetchDocument(
  applicationId: string,
  documentId: string,
): Promise<Document> {
  const response = await apiClient.get<Document>(
    `/applications/${applicationId}/documents/${documentId}`,
  )
  return response.data
}
