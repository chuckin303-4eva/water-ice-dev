import { useCallback, useEffect, useState } from 'react'
import { MapContainer, TileLayer } from 'react-leaflet'
import { competitorsApi } from '../api/competitors'
import { locationsApi } from '../api/locations'
import type { CompetitorSummary, LocationSummary } from '../api/types'
import { AddCompetitorControl } from './AddCompetitorControl'
import { AddProspectControl } from './AddProspectControl'
import { ClusteredMarkers } from './ClusteredMarkers'
import { CompetitorDetailPanel } from './CompetitorDetailPanel'
import { CompetitorMarkers } from './CompetitorMarkers'
import { LocationDetailPanel } from './LocationDetailPanel'

// Continental-US-ish default view -- reasonable starting point until
// there's a real notion of "the user's territory" to center on instead.
const DEFAULT_CENTER: [number, number] = [39.8283, -98.5795]
const DEFAULT_ZOOM = 4

type Selection =
  | { kind: 'location'; data: LocationSummary }
  | { kind: 'competitor'; data: CompetitorSummary }
  | null

export function MapView() {
  const [locations, setLocations] = useState<LocationSummary[]>([])
  const [competitors, setCompetitors] = useState<CompetitorSummary[]>([])
  const [selected, setSelected] = useState<Selection>(null)
  const [error, setError] = useState<string | null>(null)

  const refreshLocations = useCallback(() => {
    locationsApi
      .list()
      .then(setLocations)
      .catch(() => setError('Could not load locations'))
  }, [])

  const refreshCompetitors = useCallback(() => {
    competitorsApi
      .list()
      .then(setCompetitors)
      .catch(() => setError('Could not load competitors'))
  }, [])

  useEffect(() => {
    refreshLocations()
    refreshCompetitors()
  }, [refreshLocations, refreshCompetitors])

  return (
    <div className="relative h-full w-full">
      <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} className="h-full w-full">
        <TileLayer
          url={import.meta.env.VITE_TILE_URL_TEMPLATE}
          attribution={import.meta.env.VITE_TILE_ATTRIBUTION}
        />
        <ClusteredMarkers
          locations={locations}
          onSelect={(data) => setSelected({ kind: 'location', data })}
        />
        <CompetitorMarkers
          competitors={competitors}
          onSelect={(data) => setSelected({ kind: 'competitor', data })}
        />
        <AddProspectControl onCreated={refreshLocations} />
        <AddCompetitorControl onCreated={refreshCompetitors} />
      </MapContainer>

      {selected?.kind === 'location' && (
        <LocationDetailPanel
          location={selected.data}
          onClose={() => setSelected(null)}
          onChanged={refreshLocations}
        />
      )}
      {selected?.kind === 'competitor' && (
        <CompetitorDetailPanel
          competitor={selected.data}
          onClose={() => setSelected(null)}
          onChanged={refreshCompetitors}
        />
      )}

      <div className="absolute bottom-4 right-4 z-[1000] rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600 shadow-md">
        <div className="mb-1 flex items-center gap-2">
          <span className="inline-block h-3 w-3 rounded-full bg-amber-500" /> New prospect
        </div>
        <div className="mb-1 flex items-center gap-2">
          <span className="inline-block h-3 w-3 rounded-full bg-green-600" /> Good score / active
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block h-3 w-3 rounded-sm bg-orange-600" /> Competitor
        </div>
      </div>

      {error && (
        <div className="absolute bottom-4 left-1/2 z-[1000] -translate-x-1/2 rounded bg-red-600 px-3 py-1 text-sm text-white">
          {error}
        </div>
      )}
    </div>
  )
}
