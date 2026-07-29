import { api } from './client'
import type { LocationDetail, ValidationQueueItem } from './types'

export const validationApi = {
  listQueue: () => api.get<ValidationQueueItem[]>('/validation-queue'),
  approve: (id: number) => api.post<LocationDetail>(`/validation-queue/${id}/approve`),
  reject: (id: number, reason?: string) =>
    api.post<ValidationQueueItem>(`/validation-queue/${id}/reject`, { reason }),
}
