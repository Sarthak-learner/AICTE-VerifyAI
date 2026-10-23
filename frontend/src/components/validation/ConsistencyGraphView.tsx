import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchConsistencyGraph } from '../../api/validation'
import type { ComparisonItem } from '../../types'

interface ConsistencyGraphViewProps {
  applicationId: string
}

export default function ConsistencyGraphView({ applicationId }: ConsistencyGraphViewProps) {
  const [filterMode, setFilterMode] = useState<'all' | 'discrepancy' | 'match'>('all')

  const {
    data: graphData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['consistency-graph', applicationId],
    queryFn: () => fetchConsistencyGraph(applicationId),
    enabled: Boolean(applicationId),
  })

  if (isLoading) {
    return (
      <div className="p-16 text-center text-xs text-gray-500">
        <div className="inline-block animate-spin rounded-full h-7 w-7 border-b-2 border-blue-600 mb-2" />
        <p>Constructing Cross-Document Consistency Graph...</p>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="p-4 bg-rose-50 border border-rose-200 rounded text-xs text-rose-800">
        Failed to load consistency graph: {error instanceof Error ? error.message : 'Error'}
      </div>
    )
  }

  const comparisons = graphData?.comparisons || []
  const filteredComparisons = comparisons.filter((c) => {
    if (filterMode === 'discrepancy') return c.status === 'discrepancy'
    if (filterMode === 'match') return c.status === 'match'
    return true
  })

  const documentNodes = graphData?.nodes.filter((n) => n.type === 'document') || []
  const fieldNodes = graphData?.nodes.filter((n) => n.type === 'field') || []

  return (
    <div className="space-y-6">
      {/* Header & KPI Summary Bar */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-gray-900">
                Cross-Document Consistency Graph
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-100 text-indigo-800 border border-indigo-200">
                FLAGSHIP ANALYSIS
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Deterministic cross-referencing of normalized institutional attributes across all application documents.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => refetch()}
              className="px-3 py-1.5 border border-gray-300 text-gray-700 text-xs font-medium rounded-md hover:bg-gray-50 transition-colors shadow-sm"
            >
              Refresh Graph
            </button>
          </div>
        </div>

        {/* Metric Badges */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4 text-xs">
          <div className="bg-slate-50 p-3 rounded-md border border-slate-200">
            <span className="text-gray-400 block font-medium">Documents Analyzed</span>
            <span className="text-lg font-bold text-gray-800">{documentNodes.length}</span>
          </div>

          <div className="bg-slate-50 p-3 rounded-md border border-slate-200">
            <span className="text-gray-400 block font-medium">Discovered Field Nodes</span>
            <span className="text-lg font-bold text-gray-800">{fieldNodes.length}</span>
          </div>

          <div className="bg-emerald-50/60 p-3 rounded-md border border-emerald-200">
            <span className="text-emerald-700 block font-medium">Consistent Matches</span>
            <span className="text-lg font-bold text-emerald-800">
              {graphData?.total_matches || 0}
            </span>
          </div>

          <div className="bg-rose-50/60 p-3 rounded-md border border-rose-200">
            <span className="text-rose-700 block font-medium">Flagged Discrepancies</span>
            <span className="text-lg font-bold text-rose-800">
              {graphData?.total_discrepancies || 0}
            </span>
          </div>
        </div>

        {/* Informative Explanation Banner when No Comparisons Are Available */}
        {comparisons.length === 0 && (
          <div className="mt-4 bg-amber-50 border border-amber-200 rounded-lg p-4 text-xs text-amber-900 space-y-2">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-amber-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <h4 className="font-bold text-sm text-amber-950">
                No Comparable Extracted Fields Available
              </h4>
            </div>
            <p className="leading-relaxed">
              {graphData?.explanation ||
                'No comparable extracted fields are available across the uploaded documents. Cross-document consistency requires at least two documents with extracted, normalized values for common attributes (e.g. Institution Name, Land Area, Programme, Reference Number, Dates).'}
            </p>
            <div className="pt-2 border-t border-amber-200/60 text-[11px] text-amber-800 font-medium flex items-center gap-1.5">
              <span className="font-bold">⚠️ Advisory Notice:</span>
              <span>
                Zero discrepancies does not indicate verified consistency — no pairwise field evidence was available to evaluate.
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Structured Graph Visualization Diagram */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-xs font-bold text-gray-800 uppercase tracking-wider">
            Graph Topology: Ingested Documents & Linked Metadata
          </h4>
          <div className="flex items-center gap-3 text-xs text-gray-500">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" /> Consistent Edge
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" /> Discrepancy Edge
            </span>
          </div>
        </div>

        {documentNodes.length < 2 ? (
          <div className="p-8 text-center text-xs text-gray-400 bg-gray-50 rounded-lg border border-dashed border-gray-300">
            At least 2 uploaded documents are required to form a cross-document consistency graph.
          </div>
        ) : (
          <div className="bg-slate-50/70 p-5 rounded-lg border border-slate-200 overflow-x-auto">
            <div className="min-w-[650px] space-y-4">
              {/* Document Nodes Row */}
              <div className="flex flex-wrap gap-4 items-center justify-center">
                {documentNodes.map((docNode) => (
                  <div
                    key={docNode.id}
                    className="bg-white border-2 border-blue-400 rounded-lg p-3 shadow-sm min-w-[180px] max-w-[220px]"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <svg className="w-4 h-4 text-blue-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                      <span className="text-xs font-bold text-gray-900 truncate" title={docNode.label}>
                        {docNode.label}
                      </span>
                    </div>
                    <span className="text-[10px] text-gray-400 font-mono block uppercase">
                      {docNode.metadata?.category?.replace(/_/g, ' ')}
                    </span>
                  </div>
                ))}
              </div>

              {/* Connecting relationship line info */}
              <div className="text-center py-1">
                {comparisons.length === 0 ? (
                  <span className="text-[11px] font-semibold text-amber-800 bg-amber-100 border border-amber-200 px-3 py-1 rounded-full">
                    0 Evaluated Pairs — No overlapping extracted fields across documents
                  </span>
                ) : (
                  <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-widest bg-gray-200/80 px-3 py-1 rounded-full">
                    Cross-Document Consistency Analysis ({comparisons.length} Evaluated Pairs)
                  </span>
                )}
              </div>

              {/* Quick edge summary badges */}
              {comparisons.length > 0 && (
                <div className="flex flex-wrap gap-2 justify-center">
                  {comparisons.map((c, idx) => (
                    <div
                      key={idx}
                      className={`px-3 py-1.5 rounded-full text-xs font-medium border flex items-center gap-2 shadow-sm ${
                        c.status === 'match'
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                          : 'bg-rose-50 text-rose-800 border-rose-300'
                      }`}
                    >
                      <span>{c.status === 'match' ? '✓' : '⚠️'}</span>
                      <span className="font-semibold capitalize">{c.field.replace(/_/g, ' ')}:</span>
                      <span className="text-[11px]">
                        {c.doc_a_name.slice(0, 15)}... &harr; {c.doc_b_name.slice(0, 15)}...
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Side-by-Side Discrepancy & Match Comparison Cards */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-100 pb-3">
          <div>
            <h4 className="text-sm font-bold text-gray-900">
              Side-by-Side Field Evidence & Normalization
            </h4>
            <p className="text-xs text-gray-500">
              Normalized side-by-side values with source citations and discrepancy explanations.
            </p>
          </div>

          {/* Filter toggle buttons */}
          <div className="inline-flex rounded-md shadow-sm" role="group">
            <button
              type="button"
              onClick={() => setFilterMode('all')}
              className={`px-3 py-1 text-xs font-semibold rounded-l-md border ${
                filterMode === 'all'
                  ? 'bg-blue-700 text-white border-blue-700'
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              }`}
            >
              All ({comparisons.length})
            </button>
            <button
              type="button"
              onClick={() => setFilterMode('discrepancy')}
              className={`px-3 py-1 text-xs font-semibold border-t border-b ${
                filterMode === 'discrepancy'
                  ? 'bg-rose-700 text-white border-rose-700'
                  : 'bg-white text-rose-700 border-gray-300 hover:bg-gray-50'
              }`}
            >
              Discrepancies ({graphData?.total_discrepancies || 0})
            </button>
            <button
              type="button"
              onClick={() => setFilterMode('match')}
              className={`px-3 py-1 text-xs font-semibold rounded-r-md border ${
                filterMode === 'match'
                  ? 'bg-emerald-700 text-white border-emerald-700'
                  : 'bg-white text-emerald-700 border-gray-300 hover:bg-gray-50'
              }`}
            >
              Matches ({graphData?.total_matches || 0})
            </button>
          </div>
        </div>

        {/* Empty state for filtered comparisons */}
        {filteredComparisons.length === 0 ? (
          comparisons.length === 0 ? (
            <div className="p-8 text-center text-xs bg-gray-50 rounded-lg border border-dashed border-gray-300 space-y-2">
              <div className="text-gray-500 text-sm font-semibold">
                No cross-document comparisons available to display
              </div>
              <p className="text-gray-500 max-w-lg mx-auto">
                {graphData?.explanation ||
                  'Ensure documents have undergone OCR and structured field extraction, and that at least two documents share common extracted attributes.'}
              </p>
              <p className="text-[11px] text-gray-400 italic">
                Zero discrepancies does not confirm consistency when no comparable pairs exist.
              </p>
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-gray-400 bg-gray-50 rounded-lg">
              No comparisons found matching the "{filterMode}" filter.
            </div>
          )
        ) : (

          <div className="space-y-4">
            {filteredComparisons.map((item: ComparisonItem, idx: number) => {
              const isDiscrepancy = item.status === 'discrepancy'

              return (
                <div
                  key={idx}
                  className={`rounded-lg border p-5 transition-all shadow-sm ${
                    isDiscrepancy
                      ? 'bg-rose-50/30 border-rose-200 hover:border-rose-300'
                      : 'bg-emerald-50/20 border-emerald-200 hover:border-emerald-300'
                  }`}
                >
                  {/* Card Title & Status Badge */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 pb-3">
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold border ${
                          isDiscrepancy
                            ? 'bg-rose-100 text-rose-800 border-rose-300'
                            : 'bg-emerald-100 text-emerald-800 border-emerald-300'
                        }`}
                      >
                        {isDiscrepancy ? 'DISCREPANCY DETECTED' : 'CONSISTENT MATCH'}
                      </span>
                      <h5 className="text-sm font-bold text-gray-900 capitalize">
                        {item.field.replace(/_/g, ' ')}
                      </h5>
                    </div>

                    <span className="text-xs text-gray-500 font-mono">
                      Pairwise Comparison #{idx + 1}
                    </span>
                  </div>

                  {/* Side-by-Side Documents Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                    {/* Document A Column */}
                    <div className="bg-white p-3.5 rounded-md border border-gray-200">
                      <div className="flex justify-between items-start mb-1.5">
                        <span className="text-[11px] font-bold text-blue-700 truncate" title={item.doc_a_name}>
                          Document A: {item.doc_a_name}
                        </span>
                        {item.doc_a_page && (
                          <span className="text-[10px] bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-medium">
                            Page {item.doc_a_page}
                          </span>
                        )}
                      </div>
                      <div className="mt-1">
                        <span className="text-[10px] text-gray-400 block font-medium">Extracted Value</span>
                        <p className="text-xs font-mono font-semibold text-gray-900 bg-gray-50 p-2 rounded border border-gray-100">
                          {item.doc_a_value || <span className="text-gray-400 italic">Not extracted</span>}
                        </p>
                      </div>
                    </div>

                    {/* Document B Column */}
                    <div className="bg-white p-3.5 rounded-md border border-gray-200">
                      <div className="flex justify-between items-start mb-1.5">
                        <span className="text-[11px] font-bold text-blue-700 truncate" title={item.doc_b_name}>
                          Document B: {item.doc_b_name}
                        </span>
                        {item.doc_b_page && (
                          <span className="text-[10px] bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-medium">
                            Page {item.doc_b_page}
                          </span>
                        )}
                      </div>
                      <div className="mt-1">
                        <span className="text-[10px] text-gray-400 block font-medium">Extracted Value</span>
                        <p className="text-xs font-mono font-semibold text-gray-900 bg-gray-50 p-2 rounded border border-gray-100">
                          {item.doc_b_value || <span className="text-gray-400 italic">Not extracted</span>}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Discrepancy Explanation Banner */}
                  <div className={`mt-3 p-3 rounded-md text-xs border ${
                    isDiscrepancy
                      ? 'bg-rose-100/60 border-rose-200 text-rose-900 font-medium'
                      : 'bg-emerald-50 border-emerald-200 text-emerald-900'
                  }`}>
                    <span className="font-bold mr-1">Analysis:</span>
                    <span>{item.explanation}</span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
