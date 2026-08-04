import { Navigate, NavLink, Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import { AdminDashboardPage } from './core/admin/AdminDashboardPage'
import { BillingPage } from './core/admin/BillingPage'
import { RefreshPage } from './core/admin/RefreshPage'
import { ReviewQueuePage } from './core/admin/ReviewQueuePage'
import { AnalyticsPage } from './core/analytics/AnalyticsPage'
import { AuthProvider, useAuth } from './core/auth/AuthContext'
import { LoginPage } from './core/auth/LoginPage'
import { RegisterPage } from './core/auth/RegisterPage'
import { MapView } from './core/map/MapView'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { currentUser } = useAuth()
  if (currentUser !== null && currentUser.role !== 'admin') {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}

function AppShell() {
  const { isAuthenticated, currentUser, logout } = useAuth()

  return (
    <div className="flex h-full flex-col">
      {isAuthenticated && (
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2">
          <div className="flex items-center gap-4">
            <h1 className="text-sm font-semibold text-slate-900">Ice &amp; Water Intelligence</h1>
            <NavLink to="/" end className="text-sm text-slate-500 hover:text-slate-800">
              Map
            </NavLink>
            <NavLink to="/analytics" className="text-sm text-slate-500 hover:text-slate-800">
              Analytics
            </NavLink>
            {currentUser?.role === 'admin' && (
              <>
                <NavLink to="/admin" end className="text-sm text-slate-500 hover:text-slate-800">
                  Team
                </NavLink>
                <NavLink to="/admin/review" end className="text-sm text-slate-500 hover:text-slate-800">
                  Review
                </NavLink>
                <NavLink to="/admin/billing" end className="text-sm text-slate-500 hover:text-slate-800">
                  Billing
                </NavLink>
                <NavLink to="/admin/refresh" className="text-sm text-slate-500 hover:text-slate-800">
                  Refresh
                </NavLink>
              </>
            )}
          </div>
          <button type="button" onClick={logout} className="text-sm text-slate-500 hover:text-slate-800">
            Sign out
          </button>
        </header>
      )}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />} />
          <Route
            path="/register"
            element={isAuthenticated ? <Navigate to="/" replace /> : <RegisterPage />}
          />
          <Route
            path="/"
            element={
              <RequireAuth>
                <MapView />
              </RequireAuth>
            }
          />
          <Route
            path="/analytics"
            element={
              <RequireAuth>
                <AnalyticsPage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin"
            element={
              <RequireAuth>
                <RequireAdmin>
                  <AdminDashboardPage />
                </RequireAdmin>
              </RequireAuth>
            }
          />
          <Route
            path="/admin/review"
            element={
              <RequireAuth>
                <RequireAdmin>
                  <ReviewQueuePage />
                </RequireAdmin>
              </RequireAuth>
            }
          />
          <Route
            path="/admin/billing"
            element={
              <RequireAuth>
                <RequireAdmin>
                  <BillingPage />
                </RequireAdmin>
              </RequireAuth>
            }
          />
          <Route
            path="/admin/refresh"
            element={
              <RequireAuth>
                <RequireAdmin>
                  <RefreshPage />
                </RequireAdmin>
              </RequireAuth>
            }
          />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <AppShell />
      </Router>
    </AuthProvider>
  )
}
