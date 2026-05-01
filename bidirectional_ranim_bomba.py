"""
bidirectional.py — Bidirectional Search Framework for Algiers Transit Network

Architecture:
    BidirectionalSearch is a generic wrapper that can pair with ANY
    forward-search algorithm (UCS, A*, Greedy, etc.) by accepting
    callable cost functions and heuristic functions as parameters.

    Algorithm (Problem Formulation, Section 11d):
        - Forward frontier:  expands from start  → toward goal
        - Backward frontier: expands from goal   → toward start
        - Meeting condition: a node appears in BOTH visited sets
        - Path merge:        forward_path(start→meeting) + reverse(backward_path(meeting→goal))

    Termination (Kaindl-Kainz criterion):
        Stop when: min(forward_top) + min(backward_top) >= mu
        where mu = best complete path cost found so far

    Admissibility:
        If both forward and backward heuristics are admissible,
        bidirectional A* is guaranteed to find the optimal path.
        For bidirectional UCS (h=0), optimality is always guaranteed.

Usage:
    from bidirectional import BidirectionalSearch
    from ucs import TransitRouter

    router = TransitRouter('data/')
    bidir  = BidirectionalSearch(router)

    # Pair with UCS (Dijkstra)
    result = bidir.search(
        start_id='M1_MARTYRS',
        goal_id='TR01',
        metric='time',
        algorithm='ucs'
    )

    # Pair with A*
    result = bidir.search(
        start_id='M1_MARTYRS',
        goal_id='TR01',
        metric='time',
        algorithm='astar'
    )

    # Full comparison of all algorithms on same query
    report = bidir.compare_all('M1_MARTYRS', 'TR01', metric='time')
    bidir.print_report(report)
"""

import heapq
import math
import time as time_module
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, List, Tuple, Any

from ucs import TransitRouter, RouteResult, Segment, FARES, TRANSFER_PENALTY


# ═══════════════════════════════════════════════════════════════
# RESULT DATACLASS
# ═══════════════════════════════════════════════════════════════

@dataclass
class BiDirResult:
    """Result of a bidirectional search."""
    found:           bool
    path:            List[str]       # ordered stop IDs
    edges:           List[Any]       # Edge objects
    segments:        List[Segment]
    total_time:      float
    total_dist:      float
    total_co2:       float
    total_fare:      int
    nodes_explored:  int             # total nodes popped from BOTH frontiers
    forward_nodes:   int             # nodes expanded in forward direction
    backward_nodes:  int             # nodes expanded in backward direction
    meeting_node:    Optional[str]   # node where the two frontiers met
    algorithm_used:  str             # e.g. 'bidir_ucs', 'bidir_astar'
    runtime_ms:      float


# ═══════════════════════════════════════════════════════════════
# BIDIRECTIONAL SEARCH ENGINE
# ═══════════════════════════════════════════════════════════════

class BidirectionalSearch:
    """
    Generic Bidirectional Search that wraps any forward search algorithm.

    Design:
        Rather than duplicating each algorithm, BidirectionalSearch
        accepts a 'cost_fn' and 'heuristic_fn' at search time.
        This makes it trivially extensible to new algorithms:
            - bidir_ucs:    cost_fn = edge cost,  heuristic = 0
            - bidir_astar:  cost_fn = edge cost,  heuristic = admissible h(n)
            - bidir_greedy: cost_fn = heuristic,  heuristic = h(n)

    The backward search uses a reversed graph (edges flipped).
    """

    VMAX_KMH = 70.0   # km/h — used in A* heuristic (metro top speed)
    VMAX     = VMAX_KMH / 60.0  # km/min

    def __init__(self, router: TransitRouter):
        if not isinstance(router, TransitRouter):
            raise TypeError("router must be a TransitRouter instance")
        self.router  = router
        self._rev_adj = self._build_reverse_graph()

    # ───────────────────────────────────────────────────────────
    # REVERSE GRAPH
    # ───────────────────────────────────────────────────────────

    def _build_reverse_graph(self) -> Dict[str, List]:
        """
        Build a reversed adjacency list for backward search.
        Every edge (u→v) becomes (v→u) in the reverse graph.
        Edge attributes (cost, time, co2) remain the same.
        """
        from ucs import Edge
        rev = {sid: [] for sid in self.router.stops}
        for from_id, edges in self.router.graph.items():
            for e in edges:
                if e.to_id in rev:
                    rev[e.to_id].append(Edge(
                        to_id=from_id,
                        distance_km=e.distance_km,
                        time_min=e.time_min,
                        co2_g=e.co2_g,
                        transport_type=e.transport_type,
                        route_id=e.route_id,
                    ))
        return rev

    # ───────────────────────────────────────────────────────────
    # HEURISTIC FUNCTIONS
    # ───────────────────────────────────────────────────────────

    def _haversine(self, a_id: str, b_id: str) -> float:
        """Straight-line distance in km between two stops."""
        a = self.router.stops.get(a_id)
        b = self.router.stops.get(b_id)
        if not a or not b:
            return 0.0
        lat1, lon1, lat2, lon2 = map(math.radians,
                                      [a.lat, a.lon, b.lat, b.lon])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        h = (math.sin(dlat / 2) ** 2
             + math.cos(lat1) * math.cos(lat2)
             * math.sin(dlon / 2) ** 2)
        return 6371 * 2 * math.asin(math.sqrt(max(0.0, min(1.0, h))))

    def _heuristic_ucs(self, node_id: str, goal_id: str,
                        metric: str, w1: float = 1.0) -> float:
        """Zero heuristic — degrades to Dijkstra/UCS."""
        return 0.0

    def _heuristic_astar(self, node_id: str, goal_id: str,
                          metric: str, w1: float = 1.0) -> float:
        """
        Admissible heuristic h(n) = d(n, goal) / vmax.
        Same formula as A_star.py for consistency.
        """
        dist_km = self._haversine(node_id, goal_id)
        if metric == 'time':
            return w1 * (dist_km / self.VMAX)
        elif metric == 'distance':
            return dist_km
        elif metric == 'co2':
            return 0.0
        elif metric == 'weighted':
            return w1 * (dist_km / self.VMAX)
        return 0.0

    def _heuristic_greedy(self, node_id: str, goal_id: str,
                           metric: str, w1: float = 1.0) -> float:
        """Pure heuristic — greedy best-first (not optimal but fast)."""
        return self._heuristic_astar(node_id, goal_id, metric, w1) * 10.0

    # ───────────────────────────────────────────────────────────
    # EDGE COST FUNCTION
    # ───────────────────────────────────────────────────────────

    def _edge_cost(self, edge, metric: str,
                   last_route: Optional[str],
                   w1: float = 1.0,
                   w2: float = 0.0,
                   w3: float = 0.0) -> float:
        """
        Compute the cost of traversing an edge.
        Applies transfer penalty when switching non-walk lines.
        Mirrors the cost model in ucs.py and A_star.py exactly.
        """
        if metric == 'time':
            base = edge.time_min
        elif metric == 'distance':
            base = edge.distance_km
        elif metric == 'co2':
            base = edge.co2_g
        elif metric == 'weighted':
            price_est = 0.0
            if edge.transport_type != 'walk':
                price_est = FARES.get(edge.transport_type, 0) * 0.1
            base = w1 * edge.time_min + w2 * price_est + w3 * edge.co2_g
        else:
            base = edge.time_min

        # Transfer penalty (same as ucs.py)
        is_transfer = (last_route is not None
                       and edge.transport_type != 'walk'
                       and last_route != edge.route_id)
        if is_transfer:
            base += TRANSFER_PENALTY.get(metric, 0.0)

        return base

    # ───────────────────────────────────────────────────────────
    # SINGLE FRONTIER (used for both forward and backward)
    # ───────────────────────────────────────────────────────────

    def _init_frontier(self, start_id: str) -> Tuple[list, Dict, Dict, Dict]:
        """
        Initialise a search frontier.
        Returns: (heap, g_cost, best_pred, visited)
            heap      — priority queue of (f_cost, counter, node_id, last_route)
            g_cost    — {(node_id, last_route): g_cost}
            best_pred — {(node_id, last_route): (prev_state, edge)}
            visited   — set of (node_id, last_route) already expanded
        """
        start_state = (start_id, None)
        g_cost   = {start_state: 0.0}
        best_pred = {start_state: (None, None)}
        visited  = set()
        heap     = [(0.0, 0, start_id, None)]
        return heap, g_cost, best_pred, visited

    # ───────────────────────────────────────────────────────────
    # PATH RECONSTRUCTION
    # ───────────────────────────────────────────────────────────

    def _reconstruct_forward(self, pred: Dict, goal_state: Tuple,
                              start_id: str) -> Tuple[List[str], List]:
        """Reconstruct forward path from start → meeting node."""
        path, edges = [], []
        cur = goal_state
        while cur is not None:
            prev_state, edge = pred.get(cur, (None, None))
            if edge is not None:
                path.append(edge.to_id)
                edges.append(edge)
            cur = prev_state
        path.append(start_id)
        path.reverse()
        edges.reverse()
        return path, edges

    def _reconstruct_backward(self, pred: Dict, meeting_state: Tuple,
                               goal_id: str) -> Tuple[List[str], List]:
        """
        Reconstruct backward path from meeting node → goal.
        The backward search expanded from goal, so we follow predecessors
        from meeting → goal and then reverse to get meeting→goal order.
        """
        path, edges = [], []
        cur = meeting_state
        while cur is not None:
            prev_state, edge = pred.get(cur, (None, None))
            if edge is not None:
                # In backward graph, edge.to_id is actually the "from" in original
                path.append(edge.to_id)
                edges.append(edge)
            cur = prev_state
        # Reverse edges so they point forward (meeting → goal)
        path.reverse()
        edges.reverse()
        # Flip each edge's direction to restore original orientation
        from ucs import Edge
        fwd_edges = []
        for e in edges:
            fwd_edges.append(Edge(
                to_id=e.to_id,      # already points correctly after reverse
                distance_km=e.distance_km,
                time_min=e.time_min,
                co2_g=e.co2_g,
                transport_type=e.transport_type,
                route_id=e.route_id,
            ))
        return path, fwd_edges

    def _merge_paths(self, fwd_path: List[str], fwd_edges: List,
                     bwd_path: List[str], bwd_edges: List,
                     meeting_node: str) -> Tuple[List[str], List]:
        """
        Merge forward and backward paths at the meeting node.
        fwd: start → ... → meeting
        bwd: meeting → ... → goal  (already re-oriented)
        """
        # Remove duplicate meeting node
        full_path  = fwd_path + bwd_path
        full_edges = fwd_edges + bwd_edges
        return full_path, full_edges

    # ───────────────────────────────────────────────────────────
    # CORE BIDIRECTIONAL SEARCH
    # ───────────────────────────────────────────────────────────

    def _bidir_search(self, start_id: str, goal_id: str,
                      metric: str, heuristic_fn: Callable,
                      w1: float = 1.0, w2: float = 0.0,
                      w3: float = 0.0,
                      algorithm_label: str = 'bidir') -> BiDirResult:
        """
        Core bidirectional search loop.

        Kaindl-Kainz termination:
            mu  = best known complete path cost
            Stop when best_f + best_b >= mu
            where best_f/best_b = top of each frontier heap.

        Two simultaneous frontiers:
            Forward:  graph    (start → goal)
            Backward: rev_adj  (goal  → start, edges flipped)
        """
        t0 = time_module.time()

        if start_id not in self.router.stops:
            raise ValueError(f"Unknown start stop: {start_id}")
        if goal_id not in self.router.stops:
            raise ValueError(f"Unknown goal stop: {goal_id}")

        if start_id == goal_id:
            return BiDirResult(
                found=True, path=[start_id], edges=[], segments=[],
                total_time=0, total_dist=0, total_co2=0, total_fare=0,
                nodes_explored=0, forward_nodes=0, backward_nodes=0,
                meeting_node=start_id, algorithm_used=algorithm_label,
                runtime_ms=0.0
            )

        # ── Initialise both frontiers ──────────────────────────
        counter = [0]  # mutable for nested use

        def push(heap, f_cost, node_id, last_route):
            counter[0] += 1
            heapq.heappush(heap, (f_cost, counter[0], node_id, last_route))

        fwd_heap, fwd_g, fwd_pred, fwd_vis = self._init_frontier(start_id)
        bwd_heap, bwd_g, bwd_pred, bwd_vis = self._init_frontier(goal_id)

        # ── Tracking variables ─────────────────────────────────
        mu              = float('inf')  # best complete path cost found
        best_meeting    = None          # (fwd_state, bwd_state) at best meeting
        fwd_nodes       = 0
        bwd_nodes       = 0

        # ── Alternate expansion ────────────────────────────────
        while fwd_heap or bwd_heap:

            # Termination check (Kaindl-Kainz)
            fwd_top = fwd_heap[0][0] if fwd_heap else float('inf')
            bwd_top = bwd_heap[0][0] if bwd_heap else float('inf')
            if fwd_top + bwd_top >= mu:
                break

            # ── Choose which frontier to expand ──
            # Expand the frontier with the smaller top key
            if fwd_top <= bwd_top and fwd_heap:
                expand_forward = True
            elif bwd_heap:
                expand_forward = False
            else:
                expand_forward = True

            # ── FORWARD EXPANSION ─────────────────────────────
            if expand_forward:
                f, _, node, last_route = heapq.heappop(fwd_heap)
                state = (node, last_route)
                if state in fwd_vis:
                    continue
                fwd_vis.add(state)
                fwd_nodes += 1

                # Check if this node was reached by backward search
                for bwd_state, bwd_g_val in list(bwd_g.items()):
                    if bwd_state[0] == node:
                        total_cost = fwd_g.get(state, float('inf')) + bwd_g_val
                        if total_cost < mu:
                            mu           = total_cost
                            best_meeting = (state, bwd_state)

                # Expand forward neighbors
                for edge in self.router.graph.get(node, []):
                    new_last = (last_route if edge.transport_type == 'walk'
                                else edge.route_id)
                    next_state = (edge.to_id, new_last)
                    if next_state in fwd_vis:
                        continue
                    ec     = self._edge_cost(edge, metric, last_route, w1, w2, w3)
                    new_g  = fwd_g.get(state, float('inf')) + ec
                    if new_g < fwd_g.get(next_state, float('inf')):
                        fwd_g[next_state]    = new_g
                        fwd_pred[next_state] = (state, edge)
                        h = heuristic_fn(edge.to_id, goal_id, metric, w1)
                        push(fwd_heap, new_g + h, edge.to_id, new_last)

            # ── BACKWARD EXPANSION ────────────────────────────
            else:
                f, _, node, last_route = heapq.heappop(bwd_heap)
                state = (node, last_route)
                if state in bwd_vis:
                    continue
                bwd_vis.add(state)
                bwd_nodes += 1

                # Check if forward search reached this node
                for fwd_state, fwd_g_val in list(fwd_g.items()):
                    if fwd_state[0] == node:
                        total_cost = fwd_g_val + bwd_g.get(state, float('inf'))
                        if total_cost < mu:
                            mu           = total_cost
                            best_meeting = (fwd_state, state)

                # Expand backward neighbors (reversed graph)
                for edge in self._rev_adj.get(node, []):
                    new_last = (last_route if edge.transport_type == 'walk'
                                else edge.route_id)
                    next_state = (edge.to_id, new_last)
                    if next_state in bwd_vis:
                        continue
                    ec    = self._edge_cost(edge, metric, last_route, w1, w2, w3)
                    new_g = bwd_g.get(state, float('inf')) + ec
                    if new_g < bwd_g.get(next_state, float('inf')):
                        bwd_g[next_state]    = new_g
                        bwd_pred[next_state] = (state, edge)
                        # Backward heuristic: from neighbor toward start
                        h = heuristic_fn(edge.to_id, start_id, metric, w1)
                        push(bwd_heap, new_g + h, edge.to_id, new_last)

        # ── No path found ──────────────────────────────────────
        runtime_ms = (time_module.time() - t0) * 1000
        if best_meeting is None or mu == float('inf'):
            return BiDirResult(
                found=False, path=[], edges=[], segments=[],
                total_time=0, total_dist=0, total_co2=0, total_fare=0,
                nodes_explored=fwd_nodes + bwd_nodes,
                forward_nodes=fwd_nodes, backward_nodes=bwd_nodes,
                meeting_node=None, algorithm_used=algorithm_label,
                runtime_ms=round(runtime_ms, 2)
            )

        # ── Reconstruct full path ──────────────────────────────
        fwd_state, bwd_state = best_meeting
        meeting_node = fwd_state[0]

        fwd_path, fwd_edges = self._reconstruct_forward(
            fwd_pred, fwd_state, start_id)
        bwd_path, bwd_edges = self._reconstruct_backward(
            bwd_pred, bwd_state, goal_id)

        # The backward path from bwd_pred goes: meeting_node → ... → goal
        # but stored in reverse. Re-orient:
        bwd_path_fwd  = []
        bwd_edges_fwd = []
        cur = bwd_state
        while cur is not None:
            prev_s, edge = bwd_pred.get(cur, (None, None))
            if edge is not None:
                bwd_path_fwd.append(cur[0])
                bwd_edges_fwd.append(edge)
            cur = prev_s

        # bwd_path_fwd currently goes meeting→...→goal backwards
        # Flip to get meeting→...→goal forward
        bwd_path_fwd.reverse()
        bwd_edges_fwd.reverse()

        # Re-orient backward edges (they were on reversed graph)
        from ucs import Edge as UCSEdge
        bwd_edges_oriented = []
        for e in bwd_edges_fwd:
            bwd_edges_oriented.append(UCSEdge(
                to_id=e.to_id,
                distance_km=e.distance_km,
                time_min=e.time_min,
                co2_g=e.co2_g,
                transport_type=e.transport_type,
                route_id=e.route_id,
            ))

        full_path  = fwd_path + bwd_path_fwd
        full_edges = fwd_edges + bwd_edges_oriented

        # Deduplicate consecutive duplicate stops
        dedup_path  = [full_path[0]] if full_path else []
        dedup_edges = []
        for i, p in enumerate(full_path[1:], 1):
            if p != dedup_path[-1]:
                dedup_path.append(p)
                if i - 1 < len(full_edges):
                    dedup_edges.append(full_edges[i - 1])

        # Build segments and totals
        segments   = self.router._build_segments(dedup_path, dedup_edges)
        total_time = sum(e.time_min      for e in dedup_edges)
        total_dist = sum(e.distance_km   for e in dedup_edges)
        total_co2  = sum(e.co2_g         for e in dedup_edges)
        total_fare = self.router._compute_fare(dedup_edges)

        return BiDirResult(
            found=True, path=dedup_path, edges=dedup_edges,
            segments=segments,
            total_time=round(total_time, 2),
            total_dist=round(total_dist, 4),
            total_co2=round(total_co2, 2),
            total_fare=total_fare,
            nodes_explored=fwd_nodes + bwd_nodes,
            forward_nodes=fwd_nodes,
            backward_nodes=bwd_nodes,
            meeting_node=meeting_node,
            algorithm_used=algorithm_label,
            runtime_ms=round(runtime_ms, 2)
        )

    # ───────────────────────────────────────────────────────────
    # PUBLIC API — one method per algorithm pairing
    # ───────────────────────────────────────────────────────────

    def search(self, start_id: str, goal_id: str,
               metric: str = 'time',
               algorithm: str = 'ucs',
               w1: float = 1.0, w2: float = 0.0,
               w3: float = 0.0) -> BiDirResult:
        """
        Run bidirectional search paired with a chosen algorithm.

        Args:
            start_id:  origin stop ID
            goal_id:   destination stop ID
            metric:    'time' | 'distance' | 'co2' | 'weighted'
            algorithm: 'ucs' | 'astar' | 'greedy'
            w1, w2, w3: weights for weighted metric

        Returns:
            BiDirResult
        """
        algo_map = {
            'ucs':    (self._heuristic_ucs,    'bidir_ucs'),
            'astar':  (self._heuristic_astar,  'bidir_astar'),
            'greedy': (self._heuristic_greedy, 'bidir_greedy'),
        }
        if algorithm not in algo_map:
            raise ValueError(
                f"Unknown algorithm '{algorithm}'. "
                f"Choose from: {list(algo_map.keys())}"
            )
        hfn, label = algo_map[algorithm]
        return self._bidir_search(start_id, goal_id, metric,
                                  hfn, w1, w2, w3, label)

    # ───────────────────────────────────────────────────────────
    # COMPARE ALL ALGORITHMS
    # ───────────────────────────────────────────────────────────

    def compare_all(self, start_id: str, goal_id: str,
                    metric: str = 'time',
                    w1: float = 1.0, w2: float = 0.0,
                    w3: float = 0.0) -> Dict[str, Any]:
        """
        Run all 5 algorithms on the same query and return a comparison report.

        Algorithms compared:
            1. UCS (unidirectional Dijkstra)       — from ucs.py
            2. A*  (unidirectional)                 — from A_star.py
            3. Bidirectional UCS  (bidir + Dijkstra)
            4. Bidirectional A*   (bidir + A*)
            5. Bidirectional Greedy (bidir + Greedy, not optimal)

        Returns dict with results + comparison metrics.
        """
        from ucs import TransitRouter as TR
        from A_star import AStarRouter

        results = {}

        # 1. Unidirectional UCS
        t0 = time_module.time()
        ucs_r = self.router.find_route(start_id, goal_id, metric)
        results['ucs'] = {
            'found':          ucs_r.found,
            'total_time':     ucs_r.total_time,
            'total_dist':     ucs_r.total_dist,
            'total_co2':      ucs_r.total_co2,
            'total_fare':     ucs_r.total_fare,
            'nodes_explored': ucs_r.nodes_explored,
            'runtime_ms':     round((time_module.time() - t0) * 1000, 2),
            'algorithm':      'UCS (Dijkstra)',
            'meeting_node':   None,
            'segments':       ucs_r.segments,
        }

        # 2. Unidirectional A*
        try:
            astar_router = AStarRouter.__new__(AStarRouter)
            astar_router.stops  = self.router.stops
            astar_router.graph  = self.router.graph
            astar_router._vmax  = self.VMAX
            astar_router._vmax_kmh = self.VMAX_KMH
            t0 = time_module.time()
            astar_r = astar_router.find_route_astar(start_id, goal_id, metric, w1, w2, w3)
            results['astar'] = {
                'found':          astar_r.found,
                'total_time':     astar_r.total_time,
                'total_dist':     astar_r.total_dist,
                'total_co2':      astar_r.total_co2,
                'total_fare':     astar_r.total_fare,
                'nodes_explored': astar_r.nodes_explored,
                'runtime_ms':     round((time_module.time() - t0) * 1000, 2),
                'algorithm':      'A* (heuristic)',
                'meeting_node':   None,
                'segments':       astar_r.segments,
            }
        except Exception as e:
            results['astar'] = {'found': False, 'error': str(e),
                                 'algorithm': 'A*', 'nodes_explored': 0,
                                 'runtime_ms': 0}

        # 3–5. Bidirectional variants
        for algo in ('ucs', 'astar', 'greedy'):
            t0 = time_module.time()
            bd = self.search(start_id, goal_id, metric, algo, w1, w2, w3)
            label = f'bidir_{algo}'
            results[label] = {
                'found':          bd.found,
                'total_time':     bd.total_time,
                'total_dist':     bd.total_dist,
                'total_co2':      bd.total_co2,
                'total_fare':     bd.total_fare,
                'nodes_explored': bd.nodes_explored,
                'forward_nodes':  bd.forward_nodes,
                'backward_nodes': bd.backward_nodes,
                'runtime_ms':     bd.runtime_ms,
                'algorithm':      f'Bidir {algo.upper()}',
                'meeting_node':   bd.meeting_node,
                'segments':       bd.segments,
            }

        # ── Compute efficiency metrics ─────────────────────────
        ucs_nodes = results['ucs']['nodes_explored'] or 1
        for key, r in results.items():
            if key != 'ucs' and r.get('found'):
                r['node_reduction_pct'] = round(
                    (1 - r['nodes_explored'] / ucs_nodes) * 100, 1)
            else:
                r['node_reduction_pct'] = 0.0

        # Find winner (fewest nodes, found path)
        found_results = {k: v for k, v in results.items()
                         if v.get('found')}
        if found_results:
            winner = min(found_results,
                         key=lambda k: found_results[k]['nodes_explored'])
            results['_winner'] = winner
            results['_ucs_baseline_nodes'] = ucs_nodes
        else:
            results['_winner'] = None

        return results

    # ───────────────────────────────────────────────────────────
    # PRETTY PRINT REPORT
    # ───────────────────────────────────────────────────────────

    def print_report(self, report: Dict, start_id: str = '',
                     goal_id: str = '') -> None:
        """Print a formatted comparison report to stdout."""
        sep  = '═' * 100
        dash = '─' * 100

        print(f'\n{sep}')
        print(f'  ALGORITHM COMPARISON REPORT')
        if start_id and goal_id:
            sname = self.router.get_stop_name(start_id)
            gname = self.router.get_stop_name(goal_id)
            print(f'  Route: {sname}  →  {gname}')
        print(sep)

        header = (
            f"  {'Algorithm':<22} {'Found':>6} "
            f"{'Time(m)':>9} {'Dist(km)':>9} {'CO₂(g)':>8} "
            f"{'Fare(DA)':>9} {'Nodes':>8} {'Fwd':>6} {'Bwd':>6} "
            f"{'Runtime(ms)':>12} {'Reduction':>10} {'MeetNode':>15}"
        )
        print(header)
        print(dash)

        winner = report.get('_winner')
        order  = ['ucs', 'astar', 'bidir_ucs', 'bidir_astar', 'bidir_greedy']

        for key in order:
            r = report.get(key)
            if r is None:
                continue
            tag   = ' ★' if key == winner else '  '
            found = '✓' if r.get('found') else '✗'
            meet  = str(r.get('meeting_node') or '')[:14]
            fwd   = str(r.get('forward_nodes', ''))
            bwd   = str(r.get('backward_nodes', ''))
            red   = f"{r.get('node_reduction_pct', 0):+.1f}%"

            print(
                f"{tag}{r.get('algorithm',''):<22} {found:>6} "
                f"{r.get('total_time', 0):>9.1f} "
                f"{r.get('total_dist', 0):>9.3f} "
                f"{r.get('total_co2', 0):>8.1f} "
                f"{r.get('total_fare', 0):>9} "
                f"{r.get('nodes_explored', 0):>8,} "
                f"{fwd:>6} {bwd:>6} "
                f"{r.get('runtime_ms', 0):>12.2f} "
                f"{red:>10} "
                f"{meet:>15}"
            )

        print(dash)
        if winner:
            print(f"  ★ Winner (fewest nodes): {report[winner].get('algorithm')}")
            print(f"    Baseline (UCS) explored {report['_ucs_baseline_nodes']:,} nodes")
        print(sep)

    # ───────────────────────────────────────────────────────────
    # PRINT SINGLE RESULT (convenience)
    # ───────────────────────────────────────────────────────────

    def print_result(self, result: BiDirResult) -> None:
        """Pretty-print a single BiDirResult."""
        sep = '─' * 65
        print(sep)
        print(f"  {result.algorithm_used.upper()}")
        if not result.found:
            print("  ❌  No path found.")
            print(f"  Nodes explored: {result.nodes_explored:,}")
            print(sep)
            return
        print(f"  ✅  Found  |  {result.total_time:.1f} min  |  "
              f"{result.total_dist:.2f} km  |  {result.total_co2:.1f}g CO₂  |  "
              f"{result.total_fare} DA")
        print(f"  Nodes: {result.nodes_explored:,}  "
              f"(fwd: {result.forward_nodes}, bwd: {result.backward_nodes})")
        print(f"  Meeting node: {self.router.get_stop_name(result.meeting_node or '')}")
        print(f"  Runtime: {result.runtime_ms:.2f} ms")
        print()
        icons = {'metro':'🚇','tram':'🚊','bus':'🚌',
                 'train':'🚂','telepherique':'🚡','walk':'🚶'}
        for seg in result.segments:
            icon = icons.get(seg.transport_type, '•')
            fare = f" | {seg.fare} DA" if seg.fare > 0 else ""
            print(f"  {icon} {self.router.get_stop_name(seg.from_stop)}"
                  f" → {self.router.get_stop_name(seg.to_stop)}")
            print(f"     {seg.transport_type.upper()} {seg.route_id} | "
                  f"{seg.distance_km:.2f} km | {seg.time_min:.1f} min{fare}")
        print(sep)


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys
    from ucs import TransitRouter

    data_dir = sys.argv[1] if len(sys.argv) > 1 else 'data'

    print(f"Loading graph from {data_dir}...")
    t0 = time_module.time()
    router = TransitRouter(data_dir)
    print(f"  Loaded in {time_module.time()-t0:.2f}s: "
          f"{router.num_stops} stops, {router.num_edges} edges")

    bidir = BidirectionalSearch(router)
    print(f"  Reverse graph built: {sum(len(v) for v in bidir._rev_adj.values()):,} edges")

    # ── Demo queries ──────────────────────────────────────────
    queries = [
        ('M1_MARTYRS',  'TR01',       'time',     'Place des Martyrs → USTHB (Tram)'),
        ('M1_MARTYRS',  'M1_H_GARE',  'time',     'Place des Martyrs → El Harrach Gare'),
        ('M1_TAFOURAH', 'TR18',        'time',     'Tafourah → USTHB'),
        ('M1_1MAI',     'M1_HAMMA',   'distance', '1er Mai → El Hamma (by distance)'),
        ('M1_MARTYRS',  'TR01',       'weighted', 'Martyrs → USTHB (weighted: time+price+co2)'),
    ]

    for start, goal, metric, label in queries:
        print(f"\n{'─'*65}")
        print(f"  Query: {label}  |  metric={metric}")

        # Full comparison
        report = bidir.compare_all(start, goal, metric=metric,
                                   w1=0.5, w2=0.25, w3=0.25)
        bidir.print_report(report, start, goal)

        # Also show the bidirectional A* result in detail
        bd_astar = bidir.search(start, goal, metric, 'astar')
        print("\n  Bidirectional A* detail:")
        bidir.print_result(bd_astar)

    # ── Interactive mode ──────────────────────────────────────
    print("\n" + "="*65)
    print("  Interactive Bidirectional Search")
    print("="*65)

    while True:
        start = input("\nFrom (stop ID or name, 'q' to quit): ").strip()
        if start.lower() == 'q':
            break
        if start not in router.stops:
            matches = [(sid, s) for sid, s in router.stops.items()
                       if start.lower() in s.name.lower()]
            if not matches:
                print("  No stops found.")
                continue
            for sid, s in matches[:8]:
                print(f"    {sid:20s} {s.name:40s} ({s.transport_type})")
            start = input("  Enter stop ID: ").strip()

        goal = input("To (stop ID or name): ").strip()
        if goal not in router.stops:
            matches = [(sid, s) for sid, s in router.stops.items()
                       if goal.lower() in s.name.lower()]
            if not matches:
                print("  No stops found.")
                continue
            for sid, s in matches[:8]:
                print(f"    {sid:20s} {s.name:40s} ({s.transport_type})")
            goal = input("  Enter stop ID: ").strip()

        metric = input("Metric (time/distance/co2/weighted) [time]: ").strip() or 'time'
        algo   = input("Algorithm to pair with (ucs/astar/greedy) [astar]: ").strip() or 'astar'

        print(f"\nRunning bidirectional {algo.upper()}...")
        result = bidir.search(start, goal, metric, algo)
        bidir.print_result(result)

        run_compare = input("Run full comparison? (y/n) [n]: ").strip().lower()
        if run_compare == 'y':
            report = bidir.compare_all(start, goal, metric)
            bidir.print_report(report, start, goal)
