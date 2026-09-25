"""
Fuel optimization service.

Selects the most cost-effective set of fuel stops along a route while
respecting the vehicle's 500-mile maximum range.

Algorithm: Greedy Reachable-Station Optimization
-------------------------------------------------
This is a greedy algorithm that iterates through the route, segment by segment,
and at each "decision point" selects the cheapest reachable fuel station.

Key invariant: At every moment, the vehicle must be able to reach the next
stop (or the destination) without exceeding MAX_RANGE_MILES.

Assumption: The vehicle starts with a FULL tank (equivalent to MAX_RANGE_MILES
worth of fuel). This is the most driver-friendly assumption and avoids
requiring a fuel stop immediately at departure.

Steps:
  1. Start at position 0 miles with a full tank.
  2. Identify the furthest position reachable on a full tank from current pos.
  3. Within the reachable window, find all candidate stations.
  4. Among those, select the cheapest one that still allows the vehicle to
     reach the destination (or another station) — the "last possible" fallback
     guarantees progress when no cheap option exists.
  5. Refuel: buy exactly enough fuel to reach the next cheapest station or
     the destination, whichever is further, up to a full tank.
  6. Advance to that station and repeat.

Complexity: O(n²) in the worst case where n = number of candidate stations.
For ~500 candidates along a typical route this is negligible.

Limitations:
  - Does not guarantee global optimality (that would require DP).
  - Greedy may miss cases where a slightly farther (but cheaper) station
    would save more money overall. In practice it produces near-optimal results.
  - Documented per the assessment requirement.
"""

import logging
from dataclasses import dataclass

from django.conf import settings

from services.route_matching_service import CandidateStation

logger = logging.getLogger(__name__)


@dataclass
class FuelStop:
    """A selected fuel stop with purchase details."""

    station_id: int
    name: str
    address: str
    city: str
    state: str
    latitude: float
    longitude: float
    price_per_gallon: float
    distance_from_start_miles: float
    gallons_purchased: float
    cost: float


@dataclass
class OptimizationResult:
    """Result of the fuel optimization algorithm."""

    fuel_stops: list[FuelStop]
    total_gallons: float
    total_cost: float


def optimize_fuel_stops(
    candidates: list[CandidateStation],
    total_route_miles: float,
    max_range_miles: float | None = None,
    fuel_efficiency_mpg: float | None = None,
) -> OptimizationResult:
    """
    Select cost-effective fuel stops respecting the maximum vehicle range.

    Args:
        candidates: Stations near the route, sorted by distance_from_start_miles.
        total_route_miles: Total route distance in miles.
        max_range_miles: Maximum vehicle range on a full tank.
                         Defaults to settings.MAX_RANGE_MILES.
        fuel_efficiency_mpg: MPG fuel efficiency.
                             Defaults to settings.FUEL_EFFICIENCY_MPG.

    Returns:
        OptimizationResult with selected stops, gallons, and cost.
    """
    if max_range_miles is None:
        max_range_miles = settings.MAX_RANGE_MILES
    if fuel_efficiency_mpg is None:
        fuel_efficiency_mpg = settings.FUEL_EFFICIENCY_MPG

    tank_capacity_gallons = max_range_miles / fuel_efficiency_mpg

    if not candidates:
        logger.warning("No candidate fuel stations provided to optimizer.")
        # If total route <= max_range, vehicle can make it without stopping.
        if total_route_miles <= max_range_miles:
            total_gallons = total_route_miles / fuel_efficiency_mpg
            logger.info(
                "No fuel stops needed — route (%.1f mi) within max range (%.0f mi).",
                total_route_miles,
                max_range_miles,
            )
            return OptimizationResult(fuel_stops=[], total_gallons=total_gallons, total_cost=0.0)
        else:
            logger.error(
                "Route (%.1f mi) exceeds max range (%.0f mi) but no stations available.",
                total_route_miles,
                max_range_miles,
            )
            return OptimizationResult(fuel_stops=[], total_gallons=0.0, total_cost=0.0)

    # Filter out stations beyond the destination
    valid_candidates = [
        c for c in candidates if c.distance_from_start_miles < total_route_miles
    ]
    if not valid_candidates:
        total_gallons = total_route_miles / fuel_efficiency_mpg
        return OptimizationResult(fuel_stops=[], total_gallons=total_gallons, total_cost=0.0)

    fuel_stops: list[FuelStop] = []
    current_pos = 0.0  # miles from start
    # Vehicle starts with a full tank
    current_fuel_gallons = tank_capacity_gallons

    iteration = 0
    max_iterations = len(valid_candidates) + 10  # safety cap

    while True:
        iteration += 1
        if iteration > max_iterations:
            logger.error("Fuel optimization exceeded max iterations — breaking.")
            break

        fuel_miles_remaining = current_fuel_gallons * fuel_efficiency_mpg
        can_reach_destination = (current_pos + fuel_miles_remaining) >= total_route_miles

        if can_reach_destination:
            logger.debug(
                "Vehicle can reach destination from %.1f mi with %.2f gallons remaining.",
                current_pos,
                current_fuel_gallons,
            )
            break

        # Stations reachable from current position
        reachable_limit = current_pos + fuel_miles_remaining
        reachable = [
            c
            for c in valid_candidates
            if current_pos < c.distance_from_start_miles <= reachable_limit
        ]

        if not reachable:
            logger.error(
                "No reachable stations from position %.1f mi (fuel: %.2f gal, "
                "range: %.1f mi). Route is infeasible.",
                current_pos,
                current_fuel_gallons,
                fuel_miles_remaining,
            )
            break

        # Among reachable stations, find the cheapest one from which we can
        # still continue (either reach destination or reach another station).
        #
        # We implement the "look-ahead" heuristic:
        # - Prefer the cheapest station overall.
        # - But ensure we don't get stranded: the chosen station must either
        #   be within MAX_RANGE of the destination or within MAX_RANGE of
        #   another candidate station.
        chosen = _select_best_station(reachable, valid_candidates, total_route_miles, max_range_miles)

        if chosen is None:
            # Fallback: pick the furthest reachable station (maximize progress)
            chosen = max(reachable, key=lambda c: c.distance_from_start_miles)
            logger.debug("Fallback: selecting furthest reachable station.")

        # Fuel burned getting here
        miles_traveled = chosen.distance_from_start_miles - current_pos
        fuel_burned = miles_traveled / fuel_efficiency_mpg
        fuel_on_arrival = current_fuel_gallons - fuel_burned

        # Calculate how much fuel to buy at this stop.
        # If destination is reachable on a full tank from here, buy just enough to reach destination.
        # Otherwise, fill the tank to maximize range for the next leg.
        dist_to_dest = total_route_miles - chosen.distance_from_start_miles
        if dist_to_dest <= max_range_miles:
            # Destination is reachable! Buy just enough to reach it.
            fuel_needed = dist_to_dest / fuel_efficiency_mpg
            fuel_to_buy = max(0.0, fuel_needed - fuel_on_arrival)
        else:
            # Cannot reach destination in one leg — check if there is a cheaper station ahead
            cheaper_ahead = [
                c for c in valid_candidates
                if chosen.distance_from_start_miles < c.distance_from_start_miles <= chosen.distance_from_start_miles + max_range_miles
                and c.station.price_per_gallon < chosen.station.price_per_gallon
            ]
            if cheaper_ahead:
                # Buy just enough to reach the cheaper station
                target_dist = min(c.distance_from_start_miles for c in cheaper_ahead)
                fuel_needed = (target_dist - chosen.distance_from_start_miles) / fuel_efficiency_mpg
                fuel_to_buy = max(0.0, fuel_needed - fuel_on_arrival)
            else:
                # This is the cheapest station in range — fill the tank completely!
                fuel_to_buy = tank_capacity_gallons - fuel_on_arrival

        # Cap at full tank capacity
        fuel_to_buy = min(fuel_to_buy, tank_capacity_gallons - fuel_on_arrival)
        fuel_to_buy = max(0.0, round(fuel_to_buy, 4))

        if fuel_to_buy <= 0.001:
            # Don't need fuel here — we already have enough to reach the target.
            # Advance position and remove this candidate to make progress.
            current_pos = chosen.distance_from_start_miles
            current_fuel_gallons = fuel_on_arrival
            valid_candidates = [c for c in valid_candidates if c is not chosen]
            continue

        cost = round(fuel_to_buy * chosen.station.price_per_gallon, 4)

        stop = FuelStop(
            station_id=chosen.station.station_id,
            name=chosen.station.name,
            address=chosen.station.address,
            city=chosen.station.city,
            state=chosen.station.state,
            latitude=chosen.station.latitude,
            longitude=chosen.station.longitude,
            price_per_gallon=chosen.station.price_per_gallon,
            distance_from_start_miles=round(chosen.distance_from_start_miles, 2),
            gallons_purchased=round(fuel_to_buy, 2),
            cost=round(cost, 2),
        )
        fuel_stops.append(stop)

        logger.debug(
            "Fuel stop @ %.1f mi: %s, %.2f gal @ $%.3f = $%.2f",
            chosen.distance_from_start_miles,
            chosen.station.name,
            fuel_to_buy,
            chosen.station.price_per_gallon,
            cost,
        )

        current_pos = chosen.distance_from_start_miles
        current_fuel_gallons = fuel_on_arrival + fuel_to_buy
        # Remove chosen from candidates to avoid revisiting
        valid_candidates = [c for c in valid_candidates if c is not chosen]

    total_gallons = total_route_miles / fuel_efficiency_mpg
    total_cost = sum(s.cost for s in fuel_stops)

    logger.info(
        "Optimization complete: %d stops, %.2f total gallons, $%.2f total cost.",
        len(fuel_stops),
        total_gallons,
        total_cost,
    )

    return OptimizationResult(
        fuel_stops=fuel_stops,
        total_gallons=round(total_gallons, 2),
        total_cost=round(total_cost, 2),
    )


def _select_best_station(
    reachable: list[CandidateStation],
    all_candidates: list[CandidateStation],
    total_route_miles: float,
    max_range_miles: float,
) -> CandidateStation | None:
    """
    Select the cheapest reachable station that keeps the vehicle able to continue.

    A station is "safe" if from it the vehicle (on a full tank) can either:
    - Reach the destination, OR
    - Reach at least one other candidate station.
    """
    # Sort by price ascending
    by_price = sorted(reachable, key=lambda c: c.station.price_per_gallon)

    for candidate in by_price:
        reachable_from_here = candidate.distance_from_start_miles + max_range_miles
        can_finish = reachable_from_here >= total_route_miles
        has_next_station = any(
            c is not candidate
            and candidate.distance_from_start_miles < c.distance_from_start_miles <= reachable_from_here
            for c in all_candidates
        )
        if can_finish or has_next_station:
            return candidate

    # If no "safe" station found, return cheapest anyway (let the loop handle it)
    return by_price[0] if by_price else None


def _next_cheap_target(
    current: CandidateStation,
    all_candidates: list[CandidateStation],
    total_route_miles: float,
) -> float:
    """
    Determine how far ahead to fuel for (in miles from route start).

    Looks for the cheapest subsequent station within MAX_RANGE and returns
    its distance. Falls back to the destination.
    """
    ahead = [
        c
        for c in all_candidates
        if c.distance_from_start_miles > current.distance_from_start_miles
    ]
    if not ahead:
        return total_route_miles
    # Pick the cheapest station ahead within range for "buy just enough" strategy
    max_range = settings.MAX_RANGE_MILES
    within_range = [
        c
        for c in ahead
        if c.distance_from_start_miles <= current.distance_from_start_miles + max_range
    ]
    if not within_range:
        return total_route_miles
    cheapest_ahead = min(within_range, key=lambda c: c.station.price_per_gallon)
    return cheapest_ahead.distance_from_start_miles
