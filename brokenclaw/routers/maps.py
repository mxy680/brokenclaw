from fastapi import APIRouter

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

router = APIRouter(prefix="/api/maps", tags=["maps"])


@router.get("/geocode")
def geocode(address: str) -> list[GeocodeResult]:
    return maps_service.geocode(address)


@router.get("/reverse-geocode")
def reverse_geocode(lat: float, lng: float) -> list[GeocodeResult]:
    return maps_service.reverse_geocode(lat, lng)


@router.get("/directions")
def directions(origin: str, destination: str, mode: str = "driving") -> list[DirectionsRoute]:
    return maps_service.directions(origin, destination, mode)


@router.get("/places/search")
def search_places(query: str, max_results: int = 10) -> list[PlaceResult]:
    return maps_service.search_places(query, max_results)


@router.get("/places/{place_id}")
def get_place_details(place_id: str) -> PlaceDetail:
    return maps_service.get_place_details(place_id)


@router.get("/distance-matrix")
def distance_matrix(origins: str, destinations: str, mode: str = "driving") -> list[DistanceMatrixEntry]:
    """Origins and destinations are pipe-separated (e.g. 'New York|Boston')."""
    return maps_service.distance_matrix(
        origins.split("|"),
        destinations.split("|"),
        mode,
    )


@router.get("/weather/current")
def current_weather(lat: float, lng: float, units: str = "IMPERIAL") -> CurrentWeather:
    return maps_service.get_current_weather(lat, lng, units)


@router.get("/weather/forecast")
def daily_forecast(lat: float, lng: float, days: int = 5, units: str = "IMPERIAL") -> list[DailyForecast]:
    return maps_service.get_daily_forecast(lat, lng, days, units)


@router.get("/timezone")
def timezone(lat: float, lng: float) -> TimezoneResult:
    return maps_service.get_timezone(lat, lng)
