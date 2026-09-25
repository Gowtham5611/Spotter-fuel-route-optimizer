"""
Route matching service.

Finds fuel stations that lie within a configurable corridor along the route.

Algorithm:
1. Build a bounding box around the route polyline (+ corridor margin).
2. Pre-filter stations to the bounding box (O(n) linear scan — fast for ~8k stations).
3. For each pre-filtered station, compute minimum Haversine distance to any
   route segment.
4. Keep stations within FUEL_ROUTE_CORRIDOR_MILES.
5. Additionally compute each station's cumulative distance from the route start
   by finding the nearest route waypoint and projecting along the route.

This approach avoids ANY external API calls and is O(n * m) where n is the
number of candidate stations (after bbox filtering) and m is the number of
route segments. For the assessment scale (~8k stations, ~500–2000 route
points after simplification) this is fast enough without spatial indexing.
"""

import logging
import math
from dataclasses import dataclass

from django.conf import settings

from services.fuel_station_service import StationRecord

logger = logging.getLogger(__name__)

# Earth radius in miles for Haversine calculations
_EARTH_RADIUS_MILES = 3958.8

# Degrees latitude per mile (approximate)
_DEGREES_LAT_PER_MILE = 1.0 / 69.0
# Degrees longitude per mile at 40° latitude (mid-USA — good enough for bbox)
_DEGREES_LON_PER_MILE = 1.0 / 53.0


@dataclass
class CandidateStation:
    """A fuel station found near the route, with its distance from start."""

    station: StationRecord
    distance_from_start_miles: float
    distance_from_route_miles: float


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute the great-circle distance in miles between two lat/lon points.

    Uses the Haversine formula.
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * _EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def _point_to_segment_distance_miles(
    px: float,
    py: float,
    ax: float,
    ay: float,
    bx: float,
    by: float,
) -> float:
    """
    Minimum distance (miles) from point (px, py) to segment (ax,ay)-(bx,by).

    Works in lat/lon space approximated as Euclidean — acceptable for
    segments < 100 miles long within the continental USA.
    """
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        # Segment is a point
        return _haversine_miles(py, px, ay, ax)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    return _haversine_miles(py, px, proj_y, proj_x)


def _cumulative_distances(waypoints: list[tuple[float, float]]) -> list[float]:
    """
    Compute the cumulative distance (miles) along the route polyline.

    Returns a list of length len(waypoints) where entry i is the
    total distance from the first waypoint to waypoint i.
    Waypoints are (lon, lat) tuples as returned by OSRM.
    """
    cumulative = [0.0]
    for i in range(1, len(waypoints)):
        lon_a, lat_a = waypoints[i - 1]
        lon_b, lat_b = waypoints[i]
        d = _haversine_miles(lat_a, lon_a, lat_b, lon_b)
        cumulative.append(cumulative[-1] + d)
    return cumulative


def find_stations_near_route(
    stations: list[StationRecord],
    waypoints: list[tuple[float, float]],
    corridor_miles: float | None = None,
) -> list[CandidateStation]:
    """
    Find all stations within the route corridor and compute their route distances.

    Args:
        stations: All fuel stations with coordinates.
        waypoints: Ordered (lon, lat) route waypoints from OSRM.
        corridor_miles: Maximum perpendicular distance from the route to include
                        a station. Defaults to settings.FUEL_ROUTE_CORRIDOR_MILES.

    Returns:
        List of CandidateStation sorted by distance_from_start_miles ascending.
    """
    if corridor_miles is None:
        corridor_miles = settings.FUEL_ROUTE_CORRIDOR_MILES

    if not waypoints or len(waypoints) < 2:
        logger.warning("Route has fewer than 2 waypoints; cannot match stations.")
        return []

    # 1. Bounding box with corridor margin
    lons = [wp[0] for wp in waypoints]
    lats = [wp[1] for wp in waypoints]
    margin_lat = corridor_miles * _DEGREES_LAT_PER_MILE
    margin_lon = corridor_miles * _DEGREES_LON_PER_MILE

    bbox_min_lat = min(lats) - margin_lat
    bbox_max_lat = max(lats) + margin_lat
    bbox_min_lon = min(lons) - margin_lon
    bbox_max_lon = max(lons) + margin_lon

    # 2. Pre-filter by bounding box
    candidates_bbox = [
        s
        for s in stations
        if bbox_min_lat <= s.latitude <= bbox_max_lat
        and bbox_min_lon <= s.longitude <= bbox_max_lon
    ]
    logger.debug(
        "Bounding box filter: %d / %d stations in bbox.",
        len(candidates_bbox),
        len(stations),
    )

    if not candidates_bbox:
        logger.warning("No stations found within route bounding box.")
        return []

    # 3. Compute cumulative distances along route
    cum_dist = _cumulative_distances(waypoints)
    total_route_distance = cum_dist[-1]

    # 4. For each bbox candidate: compute min distance to any route segment
    results: list[CandidateStation] = []

    for station in candidates_bbox:
        slat, slon = station.latitude, station.longitude
        min_dist_to_route = float("inf")
        nearest_wp_idx = 0
        nearest_t = 0.0

        for i in range(len(waypoints) - 1):
            lon_a, lat_a = waypoints[i]
            lon_b, lat_b = waypoints[i + 1]
            seg_dist = _point_to_segment_distance_miles(
                slon, slat, lon_a, lat_a, lon_b, lat_b
            )
            if seg_dist < min_dist_to_route:
                min_dist_to_route = seg_dist
                nearest_wp_idx = i
                # Compute t along this segment for distance interpolation
                dx, dy = lon_b - lon_a, lat_b - lat_a
                if dx != 0 or dy != 0:
                    nearest_t = max(
                        0.0,
                        min(
                            1.0,
                            ((slon - lon_a) * dx + (slat - lat_a) * dy)
                            / (dx * dx + dy * dy),
                        ),
                    )
                else:
                    nearest_t = 0.0

        if min_dist_to_route > corridor_miles:
            continue

        # 5. Compute distance from start using nearest waypoint + interpolation
        seg_length = (
            _haversine_miles(
                waypoints[nearest_wp_idx][1],
                waypoints[nearest_wp_idx][0],
                waypoints[nearest_wp_idx + 1][1] if nearest_wp_idx + 1 < len(waypoints) else waypoints[nearest_wp_idx][1],
                waypoints[nearest_wp_idx + 1][0] if nearest_wp_idx + 1 < len(waypoints) else waypoints[nearest_wp_idx][0],
            )
            if nearest_wp_idx + 1 < len(waypoints)
            else 0.0
        )
        dist_from_start = cum_dist[nearest_wp_idx] + nearest_t * seg_length

        results.append(
            CandidateStation(
                station=station,
                distance_from_start_miles=dist_from_start,
                distance_from_route_miles=min_dist_to_route,
            )
        )

    results.sort(key=lambda c: c.distance_from_start_miles)
    logger.info(
        "Route matching: %d stations within %.1f-mile corridor.",
        len(results),
        corridor_miles,
    )
    return results
