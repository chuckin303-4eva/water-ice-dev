import { useEffect, useState, type FormEvent } from 'react'
import { competitorsApi } from '../api/competitors'
import { ApiError } from '../api/client'
import type { CompetitorCalendarLinks, CompetitorDetail, CompetitorSummary } from '../api/types'
import { useStopMapClickPropagation } from './useStopMapClickPropagation'

interface Props {
  competitor: CompetitorSummary
  onClose: () => void
  onChanged: () => void
}

export function CompetitorDetailPanel({ competitor, onClose, onChanged }: Props) {
  const [detail, setDetail] = useState<CompetitorDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [calendarLinks, setCalendarLinks] = useState<CompetitorCalendarLinks | null>(null)
  const panelRef = useStopMapClickPropagation<HTMLDivElement>()
  const [form, setForm] = useState({
    brand: '',
    website: '',
    phone: '',
    contact_name: '',
    contact_email: '',
    follow_up_at: '',
    serves_ice: false,
    serves_water: false,
    machine_size: '',
    is_inside: '' as '' | 'true' | 'false',
    ice_price: '',
    water_price: '',
    price_notes: '',
  })

  useEffect(() => {
    setDetail(null)
    setCalendarLinks(null)
    competitorsApi
      .get(competitor.id)
      .then((d) => {
        setDetail(d)
        setForm({
          brand: d.brand ?? '',
          website: d.website ?? '',
          phone: d.phone ?? '',
          contact_name: d.contact_name ?? '',
          contact_email: d.contact_email ?? '',
          follow_up_at: d.follow_up_at ? d.follow_up_at.slice(0, 16) : '',
          serves_ice: d.serves_ice,
          serves_water: d.serves_water,
          machine_size: d.machine_size ?? '',
          is_inside: d.is_inside == null ? '' : d.is_inside ? 'true' : 'false',
          ice_price: d.ice_price?.toString() ?? '',
          water_price: d.water_price?.toString() ?? '',
          price_notes: d.price_notes ?? '',
        })
      })
      .catch(() => setError('Could not load details'))
  }, [competitor.id])

  async function handleSave(event: FormEvent) {
    event.preventDefault()
    try {
      const updated = await competitorsApi.update(competitor.id, {
        brand: form.brand || undefined,
        website: form.website || undefined,
        phone: form.phone || undefined,
        contact_name: form.contact_name || undefined,
        contact_email: form.contact_email || undefined,
        follow_up_at: form.follow_up_at ? new Date(form.follow_up_at).toISOString() : undefined,
        serves_ice: form.serves_ice,
        serves_water: form.serves_water,
        machine_size: form.machine_size || undefined,
        is_inside: form.is_inside === '' ? undefined : form.is_inside === 'true',
        ice_price: form.ice_price === '' ? undefined : Number(form.ice_price),
        water_price: form.water_price === '' ? undefined : Number(form.water_price),
        price_notes: form.price_notes || undefined,
      })
      setDetail(updated)
      setEditing(false)
      onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save changes')
    }
  }

  async function handleGetCalendarLink() {
    try {
      const links = await competitorsApi.getCalendarLinks(competitor.id)
      setCalendarLinks(links)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not build calendar link')
    }
  }

  async function handleDelete() {
    try {
      await competitorsApi.remove(competitor.id)
      onChanged()
      onClose()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not remove competitor')
    }
  }

  return (
    <div
      ref={panelRef}
      className="absolute top-4 left-4 z-[1000] max-h-[calc(100%-2rem)] w-80 overflow-y-auto rounded-lg border border-orange-200 bg-white p-4 shadow-md"
    >
      <div className="mb-2 flex items-start justify-between">
        <h2 className="text-sm font-semibold text-slate-900">{competitor.name}</h2>
        <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600">
          ✕
        </button>
      </div>
      <p className="mb-3 text-xs text-slate-500">{competitor.address}</p>

      {detail && !editing && (
        <dl className="mb-3 space-y-1 text-xs text-slate-600">
          {detail.brand && (
            <div>
              <dt className="inline font-medium">Brand: </dt>
              <dd className="inline">{detail.brand}</dd>
            </div>
          )}
          {detail.website && (
            <div>
              <dt className="inline font-medium">Website: </dt>
              <dd className="inline">
                <a href={detail.website} target="_blank" rel="noopener" className="text-blue-600 underline">
                  {detail.website}
                </a>
              </dd>
            </div>
          )}
          {detail.phone && (
            <div>
              <dt className="inline font-medium">Phone: </dt>
              <dd className="inline">{detail.phone}</dd>
            </div>
          )}
          {(detail.contact_name || detail.contact_email) && (
            <div>
              <dt className="inline font-medium">Contact: </dt>
              <dd className="inline">
                {[detail.contact_name, detail.contact_email].filter(Boolean).join(' -- ')}
              </dd>
            </div>
          )}
          <div>
            <dt className="inline font-medium">Inside/outside: </dt>
            <dd className="inline">
              {detail.is_inside == null ? 'Unknown' : detail.is_inside ? 'Inside' : 'Outside'}
            </dd>
          </div>
          <div>
            <dt className="inline font-medium">Serves: </dt>
            <dd className="inline">
              {[detail.serves_ice && 'Ice', detail.serves_water && 'Water'].filter(Boolean).join(' + ') ||
                'Unknown'}
            </dd>
          </div>
          {detail.machine_size && (
            <div>
              <dt className="inline font-medium">Size: </dt>
              <dd className="inline">{detail.machine_size}</dd>
            </div>
          )}
          {detail.ice_price != null && (
            <div>
              <dt className="inline font-medium">Ice price: </dt>
              <dd className="inline">${detail.ice_price}</dd>
            </div>
          )}
          {detail.water_price != null && (
            <div>
              <dt className="inline font-medium">Water price: </dt>
              <dd className="inline">${detail.water_price}</dd>
            </div>
          )}
          {detail.price_notes && (
            <div>
              <dt className="inline font-medium">Price notes: </dt>
              <dd className="inline">{detail.price_notes}</dd>
            </div>
          )}
          {detail.source && (
            <div>
              <dt className="inline font-medium">Source: </dt>
              <dd className="inline">{detail.source}</dd>
            </div>
          )}
          <p className="pt-1 text-slate-400">
            No public data source auto-populates this -- these fields are only as current as the
            last manual observation.
          </p>
        </dl>
      )}

      {detail && !editing && detail.follow_up_at && (
        <div className="mb-3 text-xs">
          {calendarLinks ? (
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
          ) : (
            <button
              type="button"
              onClick={handleGetCalendarLink}
              className="w-full rounded border border-slate-300 px-2 py-1 text-blue-600"
            >
              Follow up {new Date(detail.follow_up_at).toLocaleString()} → add to calendar
            </button>
          )}
        </div>
      )}

      {detail && editing && (
        <form onSubmit={handleSave} className="mb-3 space-y-2 text-xs">
          <input
            type="text"
            list="brand-suggestions-edit"
            value={form.brand}
            onChange={(e) => setForm({ ...form, brand: e.target.value })}
            placeholder="Brand"
            className="w-full rounded border border-slate-300 px-2 py-1"
          />
          <datalist id="brand-suggestions-edit">
            <option value="Twice the Ice" />
            <option value="Kooler Ice" />
            <option value="Watermill Express" />
          </datalist>
          <input
            type="url"
            value={form.website}
            onChange={(e) => setForm({ ...form, website: e.target.value })}
            placeholder="Website"
            className="w-full rounded border border-slate-300 px-2 py-1"
          />
          <input
            type="tel"
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
            placeholder="Phone"
            className="w-full rounded border border-slate-300 px-2 py-1"
          />
          <input
            type="text"
            value={form.contact_name}
            onChange={(e) => setForm({ ...form, contact_name: e.target.value })}
            placeholder="Contact name"
            className="w-full rounded border border-slate-300 px-2 py-1"
          />
          <input
            type="email"
            value={form.contact_email}
            onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
            placeholder="Contact email"
            className="w-full rounded border border-slate-300 px-2 py-1"
          />
          <label className="block text-slate-500">Follow up on</label>
          <input
            type="datetime-local"
            value={form.follow_up_at}
            onChange={(e) => setForm({ ...form, follow_up_at: e.target.value })}
            className="w-full rounded border border-slate-300 px-2 py-1"
          />
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.serves_ice}
              onChange={(e) => setForm({ ...form, serves_ice: e.target.checked })}
            />
            Serves ice
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.serves_water}
              onChange={(e) => setForm({ ...form, serves_water: e.target.checked })}
            />
            Serves water
          </label>
          <select
            value={form.is_inside}
            onChange={(e) => setForm({ ...form, is_inside: e.target.value as '' | 'true' | 'false' })}
            className="w-full rounded border border-slate-300 px-2 py-1"
          >
            <option value="">Inside/outside unknown</option>
            <option value="true">Inside</option>
            <option value="false">Outside</option>
          </select>
          <input
            type="text"
            value={form.machine_size}
            onChange={(e) => setForm({ ...form, machine_size: e.target.value })}
            placeholder="Machine size (e.g. large kiosk)"
            className="w-full rounded border border-slate-300 px-2 py-1"
          />
          <div className="flex gap-2">
            <input
              type="number"
              step="0.01"
              value={form.ice_price}
              onChange={(e) => setForm({ ...form, ice_price: e.target.value })}
              placeholder="Ice price"
              className="w-full rounded border border-slate-300 px-2 py-1"
            />
            <input
              type="number"
              step="0.01"
              value={form.water_price}
              onChange={(e) => setForm({ ...form, water_price: e.target.value })}
              placeholder="Water price"
              className="w-full rounded border border-slate-300 px-2 py-1"
            />
          </div>
          <textarea
            value={form.price_notes}
            onChange={(e) => setForm({ ...form, price_notes: e.target.value })}
            placeholder="Price notes (units, per-bag vs per-gallon, etc.)"
            rows={2}
            className="w-full rounded border border-slate-300 px-2 py-1"
          />
          <div className="flex gap-2">
            <button type="submit" className="flex-1 rounded bg-orange-600 px-2 py-1 text-white">
              Save
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="flex-1 rounded border border-slate-300 px-2 py-1"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {detail && !editing && (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="flex-1 rounded bg-slate-700 px-2 py-1 text-xs text-white"
          >
            Edit
          </button>
          <button
            type="button"
            onClick={handleDelete}
            className="flex-1 rounded border border-red-300 px-2 py-1 text-xs text-red-600"
          >
            Remove
          </button>
        </div>
      )}

      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  )
}
