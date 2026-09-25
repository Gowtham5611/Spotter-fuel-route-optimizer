"""
Geocoding service using OpenStreetMap Nominatim.

Performs geocoding via a single HTTP call per location.
Validates that the resolved location is within the USA.
Implements simple file-based caching to avoid repeated external calls.
"""

import json
import logging
import time
from pathlib import Path
from typing import TypedDict

import requests
from django.conf import settings

from apps.routing.exceptions import (
    ExternalAPIRateLimitError,
    GeocodingError,
    LocationNotInUSAError,
    RoutingServiceError,
)

logger = logging.getLogger(__name__)

# Nominatim User-Agent — required by OSM usage policy
_USER_AGENT = "spotter-fuel-route-optimizer/1.0 (assessment project)"

# ISO country codes for USA territories accepted as valid
_USA_COUNTRY_CODES = {"us", "united states", "united states of america"}


class GeocodedLocation(TypedDict):
    """Result of a successful geocoding call."""

    display_name: str
    latitude: float
    longitude: float
    country_code: str


def _cache_path(query: str) -> Path:
    """Return the cache file path for a given query string."""
    safe = query.lower().replace(" ", "_").replace(",", "").replace("/", "_")[:80]
    return settings.CACHE_DATA_DIR / f"geocode_{safe}.json"


def _load_from_cache(query: str) -> GeocodedLocation | None:
    """Load a cached geocoding result if it exists."""
    path = _cache_path(query)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.debug("Geocoding cache hit for: %s", query)
            return data
        except (json.JSONDecodeError, KeyError):
            path.unlink(missing_ok=True)
    return None


def _save_to_cache(query: str, result: GeocodedLocation) -> None:
    """Persist a geocoding result to the cache directory."""
    try:
        settings.CACHE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = _cache_path(query)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f)
    except OSError as e:
        logger.warning("Could not write geocoding cache: %s", e)


def geocode_location(query: str) -> GeocodedLocation:
    """
    Geocode a location string using Nominatim.

    Args:
        query: A location string such as "New York, NY" or "Chicago, IL".

    Returns:
        A GeocodedLocation dict with lat/lon and country code.

    Raises:
        GeocodingError: If the location cannot be resolved.
        LocationNotInUSAError: If the resolved location is outside the USA.
        ExternalAPIRateLimitError: If Nominatim rate-limits the request.
        RoutingServiceError: On connection/timeout errors.
    """
    query = query.strip()
    if not query:
        raise GeocodingError("Location query cannot be empty.")

    # Check cache first
    cached = _load_from_cache(query)
    if cached:
        return cached

    # Nominatim API call
    url = f"{settings.GEOCODING_API_BASE_URL}/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
        "countrycodes": "us",  # restrict to USA
    }
    headers = {"User-Agent": _USER_AGENT}

    logger.info("Geocoding location: %s", query)
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=settings.EXTERNAL_API_TIMEOUT,
        )
    except requests.Timeout:
        raise RoutingServiceError(
            f"Geocoding service timed out for location: {query}"
        )
    except requests.ConnectionError as e:
        raise RoutingServiceError(
            f"Could not connect to geocoding service: {e}"
        )

    if response.status_code == 429:
        raise ExternalAPIRateLimitError("Nominatim rate limit exceeded.")
    if response.status_code != 200:
        raise GeocodingError(
            f"Geocoding service returned HTTP {response.status_code} for: {query}"
        )

    try:
        data = response.json()
    except ValueError:
        raise GeocodingError("Geocoding service returned malformed JSON.")

    if not data:
        raise GeocodingError(
            f"Could not resolve location to USA coordinates: '{query}'. "
            "Please provide a valid US city, state, or address."
        )

    place = data[0]
    country_code: str = (
        place.get("address", {}).get("country_code", "").lower()
    )

    if country_code not in ("us",):
        raise LocationNotInUSAError(
            f"Location '{query}' resolved outside the USA (country: {country_code}). "
            "Please provide a US location."
        )

    result: GeocodedLocation = {
        "display_name": place.get("display_name", query),
        "latitude": float(place["lat"]),
        "longitude": float(place["lon"]),
        "country_code": country_code,
    }

    _save_to_cache(query, result)
    logger.info(
        "Geocoded '%s' → lat=%.4f, lon=%.4f",
        query,
        result["latitude"],
        result["longitude"],
    )
    return result
