import { useState, type FormEvent } from 'react'
import { useMapEvents } from 'react-leaflet'
import { competitorsApi } from '../api/competitors'
import { ApiError } from '../api/client'
import { parseMapsListing } from './parseMapsListing'
import { useStopMapClickPropagation } from './useStopMapClickPropagation'

interface Props {
  onCreated: () => void
}

/** Mirrors AddProspectControl's pin/address minimal-entry pattern (ADR-0007)
 * plus a required name (brand/operator), since an unnamed competitor pin
 * isn't useful. Everything else (ice/water, price, size) is filled in
 * afterward via the detail panel -- same split as prospects.
 */
export function AddCompetitorControl({ onCreated }: Props) {
  const [isAdding, setIsAdding] = useState(false)
  const [addressInput, setAddressInput] = useState('')
  const [nameInput, setNameInput] = useState('')
  const [pasteInput, setPasteInput] = useState('')
  const [pendingLatLng, setPendingLatLng] = useState<{ lat: number; lng: number } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const panelRef = useStopMapClickPropagation<HTMLDivElement>()

  function handleFillFromPaste() {
    const { name, address } = parseMapsListing(pasteInput)
    if (name) setNameInput(name)
    if (address) setAddressInput(address)
    if (!name && !address) {
      setError('Could not find a name or address in that text -- fill in the fields below by hand')
    }
  }

  useMapEvents({
    click(event) {
      if (!isAdding || submitting) return
      setPendingLatLng({ lat: event.latlng.lat, lng: event.latlng.lng })
    },
  })

  async function createCompetitor(input: { address?: string; latitude?: number; longitude?: number }) {
    if (!nameInput.trim()) {
      setError('Name (brand/operator) is required')
      return
    }
    setError(null)
    setSubmitting(true)
    try {
      await competitorsApi.create({ ...input, name: nameInput.trim() })
      setIsAdding(false)
      setAddressInput('')
      setNameInput('')
      setPendingLatLng(null)
      onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create competitor')
    } finally {
      setSubmitting(false)
    }
  }

  function handleAddressSubmit(event: FormEvent) {
    event.preventDefault()
    if (!addressInput.trim()) return
    void createCompetitor({ address: addressInput.trim() })
  }

  function handlePinSubmit(event: FormEvent) {
    event.preventDefault()
    if (!pendingLatLng) return
    void createCompetitor({ latitude: pendingLatLng.lat, longitude: pendingLatLng.lng })
  }

  return (
    <div
      ref={panelRef}
      className="absolute top-4 right-4 z-[1000] mt-20 w-72 rounded-lg border border-slate-200 bg-white p-4 shadow-md"
    >
      <button
        type="button"
        onClick={() => setIsAdding((prev) => !prev)}
        className={`w-full rounded px-3 py-2 text-sm font-medium ${
          isAdding ? 'bg-orange-600 text-white' : 'bg-slate-900 text-white'
        }`}
      >
        {isAdding ? 'Click the map to place a competitor…' : '+ Add Competitor'}
      </button>

      {isAdding && (
        <div className="mt-3 space-y-2">
          <div className="rounded border border-dashed border-slate-300 p-2">
            <label className="mb-1 block text-xs text-slate-500">
              Paste text copied from a Google/Bing Maps listing
            </label>
            <textarea
              value={pasteInput}
              onChange={(e) => setPasteInput(e.target.value)}
              placeholder={'Twice the Ice\n123 Main St, Denver, CO 80202'}
              rows={2}
              className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
            />
            <button
              type="button"
              onClick={handleFillFromPaste}
              disabled={!pasteInput.trim()}
              className="mt-1 rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 disabled:opacity-50"
            >
              Fill in fields below
            </button>
            <p className="mt-1 text-[10px] text-slate-400">
              Best-effort text match, not automated lookup -- check the fields before saving.
            </p>
          </div>

          <input
            type="text"
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
            placeholder="Brand/operator name"
            className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
          />

          {pendingLatLng && (
            <form onSubmit={handlePinSubmit} className="flex gap-2">
              <p className="flex-1 self-center text-xs text-slate-500">
                Pin placed at {pendingLatLng.lat.toFixed(4)}, {pendingLatLng.lng.toFixed(4)}
              </p>
              <button
                type="submit"
                disabled={submitting}
                className="shrink-0 rounded bg-orange-600 px-3 py-1 text-sm text-white disabled:opacity-50"
              >
                Save
              </button>
            </form>
          )}

          <form onSubmit={handleAddressSubmit}>
            <label className="mb-1 block text-xs text-slate-500">…or enter an address instead</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={addressInput}
                onChange={(e) => setAddressInput(e.target.value)}
                placeholder="123 Main St, Denver, CO"
                className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
              />
              <button
                type="submit"
                disabled={submitting}
                className="shrink-0 rounded bg-slate-700 px-3 py-1 text-sm text-white disabled:opacity-50"
              >
                Add
              </button>
            </div>
          </form>
        </div>
      )}

      {submitting && <p className="mt-2 text-xs text-slate-500">Creating…</p>}
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  )
}
