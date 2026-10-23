import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchFindings, updateFindingStatus } from '../../api/validation'
import { useAuth } from '../../context/AuthContext'
import type { Finding, FindingSeverity, FindingStatus } from '../../types'

interface ValidationFindingsListProps {
  applicationId: string
  onFindingsUpdated?: () => void
}

function SeverityBadge({ severity }: { severity: FindingSeverity }) {
  if (severity === 'error') {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded text-[11px] font-bold bg-rose-100 text-rose-800 border border-rose-300">
        ERROR
      </span>
    )
  }
  if (severity === 'warning') {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
        WARNING
      </span>
    )
  }
  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded text-[11px] font-bold bg-blue-100 text-blue-800 border border-blue-300">
      INFO
    </span>
  )
}

function StatusBadge({ status }: { status: FindingStatus }) {
  const styles: Record<FindingStatus, string> = {
    open: 'bg-blue-50 text-blue-700 border-blue-200',
    under_review: 'bg-amber-50 text-amber-800 border-amber-300',
    resolved: 'bg-emerald-50 text-emerald-800 border-emerald-300',
    requires_clarification: 'bg-purple-50 text-purple-800 border-purple-300',
    dismissed: 'bg-gray-100 text-gray-700 border-gray-300',
  }
  const formatted = status.replace(/_/g, ' ').toUpperCase()
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold border ${
        styles[status] || 'bg-gray-100 text-gray-700 border-gray-300'
      }`}
    >
      {formatted}
    </span>
  )
}

export default function ValidationFindingsList({
  applicationId,
  onFindingsUpdated,
}: ValidationFindingsListProps) {
  const queryClient = useQueryClient()
  const { role, user } = useAuth()
  const isViewer = role === 'viewer'

  const [statusFilter, setStatusFilter] = useState<string>('')
  const [severityFilter, setSeverityFilter] = useState<string>('')

  // Selected finding for reviewer edits
  const [editingFindingId, setEditingFindingId] = useState<string | null>(null)
  const [reviewStatus, setReviewStatus] = useState<FindingStatus>('under_review')
  const [resolutionNote, setResolutionNote] = useState<string>('')
  const [reviewerName, setReviewerName] = useState<string>(user?.full_name || 'Authorized Officer')

  const {
    data: findingsData,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['application-findings', applicationId, statusFilter, severityFilter],
    queryFn: () =>
      fetchFindings(
        applicationId,
        statusFilter || undefined,
        severityFilter || undefined,
      ),
    enabled: Boolean(applicationId),
  })

  const updateMutation = useMutation({
    mutationFn: ({
      findingId,
      status,
      note,
      label,
    }: {
      findingId: string
      status: FindingStatus
      note: string
      label: string
    }) =>
      updateFindingStatus(applicationId, findingId, {
        status,
        resolution_note: note,
        reviewer_label: label,
      }),
    onSuccess: () => {
      setEditingFindingId(null)
      setResolutionNote('')
      queryClient.invalidateQueries({
        queryKey: ['application-findings', applicationId],
      })
      queryClient.invalidateQueries({
        queryKey: ['consistency-graph', applicationId],
      })
      if (onFindingsUpdated) onFindingsUpdated()
    },
  })

  const handleStartReview = (finding: Finding) => {
    setEditingFindingId(finding.id)
    setReviewStatus(finding.status)
    setResolutionNote(finding.resolution_note || '')
  }

  const handleSaveReview = (findingId: string) => {
    updateMutation.mutate({
      findingId,
      status: reviewStatus,
      note: resolutionNote,
      label: reviewerName,
    })
  }

  if (isLoading) {
    return (
      <div className="p-12 text-center text-xs text-gray-500">
        <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mb-2" />
        <p>Loading validation findings...</p>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="p-4 bg-rose-50 border border-rose-200 rounded text-xs text-rose-800">
        Failed to load findings: {error instanceof Error ? error.message : 'Error'}
      </div>
    )
  }

  const findings = findingsData?.items || []

  return (
    <div className="space-y-4">
      {/* Filters & Counters Bar */}
      <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Counter badges */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="font-semibold text-gray-700">Findings:</span>
          <span className="px-2.5 py-1 bg-gray-100 text-gray-800 rounded-full font-bold">
            {findingsData?.total || 0} Total
          </span>
          <span className="px-2.5 py-1 bg-blue-50 text-blue-800 rounded-full font-semibold border border-blue-200">
            {findingsData?.open_count || 0} Open
          </span>
          <span className="px-2.5 py-1 bg-amber-50 text-amber-800 rounded-full font-semibold border border-amber-200">
            {findingsData?.under_review_count || 0} Under Review
          </span>
          <span className="px-2.5 py-1 bg-purple-50 text-purple-800 rounded-full font-semibold border border-purple-200">
            {findingsData?.requires_clarification_count || 0} Requires Clarification
          </span>
          <span className="px-2.5 py-1 bg-emerald-50 text-emerald-800 rounded-full font-semibold border border-emerald-200">
            {findingsData?.resolved_count || 0} Resolved
          </span>
        </div>

        {/* Filter dropdowns */}
        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs border border-gray-300 rounded px-2.5 py-1.5 bg-white text-gray-700 focus:ring-blue-500"
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="under_review">Under Review</option>
            <option value="requires_clarification">Requires Clarification</option>
            <option value="resolved">Resolved</option>
            <option value="dismissed">Dismissed</option>
          </select>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="text-xs border border-gray-300 rounded px-2.5 py-1.5 bg-white text-gray-700 focus:ring-blue-500"
          >
            <option value="">All Severities</option>
            <option value="error">Error</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
          </select>
        </div>
      </div>

      {/* Advisory Banner */}
      <div className="bg-amber-50/70 border border-amber-200 rounded-md p-3 text-xs text-amber-900 flex items-start gap-2">
        <span className="font-bold">⚠️ Human-in-the-Loop Review:</span>
        <span>
          A validation finding is an advisory observation for preliminary screening. It does NOT automatically reject
          an application or constitute proof of forgery. Authorized AICTE officers must review all evidence.
        </span>
      </div>

      {/* Findings List */}
      {findings.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-xs text-gray-500 shadow-sm">
          No validation findings match your current filters.
        </div>
      ) : (
        <div className="space-y-3">
          {findings.map((finding) => {
            const isEditing = editingFindingId === finding.id

            return (
              <div
                key={finding.id}
                className="bg-white rounded-lg border border-gray-200 shadow-sm p-5 hover:border-gray-300 transition-all"
              >
                {/* Header row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 pb-3">
                  <div className="flex items-center gap-2.5">
                    <SeverityBadge severity={finding.severity} />
                    <span className="font-mono text-xs text-gray-500 font-medium">
                      [{finding.rule_code}]
                    </span>
                    <h4 className="text-sm font-bold text-gray-900">{finding.title}</h4>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={finding.status} />
                    {!isEditing && (
                      isViewer ? (
                        <span className="text-[11px] text-gray-400 italic">Read-Only</span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleStartReview(finding)}
                          className="px-2.5 py-1 text-xs font-semibold text-blue-700 hover:text-blue-900 bg-blue-50 hover:bg-blue-100 rounded border border-blue-200 transition-colors"
                        >
                          Review / Action
                        </button>
                      )
                    )}
                  </div>
                </div>

                {/* Body: Explanation & Details */}
                <div className="mt-3 text-xs text-gray-700 space-y-2">
                  <p className="leading-relaxed">{finding.detail}</p>

                  {/* Evidence Grid */}
                  <div className="bg-gray-50 rounded p-3 border border-gray-200 grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2 text-[11px]">
                    <div>
                      <span className="text-gray-400 block font-medium">Extracted Value / Observation</span>
                      <span className="font-mono text-gray-800 font-semibold">
                        {finding.extracted_value || <span className="text-gray-400 italic">None detected</span>}
                      </span>
                    </div>

                    <div>
                      <span className="text-gray-400 block font-medium">Expected / Reference Rule</span>
                      <span className="text-gray-800 font-semibold">
                        {finding.expected_value || <span className="text-gray-400 italic">—</span>}
                      </span>
                    </div>

                    {finding.page_number && (
                      <div>
                        <span className="text-gray-400 block font-medium">Source Document Location</span>
                        <span className="text-blue-700 font-semibold">Page {finding.page_number}</span>
                      </div>
                    )}

                    {finding.evidence?.document_filename && (
                      <div>
                        <span className="text-gray-400 block font-medium">Document</span>
                        <span className="text-gray-800 font-mono">{finding.evidence.document_filename}</span>
                      </div>
                    )}
                  </div>

                  {/* Resolution Notes (if already resolved or reviewed) */}
                  {finding.resolution_note && !isEditing && (
                    <div className="mt-2 p-2.5 bg-emerald-50/70 border border-emerald-200 rounded text-[11px] text-emerald-900">
                      <span className="font-bold">Officer Review Note:</span> {finding.resolution_note}
                    </div>
                  )}
                </div>

                {/* Reviewer Action Form (When expanded) */}
                {isEditing && (
                  <div className="mt-4 pt-4 border-t border-gray-200 bg-slate-50 p-4 rounded-md space-y-3">
                    <h5 className="text-xs font-bold text-gray-800 uppercase tracking-wider">
                      Authorized Officer Review & Action
                    </h5>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">
                          Update Finding Status
                        </label>
                        <select
                          value={reviewStatus}
                          onChange={(e) => setReviewStatus(e.target.value as FindingStatus)}
                          className="w-full text-xs border border-gray-300 rounded px-3 py-1.5 bg-white text-gray-800 focus:ring-blue-500"
                        >
                          <option value="open">Open (Unreviewed)</option>
                          <option value="under_review">Under Review (Inspection ongoing)</option>
                          <option value="requires_clarification">Requires Clarification (From institution)</option>
                          <option value="resolved">Resolved (Acceptable / Rectified)</option>
                          <option value="dismissed">Dismissed (Not applicable)</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">
                          Reviewer Designation
                        </label>
                        <input
                          type="text"
                          value={reviewerName}
                          onChange={(e) => setReviewerName(e.target.value)}
                          className="w-full text-xs border border-gray-300 rounded px-3 py-1.5 bg-white text-gray-800 focus:ring-blue-500"
                          placeholder="e.g. Authorized Officer"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">
                        Resolution Notes / Justification
                      </label>
                      <textarea
                        value={resolutionNote}
                        onChange={(e) => setResolutionNote(e.target.value)}
                        rows={2}
                        className="w-full text-xs border border-gray-300 rounded p-2 bg-white text-gray-800 focus:ring-blue-500"
                        placeholder="Explain findings review, clarification requests, or reason for resolution..."
                      />
                    </div>

                    <div className="flex justify-end gap-2 pt-2">
                      <button
                        type="button"
                        onClick={() => setEditingFindingId(null)}
                        className="px-3 py-1.5 border border-gray-300 text-gray-700 text-xs font-medium rounded hover:bg-gray-100 transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        id={`btn-save-finding-${finding.id}`}
                        onClick={() => handleSaveReview(finding.id)}
                        disabled={updateMutation.isPending}
                        className="px-3.5 py-1.5 bg-blue-700 text-white text-xs font-semibold rounded hover:bg-blue-800 disabled:opacity-50 transition-colors shadow-sm"
                      >
                        {updateMutation.isPending ? 'Saving Action...' : 'Save Review Action'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
