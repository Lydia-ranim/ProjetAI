"""Google Maps integration helpers.

Google is used for place discovery and geocoding only. LYHLYH routing remains
fully internal.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from settings import settings

ALGIERS_BOUNDS = {
    "south": 36.48,
    "west": 2.75,
    "north": 36.98,
    "east": 3.55,
}


@dataclass(frozen=True)
class NormalizedPlace:
    label: str
    lat: float
    lon: float
    place_id: str | None = None
    address: str | None = None


def validate_coordinates(lat: float, lon: float) -> tuple[float, float]:
    lat = float(lat)
    lon = float(lon)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Coordinates are outside valid latitude/longitude ranges")
    return lat, lon


def is_inside_algiers_bounds(lat: float, lon: float) -> bool:
    lat, lon = validate_coordinates(lat, lon)
    return (
        ALGIERS_BOUNDS["south"] <= lat <= ALGIERS_BOUNDS["north"]
        and ALGIERS_BOUNDS["west"] <= lon <= ALGIERS_BOUNDS["east"]
    )


def normalize_place(raw: dict[str, Any]) -> dict[str, Any]:
    geometry = raw.get("geometry") or {}
    location = geometry.get("location") or {}
    lat = location.get("lat")
    lon = location.get("lng")
    if lat is None or lon is None:
        raise ValueError("Google place has no location")
    lat, lon = validate_coordinates(lat, lon)
    place = NormalizedPlace(
        label=raw.get("name") or raw.get("formatted_address") or raw.get("place_id") or "Place",
        lat=lat,
        lon=lon,
        place_id=raw.get("place_id"),
        address=raw.get("formatted_address") or raw.get("vicinity"),
    )
    return {
        "label": place.label,
        "lat": place.lat,
        "lon": place.lon,
        "placeId": place.place_id,
        "address": place.address,
        "insideServiceArea": is_inside_algiers_bounds(place.lat, place.lon),
    }


def _google_get(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    if not settings.google_maps_api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY is not configured")
    query = {
        **params,
        "key": settings.google_maps_api_key,
        "language": settings.google_maps_language,
        "region": settings.google_maps_region,
    }
    url = f"https://maps.googleapis.com/maps/api/{endpoint}?{urllib.parse.urlencode(query)}"
    with urllib.request.urlopen(url, timeout=8) as response:
        payload = response.read().decode("utf-8")
    data = json.loads(payload)
    status = data.get("status")
    if status not in {"OK", "ZERO_RESULTS"}:
        raise RuntimeError(data.get("error_message") or f"Google Maps error: {status}")
    return data


def geocode(address: str) -> list[dict[str, Any]]:
    data = _google_get(
        "geocode/json",
        {
            "address": address,
            "bounds": (
                f"{ALGIERS_BOUNDS['south']},{ALGIERS_BOUNDS['west']}|"
                f"{ALGIERS_BOUNDS['north']},{ALGIERS_BOUNDS['east']}"
            ),
        },
    )
    return [normalize_place(item) for item in data.get("results", [])]


def reverse_geocode(lat: float, lon: float) -> list[dict[str, Any]]:
    lat, lon = validate_coordinates(lat, lon)
    data = _google_get("geocode/json", {"latlng": f"{lat},{lon}"})
    return [normalize_place(item) for item in data.get("results", [])]

