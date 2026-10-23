import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchExtraction, triggerProcessing } from '../../api/processing'
import type { ExtractedField, DocumentStatus } from '../../types'

interface DocumentExtractionCardProps {
  applicationId: string
  documentId: string
  originalFilename: string
  initialStatus: DocumentStatus
  onStatusChange?: () => void
}

const FIELD_LABELS: Record<string, string> = {
  institution_name: 'Institution Name',
  reference_number: 'Reference / Order No.',
  issue_date: 'Issue Date',
  expiry_date: 'Expiry / Validity Date',
  land_area: 'Land / Built-up Area',
  programme_name: 'Programme / Course',
  intake_figure: 'Approved / Proposed Intake',
}

function ConfidenceBadge({ confidence }: { confidence: string }) {
  if (confidence === 'high') {
    return (
      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800">
        HIGH CONFIDENCE
      </span>
    )
  }
  if (confidence === 'low') {
    return (
      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800">
        LOW CONFIDENCE
      </span>
    )
  }
  return (
    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-500">
      UNKNOWN
    </span>
  )
}

export default function DocumentExtractionCard({
  applicationId,
  documentId,
  originalFilename,
  initialStatus,
  onStatusChange,
}: DocumentExtractionCardProps) {
  const queryClient = useQueryClient()
  const [showFullText, setShowFullText] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const {
    data: extraction,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['document-extraction', applicationId, documentId],
    queryFn: () => fetchExtraction(applicationId, documentId),
    enabled: initialStatus === 'processed' || initialStatus === 'failed',
    retry: 1,
  })

  const processMutation = useMutation({
    mutationFn: () => triggerProcessing(applicationId, documentId),
    onSuccess: () => {
      setActionError(null)
      queryClient.invalidateQueries({ queryKey: ['application-documents', applicationId] })
      queryClient.invalidateQueries({
        queryKey: ['document-extraction', applicationId, documentId],
      })
      if (onStatusChange) onStatusChange()
      refetch()
    },
    onError: (err: any) => {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to process document. Please check server logs.'
      setActionError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    },
  })

  const currentStatus = extraction?.status || initialStatus

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg p-5 mt-3 space-y-4 shadow-inner">
      {/* Header bar with Status & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200">
        <div>
          <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
            <span>OCR & Field Extraction</span>
            <span className="font-mono text-xs font-normal text-gray-500">
              ({originalFilename})
            </span>
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Preliminary deterministic extraction using PyMuPDF and OCR rules.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            id={`btn-process-doc-${documentId}`}
            onClick={() => processMutation.mutate()}
            disabled={processMutation.isPending || currentStatus === 'processing'}
            className="inline-flex items-center px-3 py-1.5 bg-blue-700 text-white text-xs font-medium rounded-md hover:bg-blue-800 disabled:opacity-50 transition-colors shadow-sm"
          >
            {processMutation.isPending || currentStatus === 'processing' ? (
              <>
                <svg
                  className="animate-spin -ml-0.5 mr-1.5 h-3.5 w-3.5 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v8H4z"
                  />
                </svg>
                Processing...
              </>
            ) : currentStatus === 'processed' ? (
              'Re-run Extraction'
            ) : (
              'Run Extraction'
            )}
          </button>
        </div>
      </div>

      {/* Advisory notice */}
      <div className="bg-amber-50/70 border border-amber-200 rounded p-2.5 text-[11px] text-amber-800 flex items-start gap-1.5">
        <span className="font-bold flex-shrink-0">⚠️ Advisory Notice:</span>
        <span>
          Extracted fields are machine observations and must be verified by an authorized AICTE officer.
          Values are NOT verified against external databases or official registries.
        </span>
      </div>

      {/* Warning message from backend (e.g., Tesseract not installed) */}
      {extraction?.warning && (
        <div className="bg-blue-50 border border-blue-200 rounded p-2.5 text-xs text-blue-800">
          <span className="font-semibold">Notice:</span> {extraction.warning}
        </div>
      )}

      {/* Action Error Banner */}
      {actionError && (
        <div className="bg-rose-50 border border-rose-200 rounded p-2.5 text-xs text-rose-800">
          <span className="font-semibold">Processing Failed:</span> {actionError}
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="py-8 text-center text-xs text-gray-500">
          <div className="inline-block animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600 mb-2" />
          <p>Loading extracted data...</p>
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div className="p-3 bg-rose-50 text-rose-700 text-xs rounded border border-rose-200 flex justify-between items-center">
          <span>Failed to load extraction: {error instanceof Error ? error.message : 'Error'}</span>
          <button
            type="button"
            onClick={() => refetch()}
            className="text-xs text-blue-700 underline font-medium hover:text-blue-900"
          >
            Retry
          </button>
        </div>
      )}

      {/* Not yet processed state */}
      {!isLoading && !isError && currentStatus === 'uploaded' && !extraction?.ocr_text && (
        <div className="py-6 text-center text-xs text-gray-500 bg-white border border-gray-200 rounded-md">
          <p className="font-medium text-gray-700">This document has not been processed yet.</p>
          <p className="mt-1 text-gray-400">
            Click "Run Extraction" above to run OCR and discover structured institutional metadata.
          </p>
        </div>
      )}

      {/* Extracted Fields Table */}
      {!isLoading && extraction && (
        <div className="space-y-4">
          <div className="bg-white rounded-md border border-gray-200 overflow-hidden shadow-sm">
            <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-200 flex justify-between items-center">
              <span className="text-xs font-bold text-gray-700 uppercase tracking-wide">
                Structured Field Discoveries
              </span>
              <span className="text-[11px] text-gray-500">
                {extraction.page_count ? `${extraction.page_count} page(s) analyzed` : 'Text analyzed'}
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-left text-xs">
                <thead className="bg-gray-50/50 text-gray-500 uppercase text-[10px] font-semibold">
                  <tr>
                    <th className="px-4 py-2">Field</th>
                    <th className="px-4 py-2">Extracted Value</th>
                    <th className="px-4 py-2">Raw Span Match</th>
                    <th className="px-4 py-2">Page</th>
                    <th className="px-4 py-2">Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {extraction.extracted_fields ? (
                    Object.entries(FIELD_LABELS).map(([fieldKey, label]) => {
                      const fieldData = (extraction.extracted_fields as unknown as Record<string, ExtractedField | undefined>)?.[fieldKey]
                      const hasValue = fieldData && fieldData.value !== null && fieldData.value !== undefined

                      return (
                        <tr key={fieldKey} className="hover:bg-gray-50/80">
                          <td className="px-4 py-2.5 font-medium text-gray-800 whitespace-nowrap">
                            {label}
                          </td>
                          <td className="px-4 py-2.5">
                            {hasValue ? (
                              <span className="font-semibold text-gray-900 bg-blue-50/60 px-2 py-0.5 rounded border border-blue-100">
                                {fieldData.value}
                              </span>
                            ) : (
                              <span className="text-gray-400 italic text-[11px]">
                                UNKNOWN (Not detected)
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-2.5 font-mono text-[11px] text-gray-600 max-w-xs truncate" title={fieldData?.raw_match || ''}>
                            {fieldData?.raw_match || <span className="text-gray-300">—</span>}
                          </td>
                          <td className="px-4 py-2.5 text-gray-600 whitespace-nowrap">
                            {fieldData?.source_page ? `Page ${fieldData.source_page}` : <span className="text-gray-300">—</span>}
                          </td>
                          <td className="px-4 py-2.5 whitespace-nowrap">
                            <ConfidenceBadge confidence={fieldData?.confidence || 'unknown'} />
                          </td>
                        </tr>
                      )
                    })
                  ) : (
                    <tr>
                      <td colSpan={5} className="px-4 py-4 text-center text-gray-400 italic">
                        No structured fields could be detected.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Extracted Text Preview Section */}
          <div className="bg-white rounded-md border border-gray-200 overflow-hidden shadow-sm">
            <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-200 flex justify-between items-center">
              <span className="text-xs font-bold text-gray-700 uppercase tracking-wide">
                OCR Extracted Text
              </span>
              {extraction.ocr_text && (
                <button
                  type="button"
                  onClick={() => setShowFullText(!showFullText)}
                  className="text-xs text-blue-700 hover:text-blue-900 font-medium"
                >
                  {showFullText ? 'Show Short Preview' : 'Show Complete Extracted Text'}
                </button>
              )}
            </div>

            <div className="p-4">
              {extraction.ocr_text ? (
                <div>
                  <div className="max-h-60 overflow-y-auto font-mono text-xs text-gray-800 bg-slate-50 p-3 rounded border border-slate-200 whitespace-pre-wrap leading-relaxed">
                    {showFullText ? extraction.ocr_text : extraction.ocr_text_preview || extraction.ocr_text.slice(0, 500)}
                  </div>
                  {!showFullText && extraction.ocr_text.length > 500 && (
                    <p className="text-[11px] text-gray-400 mt-1 italic">
                      Showing preview (first 500 characters of {extraction.ocr_text.length.toLocaleString()} total characters).
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-xs text-gray-400 italic text-center py-3">
                  No textual content was returned from this document. If this is a scanned image, ensure Tesseract OCR is installed on the host system.
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
