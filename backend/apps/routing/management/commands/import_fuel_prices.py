"""
Management command: import_fuel_prices

Usage:
    python manage.py import_fuel_prices [csv_path]

Reads the company's fuel-prices CSV and imports all records into the
FuelStation table. Skips malformed rows with a warning.

The original CSV is never modified.
"""

import csv
import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.routing.models import FuelStation

logger = logging.getLogger(__name__)

# Expected CSV columns (must match actual file)
EXPECTED_COLUMNS = {
    "OPIS Truckstop ID",
    "Truckstop Name",
    "Address",
    "City",
    "State",
    "Rack ID",
    "Retail Price",
}


class Command(BaseCommand):
    """Import fuel prices from the company-provided CSV into the database."""

    help = (
        "Import fuel stations and prices from the company CSV file into the database. "
        "Run this before prepare_station_data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            nargs="?",
            default=str(settings.FUEL_PRICES_CSV),
            help=f"Path to the fuel prices CSV (default: {settings.FUEL_PRICES_CSV})",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing FuelStation records before import.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])

        if not csv_path.exists():
            raise CommandError(
                f"CSV file not found: {csv_path}\n"
                f"Place the company-provided CSV at {settings.FUEL_PRICES_CSV}"
            )

        self.stdout.write(f"Reading CSV: {csv_path}")

        # Validate header
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            actual_columns = set(reader.fieldnames or [])

        if not EXPECTED_COLUMNS.issubset(actual_columns):
            missing = EXPECTED_COLUMNS - actual_columns
            raise CommandError(
                f"CSV is missing expected columns: {missing}\n"
                f"Found columns: {actual_columns}"
            )

        if options["clear"]:
            count = FuelStation.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f"Cleared {count} existing records."))

        # Import rows
        imported = 0
        skipped = 0
        batch = []
        batch_size = 500

        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):  # row 1 = header
                try:
                    opis_id = int(row["OPIS Truckstop ID"].strip())
                    name = row["Truckstop Name"].strip()
                    address = row["Address"].strip()
                    city = row["City"].strip()
                    state = row["State"].strip().upper()
                    rack_id_str = row["Rack ID"].strip()
                    rack_id = int(rack_id_str) if rack_id_str else None
                    price_str = row["Retail Price"].strip()
                    price = float(price_str)

                    if not name or not city or not state or price <= 0:
                        raise ValueError("Required field empty or invalid price.")

                    station = FuelStation(
                        opis_truckstop_id=opis_id,
                        truckstop_name=name,
                        address=address,
                        city=city,
                        state=state,
                        rack_id=rack_id,
                        retail_price=price,
                        has_coordinates=False,
                    )
                    batch.append(station)
                    imported += 1

                    if len(batch) >= batch_size:
                        with transaction.atomic():
                            FuelStation.objects.bulk_create(batch, ignore_conflicts=False)
                        self.stdout.write(f"  Imported {imported} rows...")
                        batch = []

                except (ValueError, KeyError) as e:
                    skipped += 1
                    logger.warning("Row %d skipped: %s | Row: %s", row_num, e, dict(row))

        if batch:
            with transaction.atomic():
                FuelStation.objects.bulk_create(batch, ignore_conflicts=False)

        total = FuelStation.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"\n[OK] Import complete.\n"
                f"  Imported : {imported} rows\n"
                f"  Skipped  : {skipped} rows\n"
                f"  Total in DB: {total} stations\n\n"
                f"Next step: python manage.py prepare_station_data"
            )
        )
