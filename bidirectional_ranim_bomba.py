"""
bidirectional.py — Bidirectional Search Framework for Algiers Transit Network

Architecture:
    BidirectionalSearch is a generic wrapper that can pair with ANY
    forward-search algorithm (UCS, A*, etc.) by accepting
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
    from bidirectional_ranim_bomba import BidirectionalSearch
    from ucs import TransitRouter
    from BFS_Yanis_ZA3IM import BFSRouter

    router = TransitRouter('data/')
    bfs    = BFSRouter('data/')
    bidir  = BidirectionalSearch(router, bfs_router=bfs)   # optional BFS graph

    bd = bidir.search_bfs('M1_MARTYRS', 'TR01', depart=8.0)

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
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, List, Tuple, Any

from ucs import TransitRouter, RouteResult, Segment, FARES, TRANSFER_PENALTY, Edge as UCSEdge

from BFS_Yanis_ZA3IM import BFSRouter as _BFSRouter, Edge as BFSEdge


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
    total_wait:      float = 0.0   # headway wait (min); bidir_bfs / optional


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

    The backward search uses a reversed graph (edges flipped).
    """

    VMAX_KMH = 70.0   # km/h — used in A* heuristic (metro top speed)
    VMAX     = VMAX_KMH / 60.0  # km/min

    def __init__(self, router: TransitRouter,
                 bfs_router: Optional[_BFSRouter] = None):
        if not isinstance(router, TransitRouter):
            raise TypeError("router must be a TransitRouter instance")
        self.router = router
        self._rev_adj = self._build_reverse_graph()
        self.bfs_router: Optional[_BFSRouter] = None
        self._bfs_rev_adj: Dict[str, List[BFSEdge]] = {}
        if bfs_router is not None:
            if not isinstance(bfs_router, _BFSRouter):
                raise TypeError("bfs_router must be a BFSRouter instance")
            self.bfs_router = bfs_router
            self._bfs_rev_adj = self._build_bfs_reverse_graph()

    # ───────────────────────────────────────────────────────────
    # BFS GRAPH (BFS_Yanis_ZA3IM) — reversed adjacency
    # ───────────────────────────────────────────────────────────

    def _build_bfs_reverse_graph(self) -> Dict[str, List[BFSEdge]]:
        """Flip each BFS edge u→v to v→u (same Edge fields; ``to_id`` is the predecessor)."""
        if not self.bfs_router:
            return {}
        rev: Dict[str, List[BFSEdge]] = defaultdict(list)
        for u, edges in self.bfs_router.graph.items():
            for e in edges:
                rev[e.to_id].append(BFSEdge(
                    to_id=u,
                    time_min=e.time_min,
                    distance_km=e.distance_km,
                    transport_type=e.transport_type,
                    route_id=e.route_id,
                    co2_g=e.co2_g,
                ))
        return dict(rev)

    def _bfs_forward_edge(self, fr: str, to: str) -> Optional[BFSEdge]:
        for e in self.bfs_router.graph.get(fr, []):
            if e.to_id == to:
                return e
        return None

    # ───────────────────────────────────────────────────────────
    # REVERSE GRAPH
    # ───────────────────────────────────────────────────────────

    def _build_reverse_graph(self) -> Dict[str, List]:
        """
        Build a reversed adjacency list for backward search.
        Every edge (u→v) becomes (v→u) in the reverse graph.
        Edge attributes (cost, time, co2) remain the same.
        """
        rev = {sid: [] for sid in self.router.stops}
        for from_id, edges in self.router.graph.items():
            for e in edges:
                if e.to_id in rev:
                    rev[e.to_id].append(UCSEdge(
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
                              goal_id: str) -> Tuple[List[str], List[UCSEdge]]:
        """
        Reconstruct path from meeting node → goal.
        The backward search expanded from goal on the reversed graph; walk
        predecessors from the meeting state toward goal, then re-orient edges.
        """
        path, edges = [], []
        cur = meeting_state
        while cur is not None:
            prev_state, edge = pred.get(cur, (None, None))
            if edge is not None:
                path.append(edge.to_id)
                edges.append(edge)
            cur = prev_state
        path.append(goal_id)
        path.reverse()
        edges.reverse()
        fwd_edges: List[UCSEdge] = []
        for e in edges:
            fwd_edges.append(UCSEdge(
                to_id=e.to_id,
                distance_km=e.distance_km,
                time_min=e.time_min,
                co2_g=e.co2_g,
                transport_type=e.transport_type,
                route_id=e.route_id,
            ))
        return path, fwd_edges

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

        # O(1) meeting detection: best g-cost seen per bare node_id
        fwd_node_g: Dict[str, float] = {start_id: 0.0}
        bwd_node_g: Dict[str, float] = {goal_id: 0.0}

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

                # Check if this node was reached by backward search (skip if none yet)
                if node in bwd_node_g:
                    for bwd_state, bwd_g_val in list(bwd_g.items()):
                        if bwd_state[0] != node:
                            continue
                        total_cost = fwd_g.get(state, float('inf')) + bwd_g_val
                        fwd_route = state[1]
                        bwd_route = bwd_state[1]
                        if (fwd_route is not None and bwd_route is not None
                                and fwd_route != bwd_route):
                            total_cost += TRANSFER_PENALTY.get(metric, 0.0)
                        if total_cost < mu:
                            mu = total_cost
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
                        if new_g < fwd_node_g.get(edge.to_id, float('inf')):
                            fwd_node_g[edge.to_id] = new_g

            # ── BACKWARD EXPANSION ────────────────────────────
            else:
                f, _, node, last_route = heapq.heappop(bwd_heap)
                state = (node, last_route)
                if state in bwd_vis:
                    continue
                bwd_vis.add(state)
                bwd_nodes += 1

                # Check if forward search reached this node (skip if none yet)
                if node in fwd_node_g:
                    for fwd_state, fwd_g_val in list(fwd_g.items()):
                        if fwd_state[0] != node:
                            continue
                        total_cost = fwd_g_val + bwd_g.get(state, float('inf'))
                        fwd_route = fwd_state[1]
                        bwd_route = state[1]
                        if (fwd_route is not None and bwd_route is not None
                                and fwd_route != bwd_route):
                            total_cost += TRANSFER_PENALTY.get(metric, 0.0)
                        if total_cost < mu:
                            mu = total_cost
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
                        if new_g < bwd_node_g.get(edge.to_id, float('inf')):
                            bwd_node_g[edge.to_id] = new_g

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

        # Merge paths (drop duplicate meeting stop)
        full_path  = fwd_path[:-1] + bwd_path
        full_edges = fwd_edges + bwd_edges

        # Remove loops from the path (which can occur when bidirectional frontiers overlap)
        dedup_path = []
        dedup_edges = []
        seen = {}
        for i, p in enumerate(full_path):
            if p in seen:
                # Loop detected! Backtrack to the previous occurrence
                loop_start = seen[p]
                dedup_path = dedup_path[:loop_start + 1]
                dedup_edges = dedup_edges[:loop_start]
                # Rebuild seen dictionary
                seen = {node: idx for idx, node in enumerate(dedup_path)}
            else:
                dedup_path.append(p)
                seen[p] = len(dedup_path) - 1
                if i > 0 and i - 1 < len(full_edges):
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
            algorithm: 'ucs' | 'astar'
            w1, w2, w3: weights for weighted metric

        Returns:
            BiDirResult
        """
        algo_map = {
            'ucs':   (self._heuristic_ucs,   'bidir_ucs'),
            'astar': (self._heuristic_astar, 'bidir_astar'),
        }
        if algorithm not in algo_map:
            raise ValueError(
                f"Unknown algorithm '{algorithm}'. "
                f"Choose from: {list(algo_map.keys())}"
            )
        hfn, label = algo_map[algorithm]
        return self._bidir_search(start_id, goal_id, metric,
                                  hfn, w1, w2, w3, label)

    def search_bfs(self, start_id: str, goal_id: str,
                    depart: float = 8.0) -> BiDirResult:
        """
        Bidirectional BFS on ``bfs_router.graph`` / ``_bfs_rev_adj``:
        same hop-expansion model as ``BFSRouter.search`` (FIFO per side,
        working-hours + average wait), alternating one forward node then one backward node.
        """
        if not self.bfs_router:
            raise RuntimeError(
                "BidirectionalSearch was constructed without bfs_router=… "
                "Pass BFSRouter(data_dir) to enable search_bfs."
            )

        t0 = time_module.time()
        start_id = start_id.strip()
        goal_id = goal_id.strip()

        if start_id not in self.bfs_router.stops or goal_id not in self.bfs_router.stops:
            rt = (time_module.time() - t0) * 1000
            return BiDirResult(
                found=False, path=[], edges=[], segments=[],
                total_time=0, total_dist=0, total_co2=0, total_fare=0,
                nodes_explored=0, forward_nodes=0, backward_nodes=0,
                meeting_node=None, algorithm_used='bidir_bfs',
                runtime_ms=round(rt, 2), total_wait=0.0,
            )

        if start_id == goal_id:
            return BiDirResult(
                found=True, path=[start_id], edges=[], segments=[],
                total_time=0, total_dist=0, total_co2=0, total_fare=0,
                nodes_explored=0, forward_nodes=0, backward_nodes=0,
                meeting_node=start_id, algorithm_used='bidir_bfs',
                runtime_ms=0.0, total_wait=0.0,
            )

        if not (0.0 <= depart < 24.0):
            raise ValueError(f"depart must be in [0.0, 24.0), got {depart}")

        depart_f = float(depart)
        visited_fwd: Dict[str, Tuple[Optional[str], Optional[BFSEdge], float]] = {}
        visited_bwd: Dict[str, Tuple[Optional[str], Optional[BFSEdge], float]] = {}
        visited_fwd[start_id] = (None, None, depart_f)
        visited_bwd[goal_id] = (None, None, depart_f)

        fwd_q: deque[Tuple[str, float, Optional[str], Optional[str]]] = deque(
            [(start_id, depart_f, None, None)]
        )
        bwd_q: deque[Tuple[str, float, Optional[str], Optional[str]]] = deque(
            [(goal_id, depart_f, None, None)]
        )

        meeting: Optional[str] = None
        fwd_n = 0
        bwd_n = 0

        while fwd_q and bwd_q and meeting is None:
            # ── one forward expansion ──────────────────────────
            nid, clock, _pm, _pr = fwd_q.popleft()
            fwd_n += 1

            for edge in self.bfs_router.graph.get(nid, []):
                nb = edge.to_id
                if nb in visited_fwd:
                    continue
                if not self.bfs_router._in_service(edge.transport_type, clock):
                    continue
                w = self.bfs_router._avg_wait(edge.transport_type)
                new_c = clock + (edge.time_min + w) / 60.0
                visited_fwd[nb] = (nid, edge, new_c)
                if nb in visited_bwd:
                    meeting = nb
                    break
                fwd_q.append((nb, new_c, edge.transport_type, edge.route_id))

            if meeting is not None:
                break

            if not fwd_q or not bwd_q:
                break

            # ── one backward expansion ─────────────────────────
            nid, clock, _pm, _pr = bwd_q.popleft()
            bwd_n += 1

            for e in self._bfs_rev_adj.get(nid, []):
                pred = e.to_id
                fe = self._bfs_forward_edge(pred, nid)
                if fe is None:
                    continue
                if pred in visited_bwd:
                    continue
                if not self.bfs_router._in_service(fe.transport_type, clock):
                    continue
                w = self.bfs_router._avg_wait(fe.transport_type)
                new_c = clock + (fe.time_min + w) / 60.0
                visited_bwd[pred] = (nid, fe, new_c)
                if pred in visited_fwd:
                    meeting = pred
                    break
                bwd_q.append((pred, new_c, fe.transport_type, fe.route_id))

        rt_ms = round((time_module.time() - t0) * 1000, 2)

        if meeting is None:
            return BiDirResult(
                found=False, path=[], edges=[], segments=[],
                total_time=0, total_dist=0, total_co2=0, total_fare=0,
                nodes_explored=fwd_n + bwd_n,
                forward_nodes=fwd_n, backward_nodes=bwd_n,
                meeting_node=None, algorithm_used='bidir_bfs',
                runtime_ms=rt_ms, total_wait=0.0,
            )

        # Reconstruct start → meeting
        edges_fwd: List[BFSEdge] = []
        cur = meeting
        while cur != start_id:
            parent, edge, _ = visited_fwd[cur]
            if edge is None or parent is None:
                break
            edges_fwd.append(edge)
            cur = parent
        edges_fwd.reverse()

        # Reconstruct meeting → goal (forward edges along visited_bwd chain)
        edges_bwd: List[BFSEdge] = []
        cur = meeting
        while cur != goal_id:
            nxt, edge, _ = visited_bwd[cur]
            if nxt is None or edge is None:
                break
            edges_bwd.append(edge)
            cur = nxt

        full_edges = edges_fwd + edges_bwd
        path_ids = [start_id]
        for e in edges_fwd:
            path_ids.append(e.to_id)
        for e in edges_bwd:
            path_ids.append(e.to_id)

        ride = wait = co2 = dist = 0.0
        prev_mode: Optional[str] = None
        prev_route: Optional[str] = None
        fare_f = 0.0

        for edge in full_edges:
            mode = edge.transport_type
            w = self.bfs_router._avg_wait(mode)
            fare_f += self.bfs_router._fare(edge, prev_mode, prev_route)
            ride += edge.time_min
            wait += w
            co2 += edge.co2_g
            dist += edge.distance_km
            prev_mode = mode
            prev_route = edge.route_id

        return BiDirResult(
            found=True,
            path=path_ids,
            edges=full_edges,
            segments=[],
            total_time=round(ride, 2),
            total_dist=round(dist, 4),
            total_co2=round(co2, 2),
            total_fare=int(round(fare_f)),
            nodes_explored=fwd_n + bwd_n,
            forward_nodes=fwd_n,
            backward_nodes=bwd_n,
            meeting_node=meeting,
            algorithm_used='bidir_bfs',
            runtime_ms=rt_ms,
            total_wait=round(wait, 2),
        )

    # ───────────────────────────────────────────────────────────
    # COMPARE ALL ALGORITHMS
    # ───────────────────────────────────────────────────────────

    def compare_all(self, start_id: str, goal_id: str,
                    metric: str = 'time',
                    w1: float = 1.0, w2: float = 0.0,
                    w3: float = 0.0,
                    depart: float = 8.0) -> Dict[str, Any]:
        """
        Run UCS / A* / bidirectional UCS and A* on ``TransitRouter``, and optionally
        bidirectional BFS on ``BFSRouter`` when ``bfs_router`` was passed to the constructor.

        Algorithms compared:
            3. Bidirectional UCS  (bidir + Dijkstra)
            4. Bidirectional A*   (bidir + A*)

        ``depart`` is the departure clock hour [0, 24) for ``search_bfs`` (default 8.0).

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

        # 3–4. Bidirectional variants
        for algo in ('ucs', 'astar'):
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

        if self.bfs_router:
            bd_bfs = self.search_bfs(start_id, goal_id, depart=depart)
            journey = bd_bfs.total_time + bd_bfs.total_wait
            results['bidir_bfs'] = {
                'found':              bd_bfs.found,
                'total_time':         bd_bfs.total_time,
                'total_wait':         bd_bfs.total_wait,
                'total_journey_time': journey,
                'total_dist':         bd_bfs.total_dist,
                'total_co2':          bd_bfs.total_co2,
                'total_fare':         bd_bfs.total_fare,
                'nodes_explored':     bd_bfs.nodes_explored,
                'forward_nodes':      bd_bfs.forward_nodes,
                'backward_nodes':     bd_bfs.backward_nodes,
                'runtime_ms':         bd_bfs.runtime_ms,
                'algorithm':          'Bidir BFS',
                'meeting_node':       bd_bfs.meeting_node,
                'segments':           [],
            }

        # ── Compute efficiency metrics ─────────────────────────
        ucs_nodes = results['ucs']['nodes_explored'] or 1
        for key, r in results.items():
            if key.startswith('_'):
                continue
            if key != 'ucs' and r.get('found'):
                r['node_reduction_pct'] = round(
                    (1 - r['nodes_explored'] / ucs_nodes) * 100, 1)
            else:
                r['node_reduction_pct'] = 0.0

        # Find winner (fewest nodes, found path)
        found_results = {k: v for k, v in results.items()
                         if not k.startswith('_') and v.get('found')}
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
        order  = ['ucs', 'astar', 'bidir_ucs', 'bidir_astar', 'bidir_bfs']

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
            tshow = r.get('total_journey_time', r.get('total_time', 0))

            print(
                f"{tag}{r.get('algorithm',''):<22} {found:>6} "
                f"{tshow:>9.1f} "
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
        journey = result.total_time + result.total_wait
        print(f"  ✅  Found  |  ride {result.total_time:.1f} min  |  "
              f"wait {result.total_wait:.1f} min  |  total {journey:.1f} min  |  "
              f"{result.total_dist:.2f} km  |  {result.total_co2:.1f}g CO₂  |  "
              f"{result.total_fare} DA")
        print(f"  Nodes: {result.nodes_explored:,}  "
              f"(fwd: {result.forward_nodes}, bwd: {result.backward_nodes})")
        print(f"  Meeting node: {self.router.get_stop_name(result.meeting_node or '')}")
        print(f"  Runtime: {result.runtime_ms:.2f} ms")
        print()
        icons = {'metro':'🚇','tram':'🚊','bus':'🚌',
                 'train':'🚂','telepherique':'🚡','walk':'🚶'}
        name_fn = (
            self.bfs_router.stop_name
            if result.algorithm_used == 'bidir_bfs' and self.bfs_router
            else self.router.get_stop_name
        )
        if result.segments:
            for seg in result.segments:
                icon = icons.get(seg.transport_type, '•')
                fare = f" | {seg.fare} DA" if seg.fare > 0 else ""
                print(f"  {icon} {name_fn(seg.from_stop)}"
                      f" → {name_fn(seg.to_stop)}")
                print(f"     {seg.transport_type.upper()} {seg.route_id} | "
                      f"{seg.distance_km:.2f} km | {seg.time_min:.1f} min{fare}")
        elif result.edges and result.path:
            for i, edge in enumerate(result.edges):
                a = result.path[i]
                b = result.path[i + 1]
                icon = icons.get(edge.transport_type, '•')
                print(f"  {icon} {name_fn(a)} → {name_fn(b)}")
                print(f"     {edge.transport_type.upper()} {edge.route_id} | "
                      f"{edge.distance_km:.2f} km | {edge.time_min:.1f} min")
        print(sep)


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys
    from ucs import TransitRouter
    from BFS_Yanis_ZA3IM import BFSRouter

    data_dir = sys.argv[1] if len(sys.argv) > 1 else 'data'

    print(f"Loading graph from {data_dir}...")
    t0 = time_module.time()
    router = TransitRouter(data_dir)
    print(f"  Loaded in {time_module.time()-t0:.2f}s: "
          f"{router.num_stops} stops, {router.num_edges} edges")

    bfs_router = BFSRouter(data_dir)
    bidir = BidirectionalSearch(router, bfs_router=bfs_router)
    print(f"  Reverse graph built: {sum(len(v) for v in bidir._rev_adj.values()):,} edges")
    print(f"  BFS graph + rev: {sum(len(v) for v in bidir._bfs_rev_adj.values()):,} rev edges")

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
        algo   = input("Algorithm to pair with (ucs/astar) [astar]: ").strip() or 'astar'

        print(f"\nRunning bidirectional {algo.upper()}...")
        result = bidir.search(start, goal, metric, algo)
        bidir.print_result(result)

        run_compare = input("Run full comparison? (y/n) [n]: ").strip().lower()
        if run_compare == 'y':
            report = bidir.compare_all(start, goal, metric)
            bidir.print_report(report, start, goal)
