import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts'
import { fetchDashboardStats } from '../../api/dashboard'

const STATUS_COLORS: Record<string, string> = {
  draft: '#64748b', // Slate
  submitted: '#0284c7', // Sky
  under_review: '#f59e0b', // Amber
  validation_complete: '#8b5cf6', // Violet
  approved: '#10b981', // Emerald
  rejected: '#f43f5e', // Rose
  uploaded: '#3b82f6', // Blue
  processing: '#f59e0b', // Amber
  processed: '#10b981', // Emerald
  failed: '#ef4444', // Red
}

const CATEGORY_LABELS: Record<string, string> = {
  application_form: 'App Form',
  land_deed_lease: 'Land Deed',
  building_plan: 'Building Plan',
  faculty_list: 'Faculty List',
  affidavit: 'Affidavit',
  noc_certificate: 'NOC / Cert',
  other: 'Other',
}

function formatLabel(str: string): string {
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function DashboardPage() {
  const {
    data: stats,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: fetchDashboardStats,
    refetchInterval: 30000, // Refresh every 30s
  })

  if (isLoading) {
    return (
      <div className="p-16 text-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-3" />
        <p className="text-sm text-gray-500">Loading live analytics dashboard...</p>
      </div>
    )
  }

  if (isError || !stats) {
    return (
      <div className="max-w-2xl mx-auto mt-8 bg-rose-50 border border-rose-200 rounded-lg p-6 text-rose-800">
        <h2 className="text-base font-semibold mb-2">Failed to load dashboard metrics</h2>
        <p className="text-xs text-rose-600 mb-4">
          {error instanceof Error ? error.message : 'Database aggregation query failed.'}
        </p>
        <button
          type="button"
          onClick={() => refetch()}
          className="px-3.5 py-1.5 bg-rose-700 text-white text-xs font-medium rounded hover:bg-rose-800 transition-colors"
        >
          Retry Loading
        </button>
      </div>
    )
  }

  const hasData = stats.total_applications > 0 || stats.total_documents > 0

  // Format chart data
  const applicationStatusData = stats.applications_by_status.map((item) => ({
    name: formatLabel(item.status),
    status: item.status,
    count: item.count,
  }))

  const documentStatusData = stats.documents_by_status.map((item) => ({
    name: formatLabel(item.status),
    status: item.status,
    count: item.count,
  }))

  const documentCategoryData = stats.documents_by_category.map((item) => ({
    name: CATEGORY_LABELS[item.category] || formatLabel(item.category),
    fullCategory: formatLabel(item.category),
    count: item.count,
  }))

  // Filter non-zero for Pie chart
  const activeAppStatusData = applicationStatusData.filter((d) => d.count > 0)

  return (
    <div className="space-y-8">
      {/* Page Title & Refresh */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
            Institutional Verification Analytics
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            Real-time persisted database metrics on approval applications, ingested documents, and OCR extraction.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/applications/new"
            className="inline-flex items-center px-3.5 py-1.5 bg-blue-700 text-white text-xs font-semibold rounded-md shadow-sm hover:bg-blue-800 transition-colors"
          >
            + New Application
          </Link>
          <button
            type="button"
            onClick={() => refetch()}
            className="inline-flex items-center px-3 py-1.5 border border-gray-300 bg-white text-gray-700 text-xs font-medium rounded-md hover:bg-gray-50 transition-colors shadow-sm"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Evaluator Guided Demo Scenarios Banner */}

      <div className="bg-gradient-to-r from-slate-900 via-blue-950 to-indigo-950 rounded-xl p-5 text-white shadow-md border border-blue-900/60">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-blue-800/60 pb-3 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="bg-amber-400 text-slate-950 text-[10px] font-black uppercase px-2 py-0.5 rounded tracking-wider">
                Hackathon Showcase
              </span>
              <h2 className="text-sm sm:text-base font-bold text-white tracking-wide">
                Interactive Evaluator Demonstration Scenarios
              </h2>
            </div>
            <p className="text-xs text-blue-200 mt-1">
              Select a pre-loaded synthetic regulatory scenario to inspect automated consistency checking, security screening, and reviewer workflows:
            </p>
          </div>
          <span className="text-[11px] text-blue-300 font-mono bg-blue-900/40 px-2.5 py-1 rounded border border-blue-700/50 self-start sm:self-auto">
            Advisory Prototype • Synthetic Demo Data
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Scenario A: Cross-Document Consistency Graph */}
          <div className="bg-white/10 hover:bg-white/15 border border-white/20 rounded-lg p-4 transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[11px] font-bold text-amber-300 uppercase tracking-wider">
                  Scenario A • Consistency Graph
                </span>
                <span className="text-[10px] font-mono bg-blue-800/80 px-2 py-0.5 rounded text-white">
                  APP-2026-1CF169
                </span>
              </div>
              <h3 className="text-sm font-bold text-white mb-1">
                Demo Institute of Technology
              </h3>
              <p className="text-xs text-blue-100 leading-relaxed mb-3">
                Evaluates 2 uploaded PDFs (Land Deed & Building Plan) with extracted fields. Evaluates 4 comparisons, confirming 2 matches and flagging 2 critical discrepancies: <strong>Land Area (5.0 vs 2.5 acres)</strong> and <strong>Ref Number mismatch</strong>.
              </p>
            </div>
            <Link
              to="/applications/41dc21c3e2824e799f8fb8cef025ae9e"
              className="inline-flex items-center justify-center gap-2 px-3.5 py-2 bg-amber-400 hover:bg-amber-300 text-slate-950 text-xs font-bold rounded shadow transition-colors"
            >
              <span>Launch Consistency Graph Demo</span>
              <span>&rarr;</span>
            </Link>
          </div>

          {/* Scenario B: Deterministic Authenticity Screening */}
          <div className="bg-white/10 hover:bg-white/15 border border-white/20 rounded-lg p-4 transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[11px] font-bold text-indigo-300 uppercase tracking-wider">
                  Scenario B • Authenticity & Limitations
                </span>
                <span className="text-[10px] font-mono bg-blue-800/80 px-2 py-0.5 rounded text-white">
                  APP-2026-CDC390
                </span>
              </div>
              <h3 className="text-sm font-bold text-white mb-1">
                MIT academy of engineering [DEMO]
              </h3>
              <p className="text-xs text-blue-100 leading-relaxed mb-3">
                Runs 18 deterministic checks across 3 scanned documents. Demonstrates SHA-256 hash integrity, low-resolution image flags, and the explicit deferred OCR advisory banner.
              </p>
            </div>
            <Link
              to="/applications/0754aec6-740a-4e73-b634-badda51b9834"
              className="inline-flex items-center justify-center gap-2 px-3.5 py-2 bg-indigo-500 hover:bg-indigo-400 text-white text-xs font-bold rounded shadow transition-colors"
            >
              <span>Inspect Authenticity & Audit Trail</span>
              <span>&rarr;</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">

        <div className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-gray-500 tracking-wider">
              Total Applications
            </span>
            <span className="p-2 bg-blue-50 text-blue-700 rounded-md text-xs font-bold">
              Apps
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-gray-900" id="stat-total-applications">
              {stats.total_applications}
            </span>
            <span className="text-xs text-gray-400">records in DB</span>
          </div>
          <Link
            to="/applications"
            className="mt-3 block text-xs text-blue-700 hover:text-blue-900 font-medium"
          >
            View all applications &rarr;
          </Link>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-gray-500 tracking-wider">
              Total Documents
            </span>
            <span className="p-2 bg-indigo-50 text-indigo-700 rounded-md text-xs font-bold">
              Docs
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-gray-900" id="stat-total-documents">
              {stats.total_documents}
            </span>
            <span className="text-xs text-gray-400">stored securely</span>
          </div>
          <span className="mt-3 block text-xs text-gray-500">
            Across {stats.documents_by_category.length} registered categories
          </span>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-gray-500 tracking-wider">
              OCR Processed
            </span>
            <span className="p-2 bg-emerald-50 text-emerald-700 rounded-md text-xs font-bold">
              OCR
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-emerald-700" id="stat-processed-documents">
              {stats.processed_documents}
            </span>
            <span className="text-xs text-gray-400">
              of {stats.total_documents} ({stats.total_documents > 0 ? Math.round((stats.processed_documents / stats.total_documents) * 100) : 0}%)
            </span>
          </div>
          <span className="mt-3 block text-xs text-gray-500">
            Deterministic extraction completed
          </span>
        </div>
      </div>

      {/* Empty State Banner if no records exist */}
      {!hasData ? (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center shadow-sm">
          <div className="mx-auto w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center text-gray-400 mb-4">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h2 className="text-base font-bold text-gray-800">No Application Data Yet</h2>
          <p className="text-xs text-gray-500 max-w-md mx-auto mt-1 mb-5">
            The database is currently empty. Submit an institutional application and upload supporting documents to populate analytics charts.
          </p>
          <Link
            to="/applications/new"
            className="inline-flex items-center px-4 py-2 bg-blue-700 text-white text-xs font-semibold rounded-md shadow hover:bg-blue-800 transition-colors"
          >
            Create First Application
          </Link>
        </div>
      ) : (
        /* Visual Analytics Grid */
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Chart 1: Applications by Status */}
          <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-bold text-gray-900">Applications by Status</h2>
                <p className="text-[11px] text-gray-500">
                  Distribution of institutional applications by lifecycle stage
                </p>
              </div>
            </div>

            <div className="h-64 w-full">
              {activeAppStatusData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={applicationStatusData} margin={{ top: 10, right: 10, left: -20, bottom: 25 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis
                      dataKey="name"
                      tick={{ fontSize: 10, fill: '#64748b' }}
                      angle={-20}
                      textAnchor="end"
                      interval={0}
                    />
                    <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: '#64748b' }} />
                    <Tooltip
                      formatter={(val: any) => [`${val ?? 0} application(s)`, 'Count']}
                      contentStyle={{ fontSize: '12px', borderRadius: '6px' }}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {applicationStatusData.map((entry) => (
                        <Cell
                          key={`cell-${entry.status}`}
                          fill={STATUS_COLORS[entry.status] || '#3b82f6'}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-xs text-gray-400 italic">
                  No active application records.
                </div>
              )}
            </div>
          </div>

          {/* Chart 2: Documents by Processing Status */}
          <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-bold text-gray-900">Documents by Processing Status</h2>
                <p className="text-[11px] text-gray-500">
                  OCR ingestion pipeline status (pending, processing, processed, failed)
                </p>
              </div>
            </div>

            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={documentStatusData} margin={{ top: 10, right: 10, left: -20, bottom: 25 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 10, fill: '#64748b' }}
                    angle={-20}
                    textAnchor="end"
                    interval={0}
                  />
                  <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: '#64748b' }} />
                  <Tooltip
                    formatter={(val: any) => [`${val ?? 0} document(s)`, 'Count']}
                    contentStyle={{ fontSize: '12px', borderRadius: '6px' }}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {documentStatusData.map((entry) => (
                      <Cell
                        key={`cell-doc-${entry.status}`}
                        fill={STATUS_COLORS[entry.status] || '#3b82f6'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 3: Document Category Distribution */}
          <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-bold text-gray-900">Document Category Distribution</h2>
                <p className="text-[11px] text-gray-500">
                  Number of uploaded files classified by regulatory document type
                </p>
              </div>
            </div>

            <div className="h-64 w-full">
              {stats.total_documents > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={documentCategoryData} margin={{ top: 10, right: 20, left: -10, bottom: 25 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis
                      dataKey="name"
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      angle={-15}
                      textAnchor="end"
                      interval={0}
                    />
                    <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: '#64748b' }} />
                    <Tooltip
                      formatter={(val: any, _name: any, props: any) => [
                        `${val ?? 0} file(s)`,
                        props?.payload?.fullCategory || 'Category',
                      ]}
                      contentStyle={{ fontSize: '12px', borderRadius: '6px' }}
                    />
                    <Bar dataKey="count" fill="#4f46e5" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-xs text-gray-400 italic">
                  No documents uploaded yet to classify.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
