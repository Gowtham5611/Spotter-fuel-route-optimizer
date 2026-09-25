# Spotter AI Coding Assessment - Loom Video Walkthrough Guide

Use this script and checklist to record a 3–5 minute video demonstrating your solution.

---

## Video Outline (Target: 3–5 Minutes)

### 1. Introduction (30 seconds)
- Introduce yourself and summarize the project: **Spotter Fuel Route Optimizer**.
- Briefly explain the core problem: calculating optimal, cost-effective fuel stops for long-haul USA truck routes while strictly respecting the **500-mile vehicle range constraint** and **10 MPG fuel efficiency**.

### 2. Architecture Overview (1 minute)
- Point out the monorepo architecture:
  - **Backend**: Python / Django REST Framework with a clean layered architecture (views -> services -> data).
  - **Frontend**: React 18, Vite, TypeScript, and Leaflet for interactive geospatial rendering.
  - **Data Pipeline**: Raw company CSV (`data/raw/`) kept immutable; preprocessed local dataset (`data/processed/`) with city-centroid coordinates.
  - **External API Minimization**: Maximum 3 external API calls per uncached request (2 geocoding + 1 routing) and 0 external calls per fuel station (local spatial filtering).

### 3. Live Web UI Demonstration (1.5 minutes)
- Open `http://localhost:5173`.
- **Demo 1: New York, NY -> Chicago, IL** (~790 miles):
  - Show the route rendered on the Leaflet map.
  - Highlight the start marker (A), destination marker (B), and intermediate fuel stop pin (⛽).
  - Show the summary statistics: 790.6 miles, ~79.06 total gallons required, $88.88 total fuel cost.
  - Click on the fuel stop pin in Youngstown, OH to show popup details (price per gallon, gallons purchased, cost at stop).
  - Point out that because the route is ~790 miles and starts on a full tank (500-mile range), exactly 1 stop is needed.
- **Demo 2: Short Route (LA -> Las Vegas)** (~270 miles):
  - Show that 0 fuel stops are required since the route is under the 500-mile tank range.
- **Demo 3: Error Handling**:
  - Enter invalid locations (e.g. "London, UK") or leave a field empty to demonstrate real-time user-facing validation errors.

### 4. Postman API Demonstration (1 minute)
- Open Postman and import `docs/postman_collection.json`.
- Execute `GET /api/v1/health/` -> Status 200 OK.
- Execute `POST /api/v1/routes/optimize/` with `{"start": "New York, NY", "destination": "Chicago, IL"}`.
- Inspect JSON response:
  - `request`, `vehicle`, `route` (GeoJSON geometry), `fuel_stops`, `fuel_summary`, and `meta`.
  - Point out `"external_api_calls": 0` and `"cached": true` on repeated requests.

### 5. Automated Tests & Conclusion (30 seconds)
- Show terminal running `python -m pytest`.
- Show **28 passed tests** covering health, validation, 500-mile constraint, Haversine filtering, and greedy algorithm.
- Conclude the video.
