# Assumptions & Limitations

## Key Assumptions

### 1. Vehicle Starting State
**Assumption**: The vehicle starts with a **full tank** (50 gallons = 500-mile range).

**Rationale**: A departing truck realistically fills up before a long journey. This assumption is the most driver-friendly and simplifies the optimization problem without introducing unrealistic scenarios.

**Impact**: The first fuel stop may be further into the route than if the vehicle started empty.

### 2. Fuel Efficiency
**Assumption**: Constant **10 MPG** throughout the route.

**Real-world deviation**: Actual efficiency varies with speed, terrain, load, and weather. This simplification is per the assessment specification.

### 3. Station Coordinates — City Centroids
**Assumption**: When the CSV provides no GPS coordinates, we use **city-centroid coordinates** derived from a lookup table of US city locations.

**Rationale**: The company's CSV contains only city/state for each station — no lat/lon. Precise geocoding of 8,000+ addresses would require thousands of external API calls (violating the N+1 rule) and would be slow and rate-limited.

**Documented Limitation**: Multiple stations in the same city share the same coordinates. A station labeled "I-80, Exit 142" in Kearney, NE will have Kearney's city centroid (40.6993°N, -99.0817°W) rather than its precise highway location.

**Coverage**: ~92% of stations received coordinates (7,531 of 8,151). The remaining 8% use state centroids or were unresolvable.

### 4. Static Fuel Prices
**Assumption**: Fuel prices come from the CSV at import time and do not change.

**Real-world deviation**: Fuel prices fluctuate daily.

### 5. Retail Price Interpretation
**Assumption**: The `Retail Price` column in the CSV represents the **diesel retail price per gallon** at the given station/rack combination.

### 6. Route Geometry
**Assumption**: OSRM waypoints represent a monotonically progressing path from start to destination, so stations can be assigned a meaningful "miles from start" value.

### 7. USA-Only Constraint
**Assumption**: Both start and destination must resolve to US locations. Enforced via Nominatim's `countrycodes=us` parameter.

---

## Known Limitations

### Coordinate Accuracy
Station coordinates are city-centroid approximations. This means:
- Stations appear at the city center on the map, not their actual location
- The 15-mile corridor filter may include or exclude stations inaccurately
- A station appearing "near" the route may not actually be accessible from that highway

### Algorithm Optimality
The greedy algorithm is **near-optimal**, not globally optimal. In some edge cases:
- It may select a moderately priced station when a cheaper one slightly further ahead was reachable
- It does not explore all combinations of stops

### Public OSRM Rate Limits
The free public OSRM instance at `router.project-osrm.org` is a shared community resource. High traffic may cause timeouts. For production use, deploy a self-hosted OSRM instance.

### CSV Duplicates
The OPIS CSV contains duplicate `OPIS Truckstop ID` entries (same ID, same or different prices). All rows are imported. The optimizer may see multiple "stations" at the same location with slightly different prices.

### SQLite Concurrency
SQLite does not support concurrent writes. This is fine for the assessment (single-user, single-server) but must be replaced with PostgreSQL for multi-user production.
