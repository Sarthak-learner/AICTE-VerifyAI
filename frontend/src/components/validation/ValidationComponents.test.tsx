import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ValidationFindingsList from './ValidationFindingsList'
import ConsistencyGraphView from './ConsistencyGraphView'
import * as validationApi from '../../api/validation'
import type { Finding, ConsistencyGraphResponse } from '../../types'

function renderWithClient(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        {ui}
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ValidationFindingsList Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders validation findings with severity, evidence, and reviewer controls', async () => {
    const mockFindings: Finding[] = [
      {
        id: 'finding-1',
        application_id: 'app-1',
        document_id: 'doc-1',
        rule_code: 'REQ_INSTITUTION_NAME',
        rule_name: 'Institution Name Presence Check',
        severity: 'warning',
        status: 'open',
        title: "Institution name not detected in 'affidavit.pdf'",
        detail: 'No institutional header detected by OCR.',
        page_number: 1,
        extracted_value: null,
        expected_value: 'Institution header block',
        evidence: { field: 'institution_name', document_filename: 'affidavit.pdf' },
        created_at: new Date().toISOString(),
      },
      {
        id: 'finding-2',
        application_id: 'app-1',
        document_id: null,
        rule_code: 'CROSS_LAND_AREA_CHECK',
        rule_name: 'Cross-Document Land Area Consistency',
        severity: 'warning',
        status: 'under_review',
        title: "Land area discrepancy between 'deed.pdf' and 'building.pdf'",
        detail: "Area '10 acres' contradicts '2.5 acres'.",
        page_number: null,
        extracted_value: 'Doc A: 10 acres | Doc B: 2.5 acres',
        expected_value: 'Consistent land area',
        resolution_note: 'Requesting clarification from institution.',
        created_at: new Date().toISOString(),
      },
    ]

    vi.spyOn(validationApi, 'fetchFindings').mockResolvedValue({
      total: 2,
      open_count: 1,
      under_review_count: 1,
      resolved_count: 0,
      requires_clarification_count: 0,
      items: mockFindings,
    })

    renderWithClient(<ValidationFindingsList applicationId="app-1" />)

    expect(await screen.findByText(/Institution name not detected/i)).toBeInTheDocument()
    expect(screen.getByText(/Land area discrepancy/i)).toBeInTheDocument()
    expect(screen.getByText('2 Total')).toBeInTheDocument()
    expect(screen.getByText('1 Open')).toBeInTheDocument()

    // Test expanding reviewer controls
    const reviewBtns = screen.getAllByRole('button', { name: /review \/ action/i })
    fireEvent.click(reviewBtns[0])

    expect(screen.getByText(/Authorized Officer Review & Action/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /save review action/i })).toBeInTheDocument()
  })
})

describe('ConsistencyGraphView Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders cross-document consistency graph topology and side-by-side comparison cards', async () => {
    const mockGraph: ConsistencyGraphResponse = {
      application_id: 'app-1',
      total_matches: 1,
      total_discrepancies: 1,
      nodes: [
        {
          id: 'doc:1',
          type: 'document',
          label: 'land_deed.pdf',
          metadata: { category: 'land_deed_lease', mime_type: 'application/pdf', status: 'processed' },
        },
        {
          id: 'doc:2',
          type: 'document',
          label: 'building_plan.pdf',
          metadata: { category: 'building_plan', mime_type: 'application/pdf', status: 'processed' },
        },
        {
          id: 'field:1:land_area',
          type: 'field',
          label: 'Land Area: 5 acres',
        },
      ],
      edges: [
        { id: 'e1', source: 'doc:1', target: 'field:1:land_area', type: 'extracted_from' },
      ],
      comparisons: [
        {
          field: 'land_area',
          status: 'discrepancy',
          doc_a_id: 'doc:1',
          doc_a_name: 'land_deed.pdf',
          doc_a_value: '5 acres',
          doc_a_page: 1,
          doc_b_id: 'doc:2',
          doc_b_name: 'building_plan.pdf',
          doc_b_value: '2 acres',
          doc_b_page: 2,
          explanation: "Extracted area '5 acres' contradicts '2 acres'.",
          severity: 'warning',
        },
        {
          field: 'institution_name',
          status: 'match',
          doc_a_id: 'doc:1',
          doc_a_name: 'land_deed.pdf',
          doc_a_value: 'Apex Institute',
          doc_a_page: 1,
          doc_b_id: 'doc:2',
          doc_b_name: 'building_plan.pdf',
          doc_b_value: 'Apex Institute',
          doc_b_page: 1,
          explanation: 'Institution names match across both documents.',
          severity: 'info',
        },
      ],
    }

    vi.spyOn(validationApi, 'fetchConsistencyGraph').mockResolvedValue(mockGraph)

    renderWithClient(<ConsistencyGraphView applicationId="app-1" />)

    expect(await screen.findByText('FLAGSHIP ANALYSIS')).toBeInTheDocument()
    expect(screen.getByText('Cross-Document Consistency Graph')).toBeInTheDocument()

    // Metric numbers
    expect(screen.getByText('2')).toBeInTheDocument() // Documents Analyzed
    expect(screen.getAllByText('1').length).toBeGreaterThanOrEqual(2) // 1 Match, 1 Discrepancy

    // Side-by-side comparison cards
    expect(screen.getByText('DISCREPANCY DETECTED')).toBeInTheDocument()
    expect(screen.getByText('CONSISTENT MATCH')).toBeInTheDocument()
    expect(screen.getAllByText(/5 acres/i).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/2 acres/i).length).toBeGreaterThanOrEqual(1)

    // Test filtering by Discrepancies
    const discBtn = screen.getByRole('button', { name: /discrepancies \(1\)/i })
    fireEvent.click(discBtn)

    expect(screen.getByText('DISCREPANCY DETECTED')).toBeInTheDocument()
    expect(screen.queryByText('CONSISTENT MATCH')).not.toBeInTheDocument()
  })

  it('renders clear explanation banner when no comparable fields exist across documents', async () => {
    const emptyGraph: ConsistencyGraphResponse = {
      application_id: 'app-2',
      total_matches: 0,
      total_discrepancies: 0,
      nodes: [
        {
          id: 'doc:1',
          type: 'document',
          label: 'raw1.png',
          metadata: { category: 'application_form', mime_type: 'image/png', status: 'uploaded' },
        },
        {
          id: 'doc:2',
          type: 'document',
          label: 'raw2.png',
          metadata: { category: 'affidavit', mime_type: 'image/png', status: 'uploaded' },
        },
      ],
      edges: [],
      comparisons: [],
      evaluated_pairs: 0,
      has_comparable_fields: false,
      explanation:
        'No comparable extracted fields available. 2 document(s) have not undergone OCR and field extraction (raw1.png, raw2.png).',
      unprocessed_documents: ['raw1.png', 'raw2.png'],
    }

    vi.spyOn(validationApi, 'fetchConsistencyGraph').mockResolvedValue(emptyGraph)

    renderWithClient(<ConsistencyGraphView applicationId="app-2" />)

    expect(await screen.findByText('No Comparable Extracted Fields Available')).toBeInTheDocument()
    expect(
      screen.getAllByText(/2 document\(s\) have not undergone OCR and field extraction/i).length,
    ).toBeGreaterThanOrEqual(1)
    expect(
      screen.getByText(/Zero discrepancies does not indicate verified consistency/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText('0 Evaluated Pairs — No overlapping extracted fields across documents'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('No cross-document comparisons available to display'),
    ).toBeInTheDocument()
  })

  it('renders error state on API failure', async () => {
    vi.spyOn(validationApi, 'fetchConsistencyGraph').mockRejectedValue(
      new Error('Network error: 500 Internal Server Error'),
    )

    renderWithClient(<ConsistencyGraphView applicationId="app-3" />)

    expect(
      await screen.findByText(/Failed to load consistency graph: Network error/i),
    ).toBeInTheDocument()
  })
})

