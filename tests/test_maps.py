import pytest

from brokenclaw.config import get_settings
from brokenclaw.models.maps import (
    CurrentWeather,
    DailyForecast,
    DirectionsRoute,
    DistanceMatrixEntry,
    GeocodeResult,
    PlaceDetail,
    PlaceResult,
    TimezoneResult,
)
from brokenclaw.services import maps as maps_service

requires_maps = pytest.mark.skipif(
    not get_settings().google_maps_api_key,
    reason="Maps API key not configured — set GOOGLE_MAPS_API_KEY in .env",
)


@requires_maps
class TestGeocode:
    def test_geocode_address(self):
        results = maps_service.geocode("Empire State Building, New York")
        assert isinstance(results, list)
        assert len(results) >= 1
        assert isinstance(results[0], GeocodeResult)
        assert results[0].formatted_address
        assert results[0].location.lat != 0
        assert results[0].place_id

    def test_reverse_geocode(self):
        results = maps_service.reverse_geocode(40.748817, -73.985428)
        assert isinstance(results, list)
        assert len(results) >= 1
        assert "New York" in results[0].formatted_address


@requires_maps
class TestDirections:
    def test_driving_directions(self):
        routes = maps_service.directions("New York, NY", "Boston, MA")
        assert isinstance(routes, list)
        assert len(routes) >= 1
        route = routes[0]
        assert isinstance(route, DirectionsRoute)
        assert route.distance
        assert route.duration
        assert len(route.steps) > 0


@requires_maps
class TestPlaces:
    def test_search_places(self):
        results = maps_service.search_places("coffee near Times Square New York")
        assert isinstance(results, list)
        assert len(results) >= 1
        assert isinstance(results[0], PlaceResult)
        assert results[0].name
        assert results[0].place_id

    def test_place_details(self):
        # First search to get a place_id
        results = maps_service.search_places("Empire State Building")
        assert len(results) >= 1
        detail = maps_service.get_place_details(results[0].place_id)
        assert isinstance(detail, PlaceDetail)
        assert detail.name
        assert detail.address


@requires_maps
class TestDistanceMatrix:
    def test_distance_matrix(self):
        entries = maps_service.distance_matrix(
            origins=["New York, NY"],
            destinations=["Boston, MA", "Philadelphia, PA"],
        )
        assert isinstance(entries, list)
        assert len(entries) == 2
        for entry in entries:
            assert isinstance(entry, DistanceMatrixEntry)
            assert entry.status == "OK"
            assert entry.distance
            assert entry.duration


@requires_maps
class TestCurrentWeather:
    def test_current_weather(self):
        # New York City coordinates
        weather = maps_service.get_current_weather(40.7128, -74.0060)
        assert isinstance(weather, CurrentWeather)
        assert weather.temperature
        assert weather.description
        assert weather.humidity is not None


@requires_maps
class TestDailyForecast:
    def test_daily_forecast(self):
        forecasts = maps_service.get_daily_forecast(40.7128, -74.0060, days=3)
        assert isinstance(forecasts, list)
        assert len(forecasts) >= 1
        assert isinstance(forecasts[0], DailyForecast)
        assert forecasts[0].date


@requires_maps
class TestTimezone:
    def test_timezone(self):
        # New York City
        tz = maps_service.get_timezone(40.7128, -74.0060)
        assert isinstance(tz, TimezoneResult)
        assert tz.time_zone_id == "America/New_York"
        assert "Eastern" in tz.time_zone_name
