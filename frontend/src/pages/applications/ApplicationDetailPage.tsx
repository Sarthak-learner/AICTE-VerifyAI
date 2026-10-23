import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchApplication, fetchApplicationDocuments } from '../../api/applications'
import { uploadDocument } from '../../api/documents'
import { triggerValidation } from '../../api/validation'
import { fetchAuthenticityChecks } from '../../api/authenticity'
import type { DocumentListItem, DuplicateInfo } from '../../types'
import DocumentExtractionCard from '../../components/documents/DocumentExtractionCard'
import ValidationFindingsList from '../../components/validation/ValidationFindingsList'
import ConsistencyGraphView from '../../components/validation/ConsistencyGraphView'
import { AuthenticityScreeningView } from '../../components/authenticity/AuthenticityScreeningView'
import AuditTrailView from '../../components/audit/AuditTrailView'
import { useAuth } from '../../context/AuthContext'

const SUPPORTED_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif']
const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024 // 50 MB

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700 border-gray-300',
    submitted: 'bg-blue-50 text-blue-700 border-blue-200',
    under_review: 'bg-amber-50 text-amber-700 border-amber-200',
    validation_complete: 'bg-purple-50 text-purple-700 border-purple-200',
    approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    rejected: 'bg-rose-50 text-rose-700 border-rose-200',
    uploaded: 'bg-blue-50 text-blue-700 border-blue-200',
    processing: 'bg-amber-50 text-amber-700 border-amber-200',
    processed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    failed: 'bg-rose-50 text-rose-700 border-rose-200',
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

export default function ApplicationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const { role } = useAuth()
  const isViewer = role === 'viewer'

  // Tab navigation state
  const [activeTab, setActiveTab] = useState<'documents' | 'findings' | 'graph' | 'authenticity' | 'audit'>('documents')


  // Expanded Document State for OCR/Extraction Inspection
  const [expandedDocId, setExpandedDocId] = useState<string | null>(null)

  // Validation Status Banner State
  const [validationBanner, setValidationBanner] = useState<{
    type: 'success' | 'error'
    message: string
  } | null>(null)

  // Upload Form State
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [category, setCategory] = useState<string>('application_form')
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [duplicateAlert, setDuplicateAlert] = useState<DuplicateInfo | null>(null)
  const [uploadSuccessMessage, setUploadSuccessMessage] = useState<string | null>(null)

  // Validation Mutation
  const validateMutation = useMutation({
    mutationFn: () => triggerValidation(id!),
    onSuccess: (res) => {
      setValidationBanner({
        type: 'success',
        message: res.message,
      })
      queryClient.invalidateQueries({ queryKey: ['application-findings', id] })
      queryClient.invalidateQueries({ queryKey: ['consistency-graph', id] })
      queryClient.invalidateQueries({ queryKey: ['application', id] })
      // Auto-switch to findings or graph if discrepancies found
      if (res.consistency_graph.total_discrepancies > 0) {
        setActiveTab('graph')
      } else if (res.total_findings > 0) {
        setActiveTab('findings')
      }
    },
    onError: (err: any) => {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to execute validation rules. Please check backend logs.'
      setValidationBanner({
        type: 'error',
        message: typeof msg === 'string' ? msg : JSON.stringify(msg),
      })
    },
  })

  // Query Application Details
  const {
    data: application,
    isLoading: isAppLoading,
    isError: isAppError,
    error: appError,
  } = useQuery({
    queryKey: ['application', id],
    queryFn: () => fetchApplication(id!),
    enabled: Boolean(id),
  })

  // Query Application Documents
  const {
    data: documentsData,
    isLoading: isDocsLoading,
    isError: isDocsError,
    error: docsError,
  } = useQuery({
    queryKey: ['application-documents', id],
    queryFn: () => fetchApplicationDocuments(id!),
    enabled: Boolean(id),
  })

  // Query Authenticity Checks
  const { data: authenticityData } = useQuery({
    queryKey: ['authenticity-checks', id],
    queryFn: () => fetchAuthenticityChecks(id!),
    enabled: Boolean(id),
  })

  // Upload Mutation
  const uploadMutation = useMutation({
    mutationFn: ({ file, docCategory }: { file: File; docCategory: string }) =>
      uploadDocument(id!, file, docCategory),
    onSuccess: (data) => {
      setSelectedFile(null)
      setUploadError(null)
      // Reset file input element
      const fileInput = document.getElementById('document-file-input') as HTMLInputElement
      if (fileInput) fileInput.value = ''

      if (data.duplicate) {
        setDuplicateAlert(data.duplicate)
        setUploadSuccessMessage(
          `Document "${data.document.original_filename}" ingested, but flagged as identical to an existing document.`,
        )
      } else {
        setDuplicateAlert(null)
        setUploadSuccessMessage(
          `Document "${data.document.original_filename}" uploaded successfully.`,
        )
      }
      queryClient.invalidateQueries({ queryKey: ['application-documents', id] })
    },
    onError: (err: any) => {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to upload document. Please ensure the file format is supported and not corrupted.'
      setUploadError(typeof msg === 'string' ? msg : JSON.stringify(msg))
      setDuplicateAlert(null)
      setUploadSuccessMessage(null)
    },
  })

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUploadError(null)
    setDuplicateAlert(null)
    setUploadSuccessMessage(null)

    if (!e.target.files || e.target.files.length === 0) {
      setSelectedFile(null)
      return
    }

    const file = e.target.files[0]

    // Check extension
    const ext = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!SUPPORTED_EXTENSIONS.includes(ext)) {
      setUploadError(
        `Unsupported file type "${ext}". Supported formats are: ${SUPPORTED_EXTENSIONS.join(', ')}`,
      )
      setSelectedFile(null)
      return
    }

    // Check size
    if (file.size === 0) {
      setUploadError('The selected file is empty (0 bytes).')
      setSelectedFile(null)
      return
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setUploadError(
        `File size (${formatBytes(file.size)}) exceeds the maximum allowed limit of 50 MB.`,
      )
      setSelectedFile(null)
      return
    }

    setSelectedFile(file)
  }

  const handleUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFile || uploadMutation.isPending) return
    uploadMutation.mutate({ file: selectedFile, docCategory: category })
  }

  if (isAppLoading) {
    return (
      <div className="p-16 text-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-3" />
        <p className="text-sm text-gray-500">Loading application details...</p>
      </div>
    )
  }

  if (isAppError || !application) {
    return (
      <div className="max-w-2xl mx-auto mt-8 bg-rose-50 border border-rose-200 rounded-lg p-6 text-rose-800">
        <h2 className="text-base font-semibold mb-2">Application Not Found</h2>
        <p className="text-xs text-rose-600 mb-4">
          {appError instanceof Error ? appError.message : 'Unable to find or load this application.'}
        </p>
        <Link
          to="/applications"
          className="px-3.5 py-1.5 bg-rose-700 text-white text-xs font-medium rounded hover:bg-rose-800 transition-colors"
        >
          &larr; Return to Applications
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Breadcrumb Navigation */}
      <nav className="flex text-sm text-gray-500 gap-2 items-center">
        <Link to="/applications" className="hover:text-blue-700">
          Applications
        </Link>
        <span>&rsaquo;</span>
        <span className="font-mono text-gray-900 font-medium">{application.reference_number}</span>
      </nav>

      {/* Header Info Banner */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 border-b border-gray-100 pb-5">
          <div>
            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
              <h1 className="text-2xl font-bold text-gray-900">{application.institution_name}</h1>
              <StatusBadge status={application.status} />
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                SYNTHETIC DEMO
              </span>
            </div>
            <p className="font-mono text-xs text-blue-700 mt-1">
              Ref: <span className="font-semibold">{application.reference_number}</span>
              {application.aicte_permanent_id && (
                <span className="ml-3 text-gray-500 font-sans">
                  PID: <span className="font-mono">{application.aicte_permanent_id}</span>
                </span>
              )}
            </p>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            {isViewer ? (
              <span
                title="Running validation requires Officer or Admin role"
                className="inline-flex items-center px-3.5 py-1.5 bg-gray-100 text-gray-400 text-xs font-semibold rounded-md border border-gray-200 cursor-not-allowed shadow-none"
              >
                🔒 Validation (Officer Only)
              </span>
            ) : (
              <button
                type="button"
                id="btn-run-validation"
                onClick={() => validateMutation.mutate()}
                disabled={validateMutation.isPending}
                className="inline-flex items-center px-3.5 py-1.5 bg-indigo-700 text-white text-xs font-semibold rounded-md shadow-sm hover:bg-indigo-800 disabled:opacity-50 transition-colors"
              >
                {validateMutation.isPending ? (
                  <>
                    <svg className="animate-spin -ml-0.5 mr-1.5 h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    Running Rules & Graph...
                  </>
                ) : (
                  '⚡ Run Full Validation & Graph'
                )}
              </button>
            )}
            <div className="text-right">
              <span className="text-xs text-gray-400 block">Created On</span>
              <span className="text-xs font-medium text-gray-700">
                {new Date(application.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>

        {/* Application Metadata Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-5 text-xs">
          <div>
            <span className="text-gray-400 block font-medium">Academic Year</span>
            <span className="text-gray-800 font-semibold">{application.academic_year}</span>
          </div>
          <div>
            <span className="text-gray-400 block font-medium">Category</span>
            <span className="text-gray-800 font-semibold capitalize">
              {application.application_category.replace(/_/g, ' ')}
            </span>
          </div>
          <div>
            <span className="text-gray-400 block font-medium">Programme Type</span>
            <span className="text-gray-800 font-semibold">{application.programme_type}</span>
          </div>
          <div>
            <span className="text-gray-400 block font-medium">Applicant Contact</span>
            <span className="text-gray-800 font-semibold block">{application.applicant_name}</span>
            <span className="text-gray-500 text-[11px]">{application.applicant_email}</span>
          </div>
        </div>

        {application.description && (
          <div className="mt-4 pt-3 border-t border-gray-100 text-xs">
            <span className="text-gray-400 block font-medium mb-1">Notes / Description</span>
            <p className="text-gray-700">{application.description}</p>
          </div>
        )}
      </div>

      {/* Validation Result Banner */}
      {validationBanner && (
        <div
          className={`p-4 rounded-lg border text-xs flex items-center justify-between shadow-sm ${
            validationBanner.type === 'success'
              ? 'bg-emerald-50 border-emerald-300 text-emerald-900'
              : 'bg-rose-50 border-rose-300 text-rose-900'
          }`}
        >
          <div className="flex items-center gap-2">
            <span>{validationBanner.type === 'success' ? '⚡' : '⚠️'}</span>
            <span className="font-semibold">{validationBanner.message}</span>
          </div>
          <button
            type="button"
            onClick={() => setValidationBanner(null)}
            className="text-gray-400 hover:text-gray-700 font-bold ml-4 text-sm"
          >
            &times;
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-gray-200 gap-6 text-sm overflow-x-auto">
        <button
          type="button"
          id="tab-btn-documents"
          onClick={() => setActiveTab('documents')}
          className={`pb-3 font-semibold text-xs sm:text-sm transition-colors border-b-2 flex items-center gap-2 whitespace-nowrap ${
            activeTab === 'documents'
              ? 'border-blue-700 text-blue-700'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <span>📁</span>
          <span>Documents & OCR</span>
          <span className="ml-1 bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded-full text-[10px] font-bold">
            {documentsData?.total || 0}
          </span>
        </button>

        <button
          type="button"
          id="tab-btn-findings"
          onClick={() => setActiveTab('findings')}
          className={`pb-3 font-semibold text-xs sm:text-sm transition-colors border-b-2 flex items-center gap-2 whitespace-nowrap ${
            activeTab === 'findings'
              ? 'border-blue-700 text-blue-700'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <span>⚠️</span>
          <span>Validation Findings</span>
        </button>

        <button
          type="button"
          id="tab-btn-graph"
          onClick={() => setActiveTab('graph')}
          className={`pb-3 font-semibold text-xs sm:text-sm transition-colors border-b-2 flex items-center gap-2 whitespace-nowrap ${
            activeTab === 'graph'
              ? 'border-indigo-700 text-indigo-700'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <span>🕸️</span>
          <span>Consistency Graph & Discrepancies</span>
        </button>

        <button
          type="button"
          id="tab-btn-authenticity"
          onClick={() => setActiveTab('authenticity')}
          className={`pb-3 font-semibold text-xs sm:text-sm transition-colors border-b-2 flex items-center gap-2 whitespace-nowrap ${
            activeTab === 'authenticity'
              ? 'border-purple-700 text-purple-700'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <span>🛡️</span>
          <span>Authenticity Screening</span>
          {authenticityData?.total_review_required ? (
            <span className="ml-1 bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded-full text-[10px] font-bold">
              {authenticityData.total_review_required} review
            </span>
          ) : null}
        </button>

        <button
          type="button"
          id="tab-btn-audit"
          onClick={() => setActiveTab('audit')}
          className={`pb-3 font-semibold text-xs sm:text-sm transition-colors border-b-2 flex items-center gap-2 whitespace-nowrap ${
            activeTab === 'audit'
              ? 'border-slate-800 text-slate-800'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <span>📜</span>
          <span>Audit Trail</span>
        </button>
      </div>


      {/* Tab 1: Documents & Upload */}
      {activeTab === 'documents' && (
        <div className="space-y-8">
          {/* Document Upload Section */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-1">Upload Supporting Document</h2>
        <p className="text-xs text-gray-500 mb-4">
          Upload official documents for preliminary verification. Supported formats: PDF, PNG, JPG, TIFF (up to 50 MB).
        </p>

        {/* Upload Success Banner */}
        {uploadSuccessMessage && (
          <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-md text-xs text-emerald-800 flex items-center gap-2">
            <svg className="h-4 w-4 text-emerald-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
            </svg>
            <span>{uploadSuccessMessage}</span>
          </div>
        )}

        {/* Duplicate Advisory Alert */}
        {duplicateAlert && (
          <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-md text-xs text-amber-900">
            <div className="flex items-start gap-2">
              <svg className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div>
                <p className="font-semibold">Potential Duplicate Document Detected</p>
                <p className="mt-1 text-amber-800">{duplicateAlert.message}</p>
                <p className="mt-1 text-gray-600 font-mono text-[11px]">
                  Existing Doc ID: {duplicateAlert.existing_document_id} (App ID: {duplicateAlert.existing_application_id})
                </p>
                <p className="mt-1 text-amber-700 italic">
                  * Note: The document was safely accepted and retained. Hash collisions identify identical files, not fraud.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Upload Error Banner */}
        {uploadError && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-200 rounded-md text-xs text-rose-800 flex items-center gap-2">
            <svg className="h-4 w-4 text-rose-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{uploadError}</span>
          </div>
        )}

        <form onSubmit={handleUploadSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="document-category" className="block text-xs font-semibold text-gray-700 mb-1">
                Document Category
              </label>
              <select
                id="document-category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 bg-white focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="application_form">Application Form</option>
                <option value="land_deed_lease">Land Deed / Lease Document</option>
                <option value="building_plan">Building Plan / Approval</option>
                <option value="faculty_list">Faculty List & Qualifications</option>
                <option value="affidavit">Affidavit / Undertaking</option>
                <option value="noc_certificate">NOC / Affiliation Certificate</option>
                <option value="other">Other Supporting Document</option>
              </select>
            </div>

            <div>
              <label htmlFor="document-file-input" className="block text-xs font-semibold text-gray-700 mb-1">
                Select File (.pdf, .png, .jpg, .tiff)
              </label>
              <input
                type="file"
                id="document-file-input"
                accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
                onChange={handleFileChange}
                className="w-full text-xs text-gray-500 file:mr-4 file:py-2 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
              />
            </div>
          </div>

          <div className="flex justify-between items-center">
            {isViewer ? (
              <span className="text-xs text-amber-800 bg-amber-50 px-2.5 py-1 rounded border border-amber-200">
                ℹ️ Document uploading is disabled for Viewer role (read-only access).
              </span>
            ) : <div />}
            <button
              type="submit"
              id="btn-upload-document"
              disabled={isViewer || !selectedFile || uploadMutation.isPending}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-700 hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {uploadMutation.isPending ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  Uploading & Validating...
                </>
              ) : (
                'Upload Document'
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Uploaded Documents List */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <div>
            <h2 className="text-base font-bold text-gray-900">Uploaded Documents</h2>
            <p className="text-xs text-gray-500">
              Files uploaded to this application with safe storage references and checksum verification.
            </p>
          </div>
          <span className="text-xs bg-gray-100 text-gray-700 font-semibold px-2.5 py-1 rounded-full">
            {documentsData?.total || 0} Total
          </span>
        </div>

        {isDocsLoading && (
          <div className="p-8 text-center text-xs text-gray-500">
            Loading document list...
          </div>
        )}

        {isDocsError && (
          <div className="p-4 bg-rose-50 text-rose-700 text-xs">
            Failed to load documents: {docsError instanceof Error ? docsError.message : 'Error'}
          </div>
        )}

        {!isDocsLoading && (!documentsData?.items || documentsData.items.length === 0) && (
          <div className="p-12 text-center text-gray-500 text-sm">
            No documents uploaded yet for this application. Use the form above to add supporting files.
          </div>
        )}

        {!isDocsLoading && documentsData?.items && documentsData.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-left text-xs">
              <thead className="bg-gray-50 text-gray-500 uppercase font-semibold">
                <tr>
                  <th scope="col" className="px-6 py-3">Filename</th>
                  <th scope="col" className="px-6 py-3">Category</th>
                  <th scope="col" className="px-6 py-3">Format / MIME</th>
                  <th scope="col" className="px-6 py-3">Size</th>
                  <th scope="col" className="px-6 py-3">Status</th>
                  <th scope="col" className="px-6 py-3">Duplicate?</th>
                  <th scope="col" className="px-6 py-3">Uploaded At</th>
                  <th scope="col" className="px-6 py-3 text-right">Extraction & OCR</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {documentsData.items.map((doc: DocumentListItem) => {
                  const isExpanded = expandedDocId === doc.id
                  return (
                    <React.Fragment key={doc.id}>
                      <tr className={`hover:bg-gray-50 transition-colors ${isExpanded ? 'bg-blue-50/20' : ''}`}>
                        <td className="px-6 py-3.5 font-medium text-gray-900 flex items-center gap-2">
                          <svg className="h-4 w-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                          </svg>
                          <span className="truncate max-w-xs" title={doc.original_filename}>
                            {doc.original_filename}
                          </span>
                        </td>
                        <td className="px-6 py-3.5 capitalize text-gray-600">
                          {doc.document_type ? doc.document_type.replace(/_/g, ' ') : '—'}
                        </td>
                        <td className="px-6 py-3.5 font-mono text-[11px] text-gray-500">
                          {doc.mime_type}
                        </td>
                        <td className="px-6 py-3.5 text-gray-600 whitespace-nowrap">
                          {formatBytes(doc.file_size_bytes)}
                        </td>
                        <td className="px-6 py-3.5 whitespace-nowrap">
                          <StatusBadge status={doc.status} />
                        </td>
                        <td className="px-6 py-3.5 whitespace-nowrap">
                          {doc.is_duplicate ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800">
                              ⚠️ Potential Duplicate
                            </span>
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </td>
                        <td className="px-6 py-3.5 text-gray-500 whitespace-nowrap">
                          {new Date(doc.created_at).toLocaleString()}
                        </td>
                        <td className="px-6 py-3.5 text-right whitespace-nowrap">
                          <button
                            type="button"
                            id={`btn-toggle-extract-${doc.id}`}
                            onClick={() => setExpandedDocId(isExpanded ? null : doc.id)}
                            className={`inline-flex items-center px-2.5 py-1 text-xs font-semibold rounded border transition-colors ${
                              isExpanded
                                ? 'bg-gray-200 text-gray-800 border-gray-300'
                                : doc.status === 'processed'
                                ? 'bg-emerald-50 text-emerald-800 border-emerald-300 hover:bg-emerald-100'
                                : 'bg-blue-50 text-blue-700 border-blue-300 hover:bg-blue-100'
                            }`}
                          >
                            {isExpanded
                              ? 'Hide Details ▲'
                              : doc.status === 'processed'
                              ? 'View Extracted Fields ▼'
                              : 'Inspect / Process ▼'}
                          </button>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={8} className="px-6 py-4 bg-slate-50/60 border-t border-b border-blue-100">
                            <DocumentExtractionCard
                              applicationId={application.id}
                              documentId={doc.id}
                              originalFilename={doc.original_filename}
                              initialStatus={doc.status}
                              onStatusChange={() => {
                                queryClient.invalidateQueries({ queryKey: ['application-documents', id] })
                              }}
                            />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )}

  {/* Tab 2: Validation Findings */}
  {activeTab === 'findings' && (
    <ValidationFindingsList
      applicationId={application.id}
      onFindingsUpdated={() => {
        queryClient.invalidateQueries({ queryKey: ['application-findings', id] })
        queryClient.invalidateQueries({ queryKey: ['consistency-graph', id] })
      }}
    />
  )}

  {/* Tab 3: Cross-Document Consistency Graph */}
  {activeTab === 'graph' && (
    <ConsistencyGraphView applicationId={application.id} />
  )}

  {/* Tab 4: Authenticity Screening */}
  {activeTab === 'authenticity' && (
    <AuthenticityScreeningView applicationId={application.id} />
  )}

  {/* Tab 5: Immutable Regulatory Audit Trail */}
  {activeTab === 'audit' && (
    <AuditTrailView applicationId={application.id} />
  )}
</div>
  )
}

