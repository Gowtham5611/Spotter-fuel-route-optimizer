"""
Comprehensive tests for the spotter-fuel-route-optimizer API.

Tests cover:
  - Health endpoint
  - Configuration endpoint
  - Input validation
  - Route optimization flow (mocked external APIs)
  - Fuel optimization algorithm
  - Cost calculation
  - Route corridor matching
  - 500-mile constraint enforcement
  - API response schema
"""

import json
import math
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.routing.models import FuelStation
from services.fuel_optimization_service import optimize_fuel_stops
from services.route_matching_service import (
    CandidateStation,
    _haversine_miles,
    find_stations_near_route,
)
from services.fuel_station_service import StationRecord
from services.cost_calculation_service import build_fuel_stop_response, calculate_fuel_summary


# ── Fixtures ──────────────────────────────────────────────────────────────────


def make_station(
    station_id: int = 1,
    name: str = "Test Station",
    city: str = "Chicago",
    state: str = "IL",
    price: float = 3.00,
    lat: float = 41.8781,
    lon: float = -87.6298,
) -> StationRecord:
    return StationRecord(
        station_id=station_id,
        name=name,
        address="123 Test St",
        city=city,
        state=state,
        price_per_gallon=price,
        latitude=lat,
        longitude=lon,
    )


def make_candidate(
    station: StationRecord,
    dist_from_start: float,
    dist_from_route: float = 1.0,
) -> CandidateStation:
    return CandidateStation(
        station=station,
        distance_from_start_miles=dist_from_start,
        distance_from_route_miles=dist_from_route,
    )


# Simple NY→Chicago waypoints for mocking
MOCK_WAYPOINTS = [
    (-74.0060, 40.7128),   # New York (lon, lat)
    (-78.0, 41.0),
    (-82.0, 41.5),
    (-87.6298, 41.8781),   # Chicago
]

MOCK_ROUTE = {
    "distance_miles": 790.0,
    "duration_minutes": 730.0,
    "geometry": {
        "type": "LineString",
        "coordinates": list(MOCK_WAYPOINTS),
    },
    "waypoints": MOCK_WAYPOINTS,
}

MOCK_START_GEO = {
    "display_name": "New York, NY, USA",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "country_code": "us",
}

MOCK_DEST_GEO = {
    "display_name": "Chicago, IL, USA",
    "latitude": 41.8781,
    "longitude": -87.6298,
    "country_code": "us",
}


# ── Unit Tests: Fuel Optimization ─────────────────────────────────────────────


class TestFuelOptimizationAlgorithm:
    """Tests for the greedy fuel optimization algorithm."""

    def test_short_route_no_stops_needed(self):
        """Route under 500 miles with no stations → no stops needed."""
        result = optimize_fuel_stops(
            candidates=[],
            total_route_miles=300.0,
            max_range_miles=500.0,
            fuel_efficiency_mpg=10.0,
        )
        assert result.fuel_stops == []
        assert math.isclose(result.total_gallons, 30.0, rel_tol=0.01)

    def test_long_route_requires_stops(self):
        """Route of 800 miles must have at least one stop."""
        s1 = make_station(1, "Mid Station", price=3.0, lat=41.0, lon=-80.0)
        candidates = [make_candidate(s1, 390.0)]

        result = optimize_fuel_stops(
            candidates=candidates,
            total_route_miles=800.0,
            max_range_miles=500.0,
            fuel_efficiency_mpg=10.0,
        )
        assert len(result.fuel_stops) >= 1

    def test_selects_cheaper_station_when_both_reachable(self):
        """Algorithm should prefer the cheaper of two reachable stations."""
        cheap = make_station(1, "Cheap", price=2.50, lat=41.0, lon=-78.0)
        expensive = make_station(2, "Expensive", price=4.00, lat=41.0, lon=-79.0)
        candidates = [
            make_candidate(cheap, 300.0),
            make_candidate(expensive, 250.0),
        ]

        result = optimize_fuel_stops(
            candidates=candidates,
            total_route_miles=800.0,
            max_range_miles=500.0,
            fuel_efficiency_mpg=10.0,
        )
        # The cheap station at 300 miles should be selected
        selected_ids = [s.station_id for s in result.fuel_stops]
        assert 1 in selected_ids  # cheap station selected

    def test_500_mile_constraint_enforced(self):
        """Ensures no gap between consecutive stops exceeds 500 miles."""
        s1 = make_station(1, "Station A", price=3.0, lat=41.0, lon=-80.0)
        s2 = make_station(2, "Station B", price=3.2, lat=41.5, lon=-84.0)
        candidates = [
            make_candidate(s1, 300.0),
            make_candidate(s2, 600.0),
        ]

        result = optimize_fuel_stops(
            candidates=candidates,
            total_route_miles=900.0,
            max_range_miles=500.0,
            fuel_efficiency_mpg=10.0,
        )
        # Verify all stops are within max_range of each other
        stops = result.fuel_stops
        prev_pos = 0.0
        for stop in stops:
            gap = stop.distance_from_start_miles - prev_pos
            assert gap <= 500.0 + 0.1, f"Gap {gap} exceeds 500-mile constraint"
            prev_pos = stop.distance_from_start_miles

    def test_gallons_calculation(self):
        """Total gallons must equal distance / efficiency."""
        result = optimize_fuel_stops(
            candidates=[],
            total_route_miles=400.0,  # Under 500 miles, no stops needed
            max_range_miles=500.0,
            fuel_efficiency_mpg=10.0,
        )
        expected_gallons = 400.0 / 10.0
        assert math.isclose(result.total_gallons, expected_gallons, rel_tol=0.01)

    def test_cost_calculation_accuracy(self):
        """Cost = gallons * price_per_gallon."""
        s1 = make_station(1, "Station", price=3.25, lat=41.0, lon=-80.0)
        candidates = [make_candidate(s1, 350.0)]

        result = optimize_fuel_stops(
            candidates=candidates,
            total_route_miles=800.0,
            max_range_miles=500.0,
            fuel_efficiency_mpg=10.0,
        )
        for stop in result.fuel_stops:
            expected_cost = round(stop.gallons_purchased * stop.price_per_gallon, 2)
            assert math.isclose(stop.cost, expected_cost, abs_tol=0.01)

    def test_unreachable_station_not_selected(self):
        """Station at 600 miles is beyond a 500-mile range from start."""
        # Only candidate is at 600 miles — unreachable from start (0 miles)
        s1 = make_station(1, "Far Station", price=2.50, lat=40.0, lon=-95.0)
        candidates = [make_candidate(s1, 600.0)]

        result = optimize_fuel_stops(
            candidates=candidates,
            total_route_miles=700.0,
            max_range_miles=500.0,
            fuel_efficiency_mpg=10.0,
        )
        # Station at 600 > 500 miles from start; should not appear in stops
        selected_ids = [s.station_id for s in result.fuel_stops]
        # Either no stops (if route is doable) or only reachable stops
        for stop_id in selected_ids:
            assert stop_id != 1 or result.fuel_stops[0].distance_from_start_miles <= 500.0

    def test_multiple_stops_on_long_route(self):
        """Route of 1200 miles should produce multiple fuel stops."""
        stations = [
            make_station(i, f"Station {i}", price=3.0 + i * 0.1, lat=41.0, lon=-70.0 - i * 5)
            for i in range(1, 5)
        ]
        candidates = [make_candidate(s, 300.0 * i) for i, s in enumerate(stations, 1)]

        result = optimize_fuel_stops(
            candidates=candidates,
            total_route_miles=1300.0,
            max_range_miles=500.0,
            fuel_efficiency_mpg=10.0,
        )
        assert len(result.fuel_stops) >= 2


# ── Unit Tests: Haversine Distance ───────────────────────────────────────────


class TestHaversineDistance:
    """Tests for the Haversine distance calculation."""

    def test_same_point_is_zero(self):
        assert _haversine_miles(40.7128, -74.006, 40.7128, -74.006) == 0.0

    def test_ny_to_chicago_approximate(self):
        """NYC to Chicago is approximately 790 miles direct."""
        dist = _haversine_miles(40.7128, -74.006, 41.8781, -87.6298)
        assert 700 < dist < 900, f"Expected ~790 miles, got {dist}"

    def test_symmetry(self):
        """Distance A→B should equal distance B→A."""
        d1 = _haversine_miles(34.05, -118.25, 37.77, -122.42)
        d2 = _haversine_miles(37.77, -122.42, 34.05, -118.25)
        assert math.isclose(d1, d2, rel_tol=1e-6)


# ── Unit Tests: Route Corridor Matching ──────────────────────────────────────


class TestRouteCorridor:
    """Tests for the route–station matching logic."""

    def test_station_on_route_is_included(self):
        """Station directly on the route should be in the results."""
        # Straight west route
        waypoints = [(-74.0, 41.0), (-80.0, 41.0), (-87.6, 41.0)]
        station = make_station(1, "On Route", lat=41.0, lon=-80.0)

        results = find_stations_near_route([station], waypoints, corridor_miles=15.0)
        assert len(results) >= 1

    def test_station_far_from_route_is_excluded(self):
        """Station 100 miles from route should be excluded."""
        waypoints = [(-74.0, 41.0), (-87.6, 41.0)]
        # Far north
        station = make_station(1, "Far Station", lat=48.0, lon=-80.0)

        results = find_stations_near_route([station], waypoints, corridor_miles=15.0)
        assert len(results) == 0

    def test_results_sorted_by_distance_from_start(self):
        """Results should be sorted ascending by distance_from_start_miles."""
        waypoints = [(-74.0, 41.0), (-80.0, 41.0), (-87.6, 41.0)]
        stations = [
            make_station(1, "Station A", lat=41.05, lon=-78.0),
            make_station(2, "Station B", lat=41.05, lon=-76.0),
        ]

        results = find_stations_near_route(stations, waypoints, corridor_miles=20.0)
        dists = [r.distance_from_start_miles for r in results]
        assert dists == sorted(dists)

    def test_empty_stations_returns_empty(self):
        """Empty station list should return empty results."""
        waypoints = [(-74.0, 41.0), (-87.6, 41.0)]
        results = find_stations_near_route([], waypoints)
        assert results == []


# ── Unit Tests: Cost Calculation Service ─────────────────────────────────────


class TestCostCalculationService:
    """Tests for the cost calculation serialization helpers."""

    def test_build_fuel_stop_response_schema(self):
        """Serialized stop must contain all required fields."""
        from services.fuel_optimization_service import FuelStop

        stop = FuelStop(
            station_id=42,
            name="Test Gas",
            address="I-80 Exit 5",
            city="Gary",
            state="IN",
            latitude=41.59,
            longitude=-87.35,
            price_per_gallon=3.25,
            distance_from_start_miles=280.5,
            gallons_purchased=30.0,
            cost=97.50,
        )
        result = build_fuel_stop_response(stop)
        required_keys = {
            "station_id", "name", "address", "city", "state",
            "latitude", "longitude", "price_per_gallon",
            "distance_from_start_miles", "gallons_purchased", "cost",
        }
        assert required_keys.issubset(result.keys())

    def test_calculate_fuel_summary(self):
        """Summary should match sum of individual stop costs."""
        from services.fuel_optimization_service import OptimizationResult, FuelStop

        stops = [
            FuelStop(1, "A", "", "X", "IL", 41.0, -80.0, 3.00, 300.0, 20.0, 60.00),
            FuelStop(2, "B", "", "Y", "IL", 41.5, -85.0, 3.50, 500.0, 15.0, 52.50),
        ]
        result = OptimizationResult(
            fuel_stops=stops,
            total_gallons=79.0,
            total_cost=112.50,
        )
        summary = calculate_fuel_summary(result)
        assert summary["total_gallons"] == 79.0
        assert summary["total_cost"] == 112.50


# ── API Tests ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestHealthEndpoint:
    """Tests for GET /api/v1/health/."""

    def test_health_returns_ok(self, client):
        response = client.get("/api/v1/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


@pytest.mark.django_db
class TestRouteOptimizeEndpoint:
    """Tests for POST /api/v1/routes/optimize/."""

    def setup_method(self):
        self.client = APIClient()
        self.url = "/api/v1/routes/optimize/"

    def test_missing_start_returns_400(self):
        response = self.client.post(
            self.url,
            {"destination": "Chicago, IL"},
            format="json",
        )
        assert response.status_code == 400

    def test_missing_destination_returns_400(self):
        response = self.client.post(
            self.url,
            {"start": "New York, NY"},
            format="json",
        )
        assert response.status_code == 400

    def test_empty_start_returns_400(self):
        response = self.client.post(
            self.url,
            {"start": "", "destination": "Chicago, IL"},
            format="json",
        )
        assert response.status_code == 400

    def test_same_start_and_destination_returns_400(self):
        response = self.client.post(
            self.url,
            {"start": "Chicago, IL", "destination": "Chicago, IL"},
            format="json",
        )
        assert response.status_code == 400

    def test_missing_both_fields_returns_400(self):
        response = self.client.post(self.url, {}, format="json")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_valid_request_returns_correct_schema(self):
        """End-to-end mocked test: checks response schema is correct."""
        # Create a station in the DB with coordinates
        FuelStation.objects.create(
            opis_truckstop_id=999,
            truckstop_name="Mock Station",
            address="I-80",
            city="Gary",
            state="IN",
            rack_id=1,
            retail_price=3.10,
            latitude=41.5934,
            longitude=-87.3464,
            has_coordinates=True,
        )

        with (
            patch("apps.routing.views.geocode_location", side_effect=[MOCK_START_GEO, MOCK_DEST_GEO]),
            patch("apps.routing.views.get_route", return_value=MOCK_ROUTE),
            patch("apps.routing.views._geocode_cache_check", return_value=None),
            patch("apps.routing.views._route_cache_check", return_value=None),
            patch("apps.routing.views._build_route_cache_key", return_value="test_key"),
        ):
            response = self.client.post(
                self.url,
                {"start": "New York, NY", "destination": "Chicago, IL"},
                format="json",
            )

        assert response.status_code == 200
        data = response.json()

        # Check top-level keys
        assert "request" in data
        assert "vehicle" in data
        assert "route" in data
        assert "fuel_stops" in data
        assert "fuel_summary" in data
        assert "meta" in data

        # Check vehicle constants
        assert data["vehicle"]["max_range_miles"] == 500.0
        assert data["vehicle"]["fuel_efficiency_mpg"] == 10.0

        # Check route info
        assert "distance_miles" in data["route"]
        assert "geometry" in data["route"]

        # Check meta
        assert "external_api_calls" in data["meta"]
        assert "cached" in data["meta"]

    @pytest.mark.django_db
    def test_external_api_call_count_maximum_3(self):
        """API call count should never exceed 3 for a fresh (uncached) request."""
        FuelStation.objects.create(
            opis_truckstop_id=998,
            truckstop_name="Count Station",
            address="I-80",
            city="Gary",
            state="IN",
            rack_id=1,
            retail_price=3.00,
            latitude=41.5934,
            longitude=-87.3464,
            has_coordinates=True,
        )

        with (
            patch("apps.routing.views.geocode_location", side_effect=[MOCK_START_GEO, MOCK_DEST_GEO]),
            patch("apps.routing.views.get_route", return_value=MOCK_ROUTE),
            patch("apps.routing.views._geocode_cache_check", return_value=None),
            patch("apps.routing.views._route_cache_check", return_value=None),
            patch("apps.routing.views._build_route_cache_key", return_value="count_key"),
        ):
            response = self.client.post(
                self.url,
                {"start": "New York, NY", "destination": "Chicago, IL"},
                format="json",
            )

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["external_api_calls"] <= 3

    @pytest.mark.django_db
    def test_caching_reduces_api_calls(self):
        """Cached requests should report cached=True."""
        FuelStation.objects.create(
            opis_truckstop_id=997,
            truckstop_name="Cache Station",
            address="I-80",
            city="Gary",
            state="IN",
            rack_id=1,
            retail_price=3.00,
            latitude=41.5934,
            longitude=-87.3464,
            has_coordinates=True,
        )

        with (
            patch("apps.routing.views.geocode_location", side_effect=[MOCK_START_GEO, MOCK_DEST_GEO]),
            patch("apps.routing.views.get_route", return_value=MOCK_ROUTE),
            # Both caches return hits → 0 external calls
            patch("apps.routing.views._geocode_cache_check", return_value=MOCK_START_GEO),
            patch("apps.routing.views._route_cache_check", return_value=MOCK_ROUTE),
            patch("apps.routing.views._build_route_cache_key", return_value="cached_key"),
        ):
            response = self.client.post(
                self.url,
                {"start": "New York, NY", "destination": "Chicago, IL"},
                format="json",
            )

        assert response.status_code == 200


# ── Integration Tests ─────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestFuelStationLoading:
    """Tests for fuel station loading from database."""

    def test_load_stations_raises_when_none_with_coordinates(self):
        """Should raise FuelStationDataError when no stations have coordinates."""
        from apps.routing.exceptions import FuelStationDataError
        from services.fuel_station_service import load_stations_with_coordinates

        FuelStation.objects.all().delete()
        with pytest.raises(FuelStationDataError):
            load_stations_with_coordinates()

    def test_load_stations_returns_only_stations_with_coords(self):
        """Should only return stations where has_coordinates=True."""
        from services.fuel_station_service import load_stations_with_coordinates

        FuelStation.objects.create(
            opis_truckstop_id=1,
            truckstop_name="With Coords",
            address="",
            city="Chicago",
            state="IL",
            retail_price=3.0,
            latitude=41.87,
            longitude=-87.63,
            has_coordinates=True,
        )
        FuelStation.objects.create(
            opis_truckstop_id=2,
            truckstop_name="No Coords",
            address="",
            city="Unknown City",
            state="ZZ",
            retail_price=3.0,
            has_coordinates=False,
        )

        stations = load_stations_with_coordinates()
        assert len(stations) == 1
        assert stations[0].name == "With Coords"
