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
            wait_note = ''
            if edge.transport_type == 'train':
                wait_note = '  ← exact schedule wait applied'
            lines.append(f"         {edge.time_min:.1f} min  |  {edge.distance_km:.2f} km  |  {edge.route_id}{wait_note}")
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

        # ── Train schedule: stop_id → sorted list of departure hours ──
        self.train_schedule: Dict[str, List[float]] = {}
        stop_times_path = os.path.join(data_dir, "stop_times.csv")
        if os.path.isfile(stop_times_path):
            raw_sched: Dict[str, List[float]] = defaultdict(list)
            try:
                with open(stop_times_path, encoding="utf-8-sig", newline="") as fh:
                    for row in csv.DictReader(fh):
                        sid = row.get("stop_id", "").strip()
                        dep = row.get("departure_time", "").strip()
                        if not sid or not dep:
                            continue
                        # Parse HH:MM:SS — GTFS allows hours >= 24
                        parts = dep.split(":")
                        if len(parts) != 3:
                            continue
                        try:
                            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
                            dep_hour = h + m / 60.0 + s / 3600.0
                            # Normalise past-midnight times into [0, 48)
                            # We keep them as-is so that a 25:10 train
                            # is still later than a 23:50 one on the same night.
                            raw_sched[sid].append(dep_hour)
                        except ValueError:
                            continue
            except Exception:
                pass  # schedule is optional — fall back to avg wait
            for sid, times in raw_sched.items():
                self.train_schedule[sid] = sorted(times)
        # If stop_times.csv is absent, self.train_schedule stays {}
        # and _train_wait falls back to HEADWAY_MIN average.

    def _in_service(self, mode: str, t: float) -> bool:
        if mode == "walk":
            return True
        o, c = WORKING_HOURS.get(mode, (0.0, 24.0))
        return o <= t < c

    def _avg_wait(self, mode: str) -> float:
        """
        Average waiting time for non-train modes.
        Train wait is computed exactly via _train_wait — do NOT call
        this method for mode == 'train'.
        """
        if mode == 'train':
            # Should not be called for trains; return average as fallback
            return HEADWAY_MIN.get('train', 30.0) / 2.0
        return HEADWAY_MIN.get(mode, 0.0) / 2.0

    def _train_wait(self, stop_id: str, clock_hour: float) -> float:
        """
        Compute exact waiting time (minutes) for a train at stop_id,
        given that the traveller arrives at clock_hour (fractional hours,
        e.g. 8.5 = 08:30).

        Logic:
          1. Look up sorted departure list for this stop in self.train_schedule.
          2. Find the first departure >= clock_hour using binary search.
          3. If found: wait = (next_departure - clock_hour) * 60  minutes.
          4. If none found today (past last train): service has ended,
             return inf so the caller can mark the edge as out of service.
          5. If stop has no schedule entry: fall back to HEADWAY_MIN['train']/2.

        Clock values >= 24.0 are treated as next-day GTFS times and
        compared directly against GTFS departure_time values that may
        also exceed 24.
        """
        import bisect
        schedule = self.train_schedule.get(stop_id)
        if not schedule:
            # No schedule data for this stop — use average headway
            return HEADWAY_MIN.get('train', 30.0) / 2.0

        # Binary search: index of first departure >= clock_hour
        idx = bisect.bisect_left(schedule, clock_hour)
        if idx >= len(schedule):
            # Past the last train of the day
            return float('inf')

        next_dep = schedule[idx]
        wait_min = (next_dep - clock_hour) * 60.0
        # Clamp negatives caused by float precision
        return max(0.0, round(wait_min, 2))

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
        start_state = (start, None, None)
        visited: Set[Tuple[str, Optional[str], Optional[str]]] = {start_state}
        parent:  Dict[Tuple[str, Optional[str], Optional[str]], Tuple[Tuple[str, Optional[str], Optional[str]], Edge]] = {}
        expanded = 0

        while queue:
            nid, clock, prev_mode, prev_route = queue.popleft()
            curr_state = (nid, prev_mode, prev_route)
            expanded += 1

            for edge in self.graph.get(nid, []):
                nb   = edge.to_id
                mode = edge.transport_type
                next_state = (nb, mode, edge.route_id)

                if next_state in visited:
                    continue
                if allowed and mode not in allowed:
                    continue
                if not self._in_service(mode, clock):
                    continue

                # Compute wait time at the NEXT node (nb) before boarding
                if mode == 'train':
                    # Arrival time at nb after riding this edge
                    arr_at_nb = clock + edge.time_min / 60.0
                    w = self._train_wait(nb, arr_at_nb)
                    if w == float('inf'):
                        # No more trains from this stop today — skip edge
                        continue
                else:
                    w = self._avg_wait(mode)

                parent[next_state] = (curr_state, edge)

                if nb == goal:
                    return self._build(start, next_state, parent, expanded, depart)

                visited.add(next_state)
                queue.append((nb, clock + (edge.time_min + w) / 60.0, mode, edge.route_id))

        return BFSResult(found=False, nodes_expanded=expanded)

    def _build(
        self,
        start:    str,
        goal_state: Tuple[str, Optional[str], Optional[str]],
        parent:   Dict[Tuple[str, Optional[str], Optional[str]], Tuple[Tuple[str, Optional[str], Optional[str]], Edge]],
        expanded: int,
        depart:   float = 0.0,
    ) -> BFSResult:
        """
        Reconstruct path and compute exact costs.
        For train edges, uses _train_wait(stop_id, arrival_hour) to get
        the real waiting time at that station.
        For all other modes, uses _avg_wait(mode) as before.
        """
        path_ids:   List[str]  = [goal_state[0]]
        path_edges: List[Edge] = []
        state = goal_state
        while state[0] != start:
            p_state, edge = parent[state]
            path_ids.append(p_state[0])
            path_edges.append(edge)
            state = p_state
        path_ids.reverse()
        path_edges.reverse()

        time = wait = price = co2 = 0.0
        transfers  = 0
        prev_mode  = prev_route = None
        clock = depart  # track real clock time through the journey

        for i, edge in enumerate(path_edges):
            mode  = edge.transport_type
            is_tr = (
                prev_mode is not None
                and prev_mode != "walk"
                and mode != "walk"
                and mode != prev_mode
            )

            # Waiting time at the CURRENT stop before boarding this edge
            if mode == 'train':
                w = self._train_wait(path_ids[i], clock)
                if w == float('inf'):
                    w = HEADWAY_MIN.get('train', 30.0) / 2.0  # safe fallback
            else:
                w = self._avg_wait(mode)

            price += self._fare(edge, prev_mode, prev_route)
            time  += edge.time_min
            wait  += w
            co2   += edge.co2_g
            transfers  += is_tr
            prev_mode   = mode
            prev_route  = edge.route_id

            # Advance clock: wait at stop + ride time
            clock += (w + edge.time_min) / 60.0

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
    n_sched = sum(len(v) for v in router.train_schedule.values())
    if n_sched:
        print(f"  Train schedule loaded: {len(router.train_schedule)} stops, "
              f"{n_sched} departure entries")
    else:
        print("  No stop_times.csv found — using average headway for trains")
    result = router.search(start, goal, depart)
    print(result)