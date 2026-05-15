"""
FastAPI backend for LYHLYH — serves /api/stops, /api/nearest-stop, /api/route
using A_star.AStarRouter (which extends ucs.TransitRouter) and data/*.csv.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from A_star import AStarRouter
from ucs import TransitRouter, Segment, RouteResult
from schedule import WORKING_HOURS

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
    router_engine = AStarRouter(DATA_DIR)


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
    departureTime: Optional[float] = None  # Fractional hour (8.5 = 08:30)
    algorithm: str = "A*"


def resolve_endpoint(r: TransitRouter, pt: GeoPoint) -> str:
    if pt.stopId and pt.stopId in r.stops:
        return pt.stopId
    nearest = r.find_nearest(pt.lat, pt.lon, limit=1)
    if not nearest:
        raise HTTPException(status_code=400, detail="No stop near the given coordinates")
    return nearest[0][0]


def segment_to_api(r: TransitRouter, seg: Segment) -> dict[str, Any]:
    # Build polyline by concatenating per-link geometries (if available).
    # This avoids duplicating all stop coordinates then appending link shapes,
    # which produced jagged or mis-ordered polylines. We also normalize points
    # to [lat, lon] and avoid duplicate consecutive points.
    poly: list[list[float]] = []

    def _normalize_point(pt: list[float]) -> list[float]:
        # If values look like (lon, lat) (lon outside [-90,90]) swap them.
        if not isinstance(pt, (list, tuple)) or len(pt) < 2:
            return pt
        a, b = pt[0], pt[1]
        try:
            fa, fb = float(a), float(b)
        except Exception:
            return [a, b]
        if abs(fa) > 90 and abs(fb) <= 90:
            return [fb, fa]
        return [fa, fb]

    stops = seg.stops or []
    for i in range(len(stops) - 1):
        s1 = stops[i]
        s2 = stops[i + 1]

        key1 = f"{s1}|{s2}|{seg.route_id}"
        key2 = f"{s2}|{s1}|{seg.route_id}"

        geom = None
        if hasattr(r, 'bus_geometries') and key1 in r.bus_geometries:
            geom = r.bus_geometries[key1]
        elif hasattr(r, 'bus_geometries') and key2 in r.bus_geometries:
            geom = list(reversed(r.bus_geometries[key2]))

        if geom and isinstance(geom, list) and len(geom) > 0:
            # Normalize and append geometry points, avoiding duplicate consecutive points
            for pt in geom:
                np = _normalize_point(pt)
                if not poly or poly[-1] != np:
                    poly.append(np)
        else:
            # Fallback to using the stop coordinate for this link start
            s1_node = r.stops.get(s1)
            if s1_node:
                np = [s1_node.lat, s1_node.lon]
                if not poly or poly[-1] != np:
                    poly.append(np)

    # Ensure the final stop is appended
    if stops:
        last = r.stops.get(stops[-1])
        if last:
            np = [last.lat, last.lon]
            if not poly or poly[-1] != np:
                poly.append(np)
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


def build_schedule_warnings(result: RouteResult, depart: float) -> list:
    """Generate schedule warnings for segments near service closure."""
    warnings = []
    clock = depart
    for seg in result.segments:
        mode = seg.transport_type
        if mode != 'walk':
            o, c = WORKING_HOURS.get(mode, (0, 24))
            end_clock = clock + seg.time_min / 60.0
            if c - end_clock < 0.5 and c - end_clock > 0:
                warnings.append({
                    "type": "service_ending_soon",
                    "mode": mode,
                    "closesAt": c,
                    "message": f"{mode.capitalize()} closes at {int(c)}:{int((c % 1) * 60):02d}"
                })
        clock += seg.time_min / 60.0
    return warnings


def route_result_to_api(
    r: TransitRouter,
    label: str,
    result: RouteResult,
    algo: str = "A*",
    depart: float = None,
) -> dict[str, Any]:
    rid = {
        "fastest": "r-fast", "cheapest": "r-cheap",
        "greenest": "r-green", "recommended": "r-rec",
    }.get(label, "r-1")
    segments = [segment_to_api(r, s) for s in result.segments]
    warnings = build_schedule_warnings(result, depart) if depart is not None else []
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
            "departureTime": depart,
        },
        "scheduleWarnings": warnings,
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "LYHLYH API", "docs": "/docs", "health": "ok"}


@app.get("/api/working-hours")
def api_working_hours() -> dict[str, Any]:
    """Return operating hours for each transport mode (fractional hours, 24h)."""
    return {
        mode: {"open": hours[0], "close": hours[1]}
        for mode, hours in WORKING_HOURS.items()
    }


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
    Returns up to four route variants:
      1. recommended — uses user's weight preferences (w1*Time + w2*Price + w3*CO2)
      2. fastest     — pure time optimization
      3. greenest    — pure CO2 optimization
      4. cheapest    — distance-minimizing (proxy for lower fare)

    Supports algorithm switching via body.algorithm ('A*' or 'UCS').
    """
    r = get_router()
    start_id = resolve_endpoint(r, body.start)
    end_id = resolve_endpoint(r, body.end)

    # Determine departure time
    depart = body.departureTime if body.departureTime is not None else (datetime.now().hour + datetime.now().minute / 60.0)

    if start_id == end_id:
        empty = RouteResult(
            found=True, path=[start_id], edges=[], segments=[], total_time=0,
            total_dist=0, total_co2=0, total_fare=0, nodes_explored=0
        )
        z = route_result_to_api(r, "fastest", empty, algo=body.algorithm, depart=depart)
        return {"routes": [z, z, z]}

    # Extract user weight preferences
    w = body.weights or {}
    w1, w2, w3 = float(w.get("time", 0.33)), float(w.get("cost", 0.33)), float(w.get("co2", 0.34))

    routes_out = []

    # ── Recommended ──
    if body.algorithm.upper() == "UCS":
        rec = r.find_route(start_id, end_id, metric="weighted", depart=depart, w1=w1, w2=w2, w3=w3)
        rec_algo = "UCS-weighted"
    else:
        rec = r.find_route_astar(start_id, end_id, metric="weighted", w1=w1, w2=w2, w3=w3, depart=depart)
        rec_algo = "A*-weighted"
    routes_out.append(route_result_to_api(r, "recommended", rec, algo=rec_algo, depart=depart))

    # ── Pareto variants ──
    for label, metric in [("fastest", "time"), ("greenest", "co2"), ("cheapest", "distance")]:
        if body.algorithm.upper() == "UCS":
            res = r.find_route(start_id, end_id, metric=metric, depart=depart)
            algo_used = "UCS"
        else:
            res = r.find_route_astar(start_id, end_id, metric=metric, w1=w1, w2=w2, w3=w3, depart=depart)
            algo_used = "A*"
        routes_out.append(route_result_to_api(r, label, res, algo=algo_used, depart=depart))

    return {"routes": routes_out}
