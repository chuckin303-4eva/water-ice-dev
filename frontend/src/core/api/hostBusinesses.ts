import { api } from './client'
import type { CreateHostBusinessInput, HostBusiness } from './types'

export const hostBusinessesApi = {
  list: (search?: string) =>
    api.get<HostBusiness[]>(`/host-businesses${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  create: (input: CreateHostBusinessInput) => api.post<HostBusiness>('/host-businesses', input),
}
