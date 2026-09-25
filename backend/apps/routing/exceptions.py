"""
Custom exception handler for the routing API.

Maps domain exceptions to appropriate HTTP responses with clean
error messages (no stack traces in responses).
"""

import logging

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class GeocodingError(Exception):
    """Raised when a location cannot be geocoded."""

    pass


class LocationNotInUSAError(GeocodingError):
    """Raised when a geocoded location is outside the USA."""

    pass


class RoutingServiceError(Exception):
    """Raised when the external routing service fails."""

    pass


class NoRouteFoundError(RoutingServiceError):
    """Raised when OSRM cannot find a route between two points."""

    pass


class ExternalAPIRateLimitError(Exception):
    """Raised when an external service returns a rate limit response."""

    pass


class FuelStationDataError(Exception):
    """Raised when the local fuel station dataset is unavailable or invalid."""

    pass


def custom_exception_handler(exc: Exception, context: dict) -> Response | None:
    """
    Custom DRF exception handler.

    Handles domain-specific exceptions and returns clean JSON error responses.
    Internal details are logged but never exposed in the response body.
    """
    # Let DRF handle its own exceptions first
    response = exception_handler(exc, context)
    if response is not None:
        return response

    request: Request | None = context.get("request")
    view = context.get("view")
    logger.error(
        "Unhandled exception in %s: %s",
        view.__class__.__name__ if view else "unknown",
        exc,
        exc_info=True,
    )

    # Domain exceptions → HTTP codes
    if isinstance(exc, LocationNotInUSAError):
        return Response(
            {"error": str(exc) or "Location must be within the USA."},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if isinstance(exc, GeocodingError):
        return Response(
            {"error": str(exc) or "Could not geocode one or more locations."},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if isinstance(exc, NoRouteFoundError):
        return Response(
            {"error": "No driving route found between the given locations."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if isinstance(exc, ExternalAPIRateLimitError):
        return Response(
            {"error": "External mapping service rate limit reached. Please retry shortly."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    if isinstance(exc, RoutingServiceError):
        return Response(
            {"error": "Routing service is currently unavailable. Please try again later."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if isinstance(exc, FuelStationDataError):
        return Response(
            {"error": "Fuel station data is unavailable. Run the import pipeline first."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # Generic fallback
    return Response(
        {"error": "An unexpected server error occurred."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
