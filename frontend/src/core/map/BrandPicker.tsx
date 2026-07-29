import { useState } from 'react'
import { brandsApi } from '../api/brands'
import { ApiError } from '../api/client'
import type { Brand } from '../api/types'

interface Props {
  onSelect: (brand: Brand) => void
  onCancel: () => void
}

/** Search-or-create picker for linking a location to a brand (the parent
 * franchise, e.g. "Twice the Ice"). `brands` is a normalized table
 * (ADR-0002), same "find or add" shape as HostBusinessPicker -- kept to
 * just a name at creation time, matching how simple `competitors.brand`
 * (free text) already is; description/logo_url exist on the model for
 * later, not needed for a quick link.
 */
export function BrandPicker({ onSelect, onCancel }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Brand[]>([])
  const [searched, setSearched] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [name, setName] = useState('')
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
      const matches = await brandsApi.list(value.trim())
      setResults(matches)
      setSearched(true)
    } catch {
      setResults([])
      setSearched(true)
    }
  }

  async function handleCreate() {
    if (!name.trim()) return
    setBusy(true)
    setError(null)
    try {
      const created = await brandsApi.create({ name: name.trim() })
      onSelect(created)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create brand')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-2 rounded border border-slate-100 bg-slate-50 p-2 text-xs">
      {!showCreateForm && (
        <>
          <label className="block text-slate-500">Search brands</label>
          <input
            type="text"
            value={query}
            onChange={(e) => void handleSearch(e.target.value)}
            placeholder="Twice the Ice, Kooler Ice..."
            className="w-full rounded border border-slate-300 px-2 py-1"
            autoFocus
          />
          {results.length > 0 && (
            <ul className="max-h-32 space-y-1 overflow-y-auto">
              {results.map((b) => (
                <li key={b.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(b)}
                    className="w-full rounded border border-slate-200 bg-white px-2 py-1 text-left hover:bg-slate-100"
                  >
                    {b.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {searched && results.length === 0 && <p className="text-slate-400">No matches.</p>}
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
        // Plain div, not a <form> -- this picker can end up rendered
        // inside a parent <form> (e.g. AddProspectControl), and a
        // nested <form> silently fails to submit in this browser
        // (confirmed: React warns "cannot contain a nested form" and
        // the click produces no network activity at all).
        <div className="space-y-2">
          <label className="block text-slate-500">Brand name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                void handleCreate()
              }
            }}
            placeholder="Twice the Ice"
            className="w-full rounded border border-slate-300 px-2 py-1"
            autoFocus
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => void handleCreate()}
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
        </div>
      )}
    </div>
  )
}
