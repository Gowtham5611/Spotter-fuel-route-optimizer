"""
Cost calculation service.

Computes the final fuel cost summary from selected fuel stops.
Separated from optimization logic for testability.
"""

import logging

from services.fuel_optimization_service import FuelStop, OptimizationResult

logger = logging.getLogger(__name__)


def calculate_fuel_summary(result: OptimizationResult) -> dict:
    """
    Build the fuel_summary portion of the API response.

    Args:
        result: The output from optimize_fuel_stops().

    Returns:
        Dict with total_gallons and total_cost.
    """
    return {
        "total_gallons": round(result.total_gallons, 2),
        "total_cost": round(result.total_cost, 2),
    }


def build_fuel_stop_response(stop: FuelStop) -> dict:
    """
    Serialize a FuelStop dataclass to the API response schema.

    Args:
        stop: A selected FuelStop.

    Returns:
        Dict matching the FuelStopSerializer schema.
    """
    return {
        "station_id": stop.station_id,
        "name": stop.name,
        "address": stop.address,
        "city": stop.city,
        "state": stop.state,
        "latitude": stop.latitude,
        "longitude": stop.longitude,
        "price_per_gallon": round(stop.price_per_gallon, 4),
        "distance_from_start_miles": round(stop.distance_from_start_miles, 2),
        "gallons_purchased": round(stop.gallons_purchased, 2),
        "cost": round(stop.cost, 2),
    }
