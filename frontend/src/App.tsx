import { useState } from 'react'
import type { RouteOptimizeResponse } from './types/api'
import { RouteForm } from './components/RouteForm'
import { RouteMap } from './components/RouteMap'
import { RouteSummary } from './components/RouteSummary'
import { FuelStopList } from './components/FuelStopList'
import './App.css'

export default function App() {
  const [routeData, setRouteData] = useState<RouteOptimizeResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__inner">
          <div className="app-header__brand">
            <span className="app-header__logo">⛽</span>
            <div>
              <h1 className="app-header__title">Spotter Fuel Route Optimizer</h1>
              <p className="app-header__subtitle">Find the most cost-effective fuel stops for your route</p>
            </div>
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className="app-layout">
          {/* Left Panel */}
          <aside className="app-sidebar">
            <RouteForm
              onResult={setRouteData}
              onLoading={setIsLoading}
              onError={setError}
            />

            {error && (
              <div className="alert alert--error" role="alert">
                <strong>Error:</strong> {error}
              </div>
            )}

            {isLoading && (
              <div className="loading-card">
                <div className="loading-spinner" />
                <p>Calculating optimal route...</p>
              </div>
            )}

            {routeData && !isLoading && (
              <>
                <RouteSummary data={routeData} />
                <FuelStopList stops={routeData.fuel_stops} />
              </>
            )}
          </aside>

          {/* Map Panel */}
          <div className="app-map-panel">
            <RouteMap routeData={routeData} />
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>Spotter Fuel Route Optimizer &mdash; Assessment Project</p>
      </footer>
    </div>
  )
}
