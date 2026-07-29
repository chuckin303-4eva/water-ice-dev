import L from 'leaflet'
import 'leaflet.markercluster'
import { useEffect, useRef } from 'react'
import { useMap } from 'react-leaflet'
import type { LocationSummary } from '../api/types'

const GREEN = '#16a34a'
const YELLOW = '#f59e0b'
const SLATE = '#94a3b8'

// Basic scoring (Phase 1, item 5) isn't built yet, so opportunity_score is
// null on every prospect today -- this threshold is a provisional
// placeholder for "good enough to turn green" and has no real basis until
// that feature defines the actual scoring scale. Revisit then.
const GOOD_SCORE_THRESHOLD = 70

function locationColor(location: LocationSummary): string {
  if (location.status === 'archived') return SLATE
  if (location.status === 'active') return GREEN
  // prospect: yellow until scored, green once scored well
  if (location.opportunity_score != null && location.opportunity_score >= GOOD_SCORE_THRESHOLD) {
    return GREEN
  }
  return YELLOW
}

export function markerIcon(color: string, shape: 'circle' | 'square' = 'circle'): L.DivIcon {
  const radius = shape === 'circle' ? '50%' : '3px'
  return L.divIcon({
    className: '',
    html: `<span style="display:block;width:14px;height:14px;border-radius:${radius};background:${color};border:2px solid white;box-shadow:0 0 2px rgba(0,0,0,0.5)"></span>`,
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
        icon: markerIcon(locationColor(location)),
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
