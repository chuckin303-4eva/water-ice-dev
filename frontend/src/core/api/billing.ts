import { api } from './client'
import type { Invoice, Plan, Subscription } from './types'

export const billingApi = {
  listPlans: () => api.get<Plan[]>('/billing/plans'),
  getSubscription: () => api.get<Subscription>('/billing/subscription'),
  subscribe: (planSlug: string) => api.post<Subscription>('/billing/subscribe', { plan_slug: planSlug }),
  cancel: () => api.post<Subscription>('/billing/cancel'),
  listInvoices: () => api.get<Invoice[]>('/billing/invoices'),
}
