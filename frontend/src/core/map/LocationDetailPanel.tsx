import { useEffect, useState, type FormEvent } from 'react'
import { locationsApi } from '../api/locations'
import { ApiError } from '../api/client'
import { isPendingReview, type CallNote, type LocationDetail, type LocationSummary } from '../api/types'
import { useStopMapClickPropagation } from './useStopMapClickPropagation'

interface Props {
  location: LocationSummary
  onClose: () => void
  onChanged: () => void
}

export function LocationDetailPanel({ location, onClose, onChanged }: Props) {
  const [detail, setDetail] = useState<LocationDetail | null>(null)
  const [notes, setNotes] = useState<CallNote[]>([])
  const [noteText, setNoteText] = useState('')
  const [followUpAt, setFollowUpAt] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [editingScore, setEditingScore] = useState(false)
  const [visibilityRating, setVisibilityRating] = useState('')
  const [trafficScore, setTrafficScore] = useState('')
  const [recalculating, setRecalculating] = useState(false)
  const [queuedMessage, setQueuedMessage] = useState<string | null>(null)
  const panelRef = useStopMapClickPropagation<HTMLDivElement>()

  useEffect(() => {
    setDetail(null)
    setNotes([])
    locationsApi
      .get(location.id)
      .then((d) => {
        setDetail(d)
        setVisibilityRating(d.visibility_rating?.toString() ?? '')
        setTrafficScore(d.traffic_score?.toString() ?? '')
      })
      .catch(() => setError('Could not load details'))
    locationsApi.listCallNotes(location.id).then(setNotes).catch(() => undefined)
  }, [location.id])

  async function handleSaveRatings(event: FormEvent) {
    event.preventDefault()
    setQueuedMessage(null)
    try {
      const result = await locationsApi.update(location.id, {
        visibility_rating: visibilityRating === '' ? undefined : Number(visibilityRating),
        traffic_score: trafficScore === '' ? undefined : Number(trafficScore),
      })
      setEditingScore(false)
      if (isPendingReview(result)) {
        // Validation workflow (ADR-0014) -- the change hasn't actually
        // been applied yet, so `detail` intentionally isn't touched.
        setQueuedMessage('Change submitted for review -- an admin needs to approve it first.')
      } else {
        setDetail(result)
        onChanged()
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save ratings')
    }
  }

  async function handleRecalculate() {
    setRecalculating(true)
    try {
      const updated = await locationsApi.recalculateScore(location.id)
      setDetail(updated)
      onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not recalculate score')
    } finally {
      setRecalculating(false)
    }
  }

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
    <div
      ref={panelRef}
      className="absolute top-4 left-4 z-[1000] max-h-[calc(100%-2rem)] w-80 overflow-y-auto rounded-lg border border-slate-200 bg-white p-4 shadow-md"
    >
      <div className="mb-2 flex items-start justify-between">
        <h2 className="text-sm font-semibold text-slate-900">{location.address}</h2>
        <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600">
          ✕
        </button>
      </div>
      <p className="mb-3 text-xs text-slate-500">Status: {location.status}</p>

      {detail && !editingScore && (
        <div className="mb-3 rounded border border-slate-100 bg-slate-50 p-2 text-xs text-slate-600">
          <div className="mb-1 flex items-center justify-between">
            <span className="font-semibold text-slate-700">Score</span>
            <button
              type="button"
              onClick={handleRecalculate}
              disabled={recalculating}
              className="text-blue-600 underline disabled:opacity-50"
            >
              {recalculating ? 'Recalculating…' : 'Recalculate'}
            </button>
          </div>
          <p>
            Opportunity:{' '}
            {detail.opportunity_score != null ? detail.opportunity_score : 'not scored yet'}
          </p>
          <p>Competition: {detail.competition_score}</p>
          <p>
            Visibility: {detail.visibility_rating ?? 'not rated'} / Traffic:{' '}
            {detail.traffic_score ?? 'not rated'}
          </p>
          {detail.opportunity_score == null && (
            <p className="mt-1 text-slate-400">
              Rate visibility and traffic below to get an opportunity score.
            </p>
          )}
          <button
            type="button"
            onClick={() => setEditingScore(true)}
            className="mt-1 text-blue-600 underline"
          >
            Rate this site
          </button>
        </div>
      )}

      {detail && editingScore && (
        <form
          onSubmit={handleSaveRatings}
          className="mb-3 space-y-2 rounded border border-slate-100 bg-slate-50 p-2 text-xs"
        >
          <label className="block text-slate-500">Visibility (1-10)</label>
          <input
            type="number"
            min={1}
            max={10}
            value={visibilityRating}
            onChange={(e) => setVisibilityRating(e.target.value)}
            className="w-full rounded border border-slate-300 px-2 py-1"
          />
          <label className="block text-slate-500">Traffic (1-10)</label>
          <input
            type="number"
            min={1}
            max={10}
            value={trafficScore}
            onChange={(e) => setTrafficScore(e.target.value)}
            className="w-full rounded border border-slate-300 px-2 py-1"
          />
          <div className="flex gap-2">
            <button type="submit" className="flex-1 rounded bg-slate-700 px-2 py-1 text-white">
              Save
            </button>
            <button
              type="button"
              onClick={() => setEditingScore(false)}
              className="flex-1 rounded border border-slate-300 px-2 py-1"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

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

      {queuedMessage && <p className="mt-2 text-xs text-amber-700">{queuedMessage}</p>}
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  )
}
