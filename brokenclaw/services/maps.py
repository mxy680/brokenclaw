import requests

from brokenclaw.config import get_settings
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.maps import (
    DirectionsRoute,
    DirectionsStep,
    DistanceMatrixEntry,
    GeocodeResult,
    LatLng,
    PlaceDetail,
    PlaceResult,
)

MAPS_BASE = "https://maps.googleapis.com/maps/api"


def _get_api_key() -> str:
    key = get_settings().google_maps_api_key
    if not key:
        raise AuthenticationError(
            "Google Maps API key not configured. Set GOOGLE_MAPS_API_KEY in .env"
        )
    return key


def _handle_response(resp: requests.Response) -> dict:
    """Check HTTP and API-level errors, return parsed JSON."""
    if resp.status_code == 429:
        raise RateLimitError("Maps API rate limit exceeded. Try again shortly.")
    if resp.status_code in (401, 403):
        raise AuthenticationError("Maps API key is invalid or restricted.")
    if resp.status_code != 200:
        raise IntegrationError(f"Maps API HTTP error {resp.status_code}: {resp.text}")
    data = resp.json()
    status = data.get("status", "OK")
    if status == "REQUEST_DENIED":
        raise AuthenticationError(f"Maps API request denied: {data.get('error_message', '')}")
    if status == "OVER_QUERY_LIMIT":
        raise RateLimitError("Maps API query limit exceeded.")
    if status not in ("OK", "ZERO_RESULTS"):
        raise IntegrationError(f"Maps API error: {status} — {data.get('error_message', '')}")
    return data


def geocode(address: str) -> list[GeocodeResult]:
    """Convert an address to coordinates."""
    resp = requests.get(
        f"{MAPS_BASE}/geocode/json",
        params={"address": address, "key": _get_api_key()},
    )
    data = _handle_response(resp)
    results = []
    for r in data.get("results", []):
        loc = r.get("geometry", {}).get("location", {})
        results.append(GeocodeResult(
            formatted_address=r.get("formatted_address", ""),
            location=LatLng(lat=loc.get("lat", 0), lng=loc.get("lng", 0)),
            place_id=r.get("place_id", ""),
        ))
    return results


def reverse_geocode(lat: float, lng: float) -> list[GeocodeResult]:
    """Convert coordinates to addresses."""
    resp = requests.get(
        f"{MAPS_BASE}/geocode/json",
        params={"latlng": f"{lat},{lng}", "key": _get_api_key()},
    )
    data = _handle_response(resp)
    results = []
    for r in data.get("results", []):
        loc = r.get("geometry", {}).get("location", {})
        results.append(GeocodeResult(
            formatted_address=r.get("formatted_address", ""),
            location=LatLng(lat=loc.get("lat", 0), lng=loc.get("lng", 0)),
            place_id=r.get("place_id", ""),
        ))
    return results


def _strip_html(text: str) -> str:
    """Remove HTML tags from directions instructions."""
    import re
    return re.sub(r"<[^>]+>", "", text)


def directions(
    origin: str,
    destination: str,
    mode: str = "driving",
) -> list[DirectionsRoute]:
    """Get directions between two places. Mode: driving, walking, bicycling, transit."""
    resp = requests.get(
        f"{MAPS_BASE}/directions/json",
        params={
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "key": _get_api_key(),
        },
    )
    data = _handle_response(resp)
    routes = []
    for route in data.get("routes", []):
        leg = route.get("legs", [{}])[0]
        steps = []
        for step in leg.get("steps", []):
            steps.append(DirectionsStep(
                instruction=_strip_html(step.get("html_instructions", "")),
                distance=step.get("distance", {}).get("text", ""),
                duration=step.get("duration", {}).get("text", ""),
            ))
        routes.append(DirectionsRoute(
            summary=route.get("summary", ""),
            distance=leg.get("distance", {}).get("text", ""),
            duration=leg.get("duration", {}).get("text", ""),
            start_address=leg.get("start_address", ""),
            end_address=leg.get("end_address", ""),
            steps=steps,
        ))
    return routes


def search_places(query: str, max_results: int = 10) -> list[PlaceResult]:
    """Search for places by text query."""
    resp = requests.get(
        f"{MAPS_BASE}/place/textsearch/json",
        params={"query": query, "key": _get_api_key()},
    )
    data = _handle_response(resp)
    results = []
    for r in data.get("results", [])[:max_results]:
        loc = r.get("geometry", {}).get("location", {})
        results.append(PlaceResult(
            name=r.get("name", ""),
            address=r.get("formatted_address", ""),
            place_id=r.get("place_id", ""),
            rating=r.get("rating"),
            types=r.get("types", []),
            location=LatLng(lat=loc.get("lat", 0), lng=loc.get("lng", 0)) if loc else None,
        ))
    return results


def get_place_details(place_id: str) -> PlaceDetail:
    """Get detailed information about a place."""
    resp = requests.get(
        f"{MAPS_BASE}/place/details/json",
        params={
            "place_id": place_id,
            "fields": "name,formatted_address,place_id,formatted_phone_number,website,rating,user_ratings_total,types,geometry,url",
            "key": _get_api_key(),
        },
    )
    data = _handle_response(resp)
    r = data.get("result", {})
    loc = r.get("geometry", {}).get("location", {})
    return PlaceDetail(
        name=r.get("name", ""),
        address=r.get("formatted_address", ""),
        place_id=r.get("place_id", place_id),
        phone=r.get("formatted_phone_number"),
        website=r.get("website"),
        rating=r.get("rating"),
        total_ratings=r.get("user_ratings_total"),
        types=r.get("types", []),
        location=LatLng(lat=loc.get("lat", 0), lng=loc.get("lng", 0)) if loc else None,
        url=r.get("url"),
    )


def distance_matrix(
    origins: list[str],
    destinations: list[str],
    mode: str = "driving",
) -> list[DistanceMatrixEntry]:
    """Get travel distance and time for multiple origin/destination pairs."""
    resp = requests.get(
        f"{MAPS_BASE}/distancematrix/json",
        params={
            "origins": "|".join(origins),
            "destinations": "|".join(destinations),
            "mode": mode,
            "key": _get_api_key(),
        },
    )
    data = _handle_response(resp)
    entries = []
    origin_addrs = data.get("origin_addresses", origins)
    dest_addrs = data.get("destination_addresses", destinations)
    for i, row in enumerate(data.get("rows", [])):
        for j, element in enumerate(row.get("elements", [])):
            entries.append(DistanceMatrixEntry(
                origin=origin_addrs[i] if i < len(origin_addrs) else origins[i],
                destination=dest_addrs[j] if j < len(dest_addrs) else destinations[j],
                distance=element.get("distance", {}).get("text") if element.get("status") == "OK" else None,
                duration=element.get("duration", {}).get("text") if element.get("status") == "OK" else None,
                status=element.get("status", "UNKNOWN"),
            ))
    return entries
