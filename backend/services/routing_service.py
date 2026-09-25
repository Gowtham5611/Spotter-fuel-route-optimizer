"""
Routing service using OSRM (Open Source Routing Machine).

Makes a SINGLE routing API call for the full start→destination route.
Returns distance, duration, and a GeoJSON-compatible route geometry.

External calls: 1 per unique (start_lat, start_lon, dest_lat, dest_lon) tuple.
Caching prevents repeated calls for the same coordinate pair.
"""

import json
import logging
import math
from pathlib import Path
from typing import TypedDict

import requests
from django.conf import settings

from apps.routing.exceptions import (
    ExternalAPIRateLimitError,
    NoRouteFoundError,
    RoutingServiceError,
)

logger = logging.getLogger(__name__)

_USER_AGENT = "spotter-fuel-route-optimizer/1.0 (assessment project)"

# OSRM returns distances in metres; 1 metre = 0.000621371 miles
_METRES_PER_MILE = 1609.344
# OSRM returns duration in seconds; /60 → minutes
_SECONDS_PER_MINUTE = 60.0


class RouteGeometry(TypedDict):
    """GeoJSON LineString geometry."""

    type: str
    coordinates: list[list[float]]


class RouteResult(TypedDict):
    """Parsed route returned by the routing service."""

    distance_miles: float
    duration_minutes: float | None
    geometry: RouteGeometry
    # Ordered list of (lon, lat) waypoints decoded from geometry
    waypoints: list[tuple[float, float]]


def _cache_key(slat: float, slon: float, dlat: float, dlon: float) -> str:
    return f"route_{slat:.4f}_{slon:.4f}_{dlat:.4f}_{dlon:.4f}"


def _cache_path(key: str) -> Path:
    return settings.CACHE_DATA_DIR / f"{key}.json"


def _load_from_cache(key: str) -> RouteResult | None:
    path = _cache_path(key)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.debug("Routing cache hit for key: %s", key)
            return data
        except (json.JSONDecodeError, KeyError):
            path.unlink(missing_ok=True)
    return None


def _save_to_cache(key: str, result: RouteResult) -> None:
    try:
        settings.CACHE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = _cache_path(key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f)
    except OSError as e:
        logger.warning("Could not write routing cache: %s", e)


def get_route(
    start_lat: float,
    start_lon: float,
    dest_lat: float,
    dest_lon: float,
) -> RouteResult:
    """
    Request a driving route from OSRM.

    Makes exactly ONE external HTTP call (or zero if cached).

    Args:
        start_lat: Start latitude.
        start_lon: Start longitude.
        dest_lat: Destination latitude.
        dest_lon: Destination longitude.

    Returns:
        RouteResult with distance, optional duration, geometry, and waypoints.

    Raises:
        NoRouteFoundError: When OSRM cannot compute a route.
        RoutingServiceError: On connection/timeout/HTTP errors.
        ExternalAPIRateLimitError: If rate-limited.
    """
    key = _cache_key(start_lat, start_lon, dest_lat, dest_lon)
    cached = _load_from_cache(key)
    if cached:
        return cached

    # Build OSRM route URL
    # Format: /route/v1/driving/{lon1},{lat1};{lon2},{lat2}
    coords = f"{start_lon},{start_lat};{dest_lon},{dest_lat}"
    url = (
        f"{settings.ROUTING_API_BASE_URL}/route/v1/driving/{coords}"
        "?overview=full&geometries=geojson&steps=false"
    )

    logger.info(
        "Requesting route from OSRM: (%.4f, %.4f) → (%.4f, %.4f)",
        start_lat,
        start_lon,
        dest_lat,
        dest_lon,
    )

    headers = {"User-Agent": _USER_AGENT}
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=settings.EXTERNAL_API_TIMEOUT,
        )
    except requests.Timeout:
        raise RoutingServiceError(
            "OSRM routing service timed out. Please try again."
        )
    except requests.ConnectionError as e:
        raise RoutingServiceError(f"Cannot connect to OSRM: {e}")

    if response.status_code == 429:
        raise ExternalAPIRateLimitError("OSRM rate limit exceeded.")
    if response.status_code != 200:
        raise RoutingServiceError(
            f"OSRM returned HTTP {response.status_code}."
        )

    try:
        data = response.json()
    except ValueError:
        raise RoutingServiceError("OSRM returned malformed JSON.")

    if data.get("code") != "Ok":
        code = data.get("code", "Unknown")
        if code in ("NoRoute", "NoSegment"):
            raise NoRouteFoundError(
                "No driving route found between the given locations."
            )
        raise RoutingServiceError(f"OSRM error code: {code}")

    routes = data.get("routes", [])
    if not routes:
        raise NoRouteFoundError("OSRM returned no routes.")

    route = routes[0]
    distance_metres: float = route.get("distance", 0.0)
    duration_seconds: float | None = route.get("duration")

    geometry_raw = route.get("geometry", {})
    if not geometry_raw or geometry_raw.get("type") != "LineString":
        raise RoutingServiceError("OSRM returned unexpected geometry format.")

    coordinates: list[list[float]] = geometry_raw.get("coordinates", [])
    if len(coordinates) < 2:
        raise NoRouteFoundError("OSRM route geometry contains too few points.")

    geometry: RouteGeometry = {
        "type": "LineString",
        "coordinates": coordinates,
    }

    # Waypoints as (lon, lat) tuples — preserved as returned by OSRM
    waypoints: list[tuple[float, float]] = [(c[0], c[1]) for c in coordinates]

    result: RouteResult = {
        "distance_miles": distance_metres / _METRES_PER_MILE,
        "duration_minutes": (
            duration_seconds / _SECONDS_PER_MINUTE
            if duration_seconds is not None
            else None
        ),
        "geometry": geometry,
        "waypoints": waypoints,
    }

    _save_to_cache(key, result)
    logger.info(
        "Route computed: %.1f miles, %.0f minutes, %d geometry points",
        result["distance_miles"],
        result["duration_minutes"] or 0,
        len(coordinates),
    )
    return result
