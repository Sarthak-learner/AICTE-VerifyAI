import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchApplications } from '../../api/applications'
import type { ApplicationListItem } from '../../types'

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700 border-gray-300',
    submitted: 'bg-blue-50 text-blue-700 border-blue-200',
    under_review: 'bg-amber-50 text-amber-700 border-amber-200',
    validation_complete: 'bg-purple-50 text-purple-700 border-purple-200',
    approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    rejected: 'bg-rose-50 text-rose-700 border-rose-200',
  }
  const formatted = status.replace(/_/g, ' ').toUpperCase()
  return (
    <span
      className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
        styles[status] || 'bg-gray-100 text-gray-700 border-gray-300'
      }`}
    >
      {formatted}
    </span>
  )
}

export default function ApplicationListPage() {
  const [search, setSearch] = useState('')

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['applications'],
    queryFn: () => fetchApplications(0, 100),
  })

  const filteredItems = (data?.items || []).filter((app: ApplicationListItem) => {
    if (!search.trim()) return true
    const term = search.toLowerCase()
    return (
      app.reference_number.toLowerCase().includes(term) ||
      app.institution_name.toLowerCase().includes(term) ||
      app.academic_year.toLowerCase().includes(term) ||
      app.application_category.toLowerCase().includes(term)
    )
  })

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-gray-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">
            Institutional Applications
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage institutional approval applications and preliminary verification status.
          </p>
        </div>
        <div>
          <Link
            to="/applications/new"
            id="btn-create-application"
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-700 hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
          >
            <svg
              className="-ml-1 mr-2 h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
            </svg>
            New Application
          </Link>
        </div>
      </div>

      {/* Evaluator Showcase Callout */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="bg-blue-700 text-white font-bold text-[10px] uppercase px-2 py-0.5 rounded tracking-wider">
              Evaluator Guide
            </span>
            <span className="font-bold text-gray-900 text-sm">Key Demonstration Applications</span>
          </div>
          <p className="text-gray-600">
            <strong>Demo Institute of Technology</strong> highlights cross-document discrepancy detection (5 vs 2.5 acres); <strong>MIT Academy</strong> highlights deterministic authenticity screening & deferred OCR advisories.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <Link
            to="/applications/41dc21c3e2824e799f8fb8cef025ae9e"
            className="px-3 py-1.5 bg-blue-700 hover:bg-blue-800 text-white font-semibold rounded shadow-sm transition-colors text-xs"
          >
            Open Scenario A &rarr;
          </Link>
          <Link
            to="/applications/0754aec6-740a-4e73-b634-badda51b9834"
            className="px-3 py-1.5 bg-indigo-700 hover:bg-indigo-800 text-white font-semibold rounded shadow-sm transition-colors text-xs"
          >
            Open Scenario B &rarr;
          </Link>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm flex items-center justify-between gap-4">

        <div className="relative flex-1 max-w-md">
          <input
            type="text"
            id="input-search-applications"
            placeholder="Search by reference #, institution name, or year..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
          />
          <svg
            className="absolute left-3 top-2.5 h-4 w-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <div className="text-xs text-gray-500">
          Showing {filteredItems.length} {filteredItems.length === 1 ? 'application' : 'applications'}
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="bg-white p-12 text-center rounded-lg border border-gray-200 shadow-sm">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-3" />
          <p className="text-sm text-gray-500">Loading applications...</p>
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div className="bg-rose-50 border border-rose-200 rounded-lg p-5 text-rose-800">
          <h3 className="text-sm font-semibold mb-1">Failed to load applications</h3>
          <p className="text-xs text-rose-600 mb-3">
            {error instanceof Error ? error.message : 'A server error occurred while retrieving data.'}
          </p>
          <button
            onClick={() => refetch()}
            className="px-3 py-1.5 bg-rose-600 text-white text-xs font-medium rounded hover:bg-rose-700 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Table view */}
      {!isLoading && !isError && (
        <div className="bg-white shadow-sm border border-gray-200 rounded-lg overflow-hidden">
          {filteredItems.length === 0 ? (
            <div className="p-12 text-center">
              <svg
                className="mx-auto h-12 w-12 text-gray-400 mb-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 className="text-sm font-medium text-gray-900 mb-1">
                {search ? 'No matching applications found' : 'No applications submitted yet'}
              </h3>
              <p className="text-xs text-gray-500 mb-4">
                {search ? 'Try adjusting your search criteria.' : 'Create a new institutional approval application to begin.'}
              </p>
              {!search && (
                <Link
                  to="/applications/new"
                  className="inline-flex items-center px-3.5 py-1.5 border border-transparent text-xs font-medium rounded shadow-sm text-white bg-blue-600 hover:bg-blue-700"
                >
                  Create Application
                </Link>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
                <thead className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500">
                  <tr>
                    <th scope="col" className="px-6 py-3 font-semibold">Reference #</th>
                    <th scope="col" className="px-6 py-3 font-semibold">Institution Name</th>
                    <th scope="col" className="px-6 py-3 font-semibold">Academic Year</th>
                    <th scope="col" className="px-6 py-3 font-semibold">Category</th>
                    <th scope="col" className="px-6 py-3 font-semibold">Status</th>
                    <th scope="col" className="px-6 py-3 font-semibold">Created Date</th>
                    <th scope="col" className="px-6 py-3 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {filteredItems.map((app: ApplicationListItem) => (
                    <tr key={app.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 font-mono font-medium text-blue-700 whitespace-nowrap">
                        <Link to={`/applications/${app.id}`} className="hover:underline">
                          {app.reference_number}
                        </Link>
                      </td>
                      <td className="px-6 py-4 font-medium text-gray-900">
                        {app.institution_name}
                      </td>
                      <td className="px-6 py-4 text-gray-600 whitespace-nowrap">
                        {app.academic_year}
                      </td>
                      <td className="px-6 py-4 text-gray-600 whitespace-nowrap capitalize">
                        {app.application_category.replace(/_/g, ' ')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <StatusBadge status={app.status} />
                      </td>
                      <td className="px-6 py-4 text-gray-500 whitespace-nowrap text-xs">
                        {new Date(app.created_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <Link
                          to={`/applications/${app.id}`}
                          className="inline-flex items-center text-xs font-semibold text-blue-600 hover:text-blue-900"
                        >
                          View Details &rarr;
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
