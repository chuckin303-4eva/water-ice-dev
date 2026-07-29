import L from 'leaflet'
import 'leaflet.markercluster'
import { useEffect, useRef } from 'react'
import { useMap } from 'react-leaflet'
import type { LocationSummary } from '../api/types'

const STATUS_COLORS: Record<string, string> = {
  prospect: '#f59e0b', // amber
  active: '#16a34a', // green
  archived: '#94a3b8', // slate
}

function markerIcon(status: string): L.DivIcon {
  const color = STATUS_COLORS[status] ?? '#3b82f6'
  return L.divIcon({
    className: '',
    html: `<span style="display:block;width:14px;height:14px;border-radius:50%;background:${color};border:2px solid white;box-shadow:0 0 2px rgba(0,0,0,0.5)"></span>`,
    iconSize: [14, 14],
  })
}

interface Props {
  locations: LocationSummary[]
  onSelect: (location: LocationSummary) => void
}

/** react-leaflet has no built-in clustering; leaflet.markercluster works
 * directly on the underlying Leaflet map instance, so this component
 * reaches into it imperatively via useMap(). Required at this product's
 * stated scale (100,000+ locations) -- unclustered individual markers
 * would make the map unusable well before that.
 */
export function ClusteredMarkers({ locations, onSelect }: Props) {
  const map = useMap()
  const clusterGroupRef = useRef<L.MarkerClusterGroup | null>(null)

  useEffect(() => {
    const clusterGroup = L.markerClusterGroup()
    clusterGroupRef.current = clusterGroup
    map.addLayer(clusterGroup)
    return () => {
      map.removeLayer(clusterGroup)
      clusterGroupRef.current = null
    }
  }, [map])

  useEffect(() => {
    const clusterGroup = clusterGroupRef.current
    if (!clusterGroup) return

    clusterGroup.clearLayers()
    for (const location of locations) {
      const marker = L.marker([location.latitude, location.longitude], {
        icon: markerIcon(location.status),
      })
      marker.bindPopup(
        `<strong>${location.address}</strong><br/>Status: ${location.status}`,
      )
      marker.on('click', () => onSelect(location))
      clusterGroup.addLayer(marker)
    }
  }, [locations, onSelect])

  return null
}
