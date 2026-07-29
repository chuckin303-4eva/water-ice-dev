import { useState } from 'react'
import { competitorsApi } from '../api/competitors'
import { ApiError, downloadBlob } from '../api/client'
import { locationsApi } from '../api/locations'
import type { CompetitorFilters, LocationFilters } from '../api/types'
import { useStopMapClickPropagation } from './useStopMapClickPropagation'

const ALL_STATUSES = ['prospect', 'active', 'archived']

export interface FiltersState {
  statuses: string[]
  servesIce: boolean
  servesWater: boolean
  minOpportunityScore: string
  showCompetitors: boolean
}

export const DEFAULT_FILTERS: FiltersState = {
  statuses: ALL_STATUSES,
  servesIce: false,
  servesWater: false,
  minOpportunityScore: '',
  showCompetitors: true,
}

export function toLocationFilters(filters: FiltersState): LocationFilters {
  return {
    statuses: filters.statuses.length < ALL_STATUSES.length ? filters.statuses : undefined,
    serves_ice: filters.servesIce || undefined,
    serves_water: filters.servesWater || undefined,
    min_opportunity_score: filters.minOpportunityScore === '' ? undefined : Number(filters.minOpportunityScore),
  }
}

export function toCompetitorFilters(filters: FiltersState): CompetitorFilters {
  return {
    serves_ice: filters.servesIce || undefined,
    serves_water: filters.servesWater || undefined,
  }
}

interface Props {
  filters: FiltersState
  onChange: (filters: FiltersState) => void
}

/** Ice/water checkboxes are opt-in narrowing, not exclusion -- leaving
 * both unchecked applies no capability filter at all. A brand-new
 * prospect has both serves_ice/serves_water false until someone fills
 * them in, so an exclude-based filter would make every fresh prospect
 * vanish the moment this panel is touched (see ADR for this feature).
 */
export function FilterPanel({ filters, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const [exporting, setExporting] = useState<'locations' | 'competitors' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const panelRef = useStopMapClickPropagation<HTMLDivElement>()

  function toggleStatus(status: string) {
    const next = filters.statuses.includes(status)
      ? filters.statuses.filter((s) => s !== status)
      : [...filters.statuses, status]
    onChange({ ...filters, statuses: next })
  }

  async function handleExportLocations() {
    setError(null)
    setExporting('locations')
    try {
      const blob = await locationsApi.exportCsv(toLocationFilters(filters))
      downloadBlob(blob, 'locations.csv')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not export locations')
    } finally {
      setExporting(null)
    }
  }

  async function handleExportCompetitors() {
    setError(null)
    setExporting('competitors')
    try {
      const blob = await competitorsApi.exportCsv(toCompetitorFilters(filters))
      downloadBlob(blob, 'competitors.csv')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not export competitors')
    } finally {
      setExporting(null)
    }
  }

  const activeCount =
    (filters.statuses.length < ALL_STATUSES.length ? 1 : 0) +
    (filters.servesIce ? 1 : 0) +
    (filters.servesWater ? 1 : 0) +
    (filters.minOpportunityScore !== '' ? 1 : 0) +
    (filters.showCompetitors ? 0 : 1)

  return (
    <div
      ref={panelRef}
      className="absolute bottom-4 left-4 z-[1000] w-56 rounded-lg border border-slate-200 bg-white p-2 text-xs shadow-md"
    >
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="w-full rounded bg-slate-900 px-2 py-1.5 font-medium text-white"
      >
        Filters{activeCount > 0 ? ` (${activeCount})` : ''}
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          <div>
            <p className="mb-1 font-semibold text-slate-700">Status</p>
            {ALL_STATUSES.map((status) => (
              <label key={status} className="flex items-center gap-2 capitalize text-slate-600">
                <input
                  type="checkbox"
                  checked={filters.statuses.includes(status)}
                  onChange={() => toggleStatus(status)}
                />
                {status}
              </label>
            ))}
          </div>

          <div>
            <p className="mb-1 font-semibold text-slate-700">Requires (optional)</p>
            <label className="flex items-center gap-2 text-slate-600">
              <input
                type="checkbox"
                checked={filters.servesIce}
                onChange={(e) => onChange({ ...filters, servesIce: e.target.checked })}
              />
              Serves ice
            </label>
            <label className="flex items-center gap-2 text-slate-600">
              <input
                type="checkbox"
                checked={filters.servesWater}
                onChange={(e) => onChange({ ...filters, servesWater: e.target.checked })}
              />
              Serves water
            </label>
          </div>

          <div>
            <label className="mb-1 block font-semibold text-slate-700">Min. opportunity score</label>
            <input
              type="number"
              min={0}
              max={100}
              value={filters.minOpportunityScore}
              onChange={(e) => onChange({ ...filters, minOpportunityScore: e.target.value })}
              placeholder="e.g. 50"
              className="w-full rounded border border-slate-300 px-2 py-1"
            />
          </div>

          <label className="flex items-center gap-2 text-slate-600">
            <input
              type="checkbox"
              checked={filters.showCompetitors}
              onChange={(e) => onChange({ ...filters, showCompetitors: e.target.checked })}
            />
            Show competitors
          </label>

          <button
            type="button"
            onClick={() => onChange(DEFAULT_FILTERS)}
            className="w-full rounded border border-slate-300 px-2 py-1 text-slate-600"
          >
            Reset
          </button>

          <div className="border-t border-slate-100 pt-2">
            <p className="mb-1 font-semibold text-slate-700">Export (matches filters above)</p>
            <div className="flex gap-1">
              <button
                type="button"
                onClick={handleExportLocations}
                disabled={exporting !== null}
                className="flex-1 rounded border border-slate-300 px-2 py-1 text-slate-600 disabled:opacity-50"
              >
                {exporting === 'locations' ? 'Exporting…' : 'Locations'}
              </button>
              <button
                type="button"
                onClick={handleExportCompetitors}
                disabled={exporting !== null}
                className="flex-1 rounded border border-slate-300 px-2 py-1 text-slate-600 disabled:opacity-50"
              >
                {exporting === 'competitors' ? 'Exporting…' : 'Competitors'}
              </button>
            </div>
          </div>

          {error && <p className="text-red-600">{error}</p>}
        </div>
      )}
    </div>
  )
}
