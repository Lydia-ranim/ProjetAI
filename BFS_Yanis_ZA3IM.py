

from __future__ import annotations

import heapq
import math
import os
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from matplotlib.gridspec import GridSpec

import json

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Data')

STOPS_CSV          = os.path.join(DATA_DIR, 'stops.csv')
EDGES_CSV          = os.path.join(DATA_DIR, 'edges.csv')
TRANSFERS_CSV      = os.path.join(DATA_DIR, 'transfers.csv')
BUS_GEOMETRIES_JSON = os.path.join(DATA_DIR, 'bus_geometries.json')

class TransportMode(Enum):
    WALK         = 'walk'
    BUS          = 'bus'
    TRAM         = 'tram'
    METRO        = 'metro'
    TRAIN        = 'train'
    TELEPHERIQUE = 'telepherique'

    @classmethod
    def from_string(cls, s: str) -> 'TransportMode':
        s = s.strip().lower()
        mapping = {
            'cable_car':    cls.TELEPHERIQUE,
            'telepherique': cls.TELEPHERIQUE,
            'escalator':    cls.WALK,
        }
        if s in mapping:
            return mapping[s]
        for member in cls:
            if member.value == s:
                return member
        raise ValueError(f"Unknown transport mode '{s}'. Valid: {[m.value for m in cls]}")


PRICE_DA: Dict[str, float] = {
    'walk':          0.0,
    'bus':          25.0,
    'tram':         50.0,
    'metro':        50.0,
    'train':        75.0,
    'telepherique': 30.0,
}

CO2_FACTORS: Dict[str, float] = {
    'walk':          0.0,
    'bus':          68.0,
    'tram':          6.0,
    'metro':         4.0,
    'train':        41.0,
    'telepherique':  6.0,
}

MODE_COLORS: Dict[str, str] = {
    'walk':         '#A8DADC',
    'bus':          '#E76F51',
    'tram':         '#2A9D8F',
    'metro':        '#457B9D',
    'train':        '#E9C46A',
    'telepherique': '#9B72CF',
}

MODE_ICONS: Dict[str, str] = {
    'walk':         '🚶',
    'bus':          '🚌',
    'tram':         '🚃',
    'metro':        '🚇',
    'train':        '🚆',
    'telepherique': '🚡',
}

FREE_MODES = {TransportMode.WALK}

BG_DARK   = '#0A0E1A'
BG_PANEL  = '#111827'
BG_CARD   = '#1C2333'
ACCENT    = '#4F8EF7'
ACCENT2   = '#A78BFA'
TEXT_MAIN = '#E2E8F0'
TEXT_DIM  = '#64748B'
GRID_COL  = '#1E293B'


class ModeConfig:
    ALL_MODES: Set[TransportMode] = set(TransportMode)

    def __init__(self, enabled: Optional[Set[TransportMode]] = None):
        self._enabled: Set[TransportMode] = (
            set(enabled) if enabled is not None else set(self.ALL_MODES)
        )

    def enable(self, *modes: TransportMode) -> 'ModeConfig':
        for m in modes:
            self._enabled.add(m)
        return self

    def disable(self, *modes: TransportMode) -> 'ModeConfig':
        for m in modes:
            self._enabled.discard(m)
        return self

    def is_allowed(self, mode: TransportMode) -> bool:
        return mode in self._enabled

    @property
    def active_modes(self) -> Set[TransportMode]:
        return set(self._enabled)

    @classmethod
    def all(cls) -> 'ModeConfig':
        return cls()

    @classmethod
    def only(cls, *modes: TransportMode) -> 'ModeConfig':
        return cls(set(modes))

    @classmethod
    def without(cls, *modes: TransportMode) -> 'ModeConfig':
        return cls(cls.ALL_MODES - set(modes))

    def __repr__(self):
        return f"ModeConfig(enabled={sorted(m.value for m in self._enabled)})"


@dataclass
class Node:
    node_id   : str
    name      : str
    node_type : str
    lat       : float
    lon       : float
    is_hub    : bool = False

    def haversine_km(self, other: 'Node') -> float:
        R = 6371.0
        phi1 = math.radians(self.lat)
        phi2 = math.radians(other.lat)
        dlat = math.radians(other.lat - self.lat)
        dlon = math.radians(other.lon - self.lon)
        a = (math.sin(dlat / 2) ** 2
             + math.cos(phi1) * math.cos(phi2) * math.sin(dlon / 2) ** 2)
        return R * 2 * math.asin(math.sqrt(a))

    def __hash__(self):  return hash(self.node_id)
    def __eq__(self, o): return isinstance(o, Node) and self.node_id == o.node_id
    def __repr__(self):  return f"Node({self.node_id!r}, {self.name!r})"


@dataclass
class Edge:
    from_node   : Node
    to_node     : Node
    mode        : TransportMode
    distance_km : float
    time_min    : float
    price_da    : float
    co2_g       : float
    route_id    : str = ''

    def weighted_cost(
        self,
        w_time : float = 1.0,
        w_price: float = 0.0,
        w_co2  : float = 0.0,
    ) -> float:
        total = w_time + w_price + w_co2
        if total == 0:
            raise ValueError("At least one weight must be non-zero.")
        wt, wp, wc = w_time / total, w_price / total, w_co2 / total
        return wt * self.time_min + wp * self.price_da + wc * self.co2_g

    def __repr__(self):
        return (f"Edge({self.from_node.name!r} → {self.to_node.name!r}, "
                f"{self.mode.value}, {self.time_min:.1f}m)")


class TransitGraph:
    def __init__(self):
        self._nodes     : Dict[str, Node]       = {}
        self._adj       : Dict[str, List[Edge]] = {}
        self._bus_geom  : Dict[str, List]       = {}   # key → [[lat,lon],...]

    def add_node(self, node: Node) -> None:
        if node.node_id in self._nodes:
            return
        self._nodes[node.node_id] = node
        self._adj[node.node_id]   = []

    def add_edge(self, edge: Edge) -> None:
        if edge.from_node.node_id not in self._nodes:
            raise KeyError(f"Source node '{edge.from_node.node_id}' not in graph.")
        if edge.to_node.node_id not in self._nodes:
            raise KeyError(f"Dest node '{edge.to_node.node_id}' not in graph.")
        self._adj[edge.from_node.node_id].append(edge)

    def get_node(self, node_id: str) -> Node:
        if node_id not in self._nodes:
            raise KeyError(f"Node '{node_id}' not found.")
        return self._nodes[node_id]

    def find_node_by_name(self, name: str) -> Optional[Node]:
        name_lower = name.strip().lower()
        for node in self._nodes.values():
            if node.name.strip().lower() == name_lower:
                return node
        for node in self._nodes.values():
            if name_lower in node.name.strip().lower():
                return node
        return None

    def get_neighbors(self, node_id: str) -> List[Edge]:
        return self._adj.get(node_id, [])

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return sum(len(e) for e in self._adj.values())

    def get_bus_geometry(self, edge: Edge) -> Optional[List]:
        if edge.mode != TransportMode.BUS:
            return None
        key = f"{edge.from_node.node_id}|{edge.to_node.node_id}|{edge.route_id}"
        return self._bus_geom.get(key)

    @classmethod
    def from_csvs(
        cls,
        stops_csv     : str,
        edges_csv     : str,
        transfers_csv : str,
        bus_geom_json : str = '',
    ) -> 'TransitGraph':
        for path in [stops_csv, edges_csv, transfers_csv]:
            if not os.path.isfile(path):
                raise FileNotFoundError(f"File not found: '{path}'")

        graph = cls()

        stops_df = pd.read_csv(stops_csv, encoding='utf-8-sig')
        stops_df.columns = stops_df.columns.str.strip()

        for _, row in stops_df.iterrows():
            try:
                is_hub_val = row.get('is_hub', False)
                if isinstance(is_hub_val, str):
                    is_hub = is_hub_val.strip().lower() in ('true', '1', 'yes')
                else:
                    is_hub = bool(is_hub_val)

                graph.add_node(Node(
                    node_id   = str(row['stop_id']).strip(),
                    name      = str(row['stop_name']).strip(),
                    node_type = str(row['transport_type']).strip(),
                    lat       = float(row['latitude']),
                    lon       = float(row['longitude']),
                    is_hub    = is_hub,
                ))
            except Exception as e:
                print(f"  [WARN] Skipping stop row: {e}")

        edges_df = pd.read_csv(edges_csv, encoding='utf-8-sig')
        edges_df.columns = edges_df.columns.str.strip()
        skipped = 0

        for _, row in edges_df.iterrows():
            try:
                from_id = str(row['from_stop_id']).strip()
                to_id   = str(row['to_stop_id']).strip()
                mode    = TransportMode.from_string(str(row['transport_type']))
                price   = PRICE_DA.get(mode.value, 0.0)

                if 'co2_g' in row and not pd.isna(row['co2_g']):
                    co2 = float(row['co2_g'])
                else:
                    co2 = CO2_FACTORS.get(mode.value, 0.0)

                if from_id not in graph._nodes or to_id not in graph._nodes:
                    skipped += 1
                    continue

                graph.add_edge(Edge(
                    from_node   = graph.get_node(from_id),
                    to_node     = graph.get_node(to_id),
                    mode        = mode,
                    distance_km = float(row['distance_km']),
                    time_min    = float(row['time_min']),
                    price_da    = price,
                    co2_g       = co2,
                    route_id    = str(row.get('route_id', '')).strip(),
                ))
            except Exception as e:
                skipped += 1

        transfers_df = pd.read_csv(transfers_csv, encoding='utf-8-sig')
        transfers_df.columns = transfers_df.columns.str.strip()
        t_skipped = 0

        for _, row in transfers_df.iterrows():
            try:
                from_id = str(row['from_stop_id']).strip()
                to_id   = str(row['to_stop_id']).strip()
                    continue
                if from_id not in graph._nodes or to_id not in graph._nodes:
                    t_skipped += 1
                    continue
                graph.add_edge(Edge(
                    from_node   = graph.get_node(from_id),
                    to_node     = graph.get_node(to_id),
                    mode        = TransportMode.WALK,
                    distance_km = float(row['distance_km']),
                    time_min    = float(row['total_time_min']),
                    price_da    = 0.0,
                    co2_g       = 0.0,
                    route_id    = 'TRANSFER',
                ))
            except Exception as e:
                t_skipped += 1


        if geom_path and os.path.isfile(geom_path):
            with open(geom_path, encoding='utf-8') as fh:
                graph._bus_geom = json.load(fh)
            print(f"[Graph] Loaded {len(graph._bus_geom):,} bus geometry polylines")
        else:
            print("[Graph] bus_geometries.json not found – bus edges will be straight lines")

        print(f"[Graph] Loaded {graph.node_count()} stops, {graph.edge_count()} edges")
        print(f"[Graph] Skipped {skipped} transit edges, {t_skipped} transfer edges")
        return graph

    def summary(self) -> None:
        mode_counts: Dict[str, int]   = {}
        mode_time  : Dict[str, float] = {}
        for edges in self._adj.values():
            for e in edges:
                k = e.mode.value
                mode_counts[k] = mode_counts.get(k, 0) + 1
                mode_time[k]   = mode_time.get(k, 0.0) + e.time_min

        print(f"\n{'═'*55}")
        print(f"  Algiers Transit Graph Summary")
        print(f"{'═'*55}")
        print(f"  Stops   : {self.node_count():>6,}")
        print(f"  Edges   : {self.edge_count():>6,}")
        print(f"  Bus polylines : {len(self._bus_geom):>5,}")
        print(f"  {'Mode':<14} {'Edges':>7}  {'Avg time (min)':>15}")
        print(f"  {'─'*40}")
        for mode, count in sorted(mode_counts.items()):
            avg  = mode_time[mode] / count
            icon = MODE_ICONS.get(mode, '?')
            print(f"  {icon} {mode:<12} {count:>7,}  {avg:>14.2f}")
        print(f"{'═'*55}\n")

    def __repr__(self):
        return f"TransitGraph(stops={self.node_count()}, edges={self.edge_count()})"


@dataclass
class _ChainState:
    node          : Node
    edge          : Optional[Edge]          # edge that led here (None for start)
    parent        : Optional['_ChainState'] # back-pointer
    total_time    : float = 0.0
    total_price   : float = 0.0
    total_co2     : float = 0.0
    num_transfers : int   = 0
    hops          : int   = 0

    def __lt__(self, other: '_ChainState') -> bool:
        return self.total_time < other.total_time

    @property
    def current_mode(self) -> Optional[TransportMode]:
        return self.edge.mode if self.edge else None

    def extract_edges(self) -> List[Edge]:
        edges = []
        state = self
        while state.edge is not None:
            edges.append(state.edge)
            state = state.parent
        edges.reverse()
        return edges


def _count_transfer(prev_mode: Optional[TransportMode], next_mode: TransportMode) -> int:
    if (prev_mode is not None
            and next_mode != prev_mode
            and next_mode not in FREE_MODES
            and prev_mode not in FREE_MODES):
        return 1
    return 0


@dataclass
class BFSResult:
    found          : bool
    start          : Node
    goal           : Node
    path_edges     : List[Edge] = field(default_factory=list)
    total_time     : float = 0.0
    total_price    : float = 0.0
    total_co2      : float = 0.0
    num_transfers  : int   = 0
    nodes_expanded : int   = 0
    nodes_visited  : int   = 0
    algorithm      : str   = 'bfs'

    @property
    def hops(self) -> int:
        return len(self.path_edges)

    @property
    def path_nodes(self) -> List[Node]:
        if not self.path_edges:
            return [self.start] if self.found else []
        nodes = [self.path_edges[0].from_node]
        for e in self.path_edges:
            nodes.append(e.to_node)
        return nodes

    @property
    def mode_breakdown(self) -> Dict[str, float]:
        breakdown: Dict[str, float] = {}
        for e in self.path_edges:
            k = e.mode.value
            breakdown[k] = breakdown.get(k, 0.0) + e.time_min
        return breakdown

    @property
    def mode_usage_pct(self) -> Dict[str, float]:
        bd    = self.mode_breakdown
        total = sum(bd.values())
        if total == 0:
            return {}
        return {k: v / total * 100 for k, v in bd.items()}

    def print_summary(self) -> None:
        sep = '═' * 65
        print(sep)
        print(f"  {self.algorithm.upper()} Result  │  {self.start.name}  →  {self.goal.name}")
        print(sep)
        if not self.found:
            print("  ✗  No path found.")
            print(f"  Nodes expanded : {self.nodes_expanded}")
            print(sep)
            return
        print(f"  ✓  Path found  │  {self.hops} hop(s)  │  {self.num_transfers} transfer(s)")
        print()
        for i, edge in enumerate(self.path_edges, 1):
            icon = MODE_ICONS.get(edge.mode.value, '?')
            print(f"  {i:>2}. {icon} [{edge.mode.value.upper():<12}] "
                  f"{edge.from_node.name:<28} → {edge.to_node.name}")
            print(f"       {edge.time_min:>5.1f} min  │  {edge.price_da:>4.0f} DA  │  "
                  f"{edge.co2_g:>5.1f} g CO₂  │  {edge.distance_km:.2f} km")
        print()
        print(f"  {'TOTAL':<35} {self.total_time:>6.1f} min  │  "
              f"{self.total_price:>4.0f} DA  │  {self.total_co2:>5.1f} g CO₂")
        print()
        print("  Mode usage (% of travel time):")
        for mode, pct in sorted(self.mode_usage_pct.items(), key=lambda x: -x[1]):
            icon = MODE_ICONS.get(mode, '?')
            bar  = '█' * int(pct / 5)
            print(f"    {icon} {mode:<14} {pct:>5.1f}%  {bar}")
        print()
        print(f"  Nodes expanded : {self.nodes_expanded}")
        print(f"  Nodes visited  : {self.nodes_visited}")
        print(sep)


def _make_result(
    state     : _ChainState,
    start     : Node,
    goal      : Node,
    n_exp     : int,
    n_vis     : int,
    algorithm : str,
) -> BFSResult:
    edges = state.extract_edges()
    return BFSResult(
        found=True, start=start, goal=goal,
        path_edges    = edges,
        total_time    = state.total_time,
        total_price   = state.total_price,
        total_co2     = state.total_co2,
        num_transfers = state.num_transfers,
        nodes_expanded= n_exp,
        nodes_visited = n_vis,
        algorithm     = algorithm,
    )


class BFSRouter:
    def __init__(self, graph: TransitGraph):
        self.graph = graph

    def _validate(self, start_id: str, goal_id: str) -> Tuple[Node, Node]:
        start = self.graph.get_node(start_id)
        goal  = self.graph.get_node(goal_id)
        if start_id == goal_id:
            raise ValueError(f"Start and goal are the same: '{start.name}'")
        return start, goal

    def bfs_min_hops(
        self,
        start_id    : str,
        goal_id     : str,
        mode_config : Optional[ModeConfig] = None,
    ) -> BFSResult:
        start, goal = self._validate(start_id, goal_id)
        cfg         = mode_config or ModeConfig.all()

        init  = _ChainState(node=start, edge=None, parent=None)
        queue : deque[_ChainState] = deque([init])
        visited: Set[str]          = {start_id}
        n_exp = 0

        while queue:
            state = queue.popleft()
            n_exp += 1

            for edge in self.graph.get_neighbors(state.node.node_id):
                if not cfg.is_allowed(edge.mode):
                    continue
                nid = edge.to_node.node_id
                if nid in visited:
                    continue

                xfer = _count_transfer(state.current_mode, edge.mode)
                nxt  = _ChainState(
                    node          = edge.to_node,
                    edge          = edge,
                    parent        = state,
                    total_time    = state.total_time  + edge.time_min,
                    total_price   = state.total_price + edge.price_da,
                    total_co2     = state.total_co2   + edge.co2_g,
                    num_transfers = state.num_transfers + xfer,
                    hops          = state.hops + 1,
                )
                if nid == goal_id:
                    return _make_result(nxt, start, goal, n_exp, len(visited), 'bfs_min_hops')
                visited.add(nid)
                queue.append(nxt)

        return BFSResult(found=False, start=start, goal=goal,
                         nodes_expanded=n_exp, nodes_visited=len(visited),
                         algorithm='bfs_min_hops')

    def bfs_min_transfers(
        self,
        start_id    : str,
        goal_id     : str,
        mode_config : Optional[ModeConfig] = None,
    ) -> BFSResult:
        start, goal = self._validate(start_id, goal_id)
        cfg         = mode_config or ModeConfig.all()

        init  = _ChainState(node=start, edge=None, parent=None)
        queue : deque[_ChainState] = deque([init])
        # key = (node_id, mode) so we re-visit a node via a different mode
        visited: Set[Tuple[str, Optional[str]]] = {(start_id, None)}
        best  : Optional[BFSResult] = None
        n_exp = 0

        while queue:
            state = queue.popleft()
            n_exp += 1

            if best is not None and state.num_transfers >= best.num_transfers:
                continue

            for edge in self.graph.get_neighbors(state.node.node_id):
                if not cfg.is_allowed(edge.mode):
                    continue
                nid  = edge.to_node.node_id
                xfer = state.num_transfers + _count_transfer(state.current_mode, edge.mode)
                key  = (nid, edge.mode.value)
                if key in visited:
                    continue

                nxt = _ChainState(
                    node          = edge.to_node,
                    edge          = edge,
                    parent        = state,
                    total_time    = state.total_time  + edge.time_min,
                    total_price   = state.total_price + edge.price_da,
                    total_co2     = state.total_co2   + edge.co2_g,
                    num_transfers = xfer,
                    hops          = state.hops + 1,
                )
                if nid == goal_id:
                    if best is None or xfer < best.num_transfers:
                        best = _make_result(nxt, start, goal, n_exp, len(visited),
                                            'bfs_min_transfers')
                    continue
                visited.add(key)
                queue.append(nxt)

        if best:
            best.nodes_expanded = n_exp
            best.nodes_visited  = len(visited)
            return best

        return BFSResult(found=False, start=start, goal=goal,
                         nodes_expanded=n_exp, nodes_visited=len(visited),
                         algorithm='bfs_min_transfers')

    def bfs_all_paths(
        self,
        start_id    : str,
        goal_id     : str,
        max_hops    : int = 20,
        max_paths   : int = 5,
        mode_config : Optional[ModeConfig] = None,
    ) -> List[BFSResult]:
        start, goal = self._validate(start_id, goal_id)
        cfg         = mode_config or ModeConfig.all()

        init    = _ChainState(node=start, edge=None, parent=None)
        queue   : deque[_ChainState] = deque([init])
        results : List[BFSResult]    = []
        # Track (node, mode) pairs so each combo is explored only once
        visited : Set[Tuple[str, Optional[str]]] = {(start_id, None)}
        n_exp   = 0

        while queue and len(results) < max_paths:
            state = queue.popleft()
            n_exp += 1
            if state.hops >= max_hops:
                continue

            for edge in self.graph.get_neighbors(state.node.node_id):
                if not cfg.is_allowed(edge.mode):
                    continue
                nid = edge.to_node.node_id
                key = (nid, edge.mode.value)
                if key in visited:
                    continue
                xfer = _count_transfer(state.current_mode, edge.mode)
                nxt  = _ChainState(
                    node          = edge.to_node,
                    edge          = edge,
                    parent        = state,
                    total_time    = state.total_time  + edge.time_min,
                    total_price   = state.total_price + edge.price_da,
                    total_co2     = state.total_co2   + edge.co2_g,
                    num_transfers = state.num_transfers + xfer,
                    hops          = state.hops + 1,
                )
                if nid == goal_id:
                    results.append(_make_result(nxt, start, goal, n_exp, n_exp,
                                                'bfs_all_paths'))
                    if len(results) >= max_paths:
                        break
                else:
                    visited.add(key)
                    queue.append(nxt)

        return results

    def dijkstra(
        self,
        start_id    : str,
        goal_id     : str,
        mode_config : Optional[ModeConfig] = None,
        w_time      : float = 1.0,
        w_price     : float = 0.0,
        w_co2       : float = 0.0,
    ) -> BFSResult:
        start, goal = self._validate(start_id, goal_id)
        cfg         = mode_config or ModeConfig.all()

        # dist[node_id] = best cost found so far
        dist: Dict[str, float] = {start_id: 0.0}

        init = _ChainState(node=start, edge=None, parent=None)
        # heap entries: (cost, tie_break_counter, state)
        heap     = [(0.0, 0, init)]
        counter  = 0
        n_exp    = 0
        visited  : Set[str] = set()

        while heap:
            cost, _, state = heapq.heappop(heap)
            nid = state.node.node_id

            if nid in visited:
                continue
            visited.add(nid)
            n_exp += 1

            if nid == goal_id:
                return _make_result(state, start, goal, n_exp, len(visited), 'dijkstra')

            for edge in self.graph.get_neighbors(nid):
                if not cfg.is_allowed(edge.mode):
                    continue
                nbr = edge.to_node.node_id
                if nbr in visited:
                    continue

                edge_cost = edge.weighted_cost(w_time, w_price, w_co2)
                new_cost  = cost + edge_cost

                if new_cost < dist.get(nbr, math.inf):
                    dist[nbr] = new_cost
                    xfer      = _count_transfer(state.current_mode, edge.mode)
                    nxt       = _ChainState(
                        node          = edge.to_node,
                        edge          = edge,
                        parent        = state,
                        total_time    = state.total_time  + edge.time_min,
                        total_price   = state.total_price + edge.price_da,
                        total_co2     = state.total_co2   + edge.co2_g,
                        num_transfers = state.num_transfers + xfer,
                        hops          = state.hops + 1,
                    )
                    counter += 1
                    heapq.heappush(heap, (new_cost, counter, nxt))

        return BFSResult(found=False, start=start, goal=goal,
                         nodes_expanded=n_exp, nodes_visited=len(visited),
                         algorithm='dijkstra')

    def astar(
        self,
        start_id    : str,
        goal_id     : str,
        mode_config : Optional[ModeConfig] = None,
        speed_kmh   : float = 30.0,
    ) -> BFSResult:
        start, goal = self._validate(start_id, goal_id)
        cfg         = mode_config or ModeConfig.all()

        def h(node: Node) -> float:
            km = node.haversine_km(goal)
            return km / speed_kmh * 60.0  # minutes

        g_score: Dict[str, float] = {start_id: 0.0}
        init    = _ChainState(node=start, edge=None, parent=None)
        counter = 0
        heap    = [(h(start), 0, init)]
        n_exp   = 0
        visited : Set[str] = set()

        while heap:
            f, _, state = heapq.heappop(heap)
            nid = state.node.node_id

            if nid in visited:
                continue
            visited.add(nid)
            n_exp += 1

            if nid == goal_id:
                return _make_result(state, start, goal, n_exp, len(visited), 'astar')

            for edge in self.graph.get_neighbors(nid):
                if not cfg.is_allowed(edge.mode):
                    continue
                nbr     = edge.to_node.node_id
                if nbr in visited:
                    continue
                tentative_g = g_score.get(nid, math.inf) + edge.time_min
                if tentative_g < g_score.get(nbr, math.inf):
                    g_score[nbr] = tentative_g
                    xfer         = _count_transfer(state.current_mode, edge.mode)
                    nxt          = _ChainState(
                        node          = edge.to_node,
                        edge          = edge,
                        parent        = state,
                        total_time    = state.total_time  + edge.time_min,
                        total_price   = state.total_price + edge.price_da,
                        total_co2     = state.total_co2   + edge.co2_g,
                        num_transfers = state.num_transfers + xfer,
                        hops          = state.hops + 1,
                    )
                    counter += 1
                    heapq.heappush(heap, (tentative_g + h(edge.to_node), counter, nxt))

        return BFSResult(found=False, start=start, goal=goal,
                         nodes_expanded=n_exp, nodes_visited=len(visited),
                         algorithm='astar')

    def reachable_from(
        self,
        start_id    : str,
        mode_config : Optional[ModeConfig] = None,
    ) -> Dict[str, int]:
        cfg     = mode_config or ModeConfig.all()
        visited : Dict[str, int] = {start_id: 0}
        queue   : deque[Tuple[str, int]] = deque([(start_id, 0)])
        while queue:
            nid, depth = queue.popleft()
            for edge in self.graph.get_neighbors(nid):
                if not cfg.is_allowed(edge.mode):
                    continue
                nb = edge.to_node.node_id
                if nb not in visited:
                    visited[nb] = depth + 1
                    queue.append((nb, depth + 1))
        return visited


def _style_ax(ax):
    ax.set_facecolor(BG_PANEL)
    ax.tick_params(colors=TEXT_DIM, labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COL)
    ax.yaxis.grid(True, color=GRID_COL, linewidth=0.5, linestyle='--')
    ax.set_axisbelow(True)


def plot_route(
    graph   : TransitGraph,
    result  : BFSResult,
    title   : str = '',
    save_to : str = '',
) -> None:
    """
    Plot the transit network with the result path highlighted.
    Bus edges use real-road polylines from bus_geometries.json when available.
    All other edges (metro, tram, train, walk, telepherique) draw straight lines
    between stop coordinates (that is correct – those are fixed infrastructure).
    """
    fig, ax = plt.subplots(figsize=(14, 9), facecolor=BG_DARK)
    ax.set_facecolor(BG_DARK)

    drawn: Set[Tuple] = set()
    for nid, edges in graph._adj.items():
        for edge in edges:
            a, b = edge.from_node.node_id, edge.to_node.node_id
            k    = (min(a, b), max(a, b), edge.mode.value)
            if k in drawn:
                continue
            drawn.add(k)
            color = MODE_COLORS.get(edge.mode.value, '#555')

            geom = graph.get_bus_geometry(edge)
            if geom and len(geom) >= 2:
                lats = [c[0] for c in geom]
                lons = [c[1] for c in geom]
                ax.plot(lons, lats, color=color, lw=0.4, alpha=0.10, zorder=1)
            else:
                ax.plot(
                    [edge.from_node.lon, edge.to_node.lon],
                    [edge.from_node.lat, edge.to_node.lat],
                    color=color, lw=0.5, alpha=0.12, zorder=1,
                )

    for node in graph._nodes.values():
        size  = 30 if node.is_hub else 12
        alpha = 0.7 if node.is_hub else 0.3
        ax.scatter(node.lon, node.lat, c=TEXT_DIM, s=size, zorder=2,
                   edgecolors='none', alpha=alpha)

    if result.found:
        for edge in result.path_edges:
            color = MODE_COLORS.get(edge.mode.value, '#FFF')

            geom = graph.get_bus_geometry(edge)
            if geom and len(geom) >= 2:
                lats = [c[0] for c in geom]
                lons = [c[1] for c in geom]
                ax.plot(lons, lats, color=color, lw=4, zorder=4,
                        solid_capstyle='round')
            else:
                ax.plot(
                    [edge.from_node.lon, edge.to_node.lon],
                    [edge.from_node.lat, edge.to_node.lat],
                    color=color, lw=4, zorder=4, solid_capstyle='round',
                )

        for node in result.path_nodes:
            ax.scatter(node.lon, node.lat, c=BG_CARD, s=80, zorder=5,
                       edgecolors=ACCENT, linewidths=1.5)
            ax.annotate(
                node.name,
                (node.lon, node.lat),
                fontsize=6.5, color=TEXT_MAIN,
                ha='center', xytext=(0, 10),
                textcoords='offset points', zorder=6,
                fontweight='bold',
            )

        start, goal = result.start, result.goal
        ax.scatter(start.lon, start.lat, c='#22C55E', s=350, zorder=7,
                   edgecolors='white', linewidths=1.5, marker='*')
        ax.scatter(goal.lon, goal.lat, c='#EF4444', s=350, zorder=7,
                   edgecolors='white', linewidths=1.5, marker='*')

        legend_handles = [
            Line2D([0], [0], color=MODE_COLORS[e.mode.value], lw=3,
                   label=f"{MODE_ICONS.get(e.mode.value, '')} {e.mode.value.title()}")
            for e in {e.mode.value: e for e in result.path_edges}.values()
        ]
        legend_handles += [
            mpatches.Patch(color='#22C55E', label=f"▶ {start.name}"),
            mpatches.Patch(color='#EF4444', label=f"◼ {goal.name}"),
        ]
        ax.legend(handles=legend_handles, loc='lower right',
                  facecolor=BG_CARD, edgecolor=GRID_COL,
                  labelcolor=TEXT_MAIN, fontsize=8.5, framealpha=0.95)

    ax.set_title(f"{heading}\n{info}", color=TEXT_MAIN, fontsize=12, pad=14,
                 fontweight='bold')
    ax.set_xlabel('Longitude', color=TEXT_DIM, fontsize=9)
    ax.set_ylabel('Latitude',  color=TEXT_DIM, fontsize=9)
    ax.tick_params(colors=TEXT_DIM)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COL)

    plt.tight_layout()
    out = save_to or 'route_map.png'
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG_DARK)
    print(f"[Plot] Saved → {out}")
    plt.close()


def plot_statistics_dashboard(results: List[BFSResult], save_to: str = '') -> None:
    if not results:
        print("No results to visualize.")
        return

    labels     = [f"{r.start.name[:12]}→\n{r.goal.name[:12]}" for r in results]
    times      = [r.total_time    for r in results]
    prices     = [r.total_price   for r in results]
    co2_vals   = [r.total_co2     for r in results]
    hops_vals  = [r.hops          for r in results]
    xfers_vals = [r.num_transfers  for r in results]

    all_modes: Set[str] = set()
    for r in results:
        all_modes.update(r.mode_usage_pct.keys())
    all_modes = sorted(all_modes)

    fig = plt.figure(figsize=(18, 14), facecolor=BG_DARK)
    gs  = GridSpec(3, 3, figure=fig, hspace=0.55, wspace=0.38,
                   top=0.92, bottom=0.07, left=0.07, right=0.97)

    fig.suptitle('Algiers Transit Router — Statistics Dashboard',
                 color=TEXT_MAIN, fontsize=15, fontweight='bold', y=0.97)

    def bar_chart(ax, values, color, ylabel, title):
        _style_ax(ax)
        xs   = range(len(labels))
        bars = ax.bar(xs, values, color=color, alpha=0.88, edgecolor=BG_DARK,
                      linewidth=0.8, width=0.6)
        ax.bar_label(bars, fmt='%.0f', color=TEXT_MAIN, fontsize=8,
                     padding=4, fontweight='bold')
        ax.set_xticks(list(xs))
        ax.set_xticklabels(labels, fontsize=7, color=TEXT_DIM, ha='center')
        ax.set_ylabel(ylabel, color=TEXT_DIM, fontsize=8)
        ax.set_title(title, color=TEXT_MAIN, fontsize=10, fontweight='bold', pad=8)

    bar_chart(fig.add_subplot(gs[0, 0]), times,      ACCENT,    'Minutes', '⏱  Travel Time (min)')
    bar_chart(fig.add_subplot(gs[0, 1]), prices,     '#F97316', 'DA',      '💰  Ticket Price (DA)')
    bar_chart(fig.add_subplot(gs[0, 2]), co2_vals,   '#22C55E', 'g CO₂',   '🌿  CO₂ Emissions (g)')
    bar_chart(fig.add_subplot(gs[1, 0]), hops_vals,  ACCENT2,   'Hops',    '🔗  Hops (Segments)')
    bar_chart(fig.add_subplot(gs[1, 1]), xfers_vals, '#FB7185', 'Transfers','🔄  Mode Transfers')

    ax_pie = fig.add_subplot(gs[1, 2])
    ax_pie.set_facecolor(BG_PANEL)
    ax_pie.set_title('🚦  Overall Mode Usage (%)', color=TEXT_MAIN,
                     fontsize=10, fontweight='bold', pad=8)
    combined: Dict[str, float] = {}
    for r in results:
        for mode, t in r.mode_breakdown.items():
            combined[mode] = combined.get(mode, 0.0) + t
    total_c = sum(combined.values())
    if total_c > 0:
        pie_labels = [f"{MODE_ICONS.get(k,'?')} {k}" for k in combined]
        pie_sizes  = list(combined.values())
        pie_colors = [MODE_COLORS.get(k, '#888') for k in combined]
        wedges, _, autotexts = ax_pie.pie(
            pie_sizes, labels=None, colors=pie_colors,
            autopct='%1.1f%%', startangle=90,
            wedgeprops={'edgecolor': BG_DARK, 'linewidth': 1.5},
            textprops={'color': TEXT_MAIN, 'fontsize': 8},
        )
        for at in autotexts:
            at.set_color(BG_DARK)
            at.set_fontsize(7.5)
            at.set_fontweight('bold')
        ax_pie.legend(wedges, pie_labels, loc='lower center',
                      bbox_to_anchor=(0.5, -0.22), ncol=2,
                      facecolor=BG_CARD, edgecolor=GRID_COL,
                      labelcolor=TEXT_MAIN, fontsize=7.5)

    ax_sc = fig.add_subplot(gs[2, 0:2])
    _style_ax(ax_sc)
    ax_sc.set_title('⚖️  Time vs Price Trade-off (bubble = CO₂)', color=TEXT_MAIN,
                    fontsize=10, fontweight='bold', pad=8)
    scatter_colors = [ACCENT, '#F97316', '#22C55E', ACCENT2, '#FB7185',
                      '#E9C46A', '#A8DADC', '#2A9D8F']
    for i, r in enumerate(results):
        c = scatter_colors[i % len(scatter_colors)]
        ax_sc.scatter(r.total_time, r.total_price,
                      s=max(r.total_co2, 10), c=c, alpha=0.85,
                      edgecolors='white', linewidths=0.8, zorder=4)
        ax_sc.annotate(
            f"{r.start.name[:10]}→{r.goal.name[:10]}",
            (r.total_time, r.total_price),
            fontsize=6.5, color=TEXT_DIM, ha='center',
            xytext=(0, 8), textcoords='offset points',
        )
    ax_sc.set_xlabel('Travel Time (min)', color=TEXT_DIM, fontsize=8)
    ax_sc.set_ylabel('Price (DA)',        color=TEXT_DIM, fontsize=8)

    ax_mb = fig.add_subplot(gs[2, 2])
    _style_ax(ax_mb)
    ax_mb.set_title('📊  Mode Usage per Route (%)', color=TEXT_MAIN,
                    fontsize=10, fontweight='bold', pad=8)
    x_pos   = range(len(results))
    bottoms = [0.0] * len(results)
    for mode in all_modes:
        pcts = [r.mode_usage_pct.get(mode, 0.0) for r in results]
        ax_mb.bar(x_pos, pcts, bottom=bottoms,
                  color=MODE_COLORS.get(mode, '#888'),
                  label=f"{MODE_ICONS.get(mode,'')} {mode}",
                  edgecolor=BG_DARK, linewidth=0.5)
        bottoms = [b + p for b, p in zip(bottoms, pcts)]
    ax_mb.set_xticks(list(x_pos))
    ax_mb.set_xticklabels([f"R{i+1}" for i in x_pos], color=TEXT_DIM, fontsize=8)
    ax_mb.set_ylabel('%', color=TEXT_DIM, fontsize=8)
    ax_mb.legend(loc='upper right', facecolor=BG_CARD, edgecolor=GRID_COL,
                 labelcolor=TEXT_MAIN, fontsize=6.5)

    out = save_to or 'statistics_dashboard.png'
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG_DARK)
    print(f"[Dashboard] Saved → {out}")
    plt.close()


def plot_bfs_frontier(
    graph    : TransitGraph,
    start_id : str,
    save_to  : str = '',
) -> None:
    router    = BFSRouter(graph)
    reachable = router.reachable_from(start_id)
    max_depth = max(reachable.values()) if reachable else 1

    cmap = plt.cm.plasma
    fig, ax = plt.subplots(figsize=(14, 9), facecolor=BG_DARK)
    ax.set_facecolor(BG_DARK)

    drawn: Set[Tuple] = set()
    for nid, edges in graph._adj.items():
        for edge in edges:
            a, b = edge.from_node.node_id, edge.to_node.node_id
            k    = (min(a, b), max(a, b))
            if k in drawn:
                continue
            drawn.add(k)
            ax.plot([edge.from_node.lon, edge.to_node.lon],
                    [edge.from_node.lat, edge.to_node.lat],
                    color=GRID_COL, lw=0.5, alpha=0.4, zorder=1)

    for nid, depth in reachable.items():
        node   = graph.get_node(nid)
        colour = cmap(depth / max_depth)
        size   = 200 if nid == start_id else 60
        ax.scatter(node.lon, node.lat, c=[colour], s=size,
                   zorder=5, edgecolors='none', alpha=0.85)

    start_node = graph.get_node(start_id)
    ax.scatter(start_node.lon, start_node.lat, c='#00FFFF', s=400,
               zorder=7, edgecolors='white', linewidths=1.5, marker='*')
    ax.annotate(start_node.name, (start_node.lon, start_node.lat),
                fontsize=8, color='#00FFFF', ha='center', fontweight='bold',
                xytext=(0, 12), textcoords='offset points', zorder=8)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=max_depth))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, pad=0.02, shrink=0.85)
    cbar.set_label('BFS Depth (hops from start)', color=TEXT_DIM, fontsize=9)
    cbar.ax.yaxis.set_tick_params(color=TEXT_DIM)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=TEXT_DIM)
    cbar.outline.set_edgecolor(GRID_COL)

    ax.set_title(
        f"BFS Frontier from '{start_node.name}'\n"
        f"{len(reachable)} nodes reachable in up to {max_depth} hops",
        color=TEXT_MAIN, fontsize=12, fontweight='bold', pad=14,
    )
    ax.set_xlabel('Longitude', color=TEXT_DIM, fontsize=9)
    ax.set_ylabel('Latitude',  color=TEXT_DIM, fontsize=9)
    ax.tick_params(colors=TEXT_DIM)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COL)

    plt.tight_layout()
    out = save_to or 'bfs_frontier.png'
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG_DARK)
    print(f"[Frontier] Saved → {out}")
    plt.close()


def plot_paths_comparison(paths: List[BFSResult], save_to: str = '') -> None:
    if not paths:
        print("No paths to compare.")
        return

    labels   = [f"Path {i+1}\n({r.hops}h, {r.num_transfers}x)" for i, r in enumerate(paths)]
    times    = [r.total_time  for r in paths]
    prices   = [r.total_price for r in paths]
    co2_vals = [r.total_co2   for r in paths]

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), facecolor=BG_DARK)
    fig.suptitle("Alternative Paths Comparison", color=TEXT_MAIN,
                 fontsize=13, fontweight='bold', y=1.01)

    bar_colors = [ACCENT, '#F97316', '#22C55E', ACCENT2, '#FB7185']
    datasets   = [
        (axes[0], times,    'Time (min)',  '⏱  Time'),
        (axes[1], prices,   'Price (DA)',  '💰  Price'),
        (axes[2], co2_vals, 'CO₂ (g)',     '🌿  CO₂'),
    ]

    for ax, data, ylabel, title in datasets:
        _style_ax(ax)
        xs     = range(len(labels))
        colors = [bar_colors[i % len(bar_colors)] for i in xs]
        bars   = ax.bar(xs, data, color=colors, alpha=0.88, edgecolor=BG_DARK,
                        linewidth=0.8, width=0.6)
        ax.bar_label(bars, fmt='%.0f', color=TEXT_MAIN, fontsize=9,
                     padding=4, fontweight='bold')
        ax.set_xticks(list(xs))
        ax.set_xticklabels(labels, fontsize=8, color=TEXT_DIM)
        ax.set_ylabel(ylabel, color=TEXT_DIM, fontsize=9)
        ax.set_title(title, color=TEXT_MAIN, fontsize=11, fontweight='bold', pad=10)

    plt.tight_layout()
    out = save_to or 'paths_comparison.png'
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG_DARK)
    print(f"[Comparison] Saved → {out}")
    plt.close()


def run_benchmark(graph: TransitGraph) -> None:
    router = BFSRouter(graph)

    queries = [
        ("Place des Martyrs → El Harrach Gare",  'M1_MARTYRS',  'M1_H_GARE'),
        ("Tafourah → Bachdjarah",                 'M1_TAFOURAH', 'M1_BACHJA'),
        ("1er Mai → Aïssat Idir",                 'M1_1MAI',     'M1_AISSAT'),
        ("El Hamma → Haï El Badr",                'M1_HAMMA',    'M1_HAI_BADR'),
        ("Les Fusillés → Gué de Constantine",     'M1_FUSILLES', 'M1_GUE_CON'),
    ]

    print(f"\n{'═'*95}")
    print(f"  BENCHMARK — Algiers Transit (BFS / Dijkstra / A*)")
    print(f"{'═'*95}")
    print(f"  {'Query':<42} {'Algo':<10} {'Hops':>5} {'Time':>8} "
          f"{'Price':>7} {'CO₂':>7} {'Xfer':>5} {'Exp.':>8}")
    print(f"  {'─'*88}")

    for label, s, g in queries:
        for algo, fn in [
            ('BFS',      lambda a, b: router.bfs_min_hops(a, b)),
            ('Dijkstra', lambda a, b: router.dijkstra(a, b)),
            ('A*',       lambda a, b: router.astar(a, b)),
        ]:
            r = fn(s, g)
            if r.found:
                print(f"  {label:<42} {algo:<10} {r.hops:>5d} "
                      f"{r.total_time:>6.0f}m {r.total_price:>5.0f}DA "
                      f"{r.total_co2:>5.0f}g {r.num_transfers:>5d} "
                      f"{r.nodes_expanded:>8,}")
            else:
                print(f"  {label:<42} {algo:<10} {'NO PATH':>5}")
        print(f"  {'─'*88}")

    print(f"{'═'*95}\n")

    print("Mode restriction tests (Martyrs → El Harrach):")
    metro_only = ModeConfig.only(TransportMode.METRO)
    no_walk    = ModeConfig.without(TransportMode.WALK)
    r_m = router.dijkstra('M1_MARTYRS', 'M1_H_GARE', metro_only)
    r_w = router.dijkstra('M1_MARTYRS', 'M1_H_GARE', no_walk)
    print(f"  [metro only]  : {'Found, ' + str(r_m.hops) + ' hops, ' + f'{r_m.total_time:.0f} min' if r_m.found else 'NO PATH'}")
    print(f"  [no walking]  : {'Found, ' + str(r_w.hops) + ' hops, ' + f'{r_w.total_time:.0f} min' if r_w.found else 'NO PATH'}")

    mt = router.bfs_min_transfers('M1_MARTYRS', 'M1_BACHJA')
    mh = router.bfs_min_hops('M1_MARTYRS', 'M1_BACHJA')
    print(f"\n  Martyrs → Bachdjarah")
    print(f"    BFS min hops     : {mh.hops} hops, {mh.num_transfers} transfers, {mh.total_time:.0f} min")
    print(f"    BFS min transfers: {mt.hops} hops, {mt.num_transfers} transfers, {mt.total_time:.0f} min")
    print()


def main():
    stops_csv     = STOPS_CSV
    edges_csv     = EDGES_CSV
    transfers_csv = TRANSFERS_CSV
    bus_geom_json = BUS_GEOMETRIES_JSON

    if not os.path.isfile(stops_csv):
        base = '/mnt/user-data/uploads'
        stops_csv     = os.path.join(base, 'stops.csv')
        edges_csv     = os.path.join(base, 'edges.csv')
        transfers_csv = os.path.join(base, 'transfers.csv')
        bus_geom_json = os.path.join(base, 'bus_geometries.json')
        if not os.path.isfile(stops_csv):
            raise FileNotFoundError(
                f"Data files not found.\n"
                f"Expected them in '{DATA_DIR}' or '/mnt/user-data/uploads/'.\n"
                "Place stops.csv, edges.csv, transfers.csv, bus_geometries.json "
                "in a 'Data/' folder next to this script."
            )

    graph = TransitGraph.from_csvs(
        stops_csv, edges_csv, transfers_csv, bus_geom_json
    )
    graph.summary()

    router = BFSRouter(graph)

    print("── BFS queries ──────────────────────────────────────")
    r1 = router.bfs_min_hops('M1_MARTYRS', 'M1_H_GARE')
    r1.print_summary()

    r2 = router.bfs_min_hops('M1_TAFOURAH', 'M1_BACHJA')
    r2.print_summary()

    r3 = router.bfs_min_transfers('M1_1MAI', 'M1_HAMMA')
    r3.print_summary()

    r4 = router.bfs_min_hops('M1_MARTYRS', 'M1_H_GARE',
                              mode_config=ModeConfig.only(TransportMode.METRO))
    r4.print_summary()

    print("── Dijkstra (min time) ──────────────────────────────")
    r5 = router.dijkstra('M1_MARTYRS', 'M1_H_GARE')
    r5.print_summary()

    print("── A* (min time, heuristic) ─────────────────────────")
    r6 = router.astar('M1_MARTYRS', 'M1_H_GARE')
    r6.print_summary()

    all_paths = router.bfs_all_paths('M1_MARTYRS', 'M1_H_GARE', max_hops=15, max_paths=4)
    print(f"\nFound {len(all_paths)} alternative path(s) from Place des Martyrs → El Harrach Gare:")
    for i, p in enumerate(all_paths, 1):
        print(f"  Path {i}: {p.hops} hops, {p.total_time:.0f} min, "
              f"{p.total_price:.0f} DA, {p.num_transfers} transfers")

    print("\nGenerating visualizations...")
    plot_route(graph, r1, title="BFS Min-Hops: Place des Martyrs → El Harrach",
               save_to='route_map_bfs.png')
    plot_route(graph, r5, title="Dijkstra Min-Time: Place des Martyrs → El Harrach",
               save_to='route_map_dijkstra.png')

    plot_statistics_dashboard(all_results, save_to='statistics_dashboard.png')

        plot_paths_comparison(all_paths, save_to='paths_comparison.png')





if __name__ == '__main__':
    main()
