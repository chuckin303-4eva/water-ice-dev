import L from 'leaflet'
import { useEffect, useRef } from 'react'

/** Any HTML overlay rendered inside <MapContainer> ends up as a DOM
 * descendant of Leaflet's own map container div, so clicks on it bubble
 * up and also fire the map's native click handler (which useMapEvents'
 * click callback listens to) -- exactly like clicking the actual map
 * would. Leaflet's own built-in controls (zoom in/out) avoid this via
 * L.DomEvent.disableClickPropagation internally; anything custom needs
 * to opt in the same way, or a click on a button inside, say,
 * AddProspectControl also gets treated as "the user clicked the map to
 * place a pin" and creates an unwanted extra prospect/competitor.
 */
export function useStopMapClickPropagation<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    L.DomEvent.disableClickPropagation(el)
    L.DomEvent.disableScrollPropagation(el)
  }, [])
  return ref
}
