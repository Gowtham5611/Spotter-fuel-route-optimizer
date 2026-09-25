import { useState } from 'react'
import { optimizeRoute, APIClientError } from '../api/client'
import type { RouteOptimizeResponse } from '../types/api'
import './RouteForm.css'

interface Props {
  onResult: (data: RouteOptimizeResponse) => void
  onLoading: (loading: boolean) => void
  onError: (error: string | null) => void
}

export function RouteForm({ onResult, onLoading, onError }: Props) {
  const [start, setStart] = useState('')
  const [destination, setDestination] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!start.trim() || !destination.trim()) return

    setIsSubmitting(true)
    onLoading(true)
    onError(null)

    try {
      const result = await optimizeRoute({ start: start.trim(), destination: destination.trim() })
      onResult(result)
    } catch (err) {
      if (err instanceof APIClientError) {
        onError(err.errorDetail)
      } else if (err instanceof Error) {
        onError(err.message)
      } else {
        onError('An unexpected error occurred. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
      onLoading(false)
    }
  }

  const handleExample = (startVal: string, destVal: string) => {
    setStart(startVal)
    setDestination(destVal)
  }

  return (
    <div className="route-form card">
      <h2 className="card__title">🗺️ Plan Your Route</h2>

      <form onSubmit={handleSubmit} className="route-form__form">
        <div className="form-field">
          <label className="form-label" htmlFor="start">
            Start Location
          </label>
          <input
            id="start"
            type="text"
            className="form-input"
            placeholder="e.g. New York, NY"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            disabled={isSubmitting}
            required
          />
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="destination">
            Destination
          </label>
          <input
            id="destination"
            type="text"
            className="form-input"
            placeholder="e.g. Chicago, IL"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            disabled={isSubmitting}
            required
          />
        </div>

        <button
          type="submit"
          className="btn btn--primary"
          disabled={isSubmitting || !start.trim() || !destination.trim()}
        >
          {isSubmitting ? (
            <>
              <span className="btn-spinner" />
              Calculating...
            </>
          ) : (
            'Calculate Route'
          )}
        </button>
      </form>

      <div className="route-form__examples">
        <p className="examples-label">Try an example:</p>
        <div className="examples-grid">
          <button
            className="example-btn"
            onClick={() => handleExample('New York, NY', 'Chicago, IL')}
            type="button"
          >
            New York → Chicago
          </button>
          <button
            className="example-btn"
            onClick={() => handleExample('Los Angeles, CA', 'Las Vegas, NV')}
            type="button"
          >
            LA → Las Vegas
          </button>
          <button
            className="example-btn"
            onClick={() => handleExample('Dallas, TX', 'Houston, TX')}
            type="button"
          >
            Dallas → Houston
          </button>
          <button
            className="example-btn"
            onClick={() => handleExample('Chicago, IL', 'Detroit, MI')}
            type="button"
          >
            Chicago → Detroit
          </button>
        </div>
      </div>
    </div>
  )
}
