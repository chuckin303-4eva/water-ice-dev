import { useState, type FormEvent } from 'react'
import { useMapEvents } from 'react-leaflet'
import { competitorsApi } from '../api/competitors'
import { ApiError } from '../api/client'
import type { CompetitorCalendarLinks } from '../api/types'
import { useStopMapClickPropagation } from './useStopMapClickPropagation'

interface Props {
  onCreated: () => void
}

const BRAND_SUGGESTIONS = ['Twice the Ice', 'Kooler Ice', 'Watermill Express']

const EMPTY_FORM = {
  name: '',
  brand: '',
  address: '',
  website: '',
  phone: '',
  contactName: '',
  email: '',
  followUpAt: '',
}

/** Compact manual-entry form -- plain fields, no auto-matching, per the
 * user's explicit preference over the earlier paste-and-parse UI. Click
 * the map or type an address; everything else (ice/water, price, size)
 * still gets filled in later via the detail panel, same minimal-add
 * split as prospects (ADR-0007).
 */
export function AddCompetitorControl({ onCreated }: Props) {
  const [isAdding, setIsAdding] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [pendingLatLng, setPendingLatLng] = useState<{ lat: number; lng: number } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [calendarLinks, setCalendarLinks] = useState<CompetitorCalendarLinks | null>(null)
  const panelRef = useStopMapClickPropagation<HTMLDivElement>()

  useMapEvents({
    click(event) {
      if (!isAdding || submitting) return
      setPendingLatLng({ lat: event.latlng.lat, lng: event.latlng.lng })
      setForm((prev) => ({ ...prev, address: '' }))
    },
  })

  function updateField<K extends keyof typeof EMPTY_FORM>(key: K, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!form.name.trim()) {
      setError('Location name is required')
      return
    }
    if (!pendingLatLng && !form.address.trim()) {
      setError('Click the map or enter an address')
      return
    }
    setError(null)
    setSubmitting(true)
    setCalendarLinks(null)
    try {
      const created = await competitorsApi.create({
        ...(pendingLatLng
          ? { latitude: pendingLatLng.lat, longitude: pendingLatLng.lng }
          : { address: form.address.trim() }),
        name: form.name.trim(),
        brand: form.brand.trim() || undefined,
        website: form.website.trim() || undefined,
        phone: form.phone.trim() || undefined,
        contact_name: form.contactName.trim() || undefined,
        contact_email: form.email.trim() || undefined,
        follow_up_at: form.followUpAt ? new Date(form.followUpAt).toISOString() : undefined,
      })
      onCreated()
      if (form.followUpAt) {
        const links = await competitorsApi.getCalendarLinks(created.id)
        setCalendarLinks(links)
      } else {
        setForm(EMPTY_FORM)
        setPendingLatLng(null)
        setIsAdding(false)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create competitor')
    } finally {
      setSubmitting(false)
    }
  }

  function handleDone() {
    setForm(EMPTY_FORM)
    setPendingLatLng(null)
    setCalendarLinks(null)
    setIsAdding(false)
  }

  return (
    <div
      ref={panelRef}
      className="absolute top-4 right-4 z-[1000] mt-20 w-60 rounded-lg border border-slate-200 bg-white p-2 shadow-md"
    >
      <button
        type="button"
        onClick={() => setIsAdding((prev) => !prev)}
        className={`w-full rounded px-2 py-1.5 text-xs font-medium ${
          isAdding ? 'bg-orange-600 text-white' : 'bg-slate-900 text-white'
        }`}
      >
        {isAdding ? (pendingLatLng ? 'Pin placed -- fill in below' : 'Click map or fill in below') : '+ Add Competitor'}
      </button>

      {isAdding && calendarLinks && (
        <div className="mt-2 space-y-1 text-xs">
          <p className="text-slate-600">Competitor saved. Add the follow-up to your calendar:</p>
          <div className="flex gap-1">
            <a
              href={calendarLinks.google}
              target="_blank"
              rel="noopener"
              className="flex-1 rounded bg-slate-700 px-2 py-1 text-center text-white"
            >
              Google
            </a>
            <a
              href={calendarLinks.outlook}
              target="_blank"
              rel="noopener"
              className="flex-1 rounded bg-slate-700 px-2 py-1 text-center text-white"
            >
              Outlook
            </a>
          </div>
          <button type="button" onClick={handleDone} className="w-full rounded border border-slate-300 px-2 py-1">
            Done
          </button>
        </div>
      )}

      {isAdding && !calendarLinks && (
        <form onSubmit={handleSubmit} className="mt-2 space-y-1 text-xs">
          <input
            type="text"
            value={form.name}
            onChange={(e) => updateField('name', e.target.value)}
            placeholder="Location name *"
            className="w-full rounded border border-slate-300 px-1.5 py-1"
          />
          <input
            type="text"
            list="brand-suggestions"
            value={form.brand}
            onChange={(e) => updateField('brand', e.target.value)}
            placeholder="Brand"
            className="w-full rounded border border-slate-300 px-1.5 py-1"
          />
          <datalist id="brand-suggestions">
            {BRAND_SUGGESTIONS.map((b) => (
              <option key={b} value={b} />
            ))}
          </datalist>

          {pendingLatLng ? (
            <p className="rounded bg-slate-50 px-1.5 py-1 text-slate-500">
              Pin at {pendingLatLng.lat.toFixed(4)}, {pendingLatLng.lng.toFixed(4)}{' '}
              <button
                type="button"
                onClick={() => setPendingLatLng(null)}
                className="text-orange-600 underline"
              >
                clear
              </button>
            </p>
          ) : (
            <input
              type="text"
              value={form.address}
              onChange={(e) => updateField('address', e.target.value)}
              placeholder="Address (or click the map)"
              className="w-full rounded border border-slate-300 px-1.5 py-1"
            />
          )}

          <input
            type="url"
            value={form.website}
            onChange={(e) => updateField('website', e.target.value)}
            placeholder="Website"
            className="w-full rounded border border-slate-300 px-1.5 py-1"
          />
          <input
            type="tel"
            value={form.phone}
            onChange={(e) => updateField('phone', e.target.value)}
            placeholder="Phone"
            className="w-full rounded border border-slate-300 px-1.5 py-1"
          />
          <input
            type="text"
            value={form.contactName}
            onChange={(e) => updateField('contactName', e.target.value)}
            placeholder="Contact name"
            className="w-full rounded border border-slate-300 px-1.5 py-1"
          />
          <input
            type="email"
            value={form.email}
            onChange={(e) => updateField('email', e.target.value)}
            placeholder="Contact email"
            className="w-full rounded border border-slate-300 px-1.5 py-1"
          />

          <label className="block pt-1 text-slate-500">Follow up on</label>
          <input
            type="datetime-local"
            value={form.followUpAt}
            onChange={(e) => updateField('followUpAt', e.target.value)}
            className="w-full rounded border border-slate-300 px-1.5 py-1"
          />

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded bg-orange-600 px-2 py-1.5 font-medium text-white disabled:opacity-50"
          >
            {submitting ? 'Saving…' : 'Save competitor'}
          </button>
        </form>
      )}

      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  )
}
