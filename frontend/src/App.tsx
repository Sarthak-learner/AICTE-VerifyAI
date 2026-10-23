import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import Layout from './components/layout/Layout'
import LoginPage from './pages/auth/LoginPage'
import DashboardPage from './pages/dashboard/DashboardPage'
import StatusPage from './pages/StatusPage'
import ApplicationListPage from './pages/applications/ApplicationListPage'
import ApplicationCreatePage from './pages/applications/ApplicationCreatePage'
import ApplicationDetailPage from './pages/applications/ApplicationDetailPage'

/**
 * AICTE VerifyAI application routing with authentication and RBAC.
 */
function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public login route */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected application routes */}
        <Route
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/applications" element={<ApplicationListPage />} />
          <Route
            path="/applications/new"
            element={
              <ProtectedRoute allowedRoles={['admin', 'officer']}>
                <ApplicationCreatePage />
              </ProtectedRoute>
            }
          />
          <Route path="/applications/:id" element={<ApplicationDetailPage />} />
          <Route path="/status" element={<StatusPage />} />
        </Route>

        {/* Fallback to dashboard */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AuthProvider>
  )
}

export default App
