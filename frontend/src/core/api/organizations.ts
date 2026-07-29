import { api } from './client'

export interface OrgUser {
  id: number
  email: string
  is_active: boolean
  role: 'admin' | 'member'
  created_at: string
}

export interface CreateOrgUserInput {
  email: string
  password: string
  role: 'admin' | 'member'
}

export interface UpdateOrgUserInput {
  is_active?: boolean
  role?: 'admin' | 'member'
}

export const organizationsApi = {
  listUsers: () => api.get<OrgUser[]>('/organizations/users'),
  createUser: (input: CreateOrgUserInput) => api.post<OrgUser>('/organizations/users', input),
  updateUser: (userId: number, input: UpdateOrgUserInput) =>
    api.put<OrgUser>(`/organizations/users/${userId}`, input),
}
