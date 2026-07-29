import { useState } from 'react'
import { hostBusinessesApi } from '../api/hostBusinesses'
import { ApiError } from '../api/client'
import type { HostBusiness } from '../api/types'

interface Props {
  onSelect: (hostBusiness: HostBusiness) => void
  onCancel: () => void
}

/** Search-or-create picker for linking a location to a host business
 * (Phase 2, "Host businesses"). `host_businesses` is a normalized table
 * shared across locations (ADR-0003), not free text -- so this searches
 * existing rows first and only falls back to a compact create form,
 * matching the "find or add" pattern this product already uses for
 * competitor brand suggestions.
 */
export function HostBusinessPicker({ onSelect, onCancel }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<HostBusiness[]>([])
  const [searched, setSearched] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [name, setName] = useState('')
  const [category, setCategory] = useState('')
  const [phone, setPhone] = useState('')
  const [website, setWebsite] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleSearch(value: string) {
    setQuery(value)
    if (!value.trim()) {
      setResults([])
      setSearched(false)
      return
    }
    try {
      const matches = await hostBusinessesApi.list(value.trim())
      setResults(matches)
      setSearched(true)
    } catch {
      setResults([])
      setSearched(true)
    }
  }

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    if (!name.trim()) return
    setBusy(true)
    setError(null)
    try {
      const created = await hostBusinessesApi.create({
        name: name.trim(),
        category: category.trim() || undefined,
        phone: phone.trim() || undefined,
        website: website.trim() || undefined,
      })
      onSelect(created)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create host business')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-2 rounded border border-slate-100 bg-slate-50 p-2 text-xs">
      {!showCreateForm && (
        <>
          <label className="block text-slate-500">Search host businesses</label>
          <input
            type="text"
            value={query}
            onChange={(e) => void handleSearch(e.target.value)}
            placeholder="Name or category..."
            className="w-full rounded border border-slate-300 px-2 py-1"
            autoFocus
          />
          {results.length > 0 && (
            <ul className="max-h-32 space-y-1 overflow-y-auto">
              {results.map((h) => (
                <li key={h.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(h)}
                    className="w-full rounded border border-slate-200 bg-white px-2 py-1 text-left hover:bg-slate-100"
                  >
                    <span className="font-medium">{h.name}</span>
                    {h.category && <span className="text-slate-400"> · {h.category}</span>}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {searched && results.length === 0 && (
            <p className="text-slate-400">No matches.</p>
          )}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setShowCreateForm(true)}
              className="flex-1 rounded bg-slate-700 px-2 py-1 text-white"
            >
              + Add new
            </button>
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 rounded border border-slate-300 px-2 py-1"
            >
              Cancel
            </button>
          </div>
        </>
      )}

      {showCreateForm && (
        <form onSubmit={handleCreate} className="space-y-2">
          <label className="block text-slate-500">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Shell Station #42"
            className="w-full rounded border border-slate-300 px-2 py-1"
            autoFocus
          />
          <label className="block text-slate-500">Category</label>
          <input
            type="text"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="gas_station, laundromat, grocery..."
            list="host-business-categories"
            className="w-full rounded border border-slate-300 px-2 py-1"
          />
          <datalist id="host-business-categories">
            <option value="gas_station" />
            <option value="laundromat" />
            <option value="grocery" />
            <option value="convenience" />
          </datalist>
          <label className="block text-slate-500">Phone</label>
          <input
            type="text"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="w-full rounded border border-slate-300 px-2 py-1"
          />
          <label className="block text-slate-500">Website</label>
          <input
            type="text"
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
            className="w-full rounded border border-slate-300 px-2 py-1"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy || !name.trim()}
              className="flex-1 rounded bg-slate-700 px-2 py-1 text-white disabled:opacity-50"
            >
              {busy ? 'Saving…' : 'Save & link'}
            </button>
            <button
              type="button"
              onClick={() => setShowCreateForm(false)}
              className="flex-1 rounded border border-slate-300 px-2 py-1"
            >
              Back
            </button>
          </div>
          {error && <p className="text-red-600">{error}</p>}
        </form>
      )}
    </div>
  )
}
