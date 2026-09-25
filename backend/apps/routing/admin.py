"""Admin registration for fuel station model."""

from django.contrib import admin

from apps.routing.models import FuelStation


@admin.register(FuelStation)
class FuelStationAdmin(admin.ModelAdmin):
    """Admin view for FuelStation with useful filters and search."""

    list_display = [
        "opis_truckstop_id",
        "truckstop_name",
        "city",
        "state",
        "retail_price",
        "has_coordinates",
    ]
    list_filter = ["state", "has_coordinates"]
    search_fields = ["truckstop_name", "city", "state", "opis_truckstop_id"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["state", "city", "retail_price"]
