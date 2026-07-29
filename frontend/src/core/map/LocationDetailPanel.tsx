import { useEffect, useState, type FormEvent } from 'react'
import { locationsApi } from '../api/locations'
import { ApiError } from '../api/client'
import type { CallNote, LocationDetail, LocationSummary } from '../api/types'

interface Props {
  location: LocationSummary
  onClose: () => void
}

export function LocationDetailPanel({ location, onClose }: Props) {
  const [detail, setDetail] = useState<LocationDetail | null>(null)
  const [notes, setNotes] = useState<CallNote[]>([])
  const [noteText, setNoteText] = useState('')
  const [followUpAt, setFollowUpAt] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setDetail(null)
    setNotes([])
    locationsApi.get(location.id).then(setDetail).catch(() => setError('Could not load details'))
    locationsApi.listCallNotes(location.id).then(setNotes).catch(() => undefined)
  }, [location.id])

  async function handleGetCalendarLink(noteId: number) {
    try {
      const links = await locationsApi.getCalendarLinks(location.id, noteId)
      window.open(links.google, '_blank', 'noopener')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not build calendar link')
    }
  }

  async function handleAddNote(event: FormEvent) {
    event.preventDefault()
    if (!noteText.trim()) return
    try {
      const note = await locationsApi.addCallNote(
        location.id,
        noteText.trim(),
        followUpAt ? new Date(followUpAt).toISOString() : undefined,
      )
      setNotes((prev) => [note, ...prev])
      setNoteText('')
      setFollowUpAt('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not add note')
    }
  }

  return (
    <div className="absolute top-4 left-4 z-[1000] max-h-[calc(100%-2rem)] w-80 overflow-y-auto rounded-lg border border-slate-200 bg-white p-4 shadow-md">
      <div className="mb-2 flex items-start justify-between">
        <h2 className="text-sm font-semibold text-slate-900">{location.address}</h2>
        <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600">
          ✕
        </button>
      </div>
      <p className="mb-3 text-xs text-slate-500">Status: {location.status}</p>

      {detail && (
        <dl className="mb-4 space-y-1 text-xs text-slate-600">
          {detail.property_owner_name && (
            <div>
              <dt className="inline font-medium">Owner: </dt>
              <dd className="inline">{detail.property_owner_name}</dd>
            </div>
          )}
          {detail.power_company && (
            <div>
              <dt className="inline font-medium">Power: </dt>
              <dd className="inline">
                {detail.power_company} ({detail.power_voltage ?? 'voltage unknown'})
              </dd>
            </div>
          )}
          {detail.water_company && (
            <div>
              <dt className="inline font-medium">Water: </dt>
              <dd className="inline">{detail.water_company}</dd>
            </div>
          )}
          {detail.pricing_estimate_monthly != null && (
            <div>
              <dt className="inline font-medium">Est. monthly cost: </dt>
              <dd className="inline">${detail.pricing_estimate_monthly}</dd>
            </div>
          )}
        </dl>
      )}

      <h3 className="mb-1 text-xs font-semibold text-slate-700">Call notes</h3>
      <form onSubmit={handleAddNote} className="mb-3 space-y-2">
        <textarea
          value={noteText}
          onChange={(e) => setNoteText(e.target.value)}
          placeholder="What happened on this call?"
          rows={2}
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
        />
        <div className="flex gap-2">
          <input
            type="datetime-local"
            value={followUpAt}
            onChange={(e) => setFollowUpAt(e.target.value)}
            className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          />
          <button
            type="submit"
            className="shrink-0 rounded bg-slate-700 px-2 py-1 text-xs text-white"
          >
            Add
          </button>
        </div>
      </form>

      <ul className="space-y-2">
        {notes.map((note) => (
          <li key={note.id} className="rounded border border-slate-100 bg-slate-50 p-2 text-xs">
            <p>{note.note_text}</p>
            <p className="mt-1 text-slate-400">{new Date(note.call_date).toLocaleString()}</p>
            {note.follow_up_at && (
              <button
                type="button"
                onClick={() => handleGetCalendarLink(note.id)}
                className="mt-1 text-blue-600 underline"
              >
                Follow up {new Date(note.follow_up_at).toLocaleDateString()} → add to calendar
              </button>
            )}
          </li>
        ))}
      </ul>

      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  )
}
