import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { authApi, type CurrentUser } from '../api/auth'
import { clearToken, getToken, setToken } from '../api/client'

interface AuthContextValue {
  isAuthenticated: boolean
  currentUser: CurrentUser | null
  login: (email: string, password: string) => Promise<void>
  register: (organizationName: string, email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(() => getToken() !== null)
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null)

  useEffect(() => {
    if (isAuthenticated) {
      authApi.me().then(setCurrentUser).catch(() => setCurrentUser(null))
    } else {
      setCurrentUser(null)
    }
  }, [isAuthenticated])

  async function login(email: string, password: string) {
    const tokens = await authApi.login(email, password)
    setToken(tokens.access_token)
    setIsAuthenticated(true)
  }

  async function register(organizationName: string, email: string, password: string) {
    const tokens = await authApi.register(organizationName, email, password)
    setToken(tokens.access_token)
    setIsAuthenticated(true)
  }

  function logout() {
    clearToken()
    setIsAuthenticated(false)
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, currentUser, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
