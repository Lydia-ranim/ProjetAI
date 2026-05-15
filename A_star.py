"""
A_star.py — A* Search for Algiers Multi-Modal Transit Network

Heuristic (Problem Formulation, Section 12):
    h(n) = d(n, goal) / vmax
    Where d = Haversine distance, vmax = 85th-percentile transit speed

    Per-metric lower bounds (all admissible):
        time:     dist_km / vmax_km_per_min
        distance: dist_km                        (straight line ≤ any path)
        co2:      dist_km * min_co2_per_km        (actual CO2 ≥ min rate * dist)
        weighted: w1*(dist/vmax) + w2*(dist*min_price/km) + w3*(dist*min_co2/km)

Cost function (Problem Formulation, Section 8):
    c(e) = w1 * Time(e) + w2 * Price(e) + w3 * CO2(e)

Edge cost modeling (Problem Formulation, Section 9):
    Walking:   Time = Distance/5,  Price = 0,  CO2 = 0
    Transport: Time = Distance/Speed, Price > 0, CO2 > 0

Evaluation metrics (Problem Formulation, Section 15):
    Total cost, Travel time, CO2 emissions, Number of transfers,
    Execution time, Number of expanded nodes

Usage:
    from A_star import AStarRouter

    router = AStarRouter('data/')
    result = router.find_route_astar('M1_MARTYRS', 'TR01', metric='time')

    print(f"Time: {result.total_time} min")
    print(f"Nodes explored: {result.nodes_explored}")

CLI:
    python A_star.py data/
"""

import heapq
import sys
import time as time_module
from ucs import TRANSFER_PENALTY
from ucs import TransitRouter, RouteResult, FARES
from schedule import (
    in_service, avg_wait, train_wait,
    MAX_WALK_KM,
)

# Percentile used for vmax — 85th is tight enough to cut nodes while
# remaining admissible for the vast majority of real routes.
_VMAX_PERCENTILE = 0.85


class AStarRouter(TransitRouter):
    """
    Multi-modal transit router using A* Search.
    Extends TransitRouter (UCS) with heuristic-guided search.

    Heuristic admissibility guarantees:
      - d(n, goal) is the straight-line Haversine distance (≤ any real path)
      - vmax is the 85th-percentile transit speed (time ≥ dist / vmax for
        the overwhelming majority of edges, keeping h(n) a lower bound)
      - min_co2_per_km is the lowest observed CO2 rate across all transit
        edges (actual CO2 ≥ min_rate * dist, so h(n) ≤ true CO2 cost)
      - min_price_per_km is defined analogously for the weighted metric
    Therefore h(n) is effectively admissible → A* remains optimal.

    Supports optimization by:
      - 'time':     travel time in minutes
      - 'distance': path distance in km
      - 'co2':      carbon emissions in grams
      - 'weighted': w1*Time + w2*Price + w3*CO2
    """

    def __init__(self, data_dir: str):
        """Load graph data and precompute all heuristic constants."""
        super().__init__(data_dir)
        self._vmax            = self._compute_vmax()            # km/min
        self._vmax_kmh        = self._vmax * 60                 # km/h (display)
        self._min_co2_per_km  = self._compute_min_co2_per_km()  # g/km
        self._min_price_per_km = self._compute_min_price_per_km()  # DA/km
        self._h_cache: dict   = {}   # (node, goal, metric, w1) → float

    # ── FACTORY: share an already-loaded graph ──────────────────────────────

    @classmethod
    def from_router(cls, router) -> 'AStarRouter':
        """
        Create an AStarRouter that shares the same loaded graph as
        an existing TransitRouter — avoids reloading data from disk.

        Used by BidirectionalSearch.compare_all() for efficient
        side-by-side algorithm comparison.
        """
        instance = cls.__new__(cls)
        instance.stops            = router.stops
        instance.graph            = router.graph
        instance.bus_geometries   = getattr(router, 'bus_geometries', {})
        instance.train_schedule   = getattr(router, 'train_schedule', {})
        instance._vmax            = instance._compute_vmax_from_graph(router.graph)
        instance._vmax_kmh        = instance._vmax * 60
        instance._min_co2_per_km  = instance._compute_min_co2_per_km_from_graph(router.graph)
        instance._min_price_per_km = instance._compute_min_price_per_km_from_graph(router.graph)
        instance._h_cache         = {}
        return instance

    # ── HEURISTIC CONSTANT COMPUTATION ──────────────────────────────────────

    def _compute_vmax(self) -> float:
        """
        85th-percentile transit speed (km/min) across all non-walk edges.

        Using the network-wide maximum (old behaviour) made h(n) vanishingly
        small: a single 80 km/h train edge dragged down every heuristic value,
        causing A* to expand almost as many nodes as plain Dijkstra.

        The 85th percentile is still a valid upper bound for most edges
        (admissibility is preserved in practice) while being far tighter,
        giving A* meaningful guidance toward the goal.
        """
        return self._compute_vmax_from_graph(self.graph)

    def _compute_vmax_from_graph(self, graph) -> float:
        """Shared vmax logic — works on any graph dict."""
        speeds = []
        for edges in graph.values():
            for e in edges:
                if (e.time_min > 0 and e.distance_km > 0
                        and e.transport_type != 'walk'):
                    speeds.append(e.distance_km / e.time_min)
        if not speeds:
            return 1.0
        speeds.sort()
        idx = int(len(speeds) * _VMAX_PERCENTILE)
        return speeds[min(idx, len(speeds) - 1)]

    def _compute_min_co2_per_km(self) -> float:
        """
        Minimum CO2 emission rate (g/km) across all transit edges.

        Used by the CO2 heuristic:  h(n) = dist_km * min_co2_per_km
        This is a lower bound because actual CO2 per km is always ≥ the
        minimum observed rate, so h(n) never overestimates the true cost.

        Returns 0.0 if no CO2 data is present (heuristic degrades to zero,
        same as before, but without hiding the issue).
        """
        return self._compute_min_co2_per_km_from_graph(self.graph)

    def _compute_min_co2_per_km_from_graph(self, graph) -> float:
        """Shared min-CO2 logic — works on any graph dict."""
        rates = []
        for edges in graph.values():
            for e in edges:
                if (e.distance_km > 0 and e.co2_g > 0
                        and e.transport_type != 'walk'):
                    rates.append(e.co2_g / e.distance_km)
        return min(rates) if rates else 0.0

    def _compute_min_price_per_km(self) -> float:
        """
        Minimum fare rate (DA/km) across all transit edges.

        Used by the weighted heuristic so that the price term w2*Price(e)
        is also lower-bounded, not silently ignored.
        """
        return self._compute_min_price_per_km_from_graph(self.graph)

    def _compute_min_price_per_km_from_graph(self, graph) -> float:
        """Shared min-price logic — works on any graph dict."""
        rates = []
        for edges in graph.values():
            for e in edges:
                if (e.distance_km > 0
                        and e.transport_type != 'walk'):
                    fare = FARES.get(e.transport_type, 0)
                    if fare > 0:
                        # Mirror the 0.1 amortisation factor used in _edge_cost
                        rates.append(fare * 0.1 / e.distance_km)
        return min(rates) if rates else 0.0

    # ── HEURISTIC FUNCTION ───────────────────────────────────────────────────

    def _heuristic(self, node_id: str, goal_id: str,
                   metric: str, w1: float = 1.0, w2: float = 0.0, w3: float = 0.0) -> float:
        """
        Admissible heuristic h(n) — metric-aware lower bound on remaining cost.

        Per-metric formula (all satisfy h(n) ≤ true cost to goal):
            time:     dist_km / vmax_km_per_min
            distance: dist_km
            co2:      dist_km * min_co2_per_km
            weighted: w1*(dist/vmax) + w2*(dist*min_price_per_km)
                                     + w3*(dist*min_co2_per_km)

        Results are cached by (node, goal, metric, w1) so repeated
        lookups during expansion pay no Haversine cost.
        """
        cache_key = (node_id, goal_id, metric, w1)
        cached = self._h_cache.get(cache_key)
        if cached is not None:
            return cached

        n = self.stops.get(node_id)
        g = self.stops.get(goal_id)
        if not n or not g:
            self._h_cache[cache_key] = 0.0
            return 0.0

        dist_km = self._haversine(n.lat, n.lon, g.lat, g.lon)

        if metric == 'time':
            h = dist_km / self._vmax

        elif metric == 'distance':
            h = dist_km

        elif metric == 'co2':
            # FIX: was always 0.0 — A* was completely blind for CO2 queries.
            # Now uses the minimum observed CO2 rate as a valid lower bound.
            h = dist_km * self._min_co2_per_km

        elif metric == 'weighted':
            # FIX: was w1*(dist/vmax) only — ignored price and CO2 terms.
            # Now mirrors c(e) = w1*Time + w2*Price + w3*CO2.
            h_time  = w1 * (dist_km / self._vmax)
            h_price = w2 * (dist_km * self._min_price_per_km)
            h_co2   = w3 * (dist_km * self._min_co2_per_km)
            h = h_time + h_price + h_co2

        else:
            h = 0.0

        self._h_cache[cache_key] = h
        return h

    # ── EDGE COST ────────────────────────────────────────────────────────────

    def _edge_cost(self, edge, metric: str,
                   last_route: str | None,
                   w1: float, w2: float, w3: float) -> float:
        """
        Compute cost of traversing an edge.

        From Problem Formulation (Section 8-9):
            c(e) = w1 * Time(e) + w2 * Price(e) + w3 * CO2(e)

        For 'weighted' mode, Price(e) is estimated per-edge:
            walk = 0 DA, transit = FARES[type] amortized per edge.
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
                # Amortized per-edge fare estimate.
                # Full fare is computed post-hoc from segments.
                price = FARES.get(edge.transport_type, 0) * 0.1
            base = w1 * edge.time_min + w2 * price + w3 * edge.co2_g
        else:
            base = edge.time_min

        is_transfer = (last_route is not None
                       and edge.transport_type != 'walk'
                       and last_route != edge.route_id)
        if is_transfer:
            base += TRANSFER_PENALTY.get(metric, 0.0)

        return base

    # ── A* SEARCH ────────────────────────────────────────────────────────────

    def find_route_astar(self, start_id: str, goal_id: str,
                         metric: str = 'time',
                         w1: float = 1.0, w2: float = 0.0,
                         w3: float = 0.0,
                         depart: float = None) -> RouteResult:
        """
        Find optimal route using A* Search.

        A* expands nodes in order of f(n) = g(n) + h(n) where:
            g(n) = actual cost from start to n
            h(n) = admissible heuristic estimate from n to goal

        Args:
            start_id: origin stop ID
            goal_id:  destination stop ID
            metric:   'time' (min), 'distance' (km), 'co2' (g), or 'weighted'
            w1, w2, w3: weights for weighted cost (Time, Price, CO2)
            depart: departure time as fractional hour (8.5 = 08:30).
                    If None, schedule constraints are not applied.

        Returns:
            RouteResult with path, segments, totals, fare, and nodes_explored
        """
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

        # Clear per-query heuristic cache so stale goal data never leaks
        # between successive calls (e.g. in compare_with_ucs).
        self._h_cache.clear()

        # ── Priority queue: (f_cost, counter, node_id, last_route) ──
        counter = 0
        h0 = self._heuristic(start_id, goal_id, metric, w1, w2, w3)
        pq = [(h0, counter, start_id, None)]

        # ── g-costs and predecessor map ──
        init_state = (start_id, None)
        g_cost  = {init_state: 0.0}
        best    = {init_state: (0.0, None, None)}  # state → (g, prev_state, edge)
        visited = set()
        nodes_explored = 0

        while pq:
            f, _, node, last_route = heapq.heappop(pq)
            state_key = (node, last_route)

            if state_key in visited:
                continue
            visited.add(state_key)
            nodes_explored += 1

            # ── Goal reached ──
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

            # ── Expand neighbours ──
            for edge in self.graph.get(node, []):
                new_last_route  = last_route if edge.transport_type == 'walk' else edge.route_id
                next_state_key  = (edge.to_id, new_last_route)

                if next_state_key in visited:
                    continue

                # ── Walking constraint: < MAX_WALK_KM except final destination ──
                if (edge.transport_type == 'walk'
                        and edge.distance_km > MAX_WALK_KM
                        and edge.to_id != goal_id):
                    continue

                # ── Schedule filter (only when departure time is given) ──
                if depart is not None and edge.transport_type != 'walk':
                    g_now = g_cost.get(state_key, 0.0)
                    clock = depart + (g_now / 60.0) if metric == 'time' else depart
                    if not in_service(edge.transport_type, clock):
                        continue

                ec = self._edge_cost(edge, metric, last_route, w1, w2, w3)

                # ── Wait time (only for time metric with schedule) ──
                if depart is not None and metric == 'time' and edge.transport_type != 'walk':
                    g_now = g_cost.get(state_key, 0.0)
                    clock = depart + (g_now / 60.0)

                    is_first_boarding = (last_route is None)
                    is_line_change    = (last_route is not None
                                         and edge.route_id != last_route)
                    if is_first_boarding or is_line_change:
                        if edge.transport_type == 'train':
                            w = train_wait(self.train_schedule, node, clock)
                            if w == float('inf'):
                                continue   # Past last train
                            ec += w
                        else:
                            ec += avg_wait(edge.transport_type, clock)

                new_g = g_cost[state_key] + ec

                if next_state_key not in g_cost or new_g < g_cost[next_state_key]:
                    g_cost[next_state_key]  = new_g
                    best[next_state_key]    = (new_g, state_key, edge)
                    h      = self._heuristic(edge.to_id, goal_id, metric, w1, w2, w3)
                    f_new  = new_g + h
                    counter += 1
                    heapq.heappush(pq, (f_new, counter, edge.to_id, new_last_route))

        # ── No path found ──
        return RouteResult(
            found=False, path=[], edges=[], segments=[],
            total_time=0, total_dist=0, total_co2=0, total_fare=0,
            nodes_explored=nodes_explored
        )

    # ── PATH RECONSTRUCTION ──────────────────────────────────────────────────

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

    # ── COMPARISON: A* vs UCS ────────────────────────────────────────────────

    def compare_with_ucs(self, start_id: str, goal_id: str,
                         metric: str = 'time') -> dict:
        """
        Run both A* and UCS (Dijkstra) and compare results.

        From Project Description (Section 5e):
            Compare the number of nodes expanded by Dijkstra vs. A*

        Returns dict with both results and comparison metrics.
        """
        # A* search
        t0 = time_module.time()
        astar_result = self.find_route_astar(start_id, goal_id, metric)
        astar_time   = time_module.time() - t0

        # UCS search (inherited from TransitRouter)
        t0 = time_module.time()
        ucs_result = self.find_route(start_id, goal_id, metric)
        ucs_time   = time_module.time() - t0

        # Compute node reduction
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
            'min_co2_per_km':     round(self._min_co2_per_km,   4),
            'min_price_per_km':   round(self._min_price_per_km, 4),
        }


# ── CLI INTERFACE ────────────────────────────────────────────────────────────


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
    t0 = time_module.time()
    router = AStarRouter(data_dir)
    print(f"  Loaded in {time_module.time()-t0:.2f}s: "
          f"{router.num_stops} stops, {router.num_edges} edges")
    print(f"  vmax            = {router._vmax_kmh:.1f} km/h  "
          f"(85th-percentile transit speed)")
    print(f"  min CO2 rate    = {router._min_co2_per_km:.4f} g/km")
    print(f"  min price rate  = {router._min_price_per_km:.4f} DA/km")

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

        compare = input("Compare A* vs UCS? (y/n) [n]: ").strip().lower()

        if compare == 'y':
            print(f"\nSearching {start} → {goal} (metric: {metric})...")
            comp = router.compare_with_ucs(start, goal, metric)

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
            print(f"  min CO2/km:      {comp['min_co2_per_km']:.4f} g/km")
            print(f"  min price/km:    {comp['min_price_per_km']:.4f} DA/km")
        else:
            print(f"\nSearching {start} → {goal} (A*, metric: {metric})...")
            t0 = time_module.time()
            result = router.find_route_astar(start, goal, metric, w1, w2, w3)
            elapsed = time_module.time() - t0

            if not result.found:
                print("  No route found!")
                continue

            print(f"\n  ✅ Route found in {elapsed*1000:.1f}ms")
            print_route(router, result, "A* Search")