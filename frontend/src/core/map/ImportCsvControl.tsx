import { useRef, useState } from 'react'
import { locationsApi } from '../api/locations'
import { ApiError } from '../api/client'
import type { LocationImportSummary } from '../api/types'
import { useStopMapClickPropagation } from './useStopMapClickPropagation'

interface Props {
  onImported: () => void
}

/** Minimal v1 column set -- address (or latitude/longitude), serves_ice,
 * serves_water, notes -- everything else gets filled in later via the
 * detail panel, same split as every other "minimal add" flow (ADR-0007).
 * Rows are geocoded one at a time server-side with a rate-limit delay
 * (ADR-0011), so a large file can take a while -- the button disables
 * and shows progress rather than looking hung.
 */
export function ImportCsvControl({ onImported }: Props) {
  const [uploading, setUploading] = useState(false)
  const [summary, setSummary] = useState<LocationImportSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const panelRef = useStopMapClickPropagation<HTMLDivElement>()

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = '' // allow re-selecting the same file later
    if (!file) return

    setUploading(true)
    setError(null)
    setSummary(null)
    try {
      const result = await locationsApi.importCsv(file)
      setSummary(result)
      onImported()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not import file')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div
      ref={panelRef}
      className="absolute bottom-4 left-64 z-[1000] w-56 rounded-lg border border-slate-200 bg-white p-2 text-xs shadow-md"
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        onChange={handleFileChange}
        className="hidden"
      />
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={uploading}
        className="w-full rounded bg-slate-900 px-2 py-1.5 font-medium text-white disabled:opacity-50"
      >
        {uploading ? 'Importing…' : 'Import CSV'}
      </button>
      <p className="mt-1 text-slate-400">
        Columns: address (or latitude/longitude), serves_ice, serves_water, notes. Max 100 rows.
      </p>

      {summary && (
        <div className="mt-2 space-y-1">
          <p className="text-slate-700">
            Created {summary.created} of {summary.total_rows} rows.
          </p>
          {summary.queued > 0 && (
            <p className="text-amber-700">
              {summary.queued} row{summary.queued === 1 ? '' : 's'} submitted for review -- an admin
              needs to approve them first.
            </p>
          )}
          {summary.errors.length > 0 && (
            <ul className="max-h-32 space-y-0.5 overflow-y-auto text-red-600">
              {summary.errors.map((e) => (
                <li key={e.row}>
                  Row {e.row}: {e.message}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {error && <p className="mt-2 text-red-600">{error}</p>}
    </div>
  )
}
