import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/dashboard'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Authentication failed. Please verify your email and password.'
      setError(msg)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleQuickLogin = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail)
    setPassword(demoPass)
    setError(null)
  }

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex items-center gap-2 mb-2">
          <span className="font-extrabold text-2xl tracking-tight text-brand-900">AICTE VerifyAI</span>
          <span className="text-blue-700 bg-blue-100 text-xs font-bold px-2.5 py-0.5 rounded border border-blue-300">
            PROTOTYPE
          </span>
        </div>
        <h2 className="text-xl font-bold text-gray-800 tracking-tight">
          Regulatory Approval Verification Portal
        </h2>
        <p className="mt-1 text-xs text-gray-500">
          Sign in to access document authenticity, compliance rules, and consistency analysis
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-sm rounded-xl border border-gray-200 sm:px-10">
          {error && (
            <div className="mb-4 bg-red-50 border-l-4 border-red-500 p-3 text-sm text-red-700 rounded">
              <p className="font-medium">Sign in error</p>
              <p className="text-xs mt-0.5">{error}</p>
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Official Email Address
              </label>
              <div className="mt-1">
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e.g. officer@aicte.gov.in"
                  className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-brand-800 focus:border-brand-800 text-sm"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Password
              </label>
              <div className="mt-1">
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-brand-800 focus:border-brand-800 text-sm"
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-semibold text-white bg-brand-800 hover:bg-brand-900 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-800 disabled:opacity-50 transition"
              >
                {isSubmitting ? 'Authenticating...' : 'Sign In'}
              </button>
            </div>
          </form>

          {/* Quick Demo Credentials for Reviewers */}
          <div className="mt-6 border-t border-gray-200 pt-5">
            <p className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wider text-center">
              Quick Demo Accounts (1-Click Fill)
            </p>
            <div className="grid grid-cols-1 gap-2">
              <button
                type="button"
                onClick={() => handleQuickLogin('officer@aicte.gov.in', 'Officer@123')}
                className="flex items-center justify-between px-3 py-2 text-xs border border-blue-200 rounded-lg hover:bg-blue-50 text-left transition"
              >
                <div>
                  <div className="font-semibold text-blue-900">Verification Officer</div>
                  <div className="text-gray-500 text-[11px]">officer@aicte.gov.in</div>
                </div>
                <span className="text-[10px] font-bold bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                  OFFICER
                </span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin('admin@aicte.gov.in', 'Admin@123')}
                className="flex items-center justify-between px-3 py-2 text-xs border border-purple-200 rounded-lg hover:bg-purple-50 text-left transition"
              >
                <div>
                  <div className="font-semibold text-purple-900">System Administrator</div>
                  <div className="text-gray-500 text-[11px]">admin@aicte.gov.in</div>
                </div>
                <span className="text-[10px] font-bold bg-purple-100 text-purple-800 px-2 py-0.5 rounded">
                  ADMIN
                </span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin('viewer@aicte.gov.in', 'Viewer@123')}
                className="flex items-center justify-between px-3 py-2 text-xs border border-gray-200 rounded-lg hover:bg-gray-50 text-left transition"
              >
                <div>
                  <div className="font-semibold text-gray-800">Public Auditor / Viewer</div>
                  <div className="text-gray-500 text-[11px]">viewer@aicte.gov.in (Read-Only)</div>
                </div>
                <span className="text-[10px] font-bold bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                  VIEWER
                </span>
              </button>
            </div>
          </div>
        </div>

        <p className="mt-4 text-center text-[11px] text-gray-500">
          AICTE VerifyAI v0.1.0 Prototype • Advisory findings only
        </p>
      </div>
    </div>
  )
}
