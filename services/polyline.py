"""Polyline processing utilities for map-friendly route payloads."""

from __future__ import annotations

from math import hypot
from typing import Iterable, Sequence

Point = list[float]


def _perpendicular_distance(point: Point, start: Point, end: Point) -> float:
    if start == end:
        return hypot(point[0] - start[0], point[1] - start[1])
    x, y = point
    x1, y1 = start
    x2, y2 = end
    num = abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1)
    den = hypot(y2 - y1, x2 - x1)
    return num / den


def simplify_polyline(points: Sequence[Point], tolerance: float) -> list[Point]:
    """Simplify lat/lon points using Douglas-Peucker."""
    if len(points) <= 2 or tolerance <= 0:
        return [list(p) for p in points]

    max_dist = 0.0
    index = 0
    start = points[0]
    end = points[-1]
    for i in range(1, len(points) - 1):
        dist = _perpendicular_distance(points[i], start, end)
        if dist > max_dist:
            index = i
            max_dist = dist

    if max_dist > tolerance:
        left = simplify_polyline(points[: index + 1], tolerance)
        right = simplify_polyline(points[index:], tolerance)
        return left[:-1] + right
    return [list(start), list(end)]


def cap_polyline_points(points: Sequence[Point], max_points: int) -> list[Point]:
    if max_points <= 0 or len(points) <= max_points:
        return [list(p) for p in points]
    if max_points == 1:
        return [list(points[0])]
    step = (len(points) - 1) / (max_points - 1)
    out = [points[round(i * step)] for i in range(max_points)]
    out[-1] = points[-1]
    return [list(p) for p in out]


def encode_polyline(points: Iterable[Point], precision: int = 5) -> str:
    """Encode points with Google's encoded polyline algorithm."""
    factor = 10**precision
    prev_lat = 0
    prev_lng = 0
    result = []

    for lat, lng in points:
        ilat = int(round(lat * factor))
        ilng = int(round(lng * factor))
        for value in (ilat - prev_lat, ilng - prev_lng):
            value = ~(value << 1) if value < 0 else value << 1
            while value >= 0x20:
                result.append(chr((0x20 | (value & 0x1F)) + 63))
                value >>= 5
            result.append(chr(value + 63))
        prev_lat = ilat
        prev_lng = ilng

    return "".join(result)


def prepare_polyline(
    points: Sequence[Point],
    tolerance: float,
    max_points: int,
) -> dict[str, object]:
    simplified = simplify_polyline(points, tolerance)
    capped = cap_polyline_points(simplified, max_points)
    return {
        "coordinates": capped,
        "encoded": encode_polyline(capped),
        "pointCount": len(capped),
        "sourcePointCount": len(points),
        "simplified": len(capped) < len(points),
    }

