import { useQuery } from '@tanstack/react-query'

import { fetchApplicationAuditTrail } from '../../api/applications'
import type { AuditEvent } from '../../types'

interface AuditTrailViewProps {
  applicationId: string
}

function ActionBadge({ action }: { action: string }) {
  const styles: Record<string, string> = {
    'application.created': 'bg-blue-50 text-blue-700 border-blue-200',
    'document.uploaded': 'bg-indigo-50 text-indigo-700 border-indigo-200',
    'application.validated': 'bg-purple-50 text-purple-700 border-purple-200',
    'finding.reviewed': 'bg-emerald-50 text-emerald-700 border-emerald-200',
    'authenticity.screened': 'bg-amber-50 text-amber-700 border-amber-200',
    'authenticity.reviewed': 'bg-teal-50 text-teal-700 border-teal-200',
  }
  const formatted = action.replace(/\./g, ' › ').toUpperCase()
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold border ${
        styles[action] || 'bg-gray-100 text-gray-700 border-gray-200'
      }`}
    >
      {formatted}
    </span>
  )
}

export default function AuditTrailView({ applicationId }: AuditTrailViewProps) {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['application-audit-trail', applicationId],
    queryFn: () => fetchApplicationAuditTrail(applicationId),
    enabled: Boolean(applicationId),
  })

  if (isLoading) {
    return (
      <div className="p-12 text-center text-xs text-gray-500">
        <div className="inline-block animate-spin rounded-full h-7 w-7 border-b-2 border-blue-600 mb-2" />
        <p>Loading regulatory audit trail...</p>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="p-4 bg-rose-50 border border-rose-200 rounded text-xs text-rose-800">
        Failed to load audit trail: {error instanceof Error ? error.message : 'Error'}
      </div>
    )
  }

  const events: AuditEvent[] = data?.events || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-gray-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-gray-900">
                Immutable Regulatory Audit Trail
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-800 border border-slate-200">
                CHAIN OF CUSTODY
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Chronological, non-repudiable log of system activities, document operations, automated validations, and officer determinations.
            </p>
          </div>
          <div>
            <button
              type="button"
              onClick={() => refetch()}
              className="px-3 py-1.5 border border-gray-300 text-gray-700 text-xs font-medium rounded-md hover:bg-gray-50 transition-colors shadow-sm"
            >
              Refresh Log
            </button>
          </div>
        </div>

        {/* Regulatory Advisory */}
        <div className="mt-4 bg-slate-50 border border-slate-200 rounded-md p-3 text-xs text-slate-700 flex items-start gap-2">
          <svg className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <div>
            <span className="font-semibold text-slate-900">Compliance & Evidentiary Standard:</span> All manual reviews, document uploads, and validation results are logged with the authenticated officer's credentials, action metadata, and UTC timestamps.
          </div>
        </div>
      </div>

      {/* Timeline List */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
        <h4 className="text-xs font-bold text-gray-800 uppercase tracking-wider mb-5">
          Activity History ({events.length} {events.length === 1 ? 'event' : 'events'})
        </h4>

        {events.length === 0 ? (
          <div className="p-8 text-center text-xs text-gray-400 bg-gray-50 rounded-lg border border-dashed border-gray-200">
            No audit records logged for this application yet.
          </div>
        ) : (
          <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-gray-200">
            {events.map((ev, idx) => (
              <div key={ev.id || idx} className="relative group">
                {/* Circle on the line */}
                <span className="absolute -left-6 top-1.5 w-4 h-4 rounded-full border-2 border-white bg-blue-600 shadow-sm" />
                <div className="bg-slate-50/70 hover:bg-slate-50 border border-slate-200 rounded-lg p-4 transition-colors">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <ActionBadge action={ev.action} />
                      <span className="text-xs font-semibold text-gray-900">
                        {ev.actor_label || 'System'}
                      </span>
                    </div>
                    <time className="text-[11px] font-mono text-gray-500">
                      {new Date(ev.created_at).toLocaleString()}
                    </time>
                  </div>
                  <p className="text-xs text-gray-700 leading-relaxed">
                    {ev.detail || 'Action recorded.'}
                  </p>
                  {ev.resource_type && (
                    <div className="mt-2 pt-2 border-t border-slate-200/60 flex items-center gap-2 text-[11px] text-gray-500 font-mono">
                      <span>Resource: {ev.resource_type}</span>
                      {ev.resource_id && <span>• ID: {ev.resource_id.slice(0, 8)}...</span>}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
