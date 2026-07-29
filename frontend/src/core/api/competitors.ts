import { api } from './client'
import type {
  CompetitorDetail,
  CompetitorSummary,
  CreateCompetitorInput,
  UpdateCompetitorInput,
} from './types'

export const competitorsApi = {
  list: () => api.get<CompetitorSummary[]>('/competitors'),
  get: (id: string) => api.get<CompetitorDetail>(`/competitors/${id}`),
  create: (input: CreateCompetitorInput) => api.post<CompetitorDetail>('/competitors', input),
  update: (id: string, input: UpdateCompetitorInput) =>
    api.put<CompetitorDetail>(`/competitors/${id}`, input),
  remove: (id: string) => api.delete<void>(`/competitors/${id}`),
}
