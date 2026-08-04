import { useEffect, useState } from 'react'
import { analyticsApi } from '../api/analytics'
import type { AnalyticsSummary, LocationSummaryRow } from '../api/types'

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-slate-200 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-lg font-semibold text-slate-900">{value}</p>
    </div>
  )
}

/** Hand-rolled horizontal bar list -- no charting library added for this,
 * since a handful of labeled bars is all Phase 4's first analytics pass
 * needs (ADR-0021); revisit if a future view needs real chart interactions.
 */
function BarList({ data, colorClass }: { data: Record<string, number>; colorClass: string }) {
  const max = Math.max(1, ...Object.values(data))
  return (
    <div className="space-y-1.5">
      {Object.entries(data).map(([label, value]) => (
        <div key={label} className="flex items-center gap-2 text-xs">
          <span className="w-24 shrink-0 truncate capitalize text-slate-500">{label}</span>
          <div className="h-3 flex-1 rounded bg-slate-100">
            <div className={`h-3 rounded ${colorClass}`} style={{ width: `${(value / max) * 100}%` }} />
          </div>
          <span className="w-6 shrink-0 text-right text-slate-700">{value}</span>
        </div>
      ))}
    </div>
  )
}

function LocationRowTable({
  rows,
  metricLabel,
  metric,
}: {
  rows: LocationSummaryRow[]
  metricLabel: string
  metric: (row: LocationSummaryRow) => string
}) {
  if (rows.length === 0) {
    return <p className="text-xs text-slate-400">No data yet.</p>
  }
  return (
    <table className="w-full text-left text-xs">
      <thead>
        <tr className="border-b border-slate-200 text-slate-500">
          <th className="py-1.5">Address</th>
          <th className="py-1.5">Market</th>
          <th className="py-1.5">{metricLabel}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id} className="border-b border-slate-100">
            <td className="py-1.5">{row.address}</td>
            <td className="py-1.5">
              {row.city_name}, {row.state_code}
            </td>
            <td className="py-1.5">{metric(row)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/** Advanced analytics (Phase 4; ADR-0021). Pure aggregation over data
 * already collected by Phases 1-3 (scoring, Market Refresh demographics,
 * competitor tracking, and the pipeline this same phase adds) -- no new
 * external calls, no new cost. Location/competitor/demographic numbers
 * are platform-wide (ADR-0002); the pipeline funnel is this org's own.
 */
export function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    analyticsApi.getSummary().then(setSummary).catch(() => setError('Could not load analytics'))
  }, [])

  if (error) {
    return <p className="p-6 text-sm text-red-600">{error}</p>
  }
  if (!summary) {
    return <p className="p-6 text-sm text-slate-500">Loading…</p>
  }

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="mb-1 text-lg font-semibold text-slate-900">Analytics</h1>
      <p className="mb-4 text-sm text-slate-500">
        Portfolio-wide location and market data plus your organization's pursuit pipeline.
      </p>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Total locations" value={String(summary.total_locations)} />
        <StatTile
          label="Avg. opportunity score"
          value={summary.average_opportunity_score != null ? summary.average_opportunity_score.toFixed(1) : '—'}
        />
        <StatTile label="Unscored prospects" value={String(summary.unscored_count)} />
        <StatTile label="Tracked competitors" value={String(summary.total_competitors)} />
      </div>

      <div className="mb-6 grid grid-cols-1 gap-6 sm:grid-cols-2">
        <div>
          <h2 className="mb-2 text-sm font-semibold text-slate-700">Portfolio by status</h2>
          <BarList data={summary.status_breakdown} colorClass="bg-slate-700" />
        </div>
        <div>
          <h2 className="mb-2 text-sm font-semibold text-slate-700">Opportunity score distribution</h2>
          <BarList data={summary.score_buckets} colorClass="bg-emerald-600" />
        </div>
        <div>
          <h2 className="mb-2 text-sm font-semibold text-slate-700">Your pipeline</h2>
          <BarList data={summary.pipeline_funnel} colorClass="bg-blue-600" />
        </div>
      </div>

      <div className="mb-6">
        <h2 className="mb-2 text-sm font-semibold text-slate-700">Top prospects</h2>
        <LocationRowTable
          rows={summary.top_prospects}
          metricLabel="Score"
          metric={(row) => (row.opportunity_score != null ? row.opportunity_score.toFixed(0) : '—')}
        />
      </div>

      <div className="mb-6">
        <h2 className="mb-2 text-sm font-semibold text-slate-700">Fastest-growing markets</h2>
        <LocationRowTable
          rows={summary.growth_markets}
          metricLabel="Growth"
          metric={(row) => (row.growth_rate != null ? `${row.growth_rate > 0 ? '+' : ''}${row.growth_rate}%` : '—')}
        />
      </div>

      <div>
        <h2 className="mb-2 text-sm font-semibold text-slate-700">Most contested markets</h2>
        <LocationRowTable
          rows={summary.most_contested_markets}
          metricLabel="Competition"
          metric={(row) => (row.competition_score != null ? row.competition_score.toFixed(1) : '—')}
        />
      </div>
    </div>
  )
}
