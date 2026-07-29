import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { validationApi } from '../api/validation'
import type { ValidationQueueItem } from '../api/types'

/** Admin-only review queue for locations submitted by non-admins when
 * the org has "require review" turned on (ADR-0014). A create proposal
 * has `entity_id: null` (nothing exists yet); an update proposal has
 * `entity_id` set and `proposed_changes` holds only the changed fields.
 */
export function ReviewQueuePage() {
  const [items, setItems] = useState<ValidationQueueItem[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)

  function refresh() {
    validationApi
      .listQueue()
      .then(setItems)
      .catch(() => setError('Could not load the review queue'))
  }

  useEffect(refresh, [])

  async function handleApprove(item: ValidationQueueItem) {
    setError(null)
    setBusyId(item.id)
    try {
      await validationApi.approve(item.id)
      refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not approve this submission')
    } finally {
      setBusyId(null)
    }
  }

  async function handleReject(item: ValidationQueueItem) {
    setError(null)
    setBusyId(item.id)
    try {
      await validationApi.reject(item.id)
      refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reject this submission')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="mb-1 text-lg font-semibold text-slate-900">Review queue</h1>
      <p className="mb-4 text-sm text-slate-500">
        Locations submitted by teammates, waiting for approval before they go live.
      </p>

      {error && <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

      {items.length === 0 && <p className="text-sm text-slate-500">Nothing waiting for review.</p>}

      <ul className="space-y-3">
        {items.map((item) => (
          <li key={item.id} className="rounded border border-slate-200 p-3 text-sm">
            <div className="mb-2 flex items-center justify-between">
              <span className="font-medium text-slate-900">
                {item.entity_id ? 'Proposed edit' : 'New location'}
              </span>
              <span className="text-xs text-slate-400">
                {item.submitted_by_email ?? 'unknown'} · {new Date(item.created_at).toLocaleString()}
              </span>
            </div>
            <dl className="mb-3 space-y-0.5 text-xs text-slate-600">
              {Object.entries(item.proposed_changes)
                .filter(([, value]) => value !== null && value !== '')
                .map(([key, value]) => (
                  <div key={key}>
                    <dt className="inline font-medium">{key}: </dt>
                    <dd className="inline">{String(value)}</dd>
                  </div>
                ))}
            </dl>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => handleApprove(item)}
                disabled={busyId === item.id}
                className="rounded bg-slate-900 px-2 py-1 text-xs text-white disabled:opacity-50"
              >
                Approve
              </button>
              <button
                type="button"
                onClick={() => handleReject(item)}
                disabled={busyId === item.id}
                className="rounded border border-red-300 px-2 py-1 text-xs text-red-600 disabled:opacity-50"
              >
                Reject
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
