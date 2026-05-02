"""
FastAPI backend for Algiers Transit Router.
Serves POST /api/route and GET /api/stops using the real 1,314-stop dataset.
"""

import sys
import time
import os

# Allow importing algorithm modules from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from ucs import TransitRouter
from A_star import AStarRouter
from BFS_Yanis_ZA3IM import BFSRouter
from bidirectional_ranim_bomba import BidirectionalSearch

# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(title="Algiers Transit API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

# Load graph once at startup — shared across all algorithms
_router = TransitRouter(DATA_DIR)
_astar  = AStarRouter.from_router(_router)
_bfs    = BFSRouter(DATA_DIR)
_bidir  = BidirectionalSearch(_router)

# ── Request / Response models ─────────────────────────────────────────────────

class Coordinates(BaseModel):
    lat: float
    lon: float
    stopId: Optional[str] = None

class Weights(BaseModel):
    time: float = 0.4
    cost: float = 0.3
    co2:  float = 0.3

class TransportModes(BaseModel):
    walk:         bool = True
    bus:          bool = True
    tram:         bool = True
    metro:        bool = True
    telepherique: bool = True
    escalator:    bool = True

class RouteRequest(BaseModel):
    start:          Coordinates
    end:            Coordinates
    weights:        Weights = Weights()
    transportModes: TransportModes = TransportModes()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_stop(coords: Coordinates, router: TransitRouter) -> str:
    """Return stop_id: use provided stopId or find nearest by coordinates."""
    if coords.stopId:
        if coords.stopId in router.stops:
            return coords.stopId
    nearest = router.find_nearest(coords.lat, coords.lon, limit=1)
    if not nearest:
        raise HTTPException(status_code=404, detail="No stop found near coordinates")
    return nearest[0][0]


def _segment_to_dict(seg, router: TransitRouter) -> dict:
    """Convert a Segment dataclass to a JSON-serialisable dict with geometry."""
    stop_coords = []
    for sid in seg.stops:
        s = router.stops.get(sid)
        if s:
            stop_coords.append([s.lat, s.lon])

    # Bus geometry: real road waypoints from bus_geometries.json
    polyline = stop_coords  # fallback: straight lines between stops
    if seg.transport_type == 'bus' and hasattr(router, 'bus_geometries') and router.bus_geometries:
        merged = []
        for i in range(len(seg.stops) - 1):
            key = f"{seg.stops[i]}|{seg.stops[i+1]}|{seg.route_id}"
            if key in router.bus_geometries:
                pts = router.bus_geometries[key]
            else:
                rev_key = f"{seg.stops[i+1]}|{seg.stops[i]}|{seg.route_id}"
                if rev_key in router.bus_geometries:
                    pts = list(reversed(router.bus_geometries[rev_key]))
                else:
                    pts = None

            if pts:
                # skip first point if it duplicates the last one we added
                start_idx = 1 if merged and merged[-1] == pts[0] else 0
                merged.extend(pts[start_idx:])
            else:
                # fallback: straight line for this edge
                for sid in [seg.stops[i], seg.stops[i+1]]:
                    s = router.stops.get(sid)
                    if s:
                        pt = [s.lat, s.lon]
                        if not merged or merged[-1] != pt:
                            merged.append(pt)
        if merged:
            polyline = merged

    from_stop = router.stops.get(seg.from_stop)
    to_stop   = router.stops.get(seg.to_stop)

    return {
        "mode":        seg.transport_type,
        "lineId":      seg.route_id,
        "fromStopId":  seg.from_stop,
        "toStopId":    seg.to_stop,
        "fromName":    from_stop.name if from_stop else seg.from_stop,
        "toName":      to_stop.name   if to_stop   else seg.to_stop,
        "stops":       seg.stops,
        "polyline":    polyline,
        "distanceKm":  seg.distance_km,
        "durationMin": seg.time_min,
        "costDzd":     seg.fare,
    }


def _build_route_response(result, label: str, algo: str, router: TransitRouter) -> dict:
    """Convert a RouteResult / BiDirResult to the frontend Route shape."""
    segments = [_segment_to_dict(s, router) for s in result.segments]
    return {
        "id":            f"{algo}-{label}",
        "label":         label,
        "algorithmUsed": algo,
        "found":         result.found,
        "segments":      segments,
        "summary": {
            "totalTimeMin":    result.total_time,
            "totalCostDzd":    result.total_fare,
            "totalCo2G":       result.total_co2,
            "totalDistanceKm": result.total_dist,
            "numStops":        len(result.path),
            "nodesExplored":   result.nodes_explored,
        },
    }

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/stops")
def get_stops():
    """Return all stops for frontend autocomplete."""
    return [
        {
            "id":   s.stop_id,
            "name": s.name,
            "lat":  s.lat,
            "lon":  s.lon,
            "type": s.transport_type,
            "isHub": s.is_hub,
        }
        for s in _router.stops.values()
    ]


@app.post("/api/route")
def find_route(req: RouteRequest):
    start_id = _resolve_stop(req.start, _router)
    end_id   = _resolve_stop(req.end,   _router)

    if start_id == end_id:
        raise HTTPException(status_code=400, detail="Start and end stops are the same")

    w1, w2, w3 = req.weights.time, req.weights.cost, req.weights.co2
    routes = []

    # A* — fastest (time)
    try:
        t0 = time.time()
        r = _astar.find_route_astar(start_id, end_id, metric='time')
        r.runtime_ms = round((time.time() - t0) * 1000, 2)
        if r.found:
            routes.append(_build_route_response(r, 'fastest', 'A*', _router))
    except Exception as e:
        pass

    # UCS — cheapest (cost proxy: weighted)
    try:
        t0 = time.time()
        r = _router.find_route(start_id, end_id, metric='time')
        r.runtime_ms = round((time.time() - t0) * 1000, 2)
        if r.found:
            routes.append(_build_route_response(r, 'cheapest', 'Dijkstra', _router))
    except Exception as e:
        pass

    # Bidirectional — greenest (co2)
    try:
        t0 = time.time()
        r = _bidir.search(start_id, end_id, metric='co2', algorithm='astar')
        r.runtime_ms = round((time.time() - t0) * 1000, 2)
        if r.found:
            routes.append(_build_route_response(r, 'greenest', 'Bidirectional', _router))
    except Exception as e:
        pass

    if not routes:
        raise HTTPException(status_code=404, detail="No route found")

    return {"routes": routes}


@app.get("/api/nearest-stop")
def nearest_stop(lat: float, lon: float, limit: int = 5):
    stops = _router.find_nearest(lat, lon, limit=limit)
    return [{"id": s.stop_id, "name": s.name, "lat": s.lat, "lon": s.lon} for s in stops]
