import { useCallback, useEffect, useState } from 'react'
import { MapContainer, TileLayer } from 'react-leaflet'
import { locationsApi } from '../api/locations'
import type { LocationSummary } from '../api/types'
import { AddProspectControl } from './AddProspectControl'
import { ClusteredMarkers } from './ClusteredMarkers'
import { LocationDetailPanel } from './LocationDetailPanel'

// Continental-US-ish default view -- reasonable starting point until
// there's a real notion of "the user's territory" to center on instead.
const DEFAULT_CENTER: [number, number] = [39.8283, -98.5795]
const DEFAULT_ZOOM = 4

export function MapView() {
  const [locations, setLocations] = useState<LocationSummary[]>([])
  const [selected, setSelected] = useState<LocationSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(() => {
    locationsApi
      .list()
      .then(setLocations)
      .catch(() => setError('Could not load locations'))
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return (
    <div className="relative h-full w-full">
      <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} className="h-full w-full">
        <TileLayer
          url={import.meta.env.VITE_TILE_URL_TEMPLATE}
          attribution={import.meta.env.VITE_TILE_ATTRIBUTION}
        />
        <ClusteredMarkers locations={locations} onSelect={setSelected} />
        <AddProspectControl onCreated={refresh} />
      </MapContainer>

      {selected && <LocationDetailPanel location={selected} onClose={() => setSelected(null)} />}

      {error && (
        <div className="absolute bottom-4 left-1/2 z-[1000] -translate-x-1/2 rounded bg-red-600 px-3 py-1 text-sm text-white">
          {error}
        </div>
      )}
    </div>
  )
}
