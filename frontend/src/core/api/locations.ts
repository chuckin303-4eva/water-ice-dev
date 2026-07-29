import { api } from './client'
import type { CallNote, CreateLocationInput, LocationDetail, LocationSummary } from './types'

interface CalendarLinks {
  google: string
  outlook: string
}

export const locationsApi = {
  list: () => api.get<LocationSummary[]>('/locations'),
  get: (id: string) => api.get<LocationDetail>(`/locations/${id}`),
  create: (input: CreateLocationInput) => api.post<LocationDetail>('/locations', input),
  update: (id: string, input: Partial<CreateLocationInput>) =>
    api.put<LocationDetail>(`/locations/${id}`, input),
  archive: (id: string) => api.delete<void>(`/locations/${id}`),
  listCallNotes: (id: string) => api.get<CallNote[]>(`/locations/${id}/call-notes`),
  addCallNote: (id: string, noteText: string, followUpAt?: string) =>
    api.post<CallNote>(`/locations/${id}/call-notes`, { note_text: noteText, follow_up_at: followUpAt }),
  // The endpoint requires auth and returns JSON with both providers'
  // URLs -- it is not itself a redirect, so it can't be a plain <a href>.
  getCalendarLinks: (locationId: string, noteId: number) =>
    api.get<CalendarLinks>(`/locations/${locationId}/call-notes/${noteId}/calendar-link`),
}
