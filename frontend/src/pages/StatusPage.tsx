import { useQuery } from '@tanstack/react-query'
import { fetchHealth, type HealthResponse } from '../api/health'

function StatusBadge({ value }: { value: string }) {
  const colour = value === 'ok' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${colour}`}>
      {value.toUpperCase()}
    </span>
  )
}

export default function StatusPage() {
  const { data, isLoading, isError } = useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
  })

  return (
    <div className="max-w-lg mx-auto mt-10">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">System Status</h1>

      {isLoading && <p className="text-gray-500">Checking backend…</p>}

      {isError && (
        <div className="bg-red-50 border border-red-200 rounded p-4 text-red-700">
          Cannot reach the backend API. Ensure the FastAPI server is running on port 8000.
        </div>
      )}

      {data && (
        <div className="bg-white border rounded-lg shadow-sm p-6 space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-gray-600">API Status</span>
            <StatusBadge value={data.status} />
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-gray-600">Database</span>
            <StatusBadge value={data.database} />
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-gray-600">Version</span>
            <span className="text-sm text-gray-800">{data.version}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-gray-600">Environment</span>
            <span className="text-sm text-gray-800">{data.environment}</span>
          </div>
          <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-700">
            {data.disclaimer}
          </div>
        </div>
      )}
    </div>
  )
}
