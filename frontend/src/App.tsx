import { AuthProvider, useAuth } from './core/auth/AuthContext'
import { LoginPage } from './core/auth/LoginPage'
import { MapView } from './core/map/MapView'

function AppShell() {
  const { isAuthenticated, logout } = useAuth()

  if (!isAuthenticated) {
    return <LoginPage />
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2">
        <h1 className="text-sm font-semibold text-slate-900">Ice &amp; Water Intelligence</h1>
        <button type="button" onClick={logout} className="text-sm text-slate-500 hover:text-slate-800">
          Sign out
        </button>
      </header>
      <main className="flex-1">
        <MapView />
      </main>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  )
}
