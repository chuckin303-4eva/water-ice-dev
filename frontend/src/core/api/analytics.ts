import { api } from './client'
import type { AnalyticsSummary } from './types'

export const analyticsApi = {
  getSummary: () => api.get<AnalyticsSummary>('/analytics/summary'),
}
