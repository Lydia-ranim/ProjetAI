"""Stop lookup and map serialization helpers."""

from __future__ import annotations

from functools import lru_cache
from math import asin, cos, radians, sin, sqrt
from typing import Any

MODE_META = {
    "metro": {"color": "#2196F3", "icon": "subway", "label": "Metro"},
    "bus": {"color": "#FF9800", "icon": "directions_bus", "label": "Bus"},
    "tram": {"color": "#4CAF50", "icon": "tram", "label": "Tram"},
    "train": {"color": "#E91E63", "icon": "train", "label": "Train"},
    "telepherique": {"color": "#9C27B0", "icon": "cable", "label": "Telepherique"},
    "walk": {"color": "#9E9E9E", "icon": "directions_walk", "label": "Walk"},
}


class StopsService:
    def __init__(self, router, cache_size: int = 512):
        self.router = router
        self.cache_size = cache_size
        self._nearest_cached = lru_cache(maxsize=cache_size)(self._nearest_uncached)

    def _nearest_uncached(
        self,
        lat_key: float,
        lon_key: float,
        limit: int,
        transport_type: str | None,
    ) -> tuple[tuple[str, float], ...]:
        return tuple(
            self.router.find_nearest(
                lat_key,
                lon_key,
                transport_type=transport_type,
                limit=limit,
            )
        )

    def nearest(
        self,
        lat: float,
        lon: float,
        limit: int = 5,
        transport_type: str | None = None,
    ) -> list[tuple[str, float]]:
        limit = max(1, min(int(limit), 50))
        lat_key = round(float(lat), 5)
        lon_key = round(float(lon), 5)
        mode = transport_type.lower() if transport_type else None
        return list(self._nearest_cached(lat_key, lon_key, limit, mode))

    def stop_to_api(self, sid: str, distance_km: float | None = None) -> dict[str, Any]:
        stop = self.router.stops[sid]
        mode = stop.transport_type
        meta = MODE_META.get(mode, MODE_META["walk"])
        payload = {
            "id": sid,
            "name": stop.name,
            "lat": stop.lat,
            "lon": stop.lon,
            "type": mode,
            "isHub": stop.is_hub,
            "map": {
                "position": {"lat": stop.lat, "lng": stop.lon},
                "color": meta["color"],
                "icon": meta["icon"],
                "label": meta["label"],
                "clusterKey": mode,
            },
        }
        if distance_km is not None:
            payload["distanceKm"] = float(distance_km)
        return payload

    def all_stops(self) -> list[dict[str, Any]]:
        return [self.stop_to_api(sid) for sid in self.router.stops]

    def categories(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for sid, stop in self.router.stops.items():
            out.setdefault(stop.transport_type, []).append(sid)
        return out

    def network_lines(self, limit: int = 2500) -> list[dict[str, Any]]:
        """Return real graph edges for map network rendering.

        This intentionally avoids synthetic "connect all stops of a mode"
        lines. Synthetic lines can cut across Algiers Bay, which is visually
        wrong and misleading.
        """
        out: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str, str]] = set()
        limit = max(1, min(int(limit), 8000))

        for from_id, edges in self.router.graph.items():
            from_stop = self.router.stops.get(from_id)
            if not from_stop:
                continue
            for edge in edges:
                mode = edge.transport_type
                if mode == "walk":
                    continue

                to_stop = self.router.stops.get(edge.to_id)
                if not to_stop:
                    continue

                dedupe = tuple(sorted((from_id, edge.to_id))) + (edge.route_id, mode)
                if dedupe in seen:
                    continue
                seen.add(dedupe)

                path = self._network_edge_path(from_id, edge)
                if len(path) < 2:
                    continue
                if self._looks_like_marine_shortcut(path):
                    continue

                meta = MODE_META.get(mode, MODE_META["walk"])
                out.append(
                    {
                        "mode": mode,
                        "routeId": edge.route_id,
                        "fromStopId": from_id,
                        "toStopId": edge.to_id,
                        "color": meta["color"],
                        "path": self._thin_path(path, max_points=80),
                    }
                )
                if len(out) >= limit:
                    return out
        return out

    def _network_edge_path(self, from_id: str, edge) -> list[list[float]]:
        if edge.transport_type == "bus":
            key1 = f"{from_id}|{edge.to_id}|{edge.route_id}"
            key2 = f"{edge.to_id}|{from_id}|{edge.route_id}"
            if key1 in getattr(self.router, "bus_geometries", {}):
                return [list(p) for p in self.router.bus_geometries[key1]]
            if key2 in getattr(self.router, "bus_geometries", {}):
                return [list(p) for p in reversed(self.router.bus_geometries[key2])]
            return []

        from_stop = self.router.stops.get(from_id)
        to_stop = self.router.stops.get(edge.to_id)
        if not from_stop or not to_stop:
            return []
        return [[from_stop.lat, from_stop.lon], [to_stop.lat, to_stop.lon]]

    @staticmethod
    def _thin_path(path: list[list[float]], max_points: int) -> list[list[float]]:
        if len(path) <= max_points:
            return path
        step = (len(path) - 1) / (max_points - 1)
        thinned = [path[round(i * step)] for i in range(max_points)]
        thinned[-1] = path[-1]
        return thinned

    @staticmethod
    def _haversine_km(a: list[float], b: list[float]) -> float:
        lat1, lon1 = map(radians, a)
        lat2, lon2 = map(radians, b)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        return 6371.0 * 2 * asin(sqrt(h))

    def _looks_like_marine_shortcut(self, path: list[list[float]]) -> bool:
        """Guard against straight overlay lines across Algiers Bay.

        Multi-point bus geometry comes from road traces and is allowed. This
        guard mainly catches fallback two-point rail/cable lines that would
        visually cross open water.
        """
        if len(path) != 2:
            return False

        a, b = path
        lon_min = min(a[1], b[1])
        lon_max = max(a[1], b[1])
        lat_max = max(a[0], b[0])
        if lon_max < 2.95 or lon_min > 3.38 or lat_max < 36.70:
            return False

        distance_km = self._haversine_km(a, b)
        if distance_km < 1.5:
            return False

        mid_lat = (a[0] + b[0]) / 2
        mid_lon = (a[1] + b[1]) / 2
        rough_coast_lat = 36.80 - 0.18 * (mid_lon - 2.95)
        return mid_lat > rough_coast_lat
