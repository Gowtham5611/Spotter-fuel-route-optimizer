# Algorithm Documentation

## Fuel Stop Optimization Algorithm

### Overview

The optimizer selects fuel stops along a driving route to minimize total fuel cost while guaranteeing the vehicle can complete the route without running out of fuel.

**Algorithm type**: Greedy Reachable-Station Strategy

**Guarantee level**: Near-optimal (not globally optimal). A dynamic programming approach would guarantee optimality but was not chosen to keep the implementation clear and explainable.

---

## Phase 1: Route Processing

**Input**: Start location string + Destination location string

**Steps**:
1. Geocode start → (lat, lon) via Nominatim [1 external call]
2. Geocode destination → (lat, lon) via Nominatim [1 external call]
3. Request driving route via OSRM [1 external call]
4. Parse route: extract distance (miles), duration, and GeoJSON polyline

**Total external API calls**: 3 (or 0 if cached)

---

## Phase 2: Route Corridor Filtering

**Input**: Route waypoints (lon, lat) + all fuel stations with coordinates

**Steps**:

### 2a. Bounding Box Pre-filter
Compute the axis-aligned bounding box of all route waypoints, expanded by `FUEL_ROUTE_CORRIDOR_MILES` in each direction. Stations outside this box are immediately excluded.

**Complexity**: O(n) where n = total stations (~8,000)

### 2b. Segment Distance Calculation
For each station that passes the bounding box filter:
- For each route segment (consecutive waypoint pair), compute the perpendicular distance from the station to the segment
- Take the minimum across all segments
- Exclude stations where minimum distance > `FUEL_ROUTE_CORRIDOR_MILES`

**Algorithm**: Point-to-segment projection using Euclidean approximation in lat/lon space (acceptable error for segments < 100 miles in the continental USA)

### 2c. Distance-From-Start Estimation
For each passing station, find the nearest route segment and compute the station's approximate cumulative distance from the route start by:
1. Finding the nearest waypoint index
2. Interpolating along the segment using the projection parameter `t`
3. Adding to the cumulative waypoint distance

**Output**: List of `CandidateStation` sorted by `distance_from_start_miles` ascending

---

## Phase 3: Fuel Stop Optimization

**Input**: Sorted candidate stations + total route distance

**Vehicle parameters**:
```
MAX_RANGE_MILES = 500
FUEL_EFFICIENCY_MPG = 10
TANK_CAPACITY_GALLONS = 500 / 10 = 50
```

**Initial state**: Vehicle starts at position 0.0 miles with a FULL tank (50 gallons).

### Greedy Algorithm Steps

```
current_pos = 0.0 miles
current_fuel = 50.0 gallons (full tank)

LOOP:
  fuel_miles_remaining = current_fuel * 10
  
  IF current_pos + fuel_miles_remaining >= destination:
    BREAK  # Can reach destination, done
  
  reachable_limit = current_pos + fuel_miles_remaining
  reachable = [stations where dist_from_start <= reachable_limit]
  
  IF reachable is empty:
    LOG ERROR "Route infeasible"
    BREAK
  
  chosen = select_best_station(reachable, all_candidates)
  
  # Determine how much fuel to buy
  next_target = next_cheapest_station_distance OR destination
  fuel_needed = (next_target - chosen.pos) / 10
  fuel_on_arrival = current_fuel - (chosen.pos - current_pos) / 10
  fuel_to_buy = min(fuel_needed - fuel_on_arrival, tank_capacity - fuel_on_arrival)
  
  # Record stop
  fuel_stops.append(stop with fuel_to_buy gallons)
  
  current_pos = chosen.pos
  current_fuel = fuel_on_arrival + fuel_to_buy
```

### Station Selection (select_best_station)

Among all reachable stations, select the **cheapest** station that is "safe":

A station is **safe** if from it (on a full tank) the vehicle can either:
- Reach the destination, OR
- Reach at least one other candidate station

If no safe station exists in the sorted-by-price list, fall back to the cheapest reachable station anyway (and let the next iteration handle the situation).

This look-ahead prevents the algorithm from selecting a cheap station that would strand the vehicle.

### Fuel Purchase Quantity

Rather than always filling to a full tank, the algorithm buys **just enough** to reach the next cheapest station ahead. This is the "buy-low-fill-little" strategy: don't over-buy expensive fuel hoping to skip a cheap station that's coming up.

---

## Phase 4: Cost Calculation

```
gallons_purchased_at_stop = computed by algorithm
cost_at_stop = gallons_purchased * price_per_gallon
total_gallons = route_distance_miles / 10
total_cost = sum(cost_at_stop for each stop)
```

---

## Complexity Analysis

| Phase | Complexity |
|-------|------------|
| Geocoding | O(1) (constant 2 calls) |
| Routing | O(1) (constant 1 call) |
| Bounding box filter | O(n) — n = ~8,000 stations |
| Segment distance | O(k × m) — k = filtered stations, m = route points |
| Greedy optimization | O(s²) — s = candidate stations on corridor |
| **Total** | O(n + k×m + s²) — fast for assessment scale |

Typical values: n=8000, k=50-200, m=500-2000, s=20-100.

---

## Assumptions

1. Vehicle starts with a full tank
2. Vehicle can be filled from any amount (no minimum purchase)
3. All candidates have valid prices
4. Route waypoints represent a monotonic path from start to finish
5. City-centroid coordinates introduce ~0–30 mile positional error per station

## Limitations

1. **Not globally optimal** — The greedy algorithm can be outperformed by a DP approach in specific configurations
2. **Look-ahead is 1 level** — Does not consider chains of future stops
3. **Coordinate approximation** — Station may not appear exactly where expected in the corridor
4. **Duplicate stations** — Same city may appear multiple times with slightly different prices
