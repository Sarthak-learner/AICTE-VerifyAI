import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthenticityScreeningView } from './AuthenticityScreeningView'
import * as authenticityApi from '../../api/authenticity'
import type { AuthenticityScreeningResponse } from '../../types'

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: Infinity },
    },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe('AuthenticityScreeningView Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders authenticity screening dashboard with metrics, advisory, and document groups', async () => {
    const mockScreeningData: AuthenticityScreeningResponse = {
      application_id: 'app-1',
      total_checks: 3,
      total_passed: 1,
      total_review_required: 1,
      total_unavailable: 1,
      disclaimer: 'Screening indicators are purely diagnostic markers.',
      message: 'Authenticity screening completed.',
      documents: [
        {
          document_id: 'doc-1',
          document_filename: 'land_title_deed.pdf',
          document_type: 'land_deed_lease',
          pass_count: 1,
          review_count: 1,
          unavailable_count: 1,
          checks: [
            {
              id: 'chk-1',
              application_id: 'app-1',
              document_id: 'doc-1',
              document_filename: 'land_title_deed.pdf',
              document_type: 'land_deed_lease',
              check_type: 'file_integrity',
              check_name: 'File SHA-256 Hash Integrity Check',
              result: 'PASS',
              explanation: 'No indicator detected by this check. Calculated file SHA-256 matches recorded upload hash.',
              evidence: { matched: true, algorithm: 'SHA-256' },
              screening_version: '1.0.0',
              reviewer_status: 'open',
              reviewer_notes: null,
              created_at: '2026-10-22T10:00:00Z',
              updated_at: '2026-10-22T10:00:00Z',
            },
            {
              id: 'chk-2',
              application_id: 'app-1',
              document_id: 'doc-1',
              document_filename: 'land_title_deed.pdf',
              document_type: 'land_deed_lease',
              check_type: 'pdf_metadata',
              check_name: 'PDF Metadata & Timestamp Inspection',
              result: 'REVIEW',
              explanation: 'Metadata timestamp anomaly detected: Modification timestamp precedes creation timestamp.',
              evidence: { modification_date: 'D:20200101', creation_date: 'D:20240101' },
              screening_version: '1.0.0',
              reviewer_status: 'open',
              reviewer_notes: null,
              created_at: '2026-10-22T10:00:00Z',
              updated_at: '2026-10-22T10:00:00Z',
            },
            {
              id: 'chk-3',
              application_id: 'app-1',
              document_id: 'doc-1',
              document_filename: 'land_title_deed.pdf',
              document_type: 'land_deed_lease',
              check_type: 'image_indicators',
              check_name: 'Image Resolution & Encoding Indicators',
              result: 'UNAVAILABLE',
              explanation: 'No raster image streams detected in PDF.',
              evidence: { embedded_images: 0 },
              screening_version: '1.0.0',
              reviewer_status: 'open',
              reviewer_notes: null,
              created_at: '2026-10-22T10:00:00Z',
              updated_at: '2026-10-22T10:00:00Z',
            },
          ],
        },
      ],
      checks: [],
    }

    vi.spyOn(authenticityApi, 'fetchAuthenticityChecks').mockResolvedValue(mockScreeningData)

    renderWithClient(<AuthenticityScreeningView applicationId="app-1" />)

    // Check header & advisory
    expect(await screen.findByText('PHASE 05 SCREENING')).toBeInTheDocument()
    expect(screen.getByText('Document Authenticity Signals & Tamper Indicators')).toBeInTheDocument()
    expect(screen.getByText('Advisory Review Notice')).toBeInTheDocument()

    // Metric counts
    expect(screen.getByText('3')).toBeInTheDocument() // Checks Evaluated
    expect(screen.getAllByText('1').length).toBeGreaterThanOrEqual(3) // 1 pass, 1 review, 1 n/a

    // Document header
    expect(screen.getByText('land_title_deed.pdf')).toBeInTheDocument()

    // Check badges
    expect(screen.getByText('No indicator detected by this check')).toBeInTheDocument()
    expect(screen.getByText('Requires human review')).toBeInTheDocument()
    expect(screen.getByText('Check unavailable / N/A')).toBeInTheDocument()

    // Test evidence expansion
    const toggleEvidenceBtn = screen.getAllByRole('button', { name: /view supporting evidence/i })[0]
    fireEvent.click(toggleEvidenceBtn)
    expect(screen.getByText(/Hide Evidence Details/i)).toBeInTheDocument()

    // Test reviewer action form
    const reviewBtn = screen.getAllByRole('button', { name: /Update Status \/ Add Notes/i })[0]
    fireEvent.click(reviewBtn)

    expect(screen.getByText('Review Status:')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Enter officer assessment/i)).toBeInTheDocument()

    const updateSpy = vi.spyOn(authenticityApi, 'updateAuthenticityCheckStatus').mockResolvedValue({
      ...mockScreeningData.documents[0].checks[0],
      reviewer_status: 'under_review',
      reviewer_notes: 'Inspected by officer',
    })

    const notesInput = screen.getByPlaceholderText(/Enter officer assessment/i)
    fireEvent.change(notesInput, { target: { value: 'Inspected by officer' } })

    const saveBtn = screen.getByRole('button', { name: /Save Assessment/i })
    fireEvent.click(saveBtn)

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        'app-1',
        'chk-1',
        expect.objectContaining({
          reviewer_notes: 'Inspected by officer',
        }),
      )
    })
  })

  it('renders empty state when no checks exist', async () => {
    const mockEmptyData: AuthenticityScreeningResponse = {
      application_id: 'app-empty',
      total_checks: 0,
      total_passed: 0,
      total_review_required: 0,
      total_unavailable: 0,
      disclaimer: 'Advisory notice',
      message: 'No checks',
      documents: [],
      checks: [],
    }

    vi.spyOn(authenticityApi, 'fetchAuthenticityChecks').mockResolvedValue(mockEmptyData)

    renderWithClient(<AuthenticityScreeningView applicationId="app-empty" />)

    expect(await screen.findByText('No Screening Results Available')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Run Screening Now/i })).toBeInTheDocument()
  })
})
