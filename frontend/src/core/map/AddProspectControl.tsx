import { useState, type FormEvent } from 'react'
import { useMapEvents } from 'react-leaflet'
import { locationsApi } from '../api/locations'
import { ApiError } from '../api/client'
import { isPendingReview } from '../api/types'
import { useStopMapClickPropagation } from './useStopMapClickPropagation'

interface Props {
  onCreated: () => void
}

/** Minimal add-prospect flow, per the "pin/address only" scope decision --
 * everything else (property owner, contacts, utilities, pricing) gets
 * filled in later via an edit view, not here. Two entry modes, matching
 * what the backend already supports: click the map to drop a pin, or
 * type an address instead.
 */
export function AddProspectControl({ onCreated }: Props) {
  const [isAdding, setIsAdding] = useState(false)
  const [addressInput, setAddressInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [queuedMessage, setQueuedMessage] = useState<string | null>(null)
  const panelRef = useStopMapClickPropagation<HTMLDivElement>()

  useMapEvents({
    click(event) {
      if (!isAdding || submitting) return
      void createProspect({ latitude: event.latlng.lat, longitude: event.latlng.lng })
    },
  })

  async function createProspect(input: { address?: string; latitude?: number; longitude?: number }) {
    setError(null)
    setQueuedMessage(null)
    setSubmitting(true)
    try {
      const result = await locationsApi.create(input)
      setIsAdding(false)
      setAddressInput('')
      if (isPendingReview(result)) {
        // Validation workflow (ADR-0014) -- the org requires review and
        // this account isn't an admin, so nothing was actually created
        // yet; an admin has to approve it on the Review page first.
        setQueuedMessage('Submitted for review -- an admin needs to approve it before it appears on the map.')
      } else {
        onCreated()
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create prospect')
    } finally {
      setSubmitting(false)
    }
  }

  function handleAddressSubmit(event: FormEvent) {
    event.preventDefault()
    if (!addressInput.trim()) return
    void createProspect({ address: addressInput.trim() })
  }

  return (
    <div
      ref={panelRef}
      className="w-72 rounded-lg border border-slate-200 bg-white p-4 shadow-md"
    >
      <button
        type="button"
        onClick={() => setIsAdding((prev) => !prev)}
        className={`w-full rounded px-3 py-2 text-sm font-medium ${
          isAdding ? 'bg-amber-500 text-white' : 'bg-slate-900 text-white'
        }`}
      >
        {isAdding ? 'Click the map to place a pin…' : '+ Add New Prospect'}
      </button>

      {isAdding && (
        <form onSubmit={handleAddressSubmit} className="mt-3">
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
      )}

      {submitting && <p className="mt-2 text-xs text-slate-500">Creating…</p>}
      {queuedMessage && <p className="mt-2 text-xs text-amber-700">{queuedMessage}</p>}
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  )
}
