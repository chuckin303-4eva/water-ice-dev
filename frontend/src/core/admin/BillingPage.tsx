import { useEffect, useState } from 'react'
import { billingApi } from '../api/billing'
import { ApiError } from '../api/client'
import type { Invoice, Plan, Subscription } from '../api/types'

function formatCents(cents: number): string {
  return cents === 0 ? 'Free' : `$${(cents / 100).toFixed(2)}/mo`
}

/** Subscriptions & billing (Phase 3; ADR-0019). Backed by a mock billing
 * provider -- no real payment processor is connected, so this page can
 * be fully exercised (subscribe, switch plans, cancel, invoice history)
 * without signing up for anything. The banner below says so plainly,
 * same "don't fake what isn't built" pattern as this app's other
 * disclosed gaps (e.g. no email service, ADR-0012).
 */
export function BillingPage() {
  const [plans, setPlans] = useState<Plan[]>([])
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  function refresh() {
    billingApi.getSubscription().then(setSubscription).catch(() => setError('Could not load subscription'))
    billingApi.listInvoices().then(setInvoices).catch(() => setError('Could not load invoices'))
  }

  useEffect(() => {
    billingApi.listPlans().then(setPlans).catch(() => setError('Could not load plans'))
    refresh()
  }, [])

  async function handleSubscribe(planSlug: string) {
    setError(null)
    setBusy(true)
    try {
      const updated = await billingApi.subscribe(planSlug)
      setSubscription(updated)
      refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not subscribe')
    } finally {
      setBusy(false)
    }
  }

  async function handleCancel() {
    setError(null)
    setBusy(true)
    try {
      const updated = await billingApi.cancel()
      setSubscription(updated)
      refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not cancel')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="mb-1 text-lg font-semibold text-slate-900">Billing</h1>
      <p className="mb-4 text-sm text-slate-500">Manage your organization's plan and view billing history.</p>

      <div className="mb-4 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
        <strong>Demo mode.</strong> No real payment processor is connected -- subscribing or switching plans
        here does not charge a real card. This exercises the full billing flow (plans, upgrade/downgrade,
        cancel, invoice history) end to end with a simulated provider.
      </div>

      {error && <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

      {subscription && (
        <div className="mb-6 rounded border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm text-slate-500">Current plan</p>
          <p className="text-lg font-semibold text-slate-900">
            {subscription.plan.name} -- {formatCents(subscription.plan.price_cents)}
          </p>
          {subscription.current_period_end && (
            <p className="mt-1 text-xs text-slate-500">
              Renews {new Date(subscription.current_period_end).toLocaleDateString()}
            </p>
          )}
          {subscription.plan.slug !== 'free' && (
            <button
              type="button"
              onClick={handleCancel}
              disabled={busy}
              className="mt-3 rounded border border-red-300 px-3 py-1.5 text-sm text-red-600 disabled:opacity-50"
            >
              Cancel subscription
            </button>
          )}
        </div>
      )}

      <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {plans.map((plan) => {
          const isCurrent = subscription?.plan.slug === plan.slug
          return (
            <div key={plan.slug} className="flex flex-col rounded border border-slate-200 p-4">
              <h2 className="text-sm font-semibold text-slate-900">{plan.name}</h2>
              <p className="mb-2 text-lg font-semibold text-slate-700">{formatCents(plan.price_cents)}</p>
              <ul className="mb-4 flex-1 space-y-1 text-xs text-slate-600">
                {plan.features.map((feature) => (
                  <li key={feature}>• {feature}</li>
                ))}
              </ul>
              <button
                type="button"
                disabled={isCurrent || busy}
                onClick={() => (plan.slug === 'free' ? handleCancel() : handleSubscribe(plan.slug))}
                className="rounded bg-slate-900 px-3 py-1.5 text-sm text-white disabled:opacity-50"
              >
                {isCurrent ? 'Current plan' : plan.slug === 'free' ? 'Downgrade to Free' : 'Subscribe'}
              </button>
            </div>
          )
        })}
      </div>

      <h2 className="mb-2 text-sm font-semibold text-slate-700">Invoice history</h2>
      {invoices.length === 0 && <p className="text-sm text-slate-500">No invoices yet.</p>}
      {invoices.length > 0 && (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-slate-500">
              <th className="py-2">Date</th>
              <th className="py-2">Plan</th>
              <th className="py-2">Amount</th>
              <th className="py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((invoice) => (
              <tr key={invoice.id} className="border-b border-slate-100">
                <td className="py-2">{new Date(invoice.issued_at).toLocaleDateString()}</td>
                <td className="py-2 capitalize">{invoice.plan_slug}</td>
                <td className="py-2">${(invoice.amount_cents / 100).toFixed(2)}</td>
                <td className="py-2 capitalize">{invoice.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
