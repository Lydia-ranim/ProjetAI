from __future__ import annotations

import csv
import os
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

WORKING_HOURS: Dict[str, Tuple[float, float]] = {
    'metro':        (5.0,  23.0),
    'tram':         (5.0,  23.0),
    'train':        (5.5,  22.0),
    'telepherique': (8.0,  19.0),
    'bus':          (5.5,  22.5),
    'walk':         (0.0,  24.0),
}

HEADWAY_MIN: Dict[str, float] = {
    'metro':        5.0,
    'tram':         8.0,
    'train':        30.0,
    'telepherique': 10.0,
    'bus':          15.0,
}

FARES: Dict[str, float] = {
    'metro':        50.0,
    'tram':         50.0,
    'train':        50.0,
    'telepherique': 50.0,
    'bus':          50.0,
}


@dataclass(frozen=True)
class Stop:
    stop_id:        str
    name:           str
    lat:            float
    lon:            float
    transport_type: str
    is_hub:         bool


@dataclass(frozen=True)
class Edge:
    to_id:          str
    time_min:       float
    distance_km:    float
    transport_type: str
    route_id:       str
    co2_g:          float


@dataclass
class BFSResult:
    found:          bool
    path_ids:       List[str]  = field(default_factory=list)
    path_edges:     List[Edge] = field(default_factory=list)
    total_time:     float      = 0.0
    total_wait:     float      = 0.0
    total_price:    float      = 0.0
    total_co2:      float      = 0.0
    num_transfers:  int        = 0
    nodes_expanded: int        = 0

    @property
    def total_journey_time(self) -> float:
        return self.total_time + self.total_wait

    def __str__(self) -> str:
        if not self.found:
            return f"No path found (expanded {self.nodes_expanded} nodes)."
        lines = [
            f"{'─'*60}",
            f"  {len(self.path_edges)} hop(s)  |  {self.num_transfers} transfer(s)",
            f"  Ride : {self.total_time:.1f} min",
            f"  Wait : {self.total_wait:.1f} min",
            f"  Total: {self.total_journey_time:.1f} min",
            f"  Price: {self.total_price:.0f} DA",
            f"  CO₂  : {self.total_co2:.1f} g",
            f"{'─'*60}",
        ]
        for i, (src, edge) in enumerate(zip(self.path_ids, self.path_edges)):
            dst = self.path_ids[i + 1]
            lines.append(f"  {i+1:>3}. [{edge.transport_type.upper():<12}]  {src}  →  {dst}")
            lines.append(f"         {edge.time_min:.1f} min  |  {edge.distance_km:.2f} km  |  {edge.route_id}")
        lines.append(f"{'─'*60}")
        return "\n".join(lines)


class BFSRouter:

    def __init__(self, data_dir: str) -> None:
        stops_path = os.path.join(data_dir, "stops.csv")
        edges_path = os.path.join(data_dir, "edges.csv")

        for path in (stops_path, edges_path):
            if not os.path.isfile(path):
                raise FileNotFoundError(f"Required data file not found: {path!r}")

        self.stops: Dict[str, Stop] = {}
        try:
            with open(stops_path, encoding="utf-8-sig", newline="") as fh:
                for row in csv.DictReader(fh):
                    sid = row["stop_id"].strip()
                    if not sid:
                        continue
                    self.stops[sid] = Stop(
                        stop_id        = sid,
                        name           = row["stop_name"].strip(),
                        lat            = float(row["latitude"]),
                        lon            = float(row["longitude"]),
                        transport_type = row["transport_type"].strip().lower(),
                        is_hub         = row.get("is_hub", "").strip().lower() in ("true", "1", "yes"),
                    )
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Malformed stops.csv: {exc}") from exc

        if not self.stops:
            raise ValueError("stops.csv is empty or contains no valid rows.")

        self.graph: Dict[str, List[Edge]] = defaultdict(list)
        try:
            with open(edges_path, encoding="utf-8-sig", newline="") as fh:
                for row in csv.DictReader(fh):
                    src = row["from_stop_id"].strip()
                    dst = row["to_stop_id"].strip()
                    if not src or not dst:
                        continue
                    self.graph[src].append(Edge(
                        to_id          = dst,
                        time_min       = float(row["time_min"]),
                        distance_km    = float(row["distance_km"]),
                        transport_type = row["transport_type"].strip().lower(),
                        route_id       = row.get("route_id", "").strip() or "UNKNOWN",
                        co2_g          = float(row.get("co2_g", 0.0) or 0.0),
                    ))
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Malformed edges.csv: {exc}") from exc

    def _in_service(self, mode: str, t: float) -> bool:
        if mode == "walk":
            return True
        o, c = WORKING_HOURS.get(mode, (0.0, 24.0))
        return o <= t < c

    def _avg_wait(self, mode: str) -> float:
        return HEADWAY_MIN.get(mode, 0.0) / 2.0

    def _fare(self, edge: Edge, prev_mode: Optional[str], prev_route: Optional[str]) -> float:
        mode = edge.transport_type
        if mode == "walk":
            return 0.0
        if mode == "bus":
            return FARES["bus"] if edge.route_id != prev_route else 0.0
        return FARES.get(mode, 0.0) if mode != prev_mode else 0.0

    def search(
        self,
        start:   str,
        goal:    str,
        depart:  float = 8.0,
        allowed: Optional[Set[str]] = None,
    ) -> BFSResult:
        if not isinstance(start, str) or not isinstance(goal, str):
            raise TypeError(f"start and goal must be str, got {type(start).__name__} and {type(goal).__name__}")
        start, goal = start.strip(), goal.strip()
        if start not in self.stops:
            raise ValueError(f"Unknown stop id: {start!r}")
        if goal not in self.stops:
            raise ValueError(f"Unknown stop id: {goal!r}")
        if start == goal:
            raise ValueError("start and goal must be different stops.")
        if not (0.0 <= depart < 24.0):
            raise ValueError(f"depart must be in [0.0, 24.0), got {depart}")

        queue:   deque[Tuple[str, float, Optional[str], Optional[str]]] = deque(
            [(start, depart, None, None)]
        )
        visited: Set[str]                    = {start}
        parent:  Dict[str, Tuple[str, Edge]] = {}
        expanded = 0

        while queue:
            nid, clock, prev_mode, prev_route = queue.popleft()
            expanded += 1

            for edge in self.graph.get(nid, []):
                nb   = edge.to_id
                mode = edge.transport_type

                if nb in visited:
                    continue
                if allowed and mode not in allowed:
                    continue
                if not self._in_service(mode, clock):
                    continue

                parent[nb] = (nid, edge)

                if nb == goal:
                    return self._build(start, goal, parent, expanded)

                visited.add(nb)
                w = self._avg_wait(mode)
                queue.append((nb, clock + (edge.time_min + w) / 60.0, mode, edge.route_id))

        return BFSResult(found=False, nodes_expanded=expanded)

    def _build(
        self,
        start:    str,
        goal:     str,
        parent:   Dict[str, Tuple[str, Edge]],
        expanded: int,
    ) -> BFSResult:
        path_ids:   List[str]  = [goal]
        path_edges: List[Edge] = []
        node = goal
        while node != start:
            p, edge = parent[node]
            path_ids.append(p)
            path_edges.append(edge)
            node = p
        path_ids.reverse()
        path_edges.reverse()

        time = wait = price = co2 = 0.0
        transfers  = 0
        prev_mode  = prev_route = None

        for edge in path_edges:
            mode  = edge.transport_type
            w     = self._avg_wait(mode)
            is_tr = (
                prev_mode is not None
                and prev_mode != "walk"
                and mode != "walk"
                and mode != prev_mode
            )
            price += self._fare(edge, prev_mode, prev_route)
            time  += edge.time_min
            wait  += w
            co2   += edge.co2_g
            transfers   += is_tr
            prev_mode    = mode
            prev_route   = edge.route_id

        return BFSResult(
            found          = True,
            path_ids       = path_ids,
            path_edges     = path_edges,
            total_time     = round(time,  2),
            total_wait     = round(wait,  2),
            total_price    = round(price, 2),
            total_co2      = round(co2,   2),
            num_transfers  = transfers,
            nodes_expanded = expanded,
        )

    def stop_name(self, stop_id: str) -> str:
        s = self.stops.get(stop_id)
        return s.name if s else stop_id


if __name__ == "__main__":
    import sys

    data_dir = sys.argv[1] if len(sys.argv) > 1 else "Data"
    start    = sys.argv[2] if len(sys.argv) > 2 else "M1_MARTYRS"
    goal     = sys.argv[3] if len(sys.argv) > 3 else "M1_HAMMA"
    depart   = float(sys.argv[4]) if len(sys.argv) > 4 else 8.0

    router = BFSRouter(data_dir)
    result = router.search(start, goal, depart)
    print(result)