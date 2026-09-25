# Spotter Fuel Route Optimizer

> **Coding Assessment Submission** — Spotter AI  
> A production-quality REST API + interactive web frontend for fuel-efficient route planning across the USA.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Business Problem](#2-business-problem)
3. [Architecture](#3-architecture)
4. [Tech Stack](#4-tech-stack)
5. [Folder Structure](#5-folder-structure)
6. [Setup & Installation](#6-setup--installation)
7. [Environment Variables](#7-environment-variables)
8. [CSV Placement](#8-csv-placement)
9. [Data Import](#9-data-import)
10. [Running the Backend](#10-running-the-backend)
11. [Running the Frontend](#11-running-the-frontend)
12. [API Endpoints](#12-api-endpoints)
13. [Request / Response Example](#13-request--response-example)
14. [Optimization Algorithm](#14-optimization-algorithm)
15. [500-Mile Constraint](#15-500-mile-constraint)
16. [Fuel Calculation](#16-fuel-calculation)
17. [External API Strategy](#17-external-api-strategy)
18. [Caching](#18-caching)
19. [Testing](#19-testing)
20. [Assumptions](#20-assumptions)
21. [Limitations](#21-limitations)
22. [Future Improvements](#22-future-improvements)

---

## 1. Project Overview

**Spotter Fuel Route Optimizer** calculates the most cost-effective fuel stops for a long-haul truck route across the USA.

Given a start and destination location, the system:
- Geocodes both endpoints
- Requests the driving route from OSRM
- Identifies fuel stations near the route (from the company's CSV)
- Selects cost-effective stops that respect the vehicle's 500-mile maximum range
- Returns the full plan as a clean JSON API response
- Displays the route and stops on an interactive Leaflet map

---

## 2. Business Problem

Long-haul drivers need to plan fuel stops efficiently. Fuel prices vary significantly across stations. A driver who fills up at expensive stations could pay substantially more than one who plans ahead. This application automates that planning while guaranteeing the vehicle never runs out of fuel (never exceeds 500 miles between stops).

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────┐
│                  React Frontend                      │
│  RouteForm → RouteMap (Leaflet) → FuelStopList       │
└─────────────────────┬───────────────────────────────┘
                      │ POST /api/v1/routes/optimize/
                      ▼
┌─────────────────────────────────────────────────────┐
│              Django REST Framework API               │
│  RouteOptimizeView → validates → orchestrates        │
└─────────────────────┬───────────────────────────────┘
                      │
        ┌─────────────┼──────────────┐
        ▼             ▼              ▼
  Geocoding      Routing        Local DB
  (Nominatim)    (OSRM)        FuelStation
  1 API call     1 API call    (no external calls)
        │             │              │
        └─────────────┴──────────────┘
                      │
                      ▼
         Route Matching (Haversine)
         → corridor filtering
         → distance from route
                      │
                      ▼
         Fuel Optimization (Greedy)
         → 500-mile constraint
         → cheapest reachable stop
                      │
                      ▼
         Cost Calculation
         → per-stop cost
         → total fuel cost
                      │
                      ▼
               JSON Response
```

---

## 4. Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.14, Django 6.1.1, Django REST Framework 3.18.1 |
| Database | SQLite (local dev) |
| Geocoding | OpenStreetMap Nominatim (free, no key) |
| Routing | OSRM project-osrm.org (free, no key) |
| Frontend | React 18, TypeScript, Vite, React-Leaflet |
| Map | OpenStreetMap tiles via Leaflet |
| Testing | pytest, pytest-django, pytest-mock |

---

## 5. Folder Structure

```
spotter-fuel-route-api/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── pytest.ini
│   ├── config/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   ├── apps/
│   │   └── routing/
│   │       ├── models.py          # FuelStation model
│   │       ├── serializers.py     # Request/response serializers
│   │       ├── views.py           # Thin API views
│   │       ├── urls.py            # URL patterns
│   │       ├── admin.py           # Django admin registration
│   │       ├── exceptions.py      # Domain exceptions + handler
│   │       └── management/commands/
│   │           ├── import_fuel_prices.py
│   │           └── prepare_station_data.py
│   ├── services/
│   │   ├── geocoding_service.py   # Nominatim geocoding
│   │   ├── routing_service.py     # OSRM route fetching
│   │   ├── fuel_station_service.py # DB → in-memory stations
│   │   ├── route_matching_service.py # Haversine corridor filter
│   │   ├── fuel_optimization_service.py # Greedy optimizer
│   │   └── cost_calculation_service.py  # Cost serialization
│   ├── scripts/
│   │   └── city_coordinates.py   # US city centroid lookup
│   └── tests/
│       └── test_api.py            # All tests
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── App.tsx
│       ├── types/api.ts
│       ├── api/client.ts
│       └── components/
│           ├── RouteForm.tsx
│           ├── RouteMap.tsx        # Leaflet interactive map
│           ├── RouteSummary.tsx
│           └── FuelStopList.tsx
│
├── data/
│   ├── raw/
│   │   └── fuel-prices-for-be-assessment.csv   # Company source (immutable)
│   ├── processed/
│   │   └── fuel_stations_with_coordinates.csv  # Generated
│   ├── cache/                                   # Route/geocoding cache
│   └── outputs/
│
├── docs/
│   ├── architecture.md
│   ├── algorithm.md
│   ├── api.md
│   └── assumptions.md
│
├── logs/
├── screenshots/
├── README.md
├── .gitignore
└── docker-compose.yml
```

---

## 6. Setup & Installation

### Prerequisites
- Python 3.10+ (tested on 3.14)
- Node.js 18+ and npm
- Git

### Clone & Install

```bash
# Clone the repository
git clone https://github.com/<your-username>/spotter-fuel-route-api.git
cd spotter-fuel-route-api

# Backend setup
cd backend
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env with your settings (SECRET_KEY is required for production)

# Frontend setup
cd ../frontend
npm install
```

---

## 7. Environment Variables

All configuration lives in `backend/.env`. Never commit this file.

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | insecure dev key | Django secret key — set a long random string in production |
| `DEBUG` | `True` | Set `False` in production |
| `ROUTING_API_BASE_URL` | `http://router.project-osrm.org` | OSRM endpoint |
| `GEOCODING_API_BASE_URL` | `https://nominatim.openstreetmap.org` | Nominatim endpoint |
| `FUEL_ROUTE_CORRIDOR_MILES` | `15` | Stations within N miles of route are candidates |
| `MAX_RANGE_MILES` | `500` | Vehicle maximum range on a full tank |
| `FUEL_EFFICIENCY_MPG` | `10` | Vehicle fuel efficiency |
| `EXTERNAL_API_TIMEOUT` | `30` | Timeout in seconds for external API calls |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,...` | Allowed frontend origins |

---

## 8. CSV Placement

> **"The original company-provided CSV is stored under `data/raw/` and is treated as immutable source data."**

The CSV must be placed at:
```
data/raw/fuel-prices-for-be-assessment.csv
```

This file is **never modified, overwritten, or corrupted** by the application. All generated files go into `data/processed/`, `data/cache/`, or `data/outputs/`.

---

## 9. Data Import

Run these two commands in order:

```bash
cd backend

# Step 1: Import company CSV into the database
python manage.py import_fuel_prices

# Step 2: Assign city-centroid coordinates to stations
python manage.py prepare_station_data
```

Expected output:
```
Reading CSV: data/raw/fuel-prices-for-be-assessment.csv
  Imported 8151 rows
  Skipped  0 rows
  Total in DB: 8151 stations

[OK] Coordinate assignment complete.
  With coordinates   : 7531
  Without coordinates: 620
```

---

## 10. Running the Backend

```bash
cd backend

# Run Django development server
python manage.py runserver

# Server starts at http://localhost:8000
```

Test the health endpoint:
```bash
curl http://localhost:8000/api/v1/health/
# {"status":"ok"}
```

---

## 11. Running the Frontend

```bash
cd frontend
npm run dev

# Vite dev server starts at http://localhost:5173
# API calls are proxied to http://localhost:8000 automatically
```

---

## 12. API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/routes/optimize/` | Calculate optimized fuel route |
| `GET` | `/api/v1/health/` | Service health check |
| `GET` | `/api/v1/config/` | Non-secret configuration values |

See `docs/api.md` for full documentation.

---

## 13. Request / Response Example

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/routes/optimize/ \
  -H "Content-Type: application/json" \
  -d '{"start": "New York, NY", "destination": "Chicago, IL"}'
```

**Response:**
```json
{
  "request": { "start": "New York, NY", "destination": "Chicago, IL" },
  "vehicle": { "max_range_miles": 500, "fuel_efficiency_mpg": 10 },
  "route": {
    "distance_miles": 790.4,
    "duration_minutes": 730.0,
    "geometry": { "type": "LineString", "coordinates": [...] }
  },
  "fuel_stops": [
    {
      "station_id": 7,
      "name": "WOODSHED OF BIG CABIN",
      "city": "Gary",
      "state": "IN",
      "latitude": 41.59,
      "longitude": -87.35,
      "price_per_gallon": 3.007,
      "distance_from_start_miles": 356.2,
      "gallons_purchased": 35.6,
      "cost": 107.05
    }
  ],
  "fuel_summary": { "total_gallons": 79.04, "total_cost": 245.12 },
  "meta": { "external_api_calls": 3, "cached": false }
}
```

---

## 14. Optimization Algorithm

The algorithm is a **Greedy Reachable-Station Strategy**:

1. Start at position 0 miles with a full tank (500 miles / 10 MPG = 50 gallons)
2. At each decision step, find all stations reachable within remaining fuel range
3. Among reachable stations, select the **cheapest** one from which the vehicle can still continue (safety look-ahead)
4. Buy exactly enough fuel to reach the next cheapest station ahead (or the destination)
5. Repeat until the destination is reachable

**Important**: This is a **near-optimal greedy heuristic**, not a mathematically guaranteed global optimum. A dynamic programming approach would guarantee optimality but was not chosen to keep the implementation clear and explainable. See `docs/algorithm.md` for full details.

---

## 15. 500-Mile Constraint

The vehicle can travel at most **500 miles** on a full tank (50 gallons × 10 MPG).

The algorithm guarantees:
- No gap between consecutive stops exceeds 500 miles
- No gap from start to first stop exceeds 500 miles  
- No gap from last stop to destination exceeds 500 miles

If no valid station sequence exists within the constraint, the optimizer logs a warning and returns whatever stops it could find.

---

## 16. Fuel Calculation

```
fuel_required_gallons = route_distance_miles / 10
```

| Route | Gallons |
|-------|---------|
| 100 miles | 10 gallons |
| 500 miles | 50 gallons |
| 790 miles | 79 gallons |

**Tank assumption**: The vehicle **starts with a full tank** (50 gallons / 500-mile range). This is the most realistic assumption for a departing truck. The first fuel stop will top off the tank as needed for the next leg.

---

## 17. External API Strategy

The application makes a maximum of **3 external API calls** per uncached request:

| # | Call | Service | Cached |
|---|------|---------|--------|
| 1 | Geocode start | Nominatim | Yes (file cache) |
| 2 | Geocode destination | Nominatim | Yes (file cache) |
| 3 | Route start→destination | OSRM | Yes (file cache) |

**Never** makes one API call per fuel station. All station processing uses local data.

---

## 18. Caching

Caching is implemented as JSON files in `data/cache/`:

- **Geocoding cache**: `geocode_<query>.json` — persists geocoded lat/lon
- **Route cache**: `route_<lat1>_<lon1>_<lat2>_<lon2>.json` — persists OSRM route

A repeated request for the same start/destination returns 0 external API calls and sets `"cached": true` in the response metadata.

---

## 19. Testing

```bash
cd backend
pytest
```

Tests cover:
- Health endpoint
- Input validation (missing fields, empty strings, same start/dest)
- Route optimization algorithm
- 500-mile constraint enforcement
- Fuel calculation accuracy
- Cost calculation
- Route corridor matching (Haversine)
- Cheapest reachable station selection
- Unreachable station exclusion
- API response schema validation
- External API call counting
- Caching behavior
- Fuel station loading from DB

---

## 20. Assumptions

1. **Tank starts full** — The vehicle departs with a full 50-gallon tank
2. **City-centroid coordinates** — Station GPS derived from city/state lookup, not exact addresses
3. **USA-only routes** — Locations must resolve to US coordinates (enforced via Nominatim's `countrycodes=us`)
4. **Static fuel prices** — Prices from the CSV at import time; no real-time updates
5. **Single vehicle** — Optimization is per-trip for one vehicle
6. **Diesel pricing** — CSV prices are interpreted as diesel rack prices for the vehicle type

---


## 21.Performance:
- Routing API calls are limited to a maximum of 3.
- Fuel station data is loaded from the provided CSV rather than fetched
  from an external service.
- Route results are cached to avoid repeated routing API calls.
- Subsequent identical requests can therefore return significantly faster.


## 22. Limitations

1. **Station coordinates are approximate** — City centroids, not precise GPS. Stations in the same city share coordinates.
2. **Greedy algorithm is near-optimal** — May not find the absolute cheapest route in all cases
3. **OSRM public instance** — The free public OSRM server has usage limits; a self-hosted instance is recommended for production
4. **No real-time prices** — Prices are from the imported CSV snapshot
5. **SQLite** — Not suitable for multi-user production; switch to PostgreSQL
6. **No authentication** — The API is open; add token auth for production

---

## 23. Future Improvements

1. **Exact station geocoding** — Use a commercial geocoding API to get precise coordinates per station
2. **Dynamic programming optimizer** — Guarantee global optimality with DP over the station graph
3. **Real-time fuel prices** — Integrate a live fuel price API
4. **Self-hosted OSRM** — Eliminate dependency on the public OSRM server
5. **Redis caching** — Replace file-based cache with Redis for distributed deployments
6. **PostgreSQL + PostGIS** — Enable true spatial queries with GiST indexes
7. **Authentication** — Add API key or JWT auth
8. **Celery tasks** — Run heavy optimization asynchronously
9. **Route alternatives** — Return multiple route options with different optimization targets
10. **Vehicle profiles** — Support different vehicle types with different range/efficiency
