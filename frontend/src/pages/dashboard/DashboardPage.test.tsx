import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DashboardPage from './DashboardPage'
import * as dashboardApi from '../../api/dashboard'

vi.mock('recharts', async () => {
  const original = await vi.importActual<any>('recharts')
  return {
    ...original,
    ResponsiveContainer: ({ children }: any) => <div className="recharts-mock" style={{ width: 600, height: 300 }}>{children}</div>,
  }
})

function renderDashboard() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('DashboardPage Analytics', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders summary cards with real database counts', async () => {
    vi.spyOn(dashboardApi, 'fetchDashboardStats').mockResolvedValue({
      total_applications: 12,
      total_documents: 34,
      processed_documents: 28,
      applications_by_status: [
        { status: 'draft', count: 5 },
        { status: 'submitted', count: 7 },
      ],
      documents_by_status: [
        { status: 'uploaded', count: 4 },
        { status: 'processed', count: 28 },
        { status: 'failed', count: 2 },
      ],
      documents_by_category: [
        { category: 'application_form', count: 12 },
        { category: 'land_deed_lease', count: 10 },
        { category: 'affidavit', count: 12 },
      ],
    })

    renderDashboard()

    expect(await screen.findByText('Institutional Verification Analytics')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument() // Total Applications
    expect(screen.getByText('34')).toBeInTheDocument() // Total Documents
    expect(screen.getByText('28')).toBeInTheDocument() // Processed
    expect(screen.getByText('Applications by Status')).toBeInTheDocument()
    expect(screen.getByText('Documents by Processing Status')).toBeInTheDocument()
    expect(screen.getByText('Document Category Distribution')).toBeInTheDocument()
  })

  it('displays empty state when total applications and documents are zero', async () => {
    vi.spyOn(dashboardApi, 'fetchDashboardStats').mockResolvedValue({
      total_applications: 0,
      total_documents: 0,
      processed_documents: 0,
      applications_by_status: [],
      documents_by_status: [],
      documents_by_category: [],
    })

    renderDashboard()

    expect(await screen.findByText('No Application Data Yet')).toBeInTheDocument()
    expect(screen.getByText(/the database is currently empty/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /create first application/i })).toBeInTheDocument()
  })
})
