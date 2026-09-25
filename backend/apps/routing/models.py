"""
Django models for the routing app.

FuelStation stores the processed/imported fuel station data with
city-level coordinates resolved during the preprocessing step.
"""

import logging

from django.db import models

logger = logging.getLogger(__name__)


class FuelStation(models.Model):
    """
    Represents a fuel station imported from the company's CSV file.

    Coordinates are derived from city/state lookup during preprocessing
    (see: python manage.py prepare_station_data).
    """

    # --- Source fields from CSV ---
    opis_truckstop_id = models.IntegerField(db_index=True)
    truckstop_name = models.CharField(max_length=255)
    address = models.CharField(max_length=500, blank=True, default="")
    city = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=2, db_index=True)
    rack_id = models.IntegerField(null=True, blank=True)
    retail_price = models.DecimalField(max_digits=10, decimal_places=8)

    # --- Derived fields from preprocessing ---
    latitude = models.FloatField(null=True, blank=True, db_index=True)
    longitude = models.FloatField(null=True, blank=True, db_index=True)
    has_coordinates = models.BooleanField(default=False, db_index=True)

    # --- Metadata ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Fuel Station"
        verbose_name_plural = "Fuel Stations"
        indexes = [
            models.Index(fields=["state", "has_coordinates"]),
            models.Index(fields=["latitude", "longitude"]),
        ]
        # Allow multiple records per OPIS ID (CSV has duplicates)
        unique_together = []

    def __str__(self) -> str:
        return f"{self.truckstop_name} ({self.city}, {self.state}) @ ${self.retail_price}"

    @property
    def price_float(self) -> float:
        """Return retail price as a Python float."""
        return float(self.retail_price)
