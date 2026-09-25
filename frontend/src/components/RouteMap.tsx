import { useEffect, useRef } from 'react'
import type { RouteOptimizeResponse } from '../types/api'
import './RouteMap.css'

// Leaflet import — must be dynamic to avoid SSR issues with Vite
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix default marker icon broken by webpack/vite bundling
import markerIconUrl from 'leaflet/dist/images/marker-icon.png'
import markerIcon2xUrl from 'leaflet/dist/images/marker-icon-2x.png'
import markerShadowUrl from 'leaflet/dist/images/marker-shadow.png'

delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
L.Icon.Default.mergeOptions({
  iconUrl: markerIconUrl,
  iconRetinaUrl: markerIcon2xUrl,
  shadowUrl: markerShadowUrl,
})

// Custom icons
const startIcon = L.divIcon({
  className: 'custom-marker custom-marker--start',
  html: `<div class="marker-pin marker-pin--start">A</div>`,
  iconSize: [32, 32],
  iconAnchor: [16, 32],
  popupAnchor: [0, -32],
})

const destIcon = L.divIcon({
  className: 'custom-marker custom-marker--dest',
  html: `<div class="marker-pin marker-pin--dest">B</div>`,
  iconSize: [32, 32],
  iconAnchor: [16, 32],
  popupAnchor: [0, -32],
})

const fuelIcon = L.divIcon({
  className: 'custom-marker custom-marker--fuel',
  html: `<div class="marker-pin marker-pin--fuel">⛽</div>`,
  iconSize: [30, 30],
  iconAnchor: [15, 30],
  popupAnchor: [0, -30],
})

interface Props {
  routeData: RouteOptimizeResponse | null
}

export function RouteMap({ routeData }: Props) {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const layerGroupRef = useRef<L.LayerGroup | null>(null)

  // Initialize Leaflet map once on mount
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return

    const map = L.map(mapContainerRef.current, {
      center: [39.5, -98.35],  // Center of USA
      zoom: 4,
      zoomControl: true,
    })

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map)

    mapRef.current = map
    layerGroupRef.current = L.layerGroup().addTo(map)

    return () => {
      map.remove()
      mapRef.current = null
      layerGroupRef.current = null
    }
  }, [])

  // Update map when route data changes
  useEffect(() => {
    const map = mapRef.current
    const layerGroup = layerGroupRef.current
    if (!map || !layerGroup) return

    // Clear previous layers
    layerGroup.clearLayers()

    if (!routeData) {
      // Reset to USA center
      map.setView([39.5, -98.35], 4)
      return
    }

    const { route, fuel_stops, request } = routeData
    const coordinates = route.geometry.coordinates // [lon, lat]

    if (!coordinates || coordinates.length < 2) return

    // 1. Draw route polyline
    const latLngs: L.LatLngExpression[] = coordinates.map(([lon, lat]) => [lat, lon])
    const polyline = L.polyline(latLngs, {
      color: '#1a56db',
      weight: 4,
      opacity: 0.8,
    })
    layerGroup.addLayer(polyline)

    // 2. Start marker (first coordinate)
    const [startLon, startLat] = coordinates[0]
    const startMarker = L.marker([startLat, startLon], { icon: startIcon })
    startMarker.bindPopup(
      `<div class="popup">
        <strong>Start</strong><br/>
        ${request.start}
      </div>`,
    )
    layerGroup.addLayer(startMarker)

    // 3. Destination marker (last coordinate)
    const [destLon, destLat] = coordinates[coordinates.length - 1]
    const destMarker = L.marker([destLat, destLon], { icon: destIcon })
    destMarker.bindPopup(
      `<div class="popup">
        <strong>Destination</strong><br/>
        ${request.destination}
      </div>`,
    )
    layerGroup.addLayer(destMarker)

    // 4. Fuel stop markers
    fuel_stops.forEach((stop, index) => {
      const marker = L.marker([stop.latitude, stop.longitude], { icon: fuelIcon })
      marker.bindPopup(
        `<div class="popup popup--fuel">
          <div class="popup__title">⛽ Stop ${index + 1}</div>
          <div class="popup__name">${stop.name}</div>
          <div class="popup__location">${stop.city}, ${stop.state}</div>
          <hr/>
          <div class="popup__row"><span>Price</span><strong>$${stop.price_per_gallon.toFixed(3)}/gal</strong></div>
          <div class="popup__row"><span>Purchase</span><strong>${stop.gallons_purchased.toFixed(2)} gal</strong></div>
          <div class="popup__row"><span>Cost</span><strong>$${stop.cost.toFixed(2)}</strong></div>
          <div class="popup__row"><span>Mile</span><strong>${stop.distance_from_start_miles.toFixed(1)} mi</strong></div>
        </div>`,
      )
      layerGroup.addLayer(marker)
    })

    // 5. Fit map bounds to the route
    const bounds = polyline.getBounds()
    map.fitBounds(bounds, { padding: [50, 50] })
  }, [routeData])

  return (
    <div className="route-map">
      {!routeData && (
        <div className="route-map__placeholder">
          <div className="placeholder-content">
            <span className="placeholder-icon">🗺️</span>
            <h3>Enter a Route to Begin</h3>
            <p>Your optimized route and fuel stops will appear here</p>
          </div>
        </div>
      )}
      <div
        ref={mapContainerRef}
        className="route-map__container"
        style={{ opacity: routeData ? 1 : 0.3 }}
      />
    </div>
  )
}
