"""URL configuration for the routing app."""

from django.urls import path

from apps.routing.views import ConfigView, HealthView, RouteOptimizeView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("config/", ConfigView.as_view(), name="config"),
    path("routes/optimize/", RouteOptimizeView.as_view(), name="route-optimize"),
]
