"""FastAPI backend for LYHLYH.

Google Maps is used for map UX, geocoding, and frontend interaction only.
Routing stays inside the custom LYHLYH graph engine.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services.google_maps import geocode, reverse_geocode, validate_coordinates
from services.route_serializer import route_result_to_api
from services.stops_service import StopsService
from settings import settings
from ucs import RouteResult, TransitRouter

router_engine: Optional[TransitRouter] = None
stops_service: Optional[StopsService] = None

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def load_graph() -> None:
    global router_engine, stops_service
    router_engine = TransitRouter(settings.data_dir)
    stops_service = StopsService(router_engine, cache_size=settings.nearest_stop_cache_size)


def get_router() -> TransitRouter:
    if router_engine is None:
        raise HTTPException(status_code=503, detail="Graph not loaded")
    return router_engine


def get_stops_service() -> StopsService:
    if stops_service is None:
        raise HTTPException(status_code=503, detail="Stops service not loaded")
    return stops_service


class GeoPoint(BaseModel):
    lat: float
    lon: float
    stopId: Optional[str] = None


class RouteRequest(BaseModel):
    start: GeoPoint
    end: GeoPoint
    weights: dict[str, float] = Field(default_factory=dict)
    transportModes: dict[str, bool] = Field(default_factory=dict)


def resolve_endpoint(r: TransitRouter, pt: GeoPoint) -> str:
    try:
        validate_coordinates(pt.lat, pt.lon)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if pt.stopId and pt.stopId in r.stops:
        return pt.stopId

    service = get_stops_service()
    nearest = service.nearest(pt.lat, pt.lon, limit=1)
    if not nearest:
        raise HTTPException(status_code=400, detail="No stop near the given coordinates")
    return nearest[0][0]


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "LYHLYH API", "docs": "/docs", "health": "ok"}


@app.get("/api/maps/config")
def api_maps_config() -> dict[str, Any]:
    return {
        "provider": "google",
        "apiKey": settings.google_maps_api_key,
        "enabled": settings.google_maps_enabled,
        "language": settings.google_maps_language,
        "region": settings.google_maps_region,
        "libraries": ["places", "geometry", "marker"],
        "visualDirections": settings.google_visual_directions,
        "center": {"lat": 36.737, "lng": 3.086},
        "bounds": {"south": 36.48, "west": 2.75, "north": 36.98, "east": 3.55},
    }


@app.get("/api/geocode")
def api_geocode(q: str) -> dict[str, Any]:
    if not q.strip():
        raise HTTPException(status_code=400, detail="Missing query")
    try:
        return {"results": geocode(q)}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/reverse-geocode")
def api_reverse_geocode(lat: float, lon: float) -> dict[str, Any]:
    try:
        validate_coordinates(lat, lon)
        return {"results": reverse_geocode(lat, lon)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/stops")
def api_stops() -> list[dict[str, Any]]:
    return get_stops_service().all_stops()


@app.get("/api/stops/categories")
def api_stop_categories() -> dict[str, list[str]]:
    return get_stops_service().categories()


@app.get("/api/network-lines")
def api_network_lines(limit: int = 2500) -> dict[str, Any]:
    return {"lines": get_stops_service().network_lines(limit=limit)}


@app.get("/api/nearest-stop")
def api_nearest_stop(
    lat: float,
    lon: float,
    limit: int = 5,
    transport_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    try:
        validate_coordinates(lat, lon)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    service = get_stops_service()
    pairs = service.nearest(lat, lon, limit=limit, transport_type=transport_type)
    return [service.stop_to_api(sid, dkm) for sid, dkm in pairs]


@app.post("/api/route")
def api_route(body: RouteRequest) -> dict[str, Any]:
    """Return backend-computed route variants optimized for map rendering."""
    r = get_router()
    start_id = resolve_endpoint(r, body.start)
    end_id = resolve_endpoint(r, body.end)

    if start_id == end_id:
        empty = RouteResult(
            found=True,
            path=[start_id],
            edges=[],
            segments=[],
            total_time=0,
            total_dist=0,
            total_co2=0,
            total_fare=0,
            nodes_explored=0,
        )
        z = route_result_to_api(r, "fastest", empty)
        return {"routes": [z], "meta": {"routingEngine": "LYHLYH", "usesGoogleDirections": False}}

    variants = [
        ("fastest", "time"),
        ("greenest", "co2"),
        ("cheapest", "distance"),
    ]
    routes_out = []
    for label, metric in variants:
        res = r.find_route(start_id, end_id, metric=metric)
        routes_out.append(route_result_to_api(r, label, res))

    return {
        "routes": routes_out,
        "meta": {
            "routingEngine": "LYHLYH",
            "usesGoogleDirections": False,
            "startStopId": start_id,
            "endStopId": end_id,
            "weightsReceived": body.weights,
            "transportModesReceived": body.transportModes,
        },
    }
