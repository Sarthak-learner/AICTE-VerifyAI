import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createApplication } from '../../api/applications'
import type { Application } from '../../types'

export default function ApplicationCreatePage() {
  const navigate = useNavigate()

  const [formData, setFormData] = useState({
    institution_name: '',
    aicte_permanent_id: '',
    academic_year: '2025-26',
    application_category: 'new_programme',
    programme_type: 'BE_BTech',
    description: '',
    applicant_name: '',
    applicant_email: '',
  })

  const [clientErrors, setClientErrors] = useState<Record<string, string>>({})
  const [serverError, setServerError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [createdApplication, setCreatedApplication] = useState<Application | null>(null)

  const validate = (): boolean => {
    const errs: Record<string, string> = {}
    if (!formData.institution_name.trim()) {
      errs.institution_name = 'Institution name is required.'
    } else if (formData.institution_name.length < 2) {
      errs.institution_name = 'Institution name must be at least 2 characters.'
    }

    if (!formData.academic_year.trim()) {
      errs.academic_year = 'Academic year is required.'
    } else if (!/^\d{4}-\d{2}$/.test(formData.academic_year)) {
      errs.academic_year = 'Academic year must be in YYYY-YY format, e.g. 2025-26.'
    }

    if (!formData.application_category) {
      errs.application_category = 'Application category is required.'
    }

    if (!formData.programme_type) {
      errs.programme_type = 'Programme type is required.'
    }

    if (!formData.applicant_name.trim()) {
      errs.applicant_name = 'Applicant name is required.'
    }

    if (!formData.applicant_email.trim()) {
      errs.applicant_email = 'Applicant email is required.'
    } else if (!formData.applicant_email.includes('@') || !formData.applicant_email.includes('.')) {
      errs.applicant_email = 'A valid email address is required.'
    }

    setClientErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
    if (clientErrors[name]) {
      setClientErrors((prev) => ({ ...prev, [name]: '' }))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (isSubmitting) return

    setServerError(null)
    if (!validate()) return

    setIsSubmitting(true)
    try {
      const result = await createApplication({
        institution_name: formData.institution_name.trim(),
        aicte_permanent_id: formData.aicte_permanent_id.trim() || undefined,
        academic_year: formData.academic_year.trim(),
        application_category: formData.application_category,
        programme_type: formData.programme_type,
        description: formData.description.trim() || undefined,
        applicant_name: formData.applicant_name.trim(),
        applicant_email: formData.applicant_email.trim(),
      })
      setCreatedApplication(result)
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to submit application. Please verify the input and try again.'
      setServerError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Breadcrumb Navigation */}
      <nav className="flex text-sm text-gray-500 gap-2 items-center">
        <Link to="/applications" className="hover:text-blue-700">
          Applications
        </Link>
        <span>&rsaquo;</span>
        <span className="text-gray-900 font-medium">New Application</span>
      </nav>

      {/* Success View */}
      {createdApplication ? (
        <div className="bg-white rounded-lg border border-emerald-200 shadow-sm p-8 text-center space-y-5">
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-emerald-100 text-emerald-600">
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">Application Created Successfully!</h2>
            <p className="text-sm text-gray-600 mt-1">
              Your institutional approval application has been initialized in{' '}
              <span className="font-semibold text-gray-800 uppercase">DRAFT</span> status.
            </p>
          </div>

          <div className="bg-gray-50 border border-gray-200 rounded-md p-4 max-w-md mx-auto text-left space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Reference Number:</span>
              <span className="font-mono font-bold text-blue-700">
                {createdApplication.reference_number}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Institution:</span>
              <span className="font-medium text-gray-800">
                {createdApplication.institution_name}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Academic Year:</span>
              <span className="text-gray-800">{createdApplication.academic_year}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Category:</span>
              <span className="capitalize text-gray-800">
                {createdApplication.application_category.replace(/_/g, ' ')}
              </span>
            </div>
          </div>

          <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-3 max-w-lg mx-auto">
            Please proceed to the application details page to upload the required supporting documents.
          </p>

          <div className="flex justify-center gap-3 pt-2">
            <Link
              to={`/applications/${createdApplication.id}`}
              className="px-4 py-2 bg-blue-700 text-white text-sm font-medium rounded-md hover:bg-blue-800 transition-colors shadow-sm"
            >
              Upload Documents &rarr;
            </Link>
            <Link
              to="/applications"
              className="px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-200 transition-colors"
            >
              Back to List
            </Link>
          </div>
        </div>
      ) : (
        /* Application Form */
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 sm:p-8">
          <div className="border-b border-gray-200 pb-4 mb-6">
            <h1 className="text-xl font-bold text-gray-900">Create Institutional Application</h1>
            <p className="text-xs text-gray-500 mt-1">
              Enter institution details for approval processing. Synthetic demo IDs may be used for prototype evaluation.
            </p>
          </div>

          {serverError && (
            <div className="mb-6 p-4 bg-rose-50 border border-rose-200 rounded-md text-sm text-rose-800">
              <p className="font-semibold">Error submitting application</p>
              <p className="text-xs mt-1">{serverError}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Institution Name */}
            <div>
              <label htmlFor="institution_name" className="block text-xs font-semibold text-gray-700 mb-1">
                Institution Name <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                id="institution_name"
                name="institution_name"
                value={formData.institution_name}
                onChange={handleChange}
                placeholder="e.g. Apex Institute of Engineering & Technology"
                className={`w-full text-sm border rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500 ${
                  clientErrors.institution_name ? 'border-rose-400 bg-rose-50' : 'border-gray-300'
                }`}
              />
              {clientErrors.institution_name && (
                <p className="text-xs text-rose-600 mt-1">{clientErrors.institution_name}</p>
              )}
            </div>

            {/* AICTE Permanent ID & Academic Year */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="aicte_permanent_id" className="block text-xs font-semibold text-gray-700 mb-1">
                  AICTE Permanent ID <span className="text-gray-400 font-normal">(or Demo ID)</span>
                </label>
                <input
                  type="text"
                  id="aicte_permanent_id"
                  name="aicte_permanent_id"
                  value={formData.aicte_permanent_id}
                  onChange={handleChange}
                  placeholder="e.g. DEMO-1-9876543210"
                  className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500 font-mono"
                />
                <p className="text-[11px] text-gray-400 mt-0.5">Synthetic demo identifiers permitted.</p>
              </div>

              <div>
                <label htmlFor="academic_year" className="block text-xs font-semibold text-gray-700 mb-1">
                  Academic Year <span className="text-rose-500">*</span>
                </label>
                <select
                  id="academic_year"
                  name="academic_year"
                  value={formData.academic_year}
                  onChange={handleChange}
                  className={`w-full text-sm border rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500 bg-white ${
                    clientErrors.academic_year ? 'border-rose-400 bg-rose-50' : 'border-gray-300'
                  }`}
                >
                  <option value="2024-25">2024-25</option>
                  <option value="2025-26">2025-26</option>
                  <option value="2026-27">2026-27</option>
                  <option value="2027-28">2027-28</option>
                </select>
                {clientErrors.academic_year && (
                  <p className="text-xs text-rose-600 mt-1">{clientErrors.academic_year}</p>
                )}
              </div>
            </div>

            {/* Application Category & Programme Type */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="application_category" className="block text-xs font-semibold text-gray-700 mb-1">
                  Application Category <span className="text-rose-500">*</span>
                </label>
                <select
                  id="application_category"
                  name="application_category"
                  value={formData.application_category}
                  onChange={handleChange}
                  className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
                >
                  <option value="new_institution">New Institution</option>
                  <option value="new_programme">New Programme</option>
                  <option value="additional_intake">Additional Intake</option>
                  <option value="extension_of_approval">Extension of Approval (EoA)</option>
                  <option value="closure">Closure</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label htmlFor="programme_type" className="block text-xs font-semibold text-gray-700 mb-1">
                  Programme / Course Type <span className="text-rose-500">*</span>
                </label>
                <select
                  id="programme_type"
                  name="programme_type"
                  value={formData.programme_type}
                  onChange={handleChange}
                  className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
                >
                  <option value="BE_BTech">Engineering & Technology (BE/BTech)</option>
                  <option value="ME_MTech">Postgraduate Engineering (ME/MTech)</option>
                  <option value="MBA">Management (MBA)</option>
                  <option value="MCA">Computer Applications (MCA)</option>
                  <option value="BCA">Computer Applications (BCA)</option>
                  <option value="Diploma">Polytechnic / Diploma</option>
                  <option value="PhD">Doctoral (PhD)</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>

            {/* Applicant Name & Email */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="applicant_name" className="block text-xs font-semibold text-gray-700 mb-1">
                  Applicant / Officer Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  id="applicant_name"
                  name="applicant_name"
                  value={formData.applicant_name}
                  onChange={handleChange}
                  placeholder="e.g. Dr. Rajesh Kumar"
                  className={`w-full text-sm border rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500 ${
                    clientErrors.applicant_name ? 'border-rose-400 bg-rose-50' : 'border-gray-300'
                  }`}
                />
                {clientErrors.applicant_name && (
                  <p className="text-xs text-rose-600 mt-1">{clientErrors.applicant_name}</p>
                )}
              </div>

              <div>
                <label htmlFor="applicant_email" className="block text-xs font-semibold text-gray-700 mb-1">
                  Applicant Email <span className="text-rose-500">*</span>
                </label>
                <input
                  type="email"
                  id="applicant_email"
                  name="applicant_email"
                  value={formData.applicant_email}
                  onChange={handleChange}
                  placeholder="e.g. principal@apex.edu.in"
                  className={`w-full text-sm border rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500 ${
                    clientErrors.applicant_email ? 'border-rose-400 bg-rose-50' : 'border-gray-300'
                  }`}
                />
                {clientErrors.applicant_email && (
                  <p className="text-xs text-rose-600 mt-1">{clientErrors.applicant_email}</p>
                )}
              </div>
            </div>

            {/* Description */}
            <div>
              <label htmlFor="description" className="block text-xs font-semibold text-gray-700 mb-1">
                Application Description / Notes <span className="text-gray-400 font-normal">(Optional)</span>
              </label>
              <textarea
                id="description"
                name="description"
                rows={3}
                value={formData.description}
                onChange={handleChange}
                placeholder="Optional background information, proposed intake capacity, or department notes..."
                className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Form Actions */}
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
              <button
                type="button"
                onClick={() => navigate('/applications')}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none"
              >
                Cancel
              </button>
              <button
                type="submit"
                id="btn-submit-application"
                disabled={isSubmitting}
                className="inline-flex items-center px-5 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-700 hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
              >
                {isSubmitting ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    Creating Application...
                  </>
                ) : (
                  'Create Application'
                )}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
