import { api } from './client'
import type {
  CallNote,
  CreateLocationInput,
  LocationDetail,
  LocationFilters,
  LocationSummary,
  UpdateLocationInput,
} from './types'

interface CalendarLinks {
  google: string
  outlook: string
}

function buildLocationQuery(filters?: LocationFilters): string {
  if (!filters) return ''
  const params = new URLSearchParams()
  for (const status of filters.statuses ?? []) {
    params.append('statuses', status)
  }
  if (filters.serves_ice) params.set('serves_ice', 'true')
  if (filters.serves_water) params.set('serves_water', 'true')
  if (filters.min_opportunity_score != null) {
    params.set('min_opportunity_score', String(filters.min_opportunity_score))
  }
  const query = params.toString()
  return query ? `?${query}` : ''
}

export const locationsApi = {
  list: (filters?: LocationFilters) => api.get<LocationSummary[]>(`/locations${buildLocationQuery(filters)}`),
  get: (id: string) => api.get<LocationDetail>(`/locations/${id}`),
  create: (input: CreateLocationInput) => api.post<LocationDetail>('/locations', input),
  update: (id: string, input: UpdateLocationInput) =>
    api.put<LocationDetail>(`/locations/${id}`, input),
  archive: (id: string) => api.delete<void>(`/locations/${id}`),
  recalculateScore: (id: string) => api.post<LocationDetail>(`/locations/${id}/recalculate-score`),
  listCallNotes: (id: string) => api.get<CallNote[]>(`/locations/${id}/call-notes`),
  addCallNote: (id: string, noteText: string, followUpAt?: string) =>
    api.post<CallNote>(`/locations/${id}/call-notes`, { note_text: noteText, follow_up_at: followUpAt }),
  // The endpoint requires auth and returns JSON with both providers'
  // URLs -- it is not itself a redirect, so it can't be a plain <a href>.
  getCalendarLinks: (locationId: string, noteId: number) =>
    api.get<CalendarLinks>(`/locations/${locationId}/call-notes/${noteId}/calendar-link`),
}
