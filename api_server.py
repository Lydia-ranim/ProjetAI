"""FastAPI backend for LYHLYH.

Google Maps is used for map UX, geocoding, and frontend interaction only.
Routing stays inside the custom LYHLYH graph engine.

Supported algorithms (selected per-request via the 'algorithm' field):
  - dijkstra  : UCS / Dijkstra — baseline, guaranteed optimal
  - astar     : A* Search — heuristic-guided, fewer node expansions
  - bidir     : Bidirectional UCS — forward + backward meet in the middle
"""

from __future__ import annotations

import time as time_module
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services.google_maps import geocode, reverse_geocode, validate_coordinates
from services.route_serializer import route_result_to_api
from services.stops_service import StopsService
from settings import settings
from ucs import RouteResult, TransitRouter
from A_star import AStarRouter
from bidirectional_ranim_bomba import BidirectionalSearch

# ── Global engine instances (populated at startup) ──────────────
router_engine: Optional[TransitRouter] = None
astar_engine: Optional[AStarRouter] = None
bidir_engine: Optional[BidirectionalSearch] = None
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
    """Load the transit graph once and create all algorithm engines.

    AStarRouter.from_router() and BidirectionalSearch() share the
    same in-memory graph — no data is loaded from disk twice.
    """
    global router_engine, astar_engine, bidir_engine, stops_service
    router_engine = TransitRouter(settings.data_dir)
    astar_engine = AStarRouter.from_router(router_engine)
    bidir_engine = BidirectionalSearch(router_engine)
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
    algorithm: str = Field(
        default="astar",
        description="Routing algorithm: 'dijkstra' (UCS), 'astar' (A*), or 'bidir' (Bidirectional UCS)",
    )


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


# ── Algorithm dispatch helpers ──────────────────────────────────

_ALGO_LABELS = {
    "dijkstra": "UCS (Dijkstra)",
    "astar": "A*",
    "bidir": "Bidirectional UCS",
}


def _bidir_to_route_result(bd) -> RouteResult:
    """Convert a BiDirResult into a RouteResult so the shared serializer works."""
    return RouteResult(
        found=bd.found,
        path=bd.path,
        edges=bd.edges,
        segments=bd.segments,
        total_time=bd.total_time,
        total_dist=bd.total_dist,
        total_co2=bd.total_co2,
        total_fare=bd.total_fare,
        nodes_explored=bd.nodes_explored,
    )


def _run_route(start_id: str, end_id: str, metric: str, algorithm: str) -> RouteResult:
    """Dispatch a single routing query to the selected algorithm engine."""
    if algorithm == "astar":
        if astar_engine is None:
            raise HTTPException(status_code=503, detail="A* engine not loaded")
        return astar_engine.find_route_astar(start_id, end_id, metric=metric)

    if algorithm == "bidir":
        if bidir_engine is None:
            raise HTTPException(status_code=503, detail="Bidirectional engine not loaded")
        bd = bidir_engine.search(start_id, end_id, metric=metric, algorithm="ucs")
        return _bidir_to_route_result(bd)

    # Default: dijkstra / UCS
    r = get_router()
    return r.find_route(start_id, end_id, metric=metric)


@app.post("/api/route")
def api_route(body: RouteRequest) -> dict[str, Any]:
    """Return backend-computed route variants optimized for map rendering.

    The frontend selects the algorithm via ``body.algorithm``:
      - dijkstra : UCS / Dijkstra (baseline)
      - astar    : A* Search (heuristic-guided)
      - bidir    : Bidirectional UCS

    Three Pareto-optimal variants (fastest, greenest, cheapest) are always
    computed so the results panel can show comparative cards.
    """
    r = get_router()
    start_id = resolve_endpoint(r, body.start)
    end_id = resolve_endpoint(r, body.end)

    algo = body.algorithm.lower().strip()
    if algo not in _ALGO_LABELS:
        algo = "astar"  # safe fallback

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
        z = route_result_to_api(r, "fastest", empty, algo=_ALGO_LABELS[algo])
        return {"routes": [z], "meta": {"routingEngine": "LYHLYH", "usesGoogleDirections": False}}

    variants = [
        ("fastest", "time"),
        ("greenest", "co2"),
        ("cheapest", "distance"),
    ]
    routes_out = []
    algo_label = _ALGO_LABELS[algo]
    for label, metric in variants:
        res = _run_route(start_id, end_id, metric, algo)
        routes_out.append(route_result_to_api(r, label, res, algo=algo_label))

    return {
        "routes": routes_out,
        "meta": {
            "routingEngine": "LYHLYH",
            "usesGoogleDirections": False,
            "algorithmUsed": algo_label,
            "startStopId": start_id,
            "endStopId": end_id,
            "weightsReceived": body.weights,
            "transportModesReceived": body.transportModes,
        },
    }
