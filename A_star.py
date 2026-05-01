"""
A_star.py — A* Search for Algiers Multi-Transport Transit Network

Heuristic (Problem Formulation, Section 12):
    h(n) = d(n, goal) / vmax
    Where d = Euclidean (Haversine) distance, vmax = max transport speed

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

from ucs import TransitRouter, RouteResult, FARES


class AStarRouter(TransitRouter):
    """
    Multi-modal transit router using A* Search.
    Extends TransitRouter (UCS) with heuristic-guided search.

    The heuristic h(n) = d(n, goal) / vmax is admissible because:
      - d(n, goal) is the straight-line distance (always <= actual path distance)
      - vmax is the fastest possible speed (time >= distance / vmax)
    Therefore h(n) never overestimates the true cost -> A* is optimal.

    Supports optimization by:
      - 'time':     travel time in minutes
      - 'distance': path distance in km
      - 'co2':      carbon emissions in grams
      - 'weighted': w1*Time + w2*Price + w3*CO2
    """

    def __init__(self, data_dir: str):
        """Load graph data and compute vmax for the heuristic."""
        super().__init__(data_dir)
        self._vmax = self._compute_vmax()       # km/min
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
        instance.stops   = router.stops
        instance.graph   = router.graph
        instance._vmax   = instance._compute_vmax_from_graph(router.graph)
        instance._vmax_kmh = instance._vmax * 60
        return instance

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

    @classmethod
    def from_router(cls, router) -> 'AStarRouter':
        """
        Create an AStarRouter that shares the same loaded graph as
        an existing TransitRouter — avoids reloading data from disk.

        Used by BidirectionalSearch.compare_all() for efficient
        side-by-side algorithm comparison.
        """
        instance = cls.__new__(cls)
        instance.stops   = router.stops
        instance.graph   = router.graph
        instance._vmax   = instance._compute_vmax_from_graph(router.graph)
        instance._vmax_kmh = instance._vmax * 60
        return instance

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

    # ═══════════════════════════════════════════
    # VMAX COMPUTATION
    # ═══════════════════════════════════════════

    def _compute_vmax(self) -> float:
        """
        Compute maximum speed (km/min) across all edges in the network.
        Used as vmax in h(n) = d(n, goal) / vmax.
        """
        vmax = 0.0
        for edges in self.graph.values():
            for e in edges:
                if e.time_min > 0 and e.distance_km > 0:
                    speed = e.distance_km / e.time_min
                    if speed > vmax:
                        vmax = speed
        return vmax if vmax > 0 else 1.0

    # ═══════════════════════════════════════════
    # HEURISTIC FUNCTION
    # ═══════════════════════════════════════════

    def _heuristic(self, node_id: str, goal_id: str,
                   metric: str, w1: float = 1.0) -> float:
        """
        Admissible heuristic: h(n) = d(n, goal) / vmax

        From Problem Formulation (Section 12):
            d(n, goal) = Euclidean (Haversine) distance in km
            vmax       = maximum transport speed

        Admissibility per metric:
            time:     h = dist_km / vmax_km_per_min  (lower bound on travel time)
            distance: h = dist_km                    (straight line <= any path)
            co2:      h = 0                          (walking has 0 CO2)
            weighted: h = w1 * dist_km / vmax        (price/co2 terms >= 0)
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
            return 0.0
        elif metric == 'weighted':
            return w1 * (dist_km / self._vmax)
        return 0.0

    # ═══════════════════════════════════════════
    # EDGE COST
    # ═══════════════════════════════════════════

    def _edge_cost(self, edge, metric: str,
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
            return edge.time_min
        elif metric == 'distance':
            return edge.distance_km
        elif metric == 'co2':
            return edge.co2_g
        elif metric == 'weighted':
            price = 0.0
            if edge.transport_type != 'walk':
                # Amortized per-edge fare estimate
                # Full fare is computed post-hoc from segments
                price = FARES.get(edge.transport_type, 0) * 0.1
            return w1 * edge.time_min + w2 * price + w3 * edge.co2_g
        return edge.time_min

    # ═══════════════════════════════════════════
    # A* SEARCH
    # ═══════════════════════════════════════════

    def find_route_astar(self, start_id: str, goal_id: str,
                         metric: str = 'time',
                         w1: float = 1.0, w2: float = 0.0,
                         w3: float = 0.0) -> RouteResult:
        """
        Find optimal route using A* Search.

        A* expands nodes in order of f(n) = g(n) + h(n) where:
            g(n) = actual cost from start to n
            h(n) = heuristic estimate from n to goal

        Args:
            start_id: origin stop ID
            goal_id:  destination stop ID
            metric:   'time' (min), 'distance' (km), 'co2' (g), or 'weighted'
            w1, w2, w3: weights for weighted cost (Time, Price, CO2)

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

        # ── Priority queue: (f_cost, counter, node_id) ──
        counter = 0
        h0 = self._heuristic(start_id, goal_id, metric, w1)
        pq = [(h0, counter, start_id)]

        # ── g-costs and predecessor map ──
        g_cost = {start_id: 0.0}
        best = {start_id: (0.0, None, None)}   # node -> (g, prev_node, edge)
        visited = set()
        nodes_explored = 0

        while pq:
            f, _, node = heapq.heappop(pq)

            if node in visited:
                continue
            visited.add(node)
            nodes_explored += 1

            # ── Goal reached ──
            if node == goal_id:
                path, edges = self._reconstruct(best, goal_id)
                segments = self._build_segments(path, edges)
                total_time = sum(e.time_min for e in edges)
                total_dist = sum(e.distance_km for e in edges)
                total_co2 = sum(e.co2_g for e in edges)
                total_fare = self._compute_fare(edges)

                return RouteResult(
                    found=True, path=path, edges=edges,
                    segments=segments,
                    total_time=round(total_time, 2),
                    total_dist=round(total_dist, 4),
                    total_co2=round(total_co2, 2),
                    total_fare=total_fare,
                    nodes_explored=nodes_explored
                )

            # ── Expand neighbors ──
            for edge in self.graph.get(node, []):
                if edge.to_id in visited:
                    continue

                ec = self._edge_cost(edge, metric, w1, w2, w3)
                new_g = g_cost[node] + ec

                if edge.to_id not in g_cost or new_g < g_cost[edge.to_id]:
                    g_cost[edge.to_id] = new_g
                    best[edge.to_id] = (new_g, node, edge)
                    h = self._heuristic(edge.to_id, goal_id, metric, w1)
                    f_new = new_g + h
                    counter += 1
                    heapq.heappush(pq, (f_new, counter, edge.to_id))

        # ── No path found ──
        return RouteResult(
            found=False, path=[], edges=[], segments=[],
            total_time=0, total_dist=0, total_co2=0, total_fare=0,
            nodes_explored=nodes_explored
        )

    # ═══════════════════════════════════════════
    # COMPARISON: A* vs UCS
    # ═══════════════════════════════════════════

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
        astar_time = time_module.time() - t0

        # UCS search (inherited from TransitRouter)
        t0 = time_module.time()
        ucs_result = self.find_route(start_id, goal_id, metric)
        ucs_time = time_module.time() - t0

        # Compute node reduction
        if ucs_result.nodes_explored > 0:
            reduction = (1 - astar_result.nodes_explored /
                         ucs_result.nodes_explored) * 100
        else:
            reduction = 0.0

        return {
            'astar': astar_result,
            'ucs': ucs_result,
            'astar_exec_ms': round(astar_time * 1000, 2),
            'ucs_exec_ms': round(ucs_time * 1000, 2),
            'speedup': (round(ucs_time / astar_time, 2)
                        if astar_time > 0 else float('inf')),
            'node_reduction_pct': round(reduction, 2),
            'vmax_kmh': round(self._vmax_kmh, 2),
        }


# ═══════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════

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
        to_name = router.get_stop_name(seg.to_stop)
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
                w1 = float(input("  w1 (Time weight)  [1.0]: ").strip()
                           or '1.0')
                w2 = float(input("  w2 (Price weight) [0.0]: ").strip()
                           or '0.0')
                w3 = float(input("  w3 (CO2 weight)   [0.0]: ").strip()
                           or '0.0')
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
        else:
            print(f"\nSearching {start} → {goal} "
                  f"(A*, metric: {metric})...")
            t0 = time_module.time()
            result = router.find_route_astar(
                start, goal, metric, w1, w2, w3)
            elapsed = time_module.time() - t0

            if not result.found:
                print("  No route found!")
                continue

            print(f"\n  ✅ Route found in {elapsed*1000:.1f}ms")
            print_route(router, result, "A* Search")
