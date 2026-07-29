import { useState, type FormEvent } from 'react'
import { useMapEvents } from 'react-leaflet'
import { locationsApi } from '../api/locations'
import { ApiError } from '../api/client'
import { isPendingReview, type Brand, type CompetitorCalendarLinks } from '../api/types'
import { BrandPicker } from './BrandPicker'
import { useStopMapClickPropagation } from './useStopMapClickPropagation'

interface Props {
  onCreated: () => void
}

const EMPTY_FORM = {
  address: '',
  website: '',
  contactName: '',
  contactPhone: '',
  contactEmail: '',
  followUpAt: '',
}

const FOLLOW_UP_NOTE_TEXT = 'Follow-up scheduled when this prospect was added.'

/** Matches AddCompetitorControl's shape (ADR-0008 addendum) so the two
 * "quick add" cards behave the same way: click the map or type an
 * address to place the pin, fill in the same contact/brand/follow-up
 * fields as a competitor, then save -- rather than the old instant-
 * create-on-click flow. Everything else (property owner, utilities,
 * pricing) still gets filled in later via the detail panel, same
 * minimal-add split as before.
 */
export function AddProspectControl({ onCreated }: Props) {
  const [isAdding, setIsAdding] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [pendingLatLng, setPendingLatLng] = useState<{ lat: number; lng: number } | null>(null)
  const [selectedBrand, setSelectedBrand] = useState<Brand | null>(null)
  const [showBrandPicker, setShowBrandPicker] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [queuedMessage, setQueuedMessage] = useState<string | null>(null)
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

  function reset() {
    setForm(EMPTY_FORM)
    setPendingLatLng(null)
    setSelectedBrand(null)
    setShowBrandPicker(false)
    setCalendarLinks(null)
    setIsAdding(false)
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!pendingLatLng && !form.address.trim()) {
      setError('Click the map or enter an address')
      return
    }
    setError(null)
    setQueuedMessage(null)
    setSubmitting(true)
    setCalendarLinks(null)
    try {
      const result = await locationsApi.create({
        ...(pendingLatLng
          ? { latitude: pendingLatLng.lat, longitude: pendingLatLng.lng }
          : { address: form.address.trim() }),
        brand_id: selectedBrand?.id,
        website: form.website.trim() || undefined,
        primary_contact_name: form.contactName.trim() || undefined,
        primary_contact_phone: form.contactPhone.trim() || undefined,
        primary_contact_email: form.contactEmail.trim() || undefined,
      })
      if (isPendingReview(result)) {
        // Validation workflow (ADR-0014) -- nothing was actually created
        // yet, so there's no location to attach a follow-up note to.
        reset()
        setQueuedMessage('Submitted for review -- an admin needs to approve it before it appears on the map.')
        return
      }
      onCreated()
      if (form.followUpAt) {
        const note = await locationsApi.addCallNote(
          result.id,
          FOLLOW_UP_NOTE_TEXT,
          new Date(form.followUpAt).toISOString(),
        )
        const links = await locationsApi.getCalendarLinks(result.id, note.id)
        setCalendarLinks(links)
      } else {
        reset()
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create prospect')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div ref={panelRef} className="w-72 rounded-lg border border-slate-200 bg-white p-4 shadow-md">
      <button
        type="button"
        onClick={() => (isAdding ? reset() : setIsAdding(true))}
        className={`w-full rounded px-3 py-2 text-sm font-medium ${
          isAdding ? 'bg-amber-500 text-white' : 'bg-slate-900 text-white'
        }`}
      >
        {isAdding ? (pendingLatLng ? 'Pin placed -- fill in below' : 'Click map or fill in below') : '+ Add New Prospect'}
      </button>

      {isAdding && calendarLinks && (
        <div className="mt-3 space-y-2 text-xs">
          <p className="text-slate-600">Prospect saved. Add the follow-up to your calendar:</p>
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
          <button type="button" onClick={reset} className="w-full rounded border border-slate-300 px-2 py-1">
            Done
          </button>
        </div>
      )}

      {isAdding && !calendarLinks && (
        <form onSubmit={handleSubmit} className="mt-3 space-y-2 text-sm">
          {pendingLatLng ? (
            <p className="rounded bg-slate-50 px-2 py-1 text-xs text-slate-500">
              Pin at {pendingLatLng.lat.toFixed(4)}, {pendingLatLng.lng.toFixed(4)}{' '}
              <button
                type="button"
                onClick={() => setPendingLatLng(null)}
                className="text-amber-600 underline"
              >
                clear
              </button>
            </p>
          ) : (
            <input
              type="text"
              value={form.address}
              onChange={(e) => updateField('address', e.target.value)}
              placeholder="123 Main St, Denver, CO"
              className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
            />
          )}

          {selectedBrand ? (
            <p className="rounded bg-slate-50 px-2 py-1 text-xs text-slate-600">
              Brand: {selectedBrand.name}{' '}
              <button
                type="button"
                onClick={() => setSelectedBrand(null)}
                className="text-blue-600 underline"
              >
                change
              </button>
            </p>
          ) : showBrandPicker ? (
            <BrandPicker
              onSelect={(brand) => {
                setSelectedBrand(brand)
                setShowBrandPicker(false)
              }}
              onCancel={() => setShowBrandPicker(false)}
            />
          ) : (
            <button
              type="button"
              onClick={() => setShowBrandPicker(true)}
              className="text-xs text-blue-600 underline"
            >
              + Link a brand
            </button>
          )}

          <input
            type="url"
            value={form.website}
            onChange={(e) => updateField('website', e.target.value)}
            placeholder="Website"
            className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
          />
          <input
            type="tel"
            value={form.contactPhone}
            onChange={(e) => updateField('contactPhone', e.target.value)}
            placeholder="Contact phone"
            className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
          />
          <input
            type="text"
            value={form.contactName}
            onChange={(e) => updateField('contactName', e.target.value)}
            placeholder="Contact name"
            className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
          />
          <input
            type="email"
            value={form.contactEmail}
            onChange={(e) => updateField('contactEmail', e.target.value)}
            placeholder="Contact email"
            className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
          />

          <label className="block text-xs text-slate-500">Follow up on</label>
          <input
            type="datetime-local"
            value={form.followUpAt}
            onChange={(e) => updateField('followUpAt', e.target.value)}
            className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
          />

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded bg-slate-700 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            {submitting ? 'Saving…' : 'Save prospect'}
          </button>
        </form>
      )}

      {queuedMessage && <p className="mt-2 text-xs text-amber-700">{queuedMessage}</p>}
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  )
}
