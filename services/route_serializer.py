"""Route serialization for Google Maps-friendly frontend rendering."""

from __future__ import annotations

from typing import Any

from services.polyline import prepare_polyline
from services.stops_service import MODE_META
from settings import settings
from ucs import RouteResult, Segment


def _fmt_minutes(minutes: float) -> str:
    minutes = int(round(minutes))
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h} h {m} min"
    if h:
        return f"{h} h"
    return f"{m} min"


def _fmt_fare(dzd: int | float) -> str:
    return f"{int(round(dzd))} DA"


def _stop_marker(router, stop_id: str, role: str, mode: str | None = None) -> dict[str, Any]:
    stop = router.stops.get(stop_id)
    if not stop:
        return {}
    key = mode or stop.transport_type
    meta = MODE_META.get(key, MODE_META["walk"])
    return {
        "id": stop_id,
        "role": role,
        "title": stop.name,
        "position": {"lat": stop.lat, "lng": stop.lon},
        "mode": key,
        "color": meta["color"],
        "icon": meta["icon"],
    }


def build_segment_polyline(router, seg: Segment) -> list[list[float]]:
    poly: list[list[float]] = []
    if not seg.stops:
        return poly

    for i in range(len(seg.stops) - 1):
        s1 = seg.stops[i]
        s2 = seg.stops[i + 1]
        key1 = f"{s1}|{s2}|{seg.route_id}"
        key2 = f"{s2}|{s1}|{seg.route_id}"
        if key1 in getattr(router, "bus_geometries", {}):
            poly.extend(router.bus_geometries[key1])
        elif key2 in getattr(router, "bus_geometries", {}):
            poly.extend(reversed(router.bus_geometries[key2]))
        else:
            s1_node = router.stops.get(s1)
            if s1_node:
                poly.append([s1_node.lat, s1_node.lon])

    last_stop = router.stops.get(seg.stops[-1])
    if last_stop:
        poly.append([last_stop.lat, last_stop.lon])
    return poly


def segment_to_api(router, seg: Segment, index: int) -> dict[str, Any]:
    mode = seg.transport_type
    meta = MODE_META.get(mode, MODE_META["walk"])
    raw_poly = build_segment_polyline(router, seg)
    processed = prepare_polyline(
        raw_poly,
        tolerance=settings.polyline_simplify_tolerance,
        max_points=settings.max_polyline_points,
    )
    is_transfer = mode == "walk" or "TRANSFER" in str(seg.route_id).upper()
    return {
        "index": index,
        "mode": mode,
        "lineId": seg.route_id,
        "fromStopId": seg.from_stop,
        "toStopId": seg.to_stop,
        "fromName": router.get_stop_name(seg.from_stop),
        "toName": router.get_stop_name(seg.to_stop),
        "stops": list(seg.stops),
        "polyline": processed["coordinates"],
        "encodedPolyline": processed["encoded"],
        "polylineMeta": {
            "pointCount": processed["pointCount"],
            "sourcePointCount": processed["sourcePointCount"],
            "simplified": processed["simplified"],
        },
        "distanceKm": float(seg.distance_km),
        "durationMin": float(seg.time_min),
        "durationText": _fmt_minutes(seg.time_min),
        "costDzd": int(seg.fare),
        "costText": _fmt_fare(seg.fare),
        "display": {
            "color": meta["color"],
            "icon": meta["icon"],
            "label": meta["label"],
            "isTransfer": is_transfer,
        },
        "markers": {
            "start": _stop_marker(router, seg.from_stop, "segment-start", mode),
            "end": _stop_marker(router, seg.to_stop, "segment-end", mode),
        },
    }


def route_result_to_api(
    router,
    label: str,
    result: RouteResult,
    algo: str = "UCS",
) -> dict[str, Any]:
    rid = {"fastest": "r-fast", "cheapest": "r-cheap", "greenest": "r-green"}.get(
        label, "r-1"
    )
    segments = [segment_to_api(router, seg, i) for i, seg in enumerate(result.segments)]
    transfer_points = [
        seg["markers"]["start"]
        for i, seg in enumerate(segments)
        if i > 0 and seg["markers"].get("start")
    ]
    all_points = [p for seg in segments for p in seg.get("polyline", [])]
    bounds = None
    if all_points:
        lats = [p[0] for p in all_points]
        lngs = [p[1] for p in all_points]
        bounds = {
            "south": min(lats),
            "west": min(lngs),
            "north": max(lats),
            "east": max(lngs),
        }

    return {
        "id": rid,
        "label": label,
        "algorithmUsed": algo,
        "found": result.found,
        "segments": segments,
        "summary": {
            "totalTimeMin": float(result.total_time),
            "totalTimeText": _fmt_minutes(result.total_time),
            "totalCostDzd": int(result.total_fare),
            "totalCostText": _fmt_fare(result.total_fare),
            "totalCo2G": float(result.total_co2),
            "totalDistanceKm": float(result.total_dist),
            "numStops": len(result.path),
            "nodesExplored": int(result.nodes_explored),
        },
        "map": {
            "bounds": bounds,
            "markers": {
                "origin": _stop_marker(router, result.path[0], "origin") if result.path else {},
                "destination": _stop_marker(router, result.path[-1], "destination") if result.path else {},
                "transfers": transfer_points,
            },
            "legend": [
                {"mode": mode, **meta}
                for mode, meta in MODE_META.items()
                if any(seg["mode"] == mode for seg in segments)
            ],
        },
    }

