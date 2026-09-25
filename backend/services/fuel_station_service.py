"""
Fuel station service.

Loads the processed fuel station dataset from the database.
Provides an efficient in-memory representation for route matching.

NO external API calls are made in this service.
Coordinates come from the preprocessing step (prepare_station_data).
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from django.conf import settings
from django.db.models import QuerySet

from apps.routing.exceptions import FuelStationDataError
from apps.routing.models import FuelStation

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StationRecord:
    """
    Lightweight in-memory representation of a fuel station.

    Used throughout the optimization pipeline to avoid repeated DB queries.
    """

    station_id: int
    name: str
    address: str
    city: str
    state: str
    price_per_gallon: float
    latitude: float
    longitude: float

    def __repr__(self) -> str:
        return (
            f"StationRecord({self.name!r}, {self.city}, {self.state}, "
            f"${self.price_per_gallon:.3f}, lat={self.latitude:.4f}, lon={self.longitude:.4f})"
        )


def load_stations_with_coordinates() -> list[StationRecord]:
    """
    Load all fuel stations that have valid coordinates from the database.

    Returns:
        List of StationRecord dataclasses ready for spatial filtering.

    Raises:
        FuelStationDataError: If no stations with coordinates are found.
    """
    qs: QuerySet[FuelStation] = FuelStation.objects.filter(
        has_coordinates=True,
        latitude__isnull=False,
        longitude__isnull=False,
    ).only(
        "id",
        "opis_truckstop_id",
        "truckstop_name",
        "address",
        "city",
        "state",
        "retail_price",
        "latitude",
        "longitude",
    )

    stations = [
        StationRecord(
            station_id=s.opis_truckstop_id,
            name=s.truckstop_name,
            address=s.address,
            city=s.city,
            state=s.state,
            price_per_gallon=float(s.retail_price),
            latitude=s.latitude,
            longitude=s.longitude,
        )
        for s in qs
    ]

    if not stations:
        raise FuelStationDataError(
            "No fuel stations with coordinates found in the database. "
            "Run: python manage.py import_fuel_prices && python manage.py prepare_station_data"
        )

    logger.info("Loaded %d fuel stations with coordinates from database.", len(stations))
    return stations
