import { api } from './client'
import type { Brand, CreateBrandInput } from './types'

export const brandsApi = {
  list: (search?: string) =>
    api.get<Brand[]>(`/brands${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  create: (input: CreateBrandInput) => api.post<Brand>('/brands', input),
}
