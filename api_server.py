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
from A_star import AStarRouter
from BFS_Yanis_ZA3IM import BFSRouter
from bidirectional_ranim_bomba import BidirectionalSearch

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

router_engine: Optional[TransitRouter] = None
astar_engine: Optional[AStarRouter] = None
bfs_engine: Optional[BFSRouter] = None
bidir_engine: Optional[BidirectionalSearch] = None

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
    global router_engine, astar_engine, bfs_engine, bidir_engine
    router_engine = TransitRouter(DATA_DIR)
    astar_engine = AStarRouter(DATA_DIR)
    bfs_engine = BFSRouter(DATA_DIR)
    bidir_engine = BidirectionalSearch(router_engine, bfs_router=bfs_engine)


def get_router() -> TransitRouter:
    if router_engine is None:
        raise HTTPException(status_code=503, detail="Graph not loaded")
    return router_engine

def get_all_engines():
    if router_engine is None or astar_engine is None or bfs_engine is None or bidir_engine is None:
        raise HTTPException(status_code=503, detail="Engines not loaded")
    return router_engine, astar_engine, bfs_engine, bidir_engine


class GeoPoint(BaseModel):
    lat: float
    lon: float
    stopId: Optional[str] = None


class RouteRequest(BaseModel):
    start: GeoPoint
    end: GeoPoint
    weights: dict[str, float] = Field(default_factory=dict)
    transportModes: dict[str, bool] = Field(default_factory=dict)
    optimizeBy: str = Field(default="time", description="Optimization target: time, cost, or distance")
    returnComparison: bool = Field(default=False, description="Return all algorithms comparison")


def resolve_endpoint(r: TransitRouter, pt: GeoPoint) -> str:
    if pt.stopId and pt.stopId in r.stops:
        return pt.stopId
    nearest = r.find_nearest(pt.lat, pt.lon, limit=1)
    if not nearest:
        raise HTTPException(status_code=400, detail="No stop near the given coordinates")
    return nearest[0][0]


def segment_to_api(r: TransitRouter, seg: Segment) -> dict[str, Any]:
    poly: list[list[float]] = []
    
    if len(seg.stops) > 0:
        for i in range(len(seg.stops) - 1):
            s1 = seg.stops[i]
            s2 = seg.stops[i+1]
            
            # Try to find the exact road geometry between the two stops
            key1 = f"{s1}|{s2}|{seg.route_id}"
            key2 = f"{s2}|{s1}|{seg.route_id}"
            
            if hasattr(r, 'bus_geometries') and key1 in r.bus_geometries:
                poly.extend(r.bus_geometries[key1])
            elif hasattr(r, 'bus_geometries') and key2 in r.bus_geometries:
                # Reverse the geometry to match the travel direction
                poly.extend(reversed(r.bus_geometries[key2]))
            else:
                s1_node = r.stops.get(s1)
                if s1_node:
                    poly.append([s1_node.lat, s1_node.lon])
        
        # Append the very last stop
        last_stop = r.stops.get(seg.stops[-1])
        if last_stop:
            poly.append([last_stop.lat, last_stop.lon])
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
    Runs all 4 algorithms (UCS, A*, Bidir-UCS, Bidir-A*) in parallel
    and returns the best route based on optimizeBy parameter.
    If returnComparison=True, also returns full comparison data.
    """
    r, astar_r, bfs_r, bidir = get_all_engines()
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
        return {"routes": [z, z, z], "comparison": None, "bestAlgorithm": "ucs"}

    comparison = bidir.compare_all(start_id, end_id, metric=body.optimizeBy)

    optimize_key = body.optimizeBy
    best_algo = None
    best_score = float('inf')

    for algo_key, algo_data in comparison.items():
        if algo_key.startswith('_'):
            continue
        if not isinstance(algo_data, dict) or not algo_data.get('found', False):
            continue
        if algo_key == 'bidir_bfs' and optimize_key == 'time':
            score = algo_data.get('total_journey_time', float('inf'))
        else:
            score = algo_data.get(optimize_key, float('inf'))
        if score <= best_score:
            best_score = score
            best_algo = algo_key

    comparison_summary = []
    for algo_key, algo_data in comparison.items():
        if algo_key.startswith('_'):
            continue
        if isinstance(algo_data, dict) and algo_data.get('found', False):
            comparison_summary.append({
                "algorithm": algo_data.get('algorithm', algo_key),
                "found": algo_data['found'],
                "totalTime": algo_data.get('total_time', 0),
                "totalDistance": algo_data.get('total_dist', 0),
                "totalCost": algo_data.get('total_fare', 0),
                "totalCo2": algo_data.get('total_co2', 0),
                "nodesExplored": algo_data.get('nodes_explored', 0),
                "runtimeMs": algo_data.get('runtime_ms', 0),
            })

    if best_algo and best_algo in comparison:
        best_data = comparison[best_algo]
        if 'segments' in best_data:
            best_result = RouteResult(
                found=best_data['found'],
                path=[],
                edges=[],
                segments=best_data['segments'],
                total_time=best_data.get('total_time', 0),
                total_dist=best_data.get('total_dist', 0),
                total_co2=best_data.get('total_co2', 0),
                total_fare=best_data.get('total_fare', 0),
                nodes_explored=best_data.get('nodes_explored', 0),
            )
            best_route = route_result_to_api(r, "best", best_result, algo=best_data.get('algorithm', best_algo))
        else:
            best_route = None
    else:
        best_route = None

    return {
        "routes": [best_route] if best_route else [],
        "comparison": comparison_summary if body.returnComparison else None,
        "bestAlgorithm": best_algo or "none",
        "optimizedBy": body.optimizeBy
    }
