import { Outlet, NavLink, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const DISCLAIMER =
  'AI-generated findings are advisory only and do not constitute a final AICTE regulatory decision.'

export default function Layout() {
  const { user, role, logout, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const roleBadgeColor = {
    admin: 'bg-purple-100 text-purple-800 border-purple-300',
    officer: 'bg-blue-100 text-blue-800 border-blue-300',
    viewer: 'bg-gray-100 text-gray-800 border-gray-300',
  }[role || 'viewer']

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Top navigation bar */}
      <header className="bg-brand-900 text-white px-6 py-3 flex items-center gap-4 shadow">
        <Link to="/applications" className="flex items-center gap-2">
          <span className="font-bold text-lg tracking-tight">AICTE VerifyAI</span>
          <span className="text-blue-300 text-xs font-medium px-2 py-0.5 border border-blue-400 rounded">
            PROTOTYPE
          </span>
        </Link>
        <nav className="ml-8 flex gap-6 text-sm items-center">
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              isActive ? 'text-white font-semibold' : 'text-blue-200 hover:text-white'
            }
          >
            Dashboard
          </NavLink>
          <NavLink
            to="/applications"
            end
            className={({ isActive }) =>
              isActive ? 'text-white font-semibold' : 'text-blue-200 hover:text-white'
            }
          >
            Applications
          </NavLink>
          {role !== 'viewer' && (
            <NavLink
              to="/applications/new"
              className={({ isActive }) =>
                isActive ? 'text-white font-semibold' : 'text-blue-200 hover:text-white'
              }
            >
              New Application
            </NavLink>
          )}
          <NavLink
            to="/status"
            className={({ isActive }) =>
              isActive ? 'text-white font-semibold' : 'text-blue-200 hover:text-white'
            }
          >
            System Status
          </NavLink>
        </nav>

        {/* User profile & session controls */}
        <div className="ml-auto flex items-center gap-3 text-xs">
          {isAuthenticated && user ? (
            <>
              <div className="text-right hidden sm:block">
                <div className="font-semibold text-white leading-tight">{user.full_name}</div>
                <div className="text-blue-300 text-[11px]">{user.email}</div>
              </div>
              <span
                className={`font-bold uppercase text-[10px] px-2 py-0.5 rounded border ${roleBadgeColor}`}
              >
                {role}
              </span>
              <button
                onClick={handleLogout}
                className="ml-2 px-2.5 py-1 text-xs font-medium bg-brand-800 hover:bg-brand-700 text-blue-100 hover:text-white rounded border border-blue-600 transition"
              >
                Sign Out
              </button>
            </>
          ) : (
            <Link
              to="/login"
              className="px-3 py-1 text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white rounded transition"
            >
              Sign In
            </Link>
          )}
        </div>
      </header>

      {/* Advisory disclaimer banner */}
      <div className="bg-amber-50 border-b border-amber-200 px-6 py-2 text-amber-800 text-xs text-center font-medium">
        ⚠️ {DISCLAIMER}
      </div>

      {/* Role banner for viewer */}
      {role === 'viewer' && (
        <div className="bg-blue-50 border-b border-blue-200 px-6 py-1.5 text-blue-800 text-xs text-center">
          ℹ️ You are viewing AICTE VerifyAI with <span className="font-semibold">Viewer (Read-Only)</span> access. Actions such as creating applications, uploading files, running validation, and resolving findings are disabled.
        </div>
      )}

      {/* Main content area */}
      <main className="flex-1 container mx-auto px-4 py-6 max-w-7xl">
        <Outlet />
      </main>

      <footer className="border-t bg-white px-6 py-3 text-xs text-gray-400 text-center">
        AICTE VerifyAI v0.1.0 — Prototype only. Not an official AICTE system.
      </footer>
    </div>
  )
}
