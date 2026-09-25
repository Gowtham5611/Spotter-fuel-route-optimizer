"""
Serializers for the routing API.

Handles input validation for route optimization requests and
output serialization for route + fuel stop responses.
"""

from rest_framework import serializers


# ── Request Serializers ──────────────────────────────────────────────────────


class RouteOptimizeRequestSerializer(serializers.Serializer):
    """Validates the POST /api/v1/routes/optimize/ request body."""

    start = serializers.CharField(
        max_length=300,
        help_text="USA start location (city, state or full address)",
    )
    destination = serializers.CharField(
        max_length=300,
        help_text="USA destination location (city, state or full address)",
    )

    def validate_start(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Start location cannot be empty.")
        return value

    def validate_destination(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Destination cannot be empty.")
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs.get("start", "").lower() == attrs.get("destination", "").lower():
            raise serializers.ValidationError(
                "Start and destination must be different locations."
            )
        return attrs


# ── Response Serializers ─────────────────────────────────────────────────────


class CoordinateSerializer(serializers.Serializer):
    """A simple lat/lon pair."""

    latitude = serializers.FloatField()
    longitude = serializers.FloatField()


class RouteGeometrySerializer(serializers.Serializer):
    """GeoJSON LineString geometry representing the route polyline."""

    type = serializers.CharField()
    coordinates = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField())
    )


class RouteInfoSerializer(serializers.Serializer):
    """Route metadata returned in the response."""

    distance_miles = serializers.FloatField()
    duration_minutes = serializers.FloatField(allow_null=True)
    geometry = RouteGeometrySerializer()


class FuelStopSerializer(serializers.Serializer):
    """A single selected fuel stop with cost breakdown."""

    station_id = serializers.IntegerField()
    name = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    price_per_gallon = serializers.FloatField()
    distance_from_start_miles = serializers.FloatField()
    gallons_purchased = serializers.FloatField()
    cost = serializers.FloatField()


class FuelSummarySerializer(serializers.Serializer):
    """Aggregate fuel cost summary."""

    total_gallons = serializers.FloatField()
    total_cost = serializers.FloatField()


class VehicleInfoSerializer(serializers.Serializer):
    """Vehicle constants used for the calculation."""

    max_range_miles = serializers.FloatField()
    fuel_efficiency_mpg = serializers.FloatField()


class MetaSerializer(serializers.Serializer):
    """Response metadata for transparency."""

    external_api_calls = serializers.IntegerField()
    cached = serializers.BooleanField()


class RouteOptimizeResponseSerializer(serializers.Serializer):
    """Complete response body for the optimize endpoint."""

    request = serializers.DictField()
    vehicle = VehicleInfoSerializer()
    route = RouteInfoSerializer()
    fuel_stops = FuelStopSerializer(many=True)
    fuel_summary = FuelSummarySerializer()
    meta = MetaSerializer()
