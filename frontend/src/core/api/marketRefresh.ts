import { api } from './client'
import type { RefreshRun } from './types'

export const marketRefreshApi = {
  trigger: () => api.post<RefreshRun>('/market-refresh/runs'),
  listRuns: () => api.get<RefreshRun[]>('/market-refresh/runs'),
}
