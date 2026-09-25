"""
Management command: prepare_station_data

Usage:
    python manage.py prepare_station_data

Assigns geographic coordinates to fuel stations using city/state centroids.

Strategy:
----------
The company's CSV does NOT include GPS coordinates. We use a hardcoded
lookup table of US city/state centroids (derived from public domain data).

For cities not in the lookup, we fall back to the state centroid.

Limitations (documented):
  - Coordinates are city-centroid approximations, NOT station-exact GPS.
  - Multiple stations in the same city get identical coordinates.
  - Stations may appear "at" a city center rather than their real address.
  - This is adequate for route-corridor filtering (±15 miles) but not
    for precision navigation.
  - A production system would geocode each station individually or use a
    commercial geocoding API with the full address.

Output:
  - Updates FuelStation.latitude, .longitude, .has_coordinates in the DB.
  - Writes data/processed/fuel_stations_with_coordinates.csv (summary).
"""

import csv
import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.routing.models import FuelStation
from scripts.city_coordinates import get_city_coordinates

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Assign city-centroid coordinates to fuel stations in the database."""

    help = (
        "Assign geographic coordinates to fuel stations using city/state centroids. "
        "Run after import_fuel_prices."
    )

    def handle(self, *args, **options):
        total = FuelStation.objects.count()
        if total == 0:
            self.stdout.write(
                self.style.ERROR(
                    "No fuel stations in database. Run: python manage.py import_fuel_prices first."
                )
            )
            return

        self.stdout.write(f"Processing {total} fuel stations...")

        updated = 0
        no_coords = 0
        batch_size = 500
        batch = []

        stations = FuelStation.objects.all().order_by("id")

        for station in stations.iterator(chunk_size=batch_size):
            coords = get_city_coordinates(station.city, station.state)
            if coords:
                station.latitude = coords[0]
                station.longitude = coords[1]
                station.has_coordinates = True
                updated += 1
            else:
                station.has_coordinates = False
                no_coords += 1

            batch.append(station)
            if len(batch) >= batch_size:
                with transaction.atomic():
                    FuelStation.objects.bulk_update(
                        batch, ["latitude", "longitude", "has_coordinates"]
                    )
                self.stdout.write(f"  Updated {updated} stations...")
                batch = []

        if batch:
            with transaction.atomic():
                FuelStation.objects.bulk_update(
                    batch, ["latitude", "longitude", "has_coordinates"]
                )

        # Write processed CSV summary
        self._write_processed_csv()

        self.stdout.write(
            self.style.SUCCESS(
                f"\n[OK] Coordinate assignment complete.\n"
                f"  With coordinates   : {updated}\n"
                f"  Without coordinates: {no_coords}\n"
                f"  Processed CSV      : {settings.PROCESSED_STATIONS_CSV}\n\n"
                f"  Note: Coordinates are city-centroid approximations.\n"
                f"  See docs/assumptions.md for limitations."
            )
        )

    def _write_processed_csv(self):
        """Write a summary CSV of stations with coordinates."""
        settings.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        output_path = settings.PROCESSED_STATIONS_CSV

        qs = FuelStation.objects.filter(has_coordinates=True).values(
            "opis_truckstop_id",
            "truckstop_name",
            "address",
            "city",
            "state",
            "retail_price",
            "latitude",
            "longitude",
        )

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "opis_truckstop_id",
                    "truckstop_name",
                    "address",
                    "city",
                    "state",
                    "retail_price",
                    "latitude",
                    "longitude",
                ],
            )
            writer.writeheader()
            for row in qs.iterator():
                writer.writerow(row)

        self.stdout.write(f"  Wrote processed CSV: {output_path}")
