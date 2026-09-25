"""App configuration for the routing Django application."""

from django.apps import AppConfig


class RoutingConfig(AppConfig):
    """Routing application configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.routing"
    verbose_name = "Fuel Route Optimization"
