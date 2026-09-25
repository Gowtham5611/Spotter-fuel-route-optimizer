import type { RouteOptimizeResponse } from '../types/api'
import './RouteSummary.css'

interface Props {
  data: RouteOptimizeResponse
}

export function RouteSummary({ data }: Props) {
  const { route, fuel_summary, vehicle, meta } = data

  const hours = route.duration_minutes
    ? Math.floor(route.duration_minutes / 60)
    : null
  const mins = route.duration_minutes
    ? Math.round(route.duration_minutes % 60)
    : null

  return (
    <div className="route-summary card">
      <h2 className="card__title">📊 Route Summary</h2>

      <div className="summary-grid">
        <div className="summary-stat">
          <span className="summary-stat__value">{route.distance_miles.toLocaleString('en-US', { maximumFractionDigits: 1 })} mi</span>
          <span className="summary-stat__label">Total Distance</span>
        </div>

        {hours !== null && mins !== null && (
          <div className="summary-stat">
            <span className="summary-stat__value">{hours}h {mins}m</span>
            <span className="summary-stat__label">Est. Drive Time</span>
          </div>
        )}

        <div className="summary-stat">
          <span className="summary-stat__value">{fuel_summary.total_gallons.toLocaleString('en-US', { maximumFractionDigits: 1 })} gal</span>
          <span className="summary-stat__label">Fuel Required</span>
        </div>

        <div className="summary-stat summary-stat--highlight">
          <span className="summary-stat__value">${fuel_summary.total_cost.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          <span className="summary-stat__label">Total Fuel Cost</span>
        </div>
      </div>

      <div className="summary-vehicle">
        <span>Range: {vehicle.max_range_miles} mi</span>
        <span>·</span>
        <span>Efficiency: {vehicle.fuel_efficiency_mpg} MPG</span>
        <span>·</span>
        <span>{data.fuel_stops.length} fuel stops</span>
      </div>

      <div className="summary-meta">
        <span className={`meta-badge ${meta.cached ? 'meta-badge--cached' : 'meta-badge--fresh'}`}>
          {meta.cached ? '⚡ Cached' : `${meta.external_api_calls} API calls`}
        </span>
      </div>
    </div>
  )
}
