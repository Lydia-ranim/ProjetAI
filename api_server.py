"""
FastAPI backend for LYHLYH — serves /api/stops, /api/nearest-stop, /api/route
using ucs.TransitRouter and data/*.csv.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ucs import TransitRouter, Segment, RouteResult

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

router_engine: Optional[TransitRouter] = None

app = FastAPI(title="LYHLYH Transit API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def load_graph() -> None:
    global router_engine
    router_engine = TransitRouter(DATA_DIR)


def get_router() -> TransitRouter:
    if router_engine is None:
        raise HTTPException(status_code=503, detail="Graph not loaded")
    return router_engine


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
    if pt.stopId and pt.stopId in r.stops:
        return pt.stopId
    nearest = r.find_nearest(pt.lat, pt.lon, limit=1)
    if not nearest:
        raise HTTPException(status_code=400, detail="No stop near the given coordinates")
    return nearest[0][0]


def segment_to_api(r: TransitRouter, seg: Segment) -> dict[str, Any]:
    poly: list[list[float]] = []
    for sid in seg.stops:
        s = r.stops.get(sid)
        if s:
            poly.append([s.lat, s.lon])
    mode = seg.transport_type
    if mode == "telepherique":
        pass  # keep backend spelling
    return {
        "mode": mode,
        "lineId": seg.route_id,
        "fromStopId": seg.from_stop,
        "toStopId": seg.to_stop,
        "fromName": r.get_stop_name(seg.from_stop),
        "toName": r.get_stop_name(seg.to_stop),
        "stops": list(seg.stops),
        "polyline": poly,
        "distanceKm": float(seg.distance_km),
        "durationMin": float(seg.time_min),
        "costDzd": int(seg.fare),
    }


def route_result_to_api(
    r: TransitRouter,
    label: str,
    result: RouteResult,
    algo: str = "UCS",
) -> dict[str, Any]:
    rid = {"fastest": "r-fast", "cheapest": "r-cheap", "greenest": "r-green"}.get(
        label, "r-1"
    )
    segments = [segment_to_api(r, s) for s in result.segments]
    return {
        "id": rid,
        "label": label,
        "algorithmUsed": algo,
        "found": result.found,
        "segments": segments,
        "summary": {
            "totalTimeMin": float(result.total_time),
            "totalCostDzd": int(result.total_fare),
            "totalCo2G": float(result.total_co2),
            "totalDistanceKm": float(result.total_dist),
            "numStops": len(result.path),
            "nodesExplored": int(result.nodes_explored),
        },
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "LYHLYH API", "docs": "/docs", "health": "ok"}


@app.get("/api/stops")
def api_stops() -> list[dict[str, Any]]:
    r = get_router()
    out = []
    for sid, s in r.stops.items():
        out.append(
            {
                "id": sid,
                "name": s.name,
                "lat": s.lat,
                "lon": s.lon,
                "type": s.transport_type,
                "isHub": s.is_hub,
            }
        )
    return out


@app.get("/api/nearest-stop")
def api_nearest_stop(lat: float, lon: float, limit: int = 5) -> list[dict[str, Any]]:
    r = get_router()
    pairs = r.find_nearest(lat, lon, limit=max(1, min(limit, 50)))
    out = []
    for sid, _dkm in pairs:
        s = r.stops[sid]
        out.append(
            {
                "id": sid,
                "name": s.name,
                "lat": s.lat,
                "lon": s.lon,
                "type": s.transport_type,
                "isHub": s.is_hub,
            }
        )
    return out


@app.post("/api/route")
def api_route(body: RouteRequest) -> dict[str, Any]:
    """
    Returns up to three Pareto-style variants:
    fastest (time), greenest (co2), cheapest uses distance-minimizing UCS as a proxy
    for lower overall resource use (fare is still reported from the actual path).
    """
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
        return {"routes": [z, z, z]}

    variants = [
        ("fastest", "time"),
        ("greenest", "co2"),
        ("cheapest", "distance"),
    ]
    routes_out = []
    for label, metric in variants:
        res = r.find_route(start_id, end_id, metric=metric)
        routes_out.append(route_result_to_api(r, label, res))

    return {"routes": routes_out}
