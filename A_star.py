
import heapq
import sys
import time as time_module
from ucs import TransitRouter, RouteResult, FARES
# WORKING HOURS


# Operating hours per transport mode: (start_hour, end_hour) in 24-h decimal.
# e.g. 5.5 = 05:30,  22.5 = 22:30
WORKING_HOURS: dict[str, tuple[float, float]] = {
    'metro':        (5.0,  23.0),
    'tram':         (5.0,  23.0),
    'train':        (5.5,  22.0),
    'bus':          (5.5,  22.5),
    'telepherique': (8.0,  19.0),
    'walk':         (0.0,  24.0),   # pedestrian — always available
}


def _is_operating(transport_type: str, clock_hour: float) -> bool:
    """
    Return True if the given transport mode is running at clock_hour.

    clock_hour is the time of day in decimal hours (e.g. 14.5 = 14:30).
    Unknown transport types default to always available.
    """
    start, end = WORKING_HOURS.get(transport_type, (0.0, 24.0))
    return start <= clock_hour < end



# A* ROUTER


class AStarRouter(TransitRouter):
    """
    Multi-modal transit router using A* Search.
    Extends TransitRouter (UCS) with heuristic-guided search.

    Following Russell & Norvig Chapter 3:
        A* expands nodes in order of f(n) = g(n) + h(n).
        It is identical to UCS but uses g + h instead of g alone.
        With a consistent heuristic, the graph-search version is optimal:
          - A* expands all nodes with f(n) < C* (optimal cost).
          - A* might expand some nodes where f(n) = C* before selecting the goal.
          - A* is optimally efficient: no other optimal algorithm expands fewer nodes.

    Heuristic h(n) = d(n, goal) / vmax is admissible because:
      - d(n, goal) is the straight-line distance (always ≤ actual path distance)
      - vmax is the fastest possible speed  (time ≥ distance / vmax)
      Therefore h(n) never overestimates the true cost → A* is optimal.

    Supports optimisation by:
      - 'time':     travel time in minutes
      - 'distance': path distance in km
      - 'co2':      carbon emissions in grams
      - 'weighted': w1*Time + w2*Price + w3*CO2
    """

    def __init__(self, data_dir: str):
        """Load graph data and compute vmax for the heuristic."""
        super().__init__(data_dir)
        self._vmax     = self._compute_vmax()   # km/min
        self._vmax_kmh = self._vmax * 60        # km/h

    @classmethod
    def from_router(cls, router) -> 'AStarRouter':
        """
        Create an AStarRouter that shares the same loaded graph as
        an existing TransitRouter — avoids reloading data from disk.

        Used by BidirectionalSearch.compare_all() for efficient
        side-by-side algorithm comparison.
        """
        instance = cls.__new__(cls)
        instance.stops     = router.stops
        instance.graph     = router.graph
        instance._vmax     = instance._compute_vmax_from_graph(router.graph)
        instance._vmax_kmh = instance._vmax * 60
        return instance

    # ─── vmax helpers 

    def _compute_vmax(self) -> float:
        """
        Compute maximum speed (km/min) across all edges in the network.
        Used as vmax in h(n) = d(n, goal) / vmax.
        """
        return self._compute_vmax_from_graph(self.graph)

    def _compute_vmax_from_graph(self, graph) -> float:
        """Compute vmax from an externally provided graph dict."""
        vmax = 0.0
        for edges in graph.values():
            for e in edges:
                if e.time_min > 0 and e.distance_km > 0:
                    speed = e.distance_km / e.time_min
                    if speed > vmax:
                        vmax = speed
        return vmax if vmax > 0 else 1.0

    # ─── Heuristic h(n) 

    def _heuristic(self, node_id: str, goal_id: str,
                   metric: str, w1: float = 1.0) -> float:
        """
        Admissible heuristic h(n) = d(n, goal) / vmax.

        From the slides (Russell & Norvig Chapter 3):
            f(n) = g(n) + h(n)
            f(n) = estimated cost of the cheapest solution through n.

        Admissibility per metric:
            time:     h = dist_km / vmax_km_per_min  (lower bound on travel time)
            distance: h = dist_km                    (straight line ≤ any path)
            co2:      h = 0                          (walking has 0 CO2)
            weighted: h = w1 * dist_km / vmax        (price/co2 terms ≥ 0)

        A consistent heuristic satisfies h(n) ≤ c(n,a,n') + h(n'),
        which is guaranteed here by the triangle inequality on distances.
        """
        n = self.stops.get(node_id)
        g = self.stops.get(goal_id)
        if not n or not g:
            return 0.0

        dist_km = self._haversine(n.lat, n.lon, g.lat, g.lon)

        if metric == 'time':
            return dist_km / self._vmax
        elif metric == 'distance':
            return dist_km
        elif metric == 'co2':
            return 0.0          # walk is always available with 0 CO2
        elif metric == 'weighted':
            return w1 * (dist_km / self._vmax)
        return 0.0

    # ─── Edge cost c(e)

    def _edge_cost(self, edge, metric: str,
                   last_route: str | None,
                   w1: float, w2: float, w3: float) -> float:
        """
        Compute cost of traversing an edge.

        From Problem Formulation (Section 8-9):
            c(e) = w1 * Time(e) + w2 * Price(e) + w3 * CO2(e)

        For 'weighted' mode, Price(e) is estimated per-edge:
            walk = 0 DA, transit = FARES[type] amortised per edge.
        Since exact fare depends on boarding sequences (computed post-hoc
        from segments), we use a per-edge estimate for search guidance.
        """
        if metric == 'time':
            base = edge.time_min
        elif metric == 'distance':
            base = edge.distance_km
        elif metric == 'co2':
            base = edge.co2_g
        elif metric == 'weighted':
            price = 0.0
            if edge.transport_type != 'walk':
                price = FARES.get(edge.transport_type, 0) * 0.1
            base = w1 * edge.time_min + w2 * price + w3 * edge.co2_g
        else:
            base = edge.time_min

        from ucs import TRANSFER_PENALTY
        is_transfer = (last_route is not None and
                       edge.transport_type != 'walk' and
                       last_route != edge.route_id)
        if is_transfer:
            base += TRANSFER_PENALTY.get(metric, 0.0)

        return base

  
    # A* SEARCH  (Russell & Norvig, Chapter 3)
    

    def find_route_astar(self, start_id: str, goal_id: str,
                         metric: str = 'time',
                         w1: float = 1.0, w2: float = 0.0,
                         w3: float = 0.0,
                         departure_time: float = 8.0) -> RouteResult:
        """
        Find the optimal route using A* Search (graph-search version).

        Algorithm (from the slides, identical to UCS but uses g+h):
        ─────────────────────────────────────────────────────────────
        1. Initialise the frontier (priority queue) with the start node.
           Priority = f(start) = g(start) + h(start) = 0 + h(start).
        2. Initialise the explored set to empty.
        3. Loop:
           a. If frontier is empty → return failure (no route).
           b. Pop node n with lowest f(n) from frontier.
           c. If n is the GOAL → return the solution (reconstruct path).
           d. Add n to explored set.
           e. For each successor n' of n:
              - Compute g(n') = g(n) + c(n, a, n')
              - Compute f(n') = g(n') + h(n', goal)
              - Check working-hours: skip n' if transport not operating.
              - If n' not in explored and (n' not in frontier or
                new g < old g) → add/update n' in frontier.

        Working-hours enforcement:
            Each edge is only traversable if the simulated clock time
            (departure_time + accumulated_time_min / 60) falls within
            the operating window of the edge's transport mode.

        Args:
            start_id       : origin stop ID
            goal_id        : destination stop ID
            metric         : 'time' | 'distance' | 'co2' | 'weighted'
            w1, w2, w3     : weights for weighted cost (Time, Price, CO2)
            departure_time : departure hour in decimal (e.g. 8.0 = 08:00)

        Returns:
            RouteResult with path, segments, totals, fare, nodes_explored
        """
        # ── Validate inputs ──────────────────────────────────────────────
        if start_id not in self.stops:
            raise ValueError(f"Unknown start stop: {start_id}")
        if goal_id not in self.stops:
            raise ValueError(f"Unknown goal stop: {goal_id}")
        if start_id == goal_id:
            return RouteResult(
                found=True, path=[start_id], edges=[], segments=[],
                total_time=0, total_dist=0, total_co2=0, total_fare=0,
                nodes_explored=0
            )

        # ── Step 1: Initialise frontier ──────────────────────────────────
        # State = (node_id, last_route_id)
        # Priority queue entry: (f_cost, tie-breaker, node_id, last_route)
        #
        # f(start) = g(start) + h(start) = 0 + h(start)
        h0      = self._heuristic(start_id, goal_id, metric, w1)
        counter = 0
        # (f, counter, node_id, last_route)
        frontier = [(h0, counter, start_id, None)]

        # g(n)  — actual cost from start to each state
        init_state   = (start_id, None)
        g_cost       = {init_state: 0.0}

        # elapsed travel time in minutes (for working-hours check, metric-agnostic)
        time_elapsed = {init_state: 0.0}

        # predecessor map: state → (g, prev_state, edge)
        best         = {init_state: (0.0, None, None)}

        # ── Step 2: Initialise explored set ──────────────────────────────
        visited        = set()
        nodes_explored = 0

        # ── Step 3: Main loop ─────────────────────────────────────────────
        while frontier:

            # 3a. Pop node with lowest f(n) = g(n) + h(n)
            f, _, node, last_route = heapq.heappop(frontier)
            state_key = (node, last_route)

            # Skip if already in explored set (graph-search duplicate guard)
            if state_key in visited:
                continue

            # 3d. Add to explored set
            visited.add(state_key)
            nodes_explored += 1

            # 3c. Goal test
            if node == goal_id:
                path, edges = self._reconstruct(best, state_key)
                segments    = self._build_segments(path, edges)
                total_time  = sum(e.time_min    for e in edges)
                total_dist  = sum(e.distance_km for e in edges)
                total_co2   = sum(e.co2_g       for e in edges)
                total_fare  = self._compute_fare(edges)

                return RouteResult(
                    found=True, path=path, edges=edges,
                    segments=segments,
                    total_time=round(total_time, 2),
                    total_dist=round(total_dist, 4),
                    total_co2=round(total_co2,  2),
                    total_fare=total_fare,
                    nodes_explored=nodes_explored
                )

            # 3e. Expand successors
            current_elapsed = time_elapsed[state_key]   # minutes since departure
            clock_hour      = departure_time + current_elapsed / 60.0

            for edge in self.graph.get(node, []):

                # ── Working-hours check ─────────────────────────────────
                # An edge is usable only if the transport operates at the
                # simulated clock time when we arrive at the edge's origin.
                if not _is_operating(edge.transport_type, clock_hour):
                    continue

                new_last_route  = (last_route if edge.transport_type == 'walk'
                                   else edge.route_id)
                next_state_key  = (edge.to_id, new_last_route)

                if next_state_key in visited:
                    continue

                # g(n') = g(n) + c(n, a, n')
                ec     = self._edge_cost(edge, metric, last_route, w1, w2, w3)
                new_g  = g_cost[state_key] + ec

                # Update frontier if n' is new or we found a cheaper path
                if next_state_key not in g_cost or new_g < g_cost[next_state_key]:
                    g_cost[next_state_key]       = new_g
                    time_elapsed[next_state_key] = current_elapsed + edge.time_min
                    best[next_state_key]         = (new_g, state_key, edge)

                    # f(n') = g(n') + h(n')
                    h       = self._heuristic(edge.to_id, goal_id, metric, w1)
                    f_new   = new_g + h
                    counter += 1
                    heapq.heappush(frontier,
                                   (f_new, counter, edge.to_id, new_last_route))

        # ── No path found ────────────────────────────────────────────────
        return RouteResult(
            found=False, path=[], edges=[], segments=[],
            total_time=0, total_dist=0, total_co2=0, total_fare=0,
            nodes_explored=nodes_explored
        )

    # ─── Path reconstruction ─────────────────────────────────────────────────

    def _reconstruct(self, best: dict, goal_state: tuple):
        """Reconstruct path from A* predecessor map: state → (g, prev_state, edge)."""
        path, edges = [], []
        state = goal_state
        while best[state][1] is not None:
            _, prev, edge = best[state]
            path.append(state[0])
            edges.append(edge)
            state = prev
        path.append(state[0])
        path.reverse()
        edges.reverse()
        return path, edges


    # COMPARISON: A* vs UCS


    def compare_with_ucs(self, start_id: str, goal_id: str,
                         metric: str = 'time',
                         departure_time: float = 8.0) -> dict:
        """
        Run both A* and UCS (Dijkstra) and compare results.

        From Project Description (Section 5e):
            Compare the number of nodes expanded by Dijkstra vs. A*.

        Returns dict with both results and comparison metrics.
        """
        # A* search
        t0           = time_module.time()
        astar_result = self.find_route_astar(start_id, goal_id, metric,
                                             departure_time=departure_time)
        astar_time   = time_module.time() - t0

        # UCS search (inherited from TransitRouter)
        t0         = time_module.time()
        ucs_result = self.find_route(start_id, goal_id, metric)
        ucs_time   = time_module.time() - t0

        # Node reduction
        if ucs_result.nodes_explored > 0:
            reduction = (1 - astar_result.nodes_explored /
                         ucs_result.nodes_explored) * 100
        else:
            reduction = 0.0

        return {
            'astar':              astar_result,
            'ucs':                ucs_result,
            'astar_exec_ms':      round(astar_time * 1000, 2),
            'ucs_exec_ms':        round(ucs_time   * 1000, 2),
            'speedup':            (round(ucs_time / astar_time, 2)
                                   if astar_time > 0 else float('inf')),
            'node_reduction_pct': round(reduction, 2),
            'vmax_kmh':           round(self._vmax_kmh, 2),
        }


# CLI INTERFACE


def print_route(router: AStarRouter, result: RouteResult, label: str = ""):
    """Pretty-print a route result."""
    if label:
        print(f"\n  {'─'*3} {label} {'─'*3}")
    print(f"  ⏱  Time:     {result.total_time:.1f} min")
    print(f"  📏 Distance: {result.total_dist:.2f} km")
    print(f"  🌿 CO2:      {result.total_co2:.1f} g")
    print(f"  💰 Fare:     {result.total_fare} DA")
    print(f"  📍 Stops:    {len(result.path)}")
    print(f"  🔍 Nodes:    {result.nodes_explored}")
    print(f"\n  Path:")
    for seg in result.segments:
        from_name = router.get_stop_name(seg.from_stop)
        to_name   = router.get_stop_name(seg.to_stop)
        icon = {
            'metro': '🚇', 'tram': '🚊', 'bus': '🚌',
            'train': '🚂', 'telepherique': '🚡', 'walk': '🚶'
        }.get(seg.transport_type, '•')
        fare_str = f" | {seg.fare} DA" if seg.fare > 0 else ""
        print(f"    {icon} {from_name} → {to_name}")
        print(f"       {seg.transport_type.upper()} {seg.route_id} | "
              f"{len(seg.stops)} stops | {seg.distance_km:.2f} km | "
              f"{seg.time_min:.1f} min{fare_str}")


if __name__ == '__main__':
    data_dir = sys.argv[1] if len(sys.argv) > 1 else 'data'

    print(f"Loading graph from {data_dir}...")
    t0     = time_module.time()
    router = AStarRouter(data_dir)
    print(f"  Loaded in {time_module.time()-t0:.2f}s: "
          f"{router.num_stops} stops, {router.num_edges} edges")
    print(f"  vmax = {router._vmax_kmh:.1f} km/h "
          f"(used in heuristic h(n) = d(n,goal) / vmax)")

    while True:
        print("\n" + "=" * 60)
        print("A* Search — Green Multi-Modal Transit Router")
        print("=" * 60)
        start = input("From (stop ID or name, 'q' to quit): ").strip()
        if start.lower() == 'q':
            break

        # Search by name if not a valid ID
        if start not in router.stops:
            matches = [(sid, s) for sid, s in router.stops.items()
                       if start.lower() in s.name.lower()]
            if not matches:
                print("  No stops found.")
                continue
            print("  Matches:")
            for sid, s in matches[:10]:
                print(f"    {sid:20s} {s.name:40s} ({s.transport_type})")
            start = input("  Enter stop ID: ").strip()

        goal = input("To (stop ID or name): ").strip()
        if goal not in router.stops:
            matches = [(sid, s) for sid, s in router.stops.items()
                       if goal.lower() in s.name.lower()]
            if not matches:
                print("  No stops found.")
                continue
            print("  Matches:")
            for sid, s in matches[:10]:
                print(f"    {sid:20s} {s.name:40s} ({s.transport_type})")
            goal = input("  Enter stop ID: ").strip()

        metric = input("Metric (time/distance/co2/weighted) [time]: "
                       ).strip() or 'time'

        w1, w2, w3 = 1.0, 0.0, 0.0
        if metric == 'weighted':
            try:
                w1 = float(input("  w1 (Time weight)  [1.0]: ").strip() or '1.0')
                w2 = float(input("  w2 (Price weight) [0.0]: ").strip() or '0.0')
                w3 = float(input("  w3 (CO2 weight)   [0.0]: ").strip() or '0.0')
            except ValueError:
                print("  Invalid weights, using defaults.")
                w1, w2, w3 = 1.0, 0.0, 0.0

        # Departure time input
        dep_raw = input("Departure time (HH:MM or decimal, e.g. 08:30 or 8.5) [08:00]: "
                        ).strip() or '08:00'
        try:
            if ':' in dep_raw:
                hh, mm       = dep_raw.split(':', 1)
                departure    = int(hh) + int(mm) / 60.0
            else:
                departure    = float(dep_raw)
        except ValueError:
            print("  Invalid time, defaulting to 08:00.")
            departure = 8.0

        # Working-hours summary
        print(f"\n  Departure at {int(departure):02d}:{int((departure % 1) * 60):02d}  "
              f"— active transport modes:")
        for mode, (s, e) in WORKING_HOURS.items():
            status = "✅" if _is_operating(mode, departure) else "❌"
            end_str = "24:00" if e == 24.0 else f"{int(e):02d}:{int((e % 1)*60):02d}"
            print(f"    {status} {mode:14s} "
                  f"{int(s):02d}:{int((s % 1)*60):02d} – {end_str}")

        compare = input("\nCompare A* vs UCS? (y/n) [n]: ").strip().lower()

        if compare == 'y':
            print(f"\nSearching {start} → {goal} (metric: {metric})...")
            comp = router.compare_with_ucs(start, goal, metric,
                                           departure_time=departure)

            if not comp['astar'].found:
                print("  No route found!")
                continue

            print_route(router, comp['astar'], "A* Search")
            print(f"\n  {'─'*3} UCS (Dijkstra) {'─'*3}")
            print(f"  🔍 Nodes:    {comp['ucs'].nodes_explored}")
            print(f"  ⏱  Time:     {comp['ucs'].total_time:.1f} min")

            print(f"\n  {'─'*3} Comparison {'─'*3}")
            print(f"  A* exec:         {comp['astar_exec_ms']:.2f} ms")
            print(f"  UCS exec:        {comp['ucs_exec_ms']:.2f} ms")
            print(f"  Speedup:         {comp['speedup']:.2f}x")
            print(f"  Node reduction:  {comp['node_reduction_pct']:.1f}%")
            print(f"  A* nodes:        {comp['astar'].nodes_explored}")
            print(f"  UCS nodes:       {comp['ucs'].nodes_explored}")
            print(f"  vmax:            {comp['vmax_kmh']:.1f} km/h")
        else:
            print(f"\nSearching {start} → {goal} "
                  f"(A*, metric: {metric}, departure: {dep_raw})...")
            t0     = time_module.time()
            result = router.find_route_astar(
                start, goal, metric, w1, w2, w3,
                departure_time=departure)
            elapsed = time_module.time() - t0

            if not result.found:
                print("  No route found!")
                continue

            print(f"\n  ✅ Route found in {elapsed*1000:.1f}ms")
            print_route(router, result, "A* Search")
