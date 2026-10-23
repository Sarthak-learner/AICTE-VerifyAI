import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchAuthenticityChecks,
  runAuthenticityScreening,
  updateAuthenticityCheckStatus,
} from '../../api/authenticity'
import { useAuth } from '../../context/AuthContext'
import type {
  AuthenticityCheck,
  AuthenticityResult,
  FindingStatus,
} from '../../types'

interface AuthenticityScreeningViewProps {
  applicationId: string
}

export const AuthenticityScreeningView: React.FC<AuthenticityScreeningViewProps> = ({
  applicationId,
}) => {
  const queryClient = useQueryClient()
  const { role, user } = useAuth()
  const isViewer = role === 'viewer'

  const [filterResult, setFilterResult] = useState<string>('all')
  const [expandedEvidence, setExpandedEvidence] = useState<Record<string, boolean>>({})
  const [editingCheckId, setEditingCheckId] = useState<string | null>(null)
  const [newStatus, setNewStatus] = useState<FindingStatus>('open')
  const [reviewerNotes, setReviewerNotes] = useState<string>('')
  const [reviewerLabel] = useState<string>(user?.full_name || 'Authorized Officer')

  // Query screening results
  const {
    data: screeningData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['authenticity-checks', applicationId],
    queryFn: () => fetchAuthenticityChecks(applicationId),
    staleTime: 30000,
  })

  // Mutation to run/rerun screening
  const screenMutation = useMutation({
    mutationFn: () => runAuthenticityScreening(applicationId),
    onSuccess: (data) => {
      queryClient.setQueryData(['authenticity-checks', applicationId], data)
      queryClient.invalidateQueries({ queryKey: ['authenticity-checks', applicationId] })
    },
  })

  // Mutation to update check status & notes
  const updateStatusMutation = useMutation({
    mutationFn: ({
      checkId,
      status,
      notes,
      label,
    }: {
      checkId: string
      status: FindingStatus
      notes: string
      label: string
    }) =>
      updateAuthenticityCheckStatus(applicationId, checkId, {
        reviewer_status: status,
        reviewer_notes: notes,
        reviewer_label: label,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['authenticity-checks', applicationId] })
      setEditingCheckId(null)
      setReviewerNotes('')
    },
  })

  const toggleEvidence = (id: string) => {
    setExpandedEvidence((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const handleStartReview = (check: AuthenticityCheck) => {
    setEditingCheckId(check.id)
    setNewStatus(check.reviewer_status)
    setReviewerNotes(check.reviewer_notes || '')
  }

  const handleSaveReview = (checkId: string) => {
    updateStatusMutation.mutate({
      checkId,
      status: newStatus,
      notes: reviewerNotes,
      label: reviewerLabel,
    })
  }

  // Wording & Badges for Check Results
  const renderResultBadge = (result: AuthenticityResult) => {
    switch (result) {
      case 'PASS':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            No indicator detected by this check
          </span>
        )
      case 'REVIEW':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-300">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
            Requires human review
          </span>
        )
      case 'UNAVAILABLE':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
            Check unavailable / N/A
          </span>
        )
    }
  }

  const renderStatusBadge = (status: FindingStatus) => {
    switch (status) {
      case 'resolved':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-100 text-emerald-800">
            Resolved
          </span>
        )
      case 'under_review':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-blue-100 text-blue-800">
            Under Review
          </span>
        )
      case 'requires_clarification':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-purple-100 text-purple-800">
            Requires Clarification
          </span>
        )
      case 'dismissed':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-gray-100 text-gray-700">
            Dismissed
          </span>
        )
      case 'open':
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-amber-100 text-amber-900">
            Open
          </span>
        )
    }
  }

  if (isLoading) {
    return (
      <div className="p-16 text-center text-xs text-gray-500">
        <div className="inline-block animate-spin rounded-full h-7 w-7 border-b-2 border-indigo-600 mb-2"></div>
        <p>Loading document authenticity checks...</p>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg text-red-700 text-xs">
        <p className="font-semibold mb-1">Failed to load authenticity checks</p>
        <p>{(error as Error)?.message || 'An unexpected error occurred.'}</p>
        <button
          onClick={() => refetch()}
          className="mt-3 px-3 py-1.5 bg-white border border-red-300 rounded text-red-800 hover:bg-red-50 text-xs font-medium"
        >
          Try Again
        </button>
      </div>
    )
  }

  const documents = screeningData?.documents || []
  const totalChecks = screeningData?.total_checks || 0
  const passedChecks = screeningData?.total_passed || 0
  const reviewChecks = screeningData?.total_review_required || 0
  const unavailableChecks = screeningData?.total_unavailable || 0

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-gray-900">
                Document Authenticity Signals & Tamper Indicators
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200">
                PHASE 05 SCREENING
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Deterministic screening of file hash integrity, PDF metadata/timestamps, container structure, resolution, textual consistency, and digital signature presence.
            </p>
          </div>
            {isViewer ? (
              <span
                title="Running authenticity screening requires Officer or Admin role"
                className="px-3.5 py-1.5 bg-gray-100 text-gray-400 text-xs font-semibold rounded-md border border-gray-200 cursor-not-allowed shadow-none"
              >
                🔒 Screening (Officer Only)
              </span>
            ) : (
              <button
                type="button"
                onClick={() => screenMutation.mutate()}
                disabled={screenMutation.isPending}
                className="px-4 py-2 bg-indigo-600 text-white text-xs font-semibold rounded-md hover:bg-indigo-700 disabled:opacity-50 transition-colors shadow-sm flex items-center gap-2"
              >
                {screenMutation.isPending ? (
                  <>
                    <span className="animate-spin h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full"></span>
                    Screening Documents...
                  </>
                ) : (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    {totalChecks > 0 ? 'Rerun Authenticity Screening' : 'Run Authenticity Screening'}
                  </>
                )}
              </button>
            )}
        </div>

        {/* Advisory Warning Banner */}
        <div className="mt-4 p-3.5 bg-amber-50/70 border border-amber-200/90 rounded-md text-amber-900 text-xs flex items-start gap-3">
          <svg className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <p className="font-semibold text-amber-950">Advisory Review Notice</p>
            <p className="text-[11px] text-amber-800 mt-0.5">
              Screening indicators are purely diagnostic markers intended for human officer evaluation. An indicator is a <strong>review trigger</strong>, NOT proof of manipulation or forgery. Conversely, the absence of flags indicates no anomaly was detected by these checks and does not constitute official certification.
            </p>
          </div>
        </div>

        {/* Screening Metrics Overview */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4 text-xs">
          <div className="bg-slate-50 p-3 rounded-md border border-slate-200">
            <span className="text-gray-500 block font-medium">Checks Evaluated</span>
            <span className="text-xl font-bold text-gray-900">{totalChecks}</span>
          </div>
          <div className="bg-emerald-50/60 p-3 rounded-md border border-emerald-200">
            <span className="text-emerald-700 block font-medium">No Indicator Detected</span>
            <span className="text-xl font-bold text-emerald-800">{passedChecks}</span>
          </div>
          <div className="bg-amber-50/80 p-3 rounded-md border border-amber-200">
            <span className="text-amber-800 block font-medium">Requires Human Review</span>
            <span className="text-xl font-bold text-amber-900">{reviewChecks}</span>
          </div>
          <div className="bg-slate-50 p-3 rounded-md border border-slate-200">
            <span className="text-gray-400 block font-medium">Unavailable / N/A</span>
            <span className="text-xl font-bold text-gray-700">{unavailableChecks}</span>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center justify-between gap-2 border-b border-gray-200 pb-2">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setFilterResult('all')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              filterResult === 'all'
                ? 'bg-slate-800 text-white'
                : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}
          >
            All Checks ({totalChecks})
          </button>
          <button
            type="button"
            onClick={() => setFilterResult('REVIEW')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              filterResult === 'REVIEW'
                ? 'bg-amber-600 text-white'
                : 'bg-white text-amber-800 border border-amber-200 hover:bg-amber-50'
            }`}
          >
            Review Flags ({reviewChecks})
          </button>
          <button
            type="button"
            onClick={() => setFilterResult('PASS')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              filterResult === 'PASS'
                ? 'bg-emerald-700 text-white'
                : 'bg-white text-emerald-700 border border-emerald-200 hover:bg-emerald-50'
            }`}
          >
            Passed ({passedChecks})
          </button>
          <button
            type="button"
            onClick={() => setFilterResult('UNAVAILABLE')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              filterResult === 'UNAVAILABLE'
                ? 'bg-gray-600 text-white'
                : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}
          >
            Unavailable ({unavailableChecks})
          </button>
        </div>
      </div>

      {/* Document Checks Grouped List */}
      {totalChecks === 0 ? (
        <div className="bg-white rounded-lg border border-dashed border-gray-300 p-12 text-center">
          <svg className="w-10 h-10 text-gray-400 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h4 className="text-sm font-semibold text-gray-900 mb-1">No Screening Results Available</h4>
          <p className="text-xs text-gray-500 max-w-sm mx-auto mb-4">
            Authenticity screening has not been executed yet for this application's documents.
          </p>
          <button
            type="button"
            onClick={() => screenMutation.mutate()}
            disabled={screenMutation.isPending}
            className="px-4 py-2 bg-indigo-600 text-white text-xs font-medium rounded-md hover:bg-indigo-700 transition-colors shadow-sm"
          >
            Run Screening Now
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {documents.map((docGroup) => {
            const visibleChecks = docGroup.checks.filter((c) =>
              filterResult === 'all' ? true : c.result === filterResult
            )

            if (visibleChecks.length === 0) return null

            return (
              <div
                key={docGroup.document_id}
                className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden"
              >
                {/* Document Group Header */}
                <div className="bg-slate-50 px-5 py-3.5 border-b border-gray-200 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                    <span className="text-xs font-bold text-gray-900">{docGroup.document_filename}</span>
                    {docGroup.document_type && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 border border-blue-200 uppercase">
                        {docGroup.document_type.replace(/_/g, ' ')}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-gray-500">
                    <span className="text-emerald-700 font-medium">{docGroup.pass_count} passed</span>
                    <span>•</span>
                    <span className="text-amber-700 font-medium">{docGroup.review_count} review</span>
                    <span>•</span>
                    <span className="text-gray-500 font-medium">{docGroup.unavailable_count} n/a</span>
                  </div>
                </div>

                {/* Checks List */}
                <div className="divide-y divide-gray-100">
                  {visibleChecks.map((check) => (
                    <div key={check.id} className="p-4 hover:bg-gray-50/50 transition-colors">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-gray-900">{check.check_name}</span>
                          <span className="text-[10px] font-mono text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                            {check.check_type}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          {renderResultBadge(check.result)}
                          {renderStatusBadge(check.reviewer_status)}
                        </div>
                      </div>

                      <p className="text-xs text-gray-700 mb-3">{check.explanation}</p>

                      {/* Evidence block toggle */}
                      {check.evidence && Object.keys(check.evidence).length > 0 && (
                        <div className="mt-2">
                          <button
                            type="button"
                            onClick={() => toggleEvidence(check.id)}
                            className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                          >
                            <svg
                              className={`w-3.5 h-3.5 transform transition-transform ${
                                expandedEvidence[check.id] ? 'rotate-90' : ''
                              }`}
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                            </svg>
                            {expandedEvidence[check.id] ? 'Hide Evidence Details' : 'View Supporting Evidence'}
                          </button>

                          {expandedEvidence[check.id] && (
                            <div className="mt-2 p-3 bg-slate-900 text-slate-100 rounded text-[11px] font-mono overflow-x-auto border border-slate-700">
                              <pre>{JSON.stringify(check.evidence, null, 2)}</pre>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Reviewer Status & Notes Block */}
                      <div className="mt-3 pt-3 border-t border-gray-100 flex flex-wrap items-center justify-between gap-3 text-xs">
                        <div className="text-gray-500 text-[11px]">
                          {check.reviewer_notes ? (
                            <span>
                              <strong>Reviewer Note:</strong> {check.reviewer_notes}
                            </span>
                          ) : (
                            <span className="italic text-gray-400">No reviewer notes recorded yet.</span>
                          )}
                        </div>

                        <div>
                          {editingCheckId === check.id ? (
                            <div className="p-3 bg-blue-50/70 border border-blue-200 rounded-md space-y-2 mt-2 w-full max-w-lg">
                              <div className="flex items-center gap-2">
                                <label className="text-[11px] font-semibold text-gray-700">Review Status:</label>
                                <select
                                  value={newStatus}
                                  onChange={(e) => setNewStatus(e.target.value as FindingStatus)}
                                  className="text-xs border border-gray-300 rounded px-2 py-1 bg-white font-medium"
                                >
                                  <option value="open">Open</option>
                                  <option value="under_review">Under Review</option>
                                  <option value="resolved">Resolved</option>
                                  <option value="requires_clarification">Requires Clarification</option>
                                  <option value="dismissed">Dismissed</option>
                                </select>
                              </div>

                              <div>
                                <label className="block text-[11px] font-semibold text-gray-700 mb-1">
                                  Resolution / Assessment Notes:
                                </label>
                                <textarea
                                  rows={2}
                                  value={reviewerNotes}
                                  onChange={(e) => setReviewerNotes(e.target.value)}
                                  placeholder="Enter officer assessment or applicant clarification request..."
                                  className="w-full text-xs border border-gray-300 rounded p-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                                />
                              </div>

                              <div className="flex items-center justify-end gap-2 pt-1">
                                <button
                                  type="button"
                                  onClick={() => setEditingCheckId(null)}
                                  className="px-2.5 py-1 text-xs border border-gray-300 rounded text-gray-600 hover:bg-gray-100"
                                >
                                  Cancel
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleSaveReview(check.id)}
                                  disabled={updateStatusMutation.isPending}
                                  className="px-3 py-1 text-xs font-semibold bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                                >
                                  {updateStatusMutation.isPending ? 'Saving...' : 'Save Assessment'}
                                </button>
                              </div>
                            </div>
                          ) : isViewer ? (
                            <span className="text-[11px] text-gray-400 italic">Read-Only</span>
                          ) : (
                            <button
                              type="button"
                              onClick={() => handleStartReview(check)}
                              className="px-2.5 py-1 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 shadow-xs"
                            >
                              Update Status / Add Notes
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
