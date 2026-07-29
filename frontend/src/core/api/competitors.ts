import { api } from './client'
import type {
  CompetitorCalendarLinks,
  CompetitorDetail,
  CompetitorFilters,
  CompetitorSummary,
  CreateCompetitorInput,
  UpdateCompetitorInput,
} from './types'

function buildCompetitorQuery(filters?: CompetitorFilters): string {
  if (!filters) return ''
  const params = new URLSearchParams()
  if (filters.serves_ice) params.set('serves_ice', 'true')
  if (filters.serves_water) params.set('serves_water', 'true')
  if (filters.brand) params.set('brand', filters.brand)
  const query = params.toString()
  return query ? `?${query}` : ''
}

export const competitorsApi = {
  list: (filters?: CompetitorFilters) =>
    api.get<CompetitorSummary[]>(`/competitors${buildCompetitorQuery(filters)}`),
  get: (id: string) => api.get<CompetitorDetail>(`/competitors/${id}`),
  create: (input: CreateCompetitorInput) => api.post<CompetitorDetail>('/competitors', input),
  update: (id: string, input: UpdateCompetitorInput) =>
    api.put<CompetitorDetail>(`/competitors/${id}`, input),
  remove: (id: string) => api.delete<void>(`/competitors/${id}`),
  getCalendarLinks: (id: string) => api.get<CompetitorCalendarLinks>(`/competitors/${id}/calendar-link`),
  exportCsv: (filters?: CompetitorFilters) =>
    api.getBlob(`/competitors/export${buildCompetitorQuery(filters)}`),
}
