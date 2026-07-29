import { useEffect, useState, type FormEvent } from 'react'
import { competitorsApi } from '../api/competitors'
import { ApiError } from '../api/client'
import type { CompetitorDetail, CompetitorSummary } from '../api/types'

interface Props {
  competitor: CompetitorSummary
  onClose: () => void
  onChanged: () => void
}

export function CompetitorDetailPanel({ competitor, onClose, onChanged }: Props) {
  const [detail, setDetail] = useState<CompetitorDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({
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
    competitorsApi
      .get(competitor.id)
      .then((d) => {
        setDetail(d)
        setForm({
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
    <div className="absolute top-4 left-4 z-[1000] max-h-[calc(100%-2rem)] w-80 overflow-y-auto rounded-lg border border-orange-200 bg-white p-4 shadow-md">
      <div className="mb-2 flex items-start justify-between">
        <h2 className="text-sm font-semibold text-slate-900">{competitor.name}</h2>
        <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600">
          ✕
        </button>
      </div>
      <p className="mb-3 text-xs text-slate-500">{competitor.address}</p>

      {detail && !editing && (
        <dl className="mb-3 space-y-1 text-xs text-slate-600">
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

      {detail && editing && (
        <form onSubmit={handleSave} className="mb-3 space-y-2 text-xs">
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
