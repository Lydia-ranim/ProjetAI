

from __future__ import annotations

import bisect
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
    'walk':         0.0,
}

FARES: Dict[str, float] = {
    'metro':        50.0,
    'tram':         50.0,
    'train':        50.0,
    'telepherique': 50.0,
    'bus':          50.0,
    'walk':          0.0,
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
    from_id:        str        
    to_id:          str
    time_min:       float
    distance_km:    float
    transport_type: str
    route_id:       str
    co2_g:          float


@dataclass
class Node:
   
    state:     Tuple[str, Optional[str], Optional[str]]
    parent:    Optional['Node']
    action:    Optional[Edge]
    path_cost: float

    @property
    def stop_id(self) -> str:
        return self.state[0]

    @property
    def prev_mode(self) -> Optional[str]:
        return self.state[1]

    @property
    def prev_route(self) -> Optional[str]:
        return self.state[2]


@dataclass
class BFSResult:
    found:           bool
    path_ids:        List[str]  = field(default_factory=list)
    path_edges:      List[Edge] = field(default_factory=list)
    total_time:      float      = 0.0
    total_wait:      float      = 0.0
    total_price:     float      = 0.0
    total_co2:       float      = 0.0
    num_transfers:   int        = 0
    nodes_expanded:  int        = 0
    nodes_generated: int        = 0   

    @property
    def total_journey_time(self) -> float:
        return self.total_time + self.total_wait

    def __str__(self) -> str:
        if not self.found:
            return (
                f"{'─'*60}\n"
                f"  No path found.\n"
                f"  Expanded : {self.nodes_expanded} nodes\n"
                f"  Generated: {self.nodes_generated} nodes\n"
                f"{'─'*60}"
            )
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
            lines.append(
                f"  {i+1:>3}. [{edge.transport_type.upper():<12}]  {src}  →  {dst}"
            )
            wait_note = '  ← exact schedule wait applied' if edge.transport_type == 'train' else ''
            lines.append(
                f"         {edge.time_min:.1f} min  |  {edge.distance_km:.2f} km"
                f"  |  {edge.route_id}{wait_note}"
            )
        lines.append(f"{'─'*60}")
        lines.append(f"  Expanded : {self.nodes_expanded} nodes")
        lines.append(f"  Generated: {self.nodes_generated} nodes")
        lines.append(f"{'─'*60}")
        return "\n".join(lines)


class TransitProblem:
   
    def __init__(
        self,
        router:        'BFSRouter',
        initial_state: str,
        goal_id:       str,
    ) -> None:
        self._router       = router
        self.initial_state = initial_state
        self.goal_id       = goal_id


    def goal_test(self, stop_id: str) -> bool:
        return stop_id == self.goal_id


    def actions(
        self,
        stop_id:  str,
        clock:    float,
        allowed:  Set[str],
    ) -> List[Edge]:
        r = self._router
        result: List[Edge] = []
        for edge in r.graph.get(stop_id, []):
            if edge.transport_type not in allowed:
                continue
            if not r._in_service(edge.transport_type, clock):
                continue
            # For trains: skip edge if no more trains today from this stop
            if edge.transport_type == 'train':
                arr = clock + edge.time_min / 60.0
                if r._train_wait(edge.to_id, arr) == float('inf'):
                    continue
            result.append(edge)
        return result

   
    def result(
        self,
        state:  Tuple[str, Optional[str], Optional[str]],
        action: Edge,
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """RESULT(state, action) → new state."""
        return (action.to_id, action.transport_type, action.route_id)


    def step_cost(
        self,
        state:  Tuple[str, Optional[str], Optional[str]],
        action: Edge,
    ) -> float:
      
        prev_mode    = state[1]
        is_new_board = (
            action.transport_type != 'walk' and
            action.transport_type != prev_mode
        )
        wait = self._router._avg_wait(action.transport_type) if is_new_board else 0.0
        return action.time_min + wait

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
                        # FIX-C: handle 'True'/'False' strings
                        is_hub         = str(row.get("is_hub", "")).strip().lower()
                                         in ("true", "1", "yes"),
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
                        from_id        = src,
                        to_id          = dst,
                        time_min       = float(row["time_min"]),
                        distance_km    = float(row["distance_km"]),
                        transport_type = row["transport_type"].strip().lower(),
                        route_id       = row.get("route_id", "").strip() or "UNKNOWN",
                        co2_g          = float(row.get("co2_g", 0.0) or 0.0),
                    ))
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Malformed edges.csv: {exc}") from exc

        
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
                        parts = dep.split(":")
                        if len(parts) != 3:
                            continue
                        try:
                            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
                            raw_sched[sid].append(h + m / 60.0 + s / 3600.0)
                        except ValueError:
                            continue
            except Exception:
                pass  
            for sid, times in raw_sched.items():
                self.train_schedule[sid] = sorted(times)


    def _in_service(self, mode: str, t: float) -> bool:
        o, c = WORKING_HOURS.get(mode, (0.0, 24.0))
        return o <= t < c

    def _avg_wait(self, mode: str) -> float:
        return HEADWAY_MIN.get(mode, 0.0) / 2.0

    def _train_wait(self, stop_id: str, clock_hour: float) -> float:
        
        schedule = self.train_schedule.get(stop_id)
        if not schedule:
            return HEADWAY_MIN.get('train', 30.0) / 2.0
        idx = bisect.bisect_left(schedule, clock_hour)
        if idx >= len(schedule):
            return float('inf')
        wait_min = (schedule[idx] - clock_hour) * 60.0
        return max(0.0, round(wait_min, 2))

    def _fare(
        self,
        edge:       Edge,
        prev_mode:  Optional[str],
        prev_route: Optional[str],
    ) -> float:
        mode = edge.transport_type
        if mode == 'walk':
            return 0.0
        if mode == 'bus':
            return FARES['bus'] if edge.route_id != prev_route else 0.0
        return FARES.get(mode, 0.0) if mode != prev_mode else 0.0


    def _solution(
        self,
        goal_node:       Node,
        nodes_expanded:  int,
        nodes_generated: int,
        depart:          float,
    ) -> BFSResult:
       
        # Walk parent chain
        path_edges: List[Edge] = []
        node = goal_node
        while node.action is not None:
            path_edges.append(node.action)
            node = node.parent  
        path_edges.reverse()

        if path_edges:
            path_ids = [path_edges[0].from_id] + [e.to_id for e in path_edges]
        else:
            path_ids = [goal_node.stop_id]

        time = wait = price = co2 = 0.0
        transfers  = 0
        prev_mode  = prev_route = None
        clock      = depart

        for i, edge in enumerate(path_edges):
            mode  = edge.transport_type
            is_tr = (
                prev_mode is not None
                and prev_mode != 'walk'
                and mode     != 'walk'
                and mode     != prev_mode
            )

            if mode == 'train':
                w = self._train_wait(path_ids[i], clock)
                if w == float('inf'):
                    w = HEADWAY_MIN.get('train', 30.0) / 2.0  # safe fallback
            else:
                w = self._avg_wait(mode)

            price     += self._fare(edge, prev_mode, prev_route)
            time      += edge.time_min
            wait      += w
            co2       += edge.co2_g
            transfers += int(is_tr)
            prev_mode  = mode
            prev_route = edge.route_id
            clock     += (w + edge.time_min) / 60.0

        return BFSResult(
            found           = True,
            path_ids        = path_ids,
            path_edges      = path_edges,
            total_time      = round(time,  2),
            total_wait      = round(wait,  2),
            total_price     = round(price, 2),
            total_co2       = round(co2,   2),
            num_transfers   = transfers,
            nodes_expanded  = nodes_expanded,
            nodes_generated = nodes_generated,
        )


    def search(
        self,
        start:   str,
        goal:    str,
        depart:  float           = 8.0,
        allowed: Optional[Set[str]] = None,
    ) -> BFSResult:
       
        if not isinstance(start, str) or not isinstance(goal, str):
            raise TypeError(
                f"start and goal must be str, "
                f"got {type(start).__name__} and {type(goal).__name__}"
            )
        start, goal = start.strip(), goal.strip()
        if start not in self.stops:
            raise ValueError(f"Unknown stop id: {start!r}")
        if goal not in self.stops:
            raise ValueError(f"Unknown stop id: {goal!r}")
        if start == goal:
            raise ValueError("start and goal must be different stops.")
        if not (0.0 <= depart < 24.0):
            raise ValueError(f"depart must be in [0.0, 24.0), got {depart}")

        if allowed is None:
            allowed = {'metro', 'tram', 'bus', 'train', 'telepherique', 'walk'}

        
        problem = TransitProblem(
            router        = self,
            initial_state = start,
            goal_id       = goal,
        )

       
        clock = depart

       
        root = Node(
            state     = (start, None, None),
            parent    = None,
            action    = None,
            path_cost = 0.0,
        )


        if problem.goal_test(root.stop_id):
            return self._solution(root, 0, 0, depart)

        frontier:        deque      = deque([root])
        frontier_states: Set[Tuple] = {root.state}   # O(1) membership mirror
        explored:        Set[Tuple] = set()
        nodes_expanded:  int        = 0
        nodes_generated: int        = 0

        while frontier:

          
            node = frontier.popleft()
            frontier_states.discard(node.state)
            nodes_expanded += 1

           
            explored.add(node.state)

           
            for action in problem.actions(node.stop_id, clock, allowed):

               
                child_state = problem.result(node.state, action)
                child = Node(
                    state     = child_state,
                    parent    = node,
                    action    = action,
                    path_cost = node.path_cost + problem.step_cost(node.state, action),
                )

               
                nodes_generated += 1

               
                if child.state not in explored and child.state not in frontier_states:

                   
                    if problem.goal_test(child.stop_id):
                        return self._solution(
                            child, nodes_expanded, nodes_generated, depart
                        )

                   
                    frontier.append(child)
                    frontier_states.add(child.state)

        return BFSResult(found=False, nodes_expanded=nodes_expanded,
                         nodes_generated=nodes_generated)

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

    if result.found:
        print("\nStop names along route:")
        for sid in result.path_ids:
            print(f"  {sid:30s}  {router.stop_name(sid)}")