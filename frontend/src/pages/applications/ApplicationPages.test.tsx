import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ApplicationListPage from './ApplicationListPage'
import ApplicationCreatePage from './ApplicationCreatePage'
import ApplicationDetailPage from './ApplicationDetailPage'
import * as appApi from '../../api/applications'

function renderWithClient(ui: React.ReactElement, initialRoute = '/') {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialRoute]}>
        {ui}
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Application Pages', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders application list page with applications and filters them', async () => {
    vi.spyOn(appApi, 'fetchApplications').mockResolvedValue({
      total: 2,
      items: [
        {
          id: 'app-1',
          reference_number: 'AICTE-2025-APP01',
          institution_name: 'Alpha Engineering College',
          academic_year: '2025-26',
          application_category: 'new_programme',
          status: 'draft',
          created_at: new Date().toISOString(),
        },
        {
          id: 'app-2',
          reference_number: 'AICTE-2025-APP02',
          institution_name: 'Beta Polytechnic',
          academic_year: '2025-26',
          application_category: 'extension_of_approval',
          status: 'submitted',
          created_at: new Date().toISOString(),
        },
      ],
    })

    renderWithClient(<ApplicationListPage />, '/applications')

    expect(await screen.findByText('Alpha Engineering College')).toBeInTheDocument()
    expect(screen.getByText('Beta Polytechnic')).toBeInTheDocument()

    // Test filter search
    const searchInput = screen.getByPlaceholderText(/search by reference/i)
    fireEvent.change(searchInput, { target: { value: 'Alpha' } })

    expect(screen.getByText('Alpha Engineering College')).toBeInTheDocument()
    expect(screen.queryByText('Beta Polytechnic')).not.toBeInTheDocument()
  })

  it('validates required fields on ApplicationCreatePage', async () => {
    renderWithClient(<ApplicationCreatePage />, '/applications/new')

    const submitBtn = screen.getByRole('button', { name: /create application/i })
    fireEvent.click(submitBtn)

    expect(await screen.findByText('Institution name is required.')).toBeInTheDocument()
    expect(screen.getByText('Applicant name is required.')).toBeInTheDocument()
    expect(screen.getByText('Applicant email is required.')).toBeInTheDocument()
  })

  it('renders ApplicationDetailPage with application details and document list', async () => {
    vi.spyOn(appApi, 'fetchApplication').mockResolvedValue({
      id: 'app-100',
      reference_number: 'AICTE-2025-APP100',
      institution_name: 'Government Engineering College',
      aicte_permanent_id: 'DEMO-100',
      academic_year: '2025-26',
      application_category: 'new_programme',
      programme_type: 'BE_BTech',
      description: 'Test application for new IT branch',
      applicant_name: 'Prof. Sharma',
      applicant_email: 'sharma@gec.edu',
      status: 'draft',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })

    vi.spyOn(appApi, 'fetchApplicationDocuments').mockResolvedValue({
      total: 1,
      items: [
        {
          id: 'doc-1',
          application_id: 'app-100',
          original_filename: 'land_affidavit.pdf',
          document_type: 'affidavit',
          mime_type: 'application/pdf',
          file_size_bytes: 1048576,
          status: 'uploaded',
          is_duplicate: false,
          created_at: new Date().toISOString(),
        },
      ],
    })

    renderWithClient(
      <Routes>
        <Route path="/applications/:id" element={<ApplicationDetailPage />} />
      </Routes>,
      '/applications/app-100',
    )

    expect(await screen.findByText('Government Engineering College')).toBeInTheDocument()
    expect(screen.getAllByText('AICTE-2025-APP100').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('land_affidavit.pdf')).toBeInTheDocument()
    expect(screen.getByText('1 MB')).toBeInTheDocument()
    expect(screen.getByText(/Inspect \/ Process/i)).toBeInTheDocument()
  })

  it('expands document extraction card to show extracted fields and OCR text', async () => {
    vi.spyOn(appApi, 'fetchApplication').mockResolvedValue({
      id: 'app-200',
      reference_number: 'AICTE-2025-APP200',
      institution_name: 'National Tech Institute',
      academic_year: '2025-26',
      application_category: 'new_programme',
      programme_type: 'BE_BTech',
      applicant_name: 'Dr. Rao',
      applicant_email: 'rao@nti.edu',
      status: 'submitted',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })

    vi.spyOn(appApi, 'fetchApplicationDocuments').mockResolvedValue({
      total: 1,
      items: [
        {
          id: 'doc-200',
          application_id: 'app-200',
          original_filename: 'approval_order.pdf',
          document_type: 'noc_certificate',
          mime_type: 'application/pdf',
          file_size_bytes: 524288,
          status: 'processed',
          is_duplicate: false,
          created_at: new Date().toISOString(),
        },
      ],
    })

    const processingApi = await import('../../api/processing')
    vi.spyOn(processingApi, 'fetchExtraction').mockResolvedValue({
      document_id: 'doc-200',
      status: 'processed',
      ocr_text: 'Institution Name: National Tech Institute\nRef: F.No. AICTE-2025-NTI\nApproved Intake: 120 seats',
      ocr_text_preview: 'Institution Name: National Tech Institute...',
      page_count: 1,
      extracted_fields: {
        institution_name: {
          value: 'National Tech Institute',
          raw_match: 'National Tech Institute',
          source_page: 1,
          confidence: 'high',
        },
        reference_number: {
          value: 'AICTE-2025-NTI',
          raw_match: 'F.No. AICTE-2025-NTI',
          source_page: 1,
          confidence: 'high',
        },
        issue_date: { value: null, raw_match: null, source_page: null, confidence: 'unknown' },
        expiry_date: { value: null, raw_match: null, source_page: null, confidence: 'unknown' },
        land_area: { value: null, raw_match: null, source_page: null, confidence: 'unknown' },
        programme_name: { value: null, raw_match: null, source_page: null, confidence: 'unknown' },
        intake_figure: {
          value: '120',
          raw_match: '120 seats',
          source_page: 1,
          confidence: 'high',
        },
      },
    })

    renderWithClient(
      <Routes>
        <Route path="/applications/:id" element={<ApplicationDetailPage />} />
      </Routes>,
      '/applications/app-200',
    )

    const viewFieldsBtn = await screen.findByRole('button', { name: /view extracted fields/i })
    expect(viewFieldsBtn).toBeInTheDocument()

    // Expand the card
    fireEvent.click(viewFieldsBtn)

    // Verify extraction card contents
    expect(await screen.findByText(/Structured Field Discoveries/i)).toBeInTheDocument()
    expect(screen.getAllByText('National Tech Institute').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('AICTE-2025-NTI')).toBeInTheDocument()
    expect(screen.getByText('120')).toBeInTheDocument()
    expect(screen.getByText(/OCR Extracted Text/i)).toBeInTheDocument()
    expect(screen.getByText(/Advisory Notice/i)).toBeInTheDocument()
  })
})
