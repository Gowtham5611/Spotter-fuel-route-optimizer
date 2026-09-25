"""
Views for the routing API.

Each view is thin — it validates input, delegates to services,
and serializes the response. No business logic lives here.
"""

import logging

from django.conf import settings
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.routing.serializers import RouteOptimizeRequestSerializer
from services.cost_calculation_service import build_fuel_stop_response, calculate_fuel_summary
from services.fuel_optimization_service import optimize_fuel_stops
from services.fuel_station_service import load_stations_with_coordinates
from services.geocoding_service import geocode_location
from services.geocoding_service import _load_from_cache as _geocode_cache_check
from services.route_matching_service import find_stations_near_route
from services.routing_service import get_route
from services.routing_service import _load_from_cache as _route_cache_check
from services.routing_service import _cache_key as _build_route_cache_key

logger = logging.getLogger(__name__)


class HealthView(APIView):
    """
    GET /api/v1/health/

    Simple health check endpoint. Returns 200 when the service is running.
    """

    def get(self, request: Request) -> Response:
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class ConfigView(APIView):
    """
    GET /api/v1/config/

    Returns non-secret configuration constants used by the optimizer.
    """

    def get(self, request: Request) -> Response:
        return Response(
            {
                "max_range_miles": settings.MAX_RANGE_MILES,
                "fuel_efficiency_mpg": settings.FUEL_EFFICIENCY_MPG,
                "fuel_route_corridor_miles": settings.FUEL_ROUTE_CORRIDOR_MILES,
                "routing_api": settings.ROUTING_API_BASE_URL,
                "geocoding_api": settings.GEOCODING_API_BASE_URL,
            },
            status=status.HTTP_200_OK,
        )


class RouteOptimizeView(APIView):
    """
    POST /api/v1/routes/optimize/

    Main endpoint: accepts start + destination, returns optimized route
    with fuel stops and cost breakdown.

    Data flow:
        1. Validate request body.
        2. Geocode start location  → 1 external call (or cached).
        3. Geocode destination     → 1 external call (or cached).
        4. Request OSRM route      → 1 external call (or cached).
        5. Load local fuel station DB → 0 external calls.
        6. Match stations to route corridor → 0 external calls.
        7. Optimize fuel stops → 0 external calls.
        8. Build and return response.

    Maximum external API calls: 3 (typically 0 after caching).
    """

    def post(self, request: Request) -> Response:
        # 1. Validate input
        serializer = RouteOptimizeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid request.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start_query: str = serializer.validated_data["start"]
        dest_query: str = serializer.validated_data["destination"]
        external_api_calls = 0
        cached = False

        logger.info("Route optimize request: '%s' → '%s'", start_query, dest_query)

        # 2. Geocode start
        start_cached = _geocode_cache_check(start_query) is not None
        start_geo = geocode_location(start_query)
        if not start_cached:
            external_api_calls += 1

        # 3. Geocode destination
        dest_cached = _geocode_cache_check(dest_query) is not None
        dest_geo = geocode_location(dest_query)
        if not dest_cached:
            external_api_calls += 1

        # 4. Get route
        route_key = _build_route_cache_key(
            start_geo["latitude"], start_geo["longitude"],
            dest_geo["latitude"], dest_geo["longitude"],
        )
        route_cached = _route_cache_check(route_key) is not None
        route = get_route(
            start_lat=start_geo["latitude"],
            start_lon=start_geo["longitude"],
            dest_lat=dest_geo["latitude"],
            dest_lon=dest_geo["longitude"],
        )
        if not route_cached:
            external_api_calls += 1
        else:
            cached = True

        if external_api_calls == 0:
            cached = True

        logger.info(
            "Route: %.1f miles, %d external API calls, cached=%s",
            route["distance_miles"],
            external_api_calls,
            cached,
        )

        # 5. Load local fuel stations (no external calls)
        stations = load_stations_with_coordinates()

        # 6. Match stations to route corridor (no external calls)
        candidates = find_stations_near_route(
            stations=stations,
            waypoints=route["waypoints"],
        )

        # 7. Optimize fuel stops (no external calls)
        optimization = optimize_fuel_stops(
            candidates=candidates,
            total_route_miles=route["distance_miles"],
        )

        # 8. Build response
        fuel_stops_response = [
            build_fuel_stop_response(stop) for stop in optimization.fuel_stops
        ]
        fuel_summary = calculate_fuel_summary(optimization)

        response_data = {
            "request": {
                "start": start_query,
                "destination": dest_query,
            },
            "vehicle": {
                "max_range_miles": settings.MAX_RANGE_MILES,
                "fuel_efficiency_mpg": settings.FUEL_EFFICIENCY_MPG,
            },
            "route": {
                "distance_miles": round(route["distance_miles"], 2),
                "duration_minutes": (
                    round(route["duration_minutes"], 1)
                    if route["duration_minutes"] is not None
                    else None
                ),
                "geometry": route["geometry"],
            },
            "fuel_stops": fuel_stops_response,
            "fuel_summary": fuel_summary,
            "meta": {
                "external_api_calls": external_api_calls,
                "cached": cached,
            },
        }

        return Response(response_data, status=status.HTTP_200_OK)
