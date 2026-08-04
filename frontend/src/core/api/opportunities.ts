import { api } from './client'
import type { CreateOpportunityInput, Opportunity, UpdateOpportunityInput } from './types'

export const opportunitiesApi = {
  list: (locationId?: string) =>
    api.get<Opportunity[]>(`/opportunities${locationId ? `?location_id=${locationId}` : ''}`),
  create: (input: CreateOpportunityInput) => api.post<Opportunity>('/opportunities', input),
  update: (id: string, input: UpdateOpportunityInput) => api.put<Opportunity>(`/opportunities/${id}`, input),
  remove: (id: string) => api.delete<void>(`/opportunities/${id}`),
}
