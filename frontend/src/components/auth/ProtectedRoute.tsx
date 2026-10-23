import React from 'react'
import { Navigate, useLocation, Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { UserRole } from '../../types/auth'

interface ProtectedRouteProps {
  children: React.ReactNode
  allowedRoles?: UserRole[]
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { isAuthenticated, isLoading, user } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-brand-800 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-gray-500 font-medium">Verifying AICTE authentication...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return (
      <div className="max-w-2xl mx-auto my-12 bg-white rounded-xl shadow-sm border border-red-200 p-8 text-center">
        <div className="w-14 h-14 bg-red-50 text-red-600 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl font-bold">
          ✕
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">403 — Access Denied</h2>
        <p className="text-sm text-gray-600 mb-4">
          Your current account role is <span className="font-semibold text-gray-800 uppercase px-2 py-0.5 bg-gray-100 rounded border border-gray-300">{user.role}</span>.
          This page requires one of the following roles:{' '}
          <span className="font-semibold text-brand-900">
            {allowedRoles.map((r) => r.toUpperCase()).join(', ')}
          </span>.
        </p>
        <p className="text-xs text-gray-500 mb-6">
          Viewer accounts have read-only access to compliance reports, validation findings, and application statistics.
          Administrative or operational actions require Officer credentials.
        </p>
        <div className="flex justify-center gap-4">
          <Link
            to="/dashboard"
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
          >
            Go to Dashboard
          </Link>
          <Link
            to="/applications"
            className="px-4 py-2 text-sm font-medium text-white bg-brand-800 rounded-lg hover:bg-brand-900"
          >
            View Applications
          </Link>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
