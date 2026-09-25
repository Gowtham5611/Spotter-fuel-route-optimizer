import type { FuelStop } from '../types/api'
import './FuelStopList.css'

interface Props {
  stops: FuelStop[]
}

export function FuelStopList({ stops }: Props) {
  if (stops.length === 0) {
    return (
      <div className="fuel-stop-list card">
        <h2 className="card__title">⛽ Fuel Stops</h2>
        <p className="fuel-stop-list__empty">
          No fuel stops needed — the vehicle can complete this route on a full tank.
        </p>
      </div>
    )
  }

  return (
    <div className="fuel-stop-list card">
      <h2 className="card__title">⛽ Fuel Stops ({stops.length})</h2>
      <div className="fuel-stop-list__items">
        {stops.map((stop, index) => (
          <div key={`${stop.station_id}-${index}`} className="fuel-stop-item">
            <div className="fuel-stop-item__header">
              <span className="fuel-stop-item__number">{index + 1}</span>
              <div className="fuel-stop-item__info">
                <span className="fuel-stop-item__name">{stop.name}</span>
                <span className="fuel-stop-item__location">
                  {stop.city}, {stop.state}
                </span>
              </div>
            </div>
            <div className="fuel-stop-item__details">
              <div className="detail-row">
                <span className="detail-label">Mile mark</span>
                <span className="detail-value">
                  {stop.distance_from_start_miles.toLocaleString('en-US', { maximumFractionDigits: 1 })} mi
                </span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Price / gallon</span>
                <span className="detail-value detail-value--price">
                  ${stop.price_per_gallon.toFixed(3)}
                </span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Gallons purchased</span>
                <span className="detail-value">
                  {stop.gallons_purchased.toFixed(2)} gal
                </span>
              </div>
              <div className="detail-row detail-row--total">
                <span className="detail-label">Stop cost</span>
                <span className="detail-value detail-value--cost">
                  ${stop.cost.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
