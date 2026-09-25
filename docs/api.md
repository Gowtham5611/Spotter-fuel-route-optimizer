# API Documentation

## Base URL

```
http://localhost:8000/api/v1/
```

---

## Endpoints

### POST `/api/v1/routes/optimize/`

Calculate an optimized fuel route between two US locations.

**Request Body:**

```json
{
  "start": "New York, NY",
  "destination": "Chicago, IL"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `start` | string | Yes | USA start location (city, state, or full address) |
| `destination` | string | Yes | USA destination location |

**Success Response (200 OK):**

```json
{
  "request": {
    "start": "New York, NY",
    "destination": "Chicago, IL"
  },
  "vehicle": {
    "max_range_miles": 500.0,
    "fuel_efficiency_mpg": 10.0
  },
  "route": {
    "distance_miles": 790.4,
    "duration_minutes": 730.0,
    "geometry": {
      "type": "LineString",
      "coordinates": [
        [-74.006, 40.7128],
        [-78.0, 41.0],
        [-87.6298, 41.8781]
      ]
    }
  },
  "fuel_stops": [
    {
      "station_id": 7,
      "name": "WOODSHED OF BIG CABIN",
      "address": "I-44, EXIT 283 & US-69",
      "city": "Gary",
      "state": "IN",
      "latitude": 41.5934,
      "longitude": -87.3464,
      "price_per_gallon": 3.007,
      "distance_from_start_miles": 356.2,
      "gallons_purchased": 35.6,
      "cost": 107.05
    }
  ],
  "fuel_summary": {
    "total_gallons": 79.04,
    "total_cost": 245.12
  },
  "meta": {
    "external_api_calls": 3,
    "cached": false
  }
}
```

**Error Responses:**

| Status | When |
|--------|------|
| `400 Bad Request` | Missing or empty fields, same start/destination |
| `404 Not Found` | No driving route found |
| `422 Unprocessable Entity` | Location cannot be geocoded or is outside USA |
| `429 Too Many Requests` | External service rate limit hit |
| `503 Service Unavailable` | OSRM or geocoding service down |
| `500 Internal Server Error` | Unexpected server error |

**Error Response Body:**
```json
{
  "error": "Human-readable error message"
}
```

---

### GET `/api/v1/health/`

Service liveness check.

**Response (200 OK):**
```json
{
  "status": "ok"
}
```

---

### GET `/api/v1/config/`

Returns non-secret configuration constants.

**Response (200 OK):**
```json
{
  "max_range_miles": 500.0,
  "fuel_efficiency_mpg": 10.0,
  "fuel_route_corridor_miles": 15.0,
  "routing_api": "http://router.project-osrm.org",
  "geocoding_api": "https://nominatim.openstreetmap.org"
}
```

---

## Postman Collection

Import the following to Postman:

1. **Health Check**: `GET http://localhost:8000/api/v1/health/`
2. **Config**: `GET http://localhost:8000/api/v1/config/`
3. **Optimize Route (NY → Chicago)**:
   - Method: `POST`
   - URL: `http://localhost:8000/api/v1/routes/optimize/`
   - Headers: `Content-Type: application/json`
   - Body: `{"start": "New York, NY", "destination": "Chicago, IL"}`

4. **Invalid location test**:
   - Body: `{"start": "London, UK", "destination": "Paris, France"}`
   - Expected: `422`

5. **Missing field test**:
   - Body: `{"start": "New York, NY"}`
   - Expected: `400`
