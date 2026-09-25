# Architecture Documentation

## System Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     User's Browser                         │
│                                                            │
│  ┌────────────┐  ┌────────────────┐  ┌─────────────────┐   │
│  │ RouteForm  │  │  RouteMap      │  │  FuelStopList   │   │
│  │ (inputs)   │  │  (Leaflet map) │  │  (cost table)   │   │ 
│  └──────┬─────┘  └────────────────┘  └─────────────────┘   │
│         │ POST /api/v1/routes/optimize/                    │
└─────────┼──────────────────────────────────────────────────┘
          │
          │ HTTP (JSON)
          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Django REST Framework                      │
│                                                             │
│  ┌────────────────────────────────────────────────────┐     │
│  │  RouteOptimizeView (apps/routing/views.py)          │    │
│  │  - Validates input (serializer)                     │    │
│  │  - Orchestrates services                            │    │
│  │  - Builds response                                  │    │
│  └──────┬────────────┬──────────────┬────────────────┘      │
│         │            │              │                       │
│         ▼            ▼              ▼                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐    │
│  │ Geocoding│  │ Routing  │  │ FuelStation Service  │    │
│  │ Service  │  │ Service  │  │ (local DB query)     │    │
│  └──────┬───┘  └────┬─────┘  └──────────┬───────────┘    │
│         │            │                   │                  │
└─────────┼────────────┼───────────────────┼──────────────────┘
          │            │                   │
     1 call        1 call             0 calls
          │            │                   │
          ▼            ▼                   ▼
┌──────────────┐ ┌──────────┐ ┌────────────────────────┐
│  Nominatim   │ │  OSRM    │ │  SQLite Database        │
│  (OSM)       │ │  Router  │ │  (FuelStation table)    │
└──────────────┘ └──────────┘ └────────────────────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │ Route Matching Svc   │
                              │ - BBox pre-filter    │
                              │ - Haversine distance │
                              │ - Corridor filter    │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │ Fuel Optimization    │
                              │ - Greedy algorithm   │
                              │ - 500-mile limit     │
                              │ - Cheapest station   │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │ Cost Calculation     │
                              │ - Per-stop cost      │
                              │ - Total fuel cost    │
                              └──────────┬───────────┘
                                         │
                                         ▼
                                   JSON Response
```

## Layer Responsibilities

### Presentation Layer (`apps/routing/views.py`)
- Receive HTTP requests
- Validate input via serializers
- Call services in correct order
- Build response from service outputs
- Handle and transform exceptions via `custom_exception_handler`

### Service Layer (`services/`)
Each service has a single responsibility:

| Service | Responsibility |
|---------|---------------|
| `geocoding_service` | Nominatim API, caching, USA validation |
| `routing_service` | OSRM API, route parsing, caching |
| `fuel_station_service` | DB → in-memory `StationRecord` objects |
| `route_matching_service` | Spatial corridor filtering (pure Python) |
| `fuel_optimization_service` | Greedy optimization algorithm |
| `cost_calculation_service` | Cost serialization for API response |

### Data Layer (`apps/routing/models.py`)
- `FuelStation` model with indexed fields
- Accessed only through `fuel_station_service`

### Scripts Layer (`scripts/`)
- `city_coordinates.py` — Lookup table, no external dependencies
- Import/prepare commands use this during preprocessing only

## Data Flow

```
User Input
  → Validation (DRF Serializer)
  → Geocoding (2× Nominatim, cached)
  → Routing (1× OSRM, cached)
  → Station Loading (local DB)
  → Route Matching (pure Python Haversine)
  → Optimization (greedy algorithm)
  → Cost Calculation
  → JSON Response
  → Frontend renders map + table
```

## External Dependencies

| Service | URL | Auth Required | Rate Limit |
|---------|-----|---------------|------------|
| Nominatim | nominatim.openstreetmap.org | No | 1 req/sec (OSM policy) |
| OSRM | router.project-osrm.org | No | Reasonable use |
| OSM Tiles | tile.openstreetmap.org | No | Reasonable use |

## Caching Architecture

```
Request arrives
  │
  ├─ Check geocode cache (data/cache/geocode_*.json)
  │   └─ HIT → return cached coords (0 external calls)
  │   └─ MISS → call Nominatim → save to cache
  │
  ├─ Check route cache (data/cache/route_*.json)
  │   └─ HIT → return cached route (0 external calls)
  │   └─ MISS → call OSRM → save to cache
  │
  └─ Station data → always local DB (0 external calls)
```
