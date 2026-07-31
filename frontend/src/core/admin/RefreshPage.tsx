import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import { marketRefreshApi } from '../api/marketRefresh'
import type { RefreshRun } from '../api/types'

/** Market Refresh Engine (Phase 3; ADR-0004, ADR-0020). Re-checks
 * existing locations against free sources (OpenStreetMap address
 * verification, US Census demographics) and queues proposed changes
 * for review -- it never writes to a location directly. Synchronous
 * and bounded (up to 20 locations per run), so it can take up to a
 * minute or so, not instant.
 */
export function RefreshPage() {
  const [runs, setRuns] = useState<RefreshRun[]>([])
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)

  function refresh() {
    marketRefreshApi.listRuns().then(setRuns).catch(() => setError('Could not load run history'))
  }

  useEffect(refresh, [])

  async function handleRun() {
    setError(null)
    setRunning(true)
    try {
      await marketRefreshApi.trigger()
      refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not run refresh')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="mb-1 text-lg font-semibold text-slate-900">Market Refresh</h1>
      <p className="mb-4 text-sm text-slate-500">
        Re-checks existing locations against free sources (OpenStreetMap address verification, US Census
        demographics) and queues proposed changes for review -- nothing is written to a location directly.
        Proposed changes show up on the{' '}
        <Link to="/admin/review" className="underline">
          Review
        </Link>{' '}
        page.
      </p>

      <button
        type="button"
        onClick={handleRun}
        disabled={running}
        className="mb-6 rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {running ? 'Running… this can take up to a minute' : 'Run refresh now'}
      </button>

      {error && <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

      <h2 className="mb-2 text-sm font-semibold text-slate-700">Run history</h2>
      {runs.length === 0 && <p className="text-sm text-slate-500">No runs yet.</p>}
      {runs.length > 0 && (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-slate-500">
              <th className="py-2">Started</th>
              <th className="py-2">Status</th>
              <th className="py-2">Reviewed</th>
              <th className="py-2">Queued</th>
              <th className="py-2">Providers</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id} className="border-b border-slate-100 align-top">
                <td className="py-2">{new Date(run.started_at).toLocaleString()}</td>
                <td className="py-2 capitalize">{run.status}</td>
                <td className="py-2">{run.locations_reviewed}</td>
                <td className="py-2">{run.changes_queued}</td>
                <td className="py-2 text-xs text-slate-500">{run.providers_used.join(', ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
