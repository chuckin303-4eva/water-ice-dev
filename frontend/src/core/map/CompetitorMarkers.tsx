import L from 'leaflet'
import 'leaflet.markercluster'
import { useEffect, useRef } from 'react'
import { useMap } from 'react-leaflet'
import type { CompetitorSummary } from '../api/types'
import { markerIcon } from './ClusteredMarkers'

const ORANGE = '#ea580c'

interface Props {
  competitors: CompetitorSummary[]
  onSelect: (competitor: CompetitorSummary) => void
}

/** Own cluster group (not merged with ClusteredMarkers' prospect/active
 * pins) so competitor density and our-own-location density stay visually
 * distinguishable even when they overlap geographically. Square icon on
 * top of the orange color, since color alone isn't reliable for the
 * ~8% of users with red-green color vision deficiency who can still
 * confuse orange/green/yellow -- shape is the fallback cue.
 */
export function CompetitorMarkers({ competitors, onSelect }: Props) {
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
    for (const competitor of competitors) {
      const marker = L.marker([competitor.latitude, competitor.longitude], {
        icon: markerIcon(ORANGE, 'square'),
      })
      marker.bindPopup(`<strong>${competitor.name}</strong><br/>${competitor.address}`)
      marker.on('click', () => onSelect(competitor))
      clusterGroup.addLayer(marker)
    }
  }, [competitors, onSelect])

  return null
}
