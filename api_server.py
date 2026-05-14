"""
FastAPI backend for LYHLYH — serves /api/stops, /api/nearest-stop, /api/route
using A_star.AStarRouter (which extends ucs.TransitRouter) and data/*.csv.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# IMPORT AJOUTÉ : On importe AStarRouter en plus de la base UCS
from A_star import AStarRouter
from ucs import TransitRouter, Segment, RouteResult

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Le moteur principal est maintenant AStarRouter (qui contient aussi l'UCS)
router_engine: Optional[AStarRouter] = None

app = FastAPI(title="LYHLYH Transit API", version="1.1.0")
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
    # AStarRouter charge les mêmes données que TransitRouter mais prépare le vmax
    router_engine = AStarRouter(DATA_DIR)


def get_router() -> AStarRouter:
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
    # SÉCURITÉ GROUPE : Paramètres optionnels. Si l'interface ne les envoie pas, ça ne crash pas.
    departureTime: float = 8.0 
    algorithm: str = "A*" # Par défaut A*, mais tes collègues peuvent envoyer "UCS" pour tester


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
    
    if len(seg.stops) > 0:
        for i in range(len(seg.stops) - 1):
            s1 = seg.stops[i]
            s2 = seg.stops[i+1]
            
            key1 = f"{s1}|{s2}|{seg.route_id}"
            key2 = f"{s2}|{s1}|{seg.route_id}"
            
            if hasattr(r, 'bus_geometries') and key1 in r.bus_geometries:
                poly.extend(r.bus_geometries[key1])
            elif hasattr(r, 'bus_geometries') and key2 in r.bus_geometries:
                poly.extend(reversed(r.bus_geometries[key2]))
            else:
                s1_node = r.stops.get(s1)
                if s1_node:
                    poly.append([s1_node.lat, s1_node.lon])
        
        last_stop = r.stops.get(seg.stops[-1])
        if last_stop:
            poly.append([last_stop.lat, last_stop.lon])
            
    mode = seg.transport_type
    if mode == "telepherique":
        pass  
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
    algo: str = "A*",
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
        z = route_result_to_api(r, "fastest", empty, algo=body.algorithm)
        return {"routes": [z, z, z]}

    variants = [
        ("fastest", "time"),
        ("greenest", "co2"),
        ("cheapest", "distance"),
    ]
    
    routes_out = []
    w1 = body.weights.get("time", 1.0)
    w2 = body.weights.get("cost", 0.0)
    w3 = body.weights.get("co2", 0.0)

    for label, metric in variants:
        if body.algorithm.upper() == "UCS":
            # Le travail de tes collègues reste intact et appelable
            res = r.find_route(start_id, end_id, metric=metric)
            algo_used = "UCS"
        else:
            # Ton algorithme A* optimisé
            res = r.find_route_astar(
                start_id, end_id, 
                metric=metric, 
                w1=w1, w2=w2, w3=w3, 
                departure_time=body.departureTime
            )
            algo_used = "A*"
            
        routes_out.append(route_result_to_api(r, label, res, algo=algo_used))

    return {"routes": routes_out}