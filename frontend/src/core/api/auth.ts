import { api } from './client'

interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface CurrentUser {
  id: number
  organization_id: number
  email: string
  is_active: boolean
  role: 'admin' | 'member'
}

export const authApi = {
  login: (email: string, password: string) =>
    api.post<TokenResponse>('/auth/login', { email, password }),
  register: (organizationName: string, email: string, password: string) =>
    api.post<TokenResponse>('/auth/register', {
      organization_name: organizationName,
      email,
      password,
    }),
  me: () => api.get<CurrentUser>('/auth/me'),
}
