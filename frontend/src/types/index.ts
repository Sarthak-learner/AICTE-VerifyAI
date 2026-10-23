/**
 * Shared TypeScript types mirroring the backend data model.
 * Keep in sync with backend Pydantic schemas.
 */

export type ApplicationStatus =
  | 'draft'
  | 'submitted'
  | 'under_review'
  | 'validation_complete'
  | 'approved'
  | 'rejected'

export type DocumentStatus = 'uploaded' | 'processing' | 'processed' | 'failed'

export type FindingSeverity = 'info' | 'warning' | 'error'
export type FindingStatus =
  | 'open'
  | 'under_review'
  | 'resolved'
  | 'dismissed'
  | 'requires_clarification'

export interface Application {
  id: string
  reference_number: string
  institution_name: string
  aicte_permanent_id?: string | null
  academic_year: string
  application_category: string
  programme_type: string
  description?: string | null
  institution_type?: string | null
  applicant_name: string
  applicant_email: string
  status: ApplicationStatus
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface ApplicationListItem {
  id: string
  reference_number: string
  institution_name: string
  academic_year: string
  application_category: string
  status: ApplicationStatus
  created_at: string
}

export interface ApplicationListResponse {
  total: number
  items: ApplicationListItem[]
}

export interface ApplicationCreatePayload {
  institution_name: string
  aicte_permanent_id?: string
  academic_year: string
  application_category: string
  programme_type: string
  description?: string
  applicant_name: string
  applicant_email: string
}

export interface Document {
  id: string
  application_id: string
  original_filename: string
  document_type?: string | null
  mime_type: string
  file_size_bytes: number
  sha256_hash: string
  page_count?: number | null
  status: DocumentStatus
  is_duplicate: boolean
  duplicate_of_id?: string | null
  created_at: string
}

export interface DocumentListItem {
  id: string
  application_id: string
  original_filename: string
  document_type?: string | null
  mime_type: string
  file_size_bytes: number
  status: DocumentStatus
  is_duplicate: boolean
  created_at: string
}

export interface DocumentListResponse {
  total: number
  items: DocumentListItem[]
}

export interface DuplicateInfo {
  existing_document_id: string
  existing_application_id: string
  message: string
}

export interface UploadResponse {
  document: Document
  duplicate?: DuplicateInfo | null
}

// ── Extraction types ──────────────────────────────────────────────────────────

export interface ExtractedField {
  value: string | null
  raw_match: string | null
  source_page: number | null
  confidence: 'high' | 'low' | 'unknown'
}

export interface ExtractedFields {
  institution_name: ExtractedField
  reference_number: ExtractedField
  issue_date: ExtractedField
  expiry_date: ExtractedField
  land_area: ExtractedField
  programme_name: ExtractedField
  intake_figure: ExtractedField
}

export interface ExtractionResult {
  document_id: string
  status: DocumentStatus
  ocr_text: string | null
  ocr_text_preview: string | null
  extracted_fields: ExtractedFields | null
  page_count: number | null
  warning?: string | null
}

export interface ProcessingStatusResponse {
  document_id: string
  status: DocumentStatus
  message: string
}

// ── Dashboard types ───────────────────────────────────────────────────────────

export interface StatusCount {
  status: string
  count: number
}

export interface CategoryCount {
  category: string
  count: number
}

export interface DashboardStats {
  total_applications: number
  total_documents: number
  processed_documents: number
  applications_by_status: StatusCount[]
  documents_by_status: StatusCount[]
  documents_by_category: CategoryCount[]
}

// ── Validation Findings & Review Types ───────────────────────────────────────

export interface Finding {
  id: string
  application_id: string
  document_id: string | null
  rule_code: string
  rule_name: string
  severity: FindingSeverity
  status: FindingStatus
  title: string
  detail: string | null
  page_number: number | null
  extracted_value: string | null
  expected_value: string | null
  evidence?: Record<string, any> | null
  resolution_note?: string | null
  created_at: string
  updated_at?: string
}

export interface FindingListResponse {
  total: number
  open_count: number
  resolved_count: number
  under_review_count: number
  requires_clarification_count: number
  items: Finding[]
}

export interface FindingUpdatePayload {
  status: FindingStatus
  resolution_note?: string | null
  reviewer_label?: string
}

// ── Cross-Document Consistency Graph Types ──────────────────────────────────

export interface ComparisonItem {
  field: string
  status: 'match' | 'discrepancy'
  doc_a_id: string
  doc_a_name: string
  doc_a_value: string | null
  doc_a_page: number | null
  doc_b_id: string
  doc_b_name: string
  doc_b_value: string | null
  doc_b_page: number | null
  explanation: string
  severity: string
}

export interface GraphNode {
  id: string
  type: 'document' | 'field'
  label: string
  metadata?: Record<string, any>
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  type: 'extracted_from' | 'consistent' | 'discrepancy'
  label?: string
}

export interface ConsistencyGraphResponse {
  application_id: string
  nodes: GraphNode[]
  edges: GraphEdge[]
  comparisons: ComparisonItem[]
  total_matches: number
  total_discrepancies: number
  evaluated_pairs?: number
  has_comparable_fields?: boolean
  explanation?: string | null
  unprocessed_documents?: string[]
}

export interface ValidationRunResponse {
  application_id: string
  total_findings: number
  findings: Finding[]
  consistency_graph: ConsistencyGraphResponse
  message: string
}

// ── Validation Rule Types ───────────────────────────────────────────────────

export interface RuleResponse {
  id?: string
  code: string
  name: string
  description?: string | null
  applies_to_document_type?: string | null
  severity: string
  is_active: boolean
  is_demo: boolean
  parameters?: Record<string, any> | null
}

export interface RuleListResponse {
  total: number
  items: RuleResponse[]
}

// ── Authenticity Screening Types ─────────────────────────────────────────────

export type AuthenticityResult = 'PASS' | 'REVIEW' | 'UNAVAILABLE'

export interface AuthenticityCheck {
  id: string
  application_id: string
  document_id: string
  document_filename?: string | null
  document_type?: string | null
  check_type: string
  check_name: string
  result: AuthenticityResult
  explanation: string
  evidence?: Record<string, any> | null
  screening_version: string
  reviewer_status: FindingStatus
  reviewer_notes?: string | null
  resolved_by_id?: string | null
  created_at: string
  updated_at: string
}

export interface DocumentAuthenticityGroup {
  document_id: string
  document_filename: string
  document_type?: string | null
  checks: AuthenticityCheck[]
  pass_count: number
  review_count: number
  unavailable_count: number
}

export interface AuthenticityScreeningResponse {
  application_id: string
  total_checks: number
  total_passed: number
  total_review_required: number
  total_unavailable: number
  documents: DocumentAuthenticityGroup[]
  checks: AuthenticityCheck[]
  message: string
  disclaimer: string
}

export interface AuthenticityCheckUpdatePayload {
  reviewer_status: FindingStatus
  reviewer_notes?: string
  reviewer_label?: string
}

// ── Audit Trail Types ────────────────────────────────────────────────────────

export interface AuditEvent {
  id: string
  application_id?: string | null
  actor_label?: string | null
  action: string
  resource_type?: string | null
  resource_id?: string | null
  detail?: string | null
  created_at: string
}

export interface AuditTrailResponse {
  total: number
  events: AuditEvent[]
}

