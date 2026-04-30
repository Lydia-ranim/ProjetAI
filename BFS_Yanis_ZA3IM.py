from __future__ import annotations

import json
import math
import os
import sys
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import pandas as pd


DATA_DIR          = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Data')
STOPS_CSV         = os.path.join(DATA_DIR, 'stops.csv')
EDGES_CSV         = os.path.join(DATA_DIR, 'edges.csv')
TRANSFERS_CSV     = os.path.join(DATA_DIR, 'transfers.csv')
BUS_GEOM_JSON     = os.path.join(DATA_DIR, 'bus_geometries.json')


class TransportMode(Enum):
    WALK         = 'walk'
    BUS          = 'bus'
    TRAM         = 'tram'
    METRO        = 'metro'
    TRAIN        = 'train'
    TELEPHERIQUE = 'telepherique'

    @classmethod
    def from_string(cls, s: str) -> 'TransportMode':
        if not isinstance(s, str):
            raise TypeError(f"Expected str for mode, got {type(s).__name__}: {s!r}")
        normalized = s.strip().lower()
        aliases = {
            'cable_car':    cls.TELEPHERIQUE,
            'telepherique': cls.TELEPHERIQUE,
            'escalator':    cls.WALK,
            'transfer':     cls.WALK,
        }
        if normalized in aliases:
            return aliases[normalized]
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(
            f"Unknown transport mode {s!r}. "
            f"Valid values: {[m.value for m in cls]}"
        )


PRICE_DA: Dict[str, float] = {
    'walk':          0.0,
    'bus':          25.0,
    'tram':         50.0,
    'metro':        50.0,
    'train':        75.0,
    'telepherique': 30.0,
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

BG_DARK  = '#0A0E1A'
BG_PANEL = '#111827'
BG_CARD  = '#1C2333'
ACCENT   = '#4F8EF7'
ACCENT2  = '#A78BFA'
TEXT     = '#E2E8F0'
TEXT_DIM = '#64748B'
GRID_COL = '#1E293B'


@dataclass
class Node:
    node_id   : str
    name      : str
    node_type : str
    lat       : float
    lon       : float
    is_hub    : bool = False

    VALID_TYPES = {'metro', 'bus', 'tram', 'train', 'telepherique'}

    def __post_init__(self):
        self.node_id = str(self.node_id).strip()
        self.name    = str(self.name).strip()
        ntype = str(self.node_type).strip().lower()
        if ntype not in self.VALID_TYPES:
            raise ValueError(
                f"Node '{self.node_id}': invalid type {self.node_type!r}. "
                f"Must be one of {self.VALID_TYPES}"
            )
        self.node_type = ntype
        if not (-90.0 <= self.lat <= 90.0):
            raise ValueError(f"Node '{self.node_id}': latitude {self.lat} outside [-90, 90]")
        if not (-180.0 <= self.lon <= 180.0):
            raise ValueError(f"Node '{self.node_id}': longitude {self.lon} outside [-180, 180]")

    def haversine_km(self, other: 'Node') -> float:
        R    = 6371.0
        phi1 = math.radians(self.lat)
        phi2 = math.radians(other.lat)
        dlat = math.radians(other.lat - self.lat)
        dlon = math.radians(other.lon  - self.lon)
        a    = math.sin(dlat / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlon / 2) ** 2
        return R * 2 * math.asin(math.sqrt(max(0.0, min(1.0, a))))

    def __hash__(self):  return hash(self.node_id)
    def __eq__(self, o): return isinstance(o, Node) and self.node_id == o.node_id
    def __repr__(self):  return f"Node({self.node_id!r}, {self.name!r}, {self.node_type})"


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
    geometry    : List[List[float]] = field(default_factory=list)

    def __post_init__(self):
        if self.distance_km < 0:
            raise ValueError(f"Edge distance negative: {self.distance_km}")
        if self.time_min < 0:
            raise ValueError(f"Edge time negative: {self.time_min}")
        if self.price_da < 0:
            raise ValueError(f"Edge price negative: {self.price_da}")
        if self.co2_g < 0:
            raise ValueError(f"Edge CO2 negative: {self.co2_g}")

    def weighted_cost(self, w_time: float = 1.0,
                            w_price: float = 0.0,
                            w_co2: float   = 0.0) -> float:
        total = w_time + w_price + w_co2
        if total == 0:
            raise ValueError("At least one weight must be non-zero.")
        wt, wp, wc = w_time / total, w_price / total, w_co2 / total
        return wt * self.time_min + wp * self.price_da + wc * self.co2_g

    def road_lons(self) -> List[float]:
        if self.geometry:
            return [pt[1] for pt in self.geometry]
        return [self.from_node.lon, self.to_node.lon]

    def road_lats(self) -> List[float]:
        if self.geometry:
            return [pt[0] for pt in self.geometry]
        return [self.from_node.lat, self.to_node.lat]

    def __repr__(self):
        return (f"Edge({self.from_node.name!r} → {self.to_node.name!r}, "
                f"{self.mode.value}, {self.time_min:.1f}min)")


class TransitGraph:
    def __init__(self):
        self._nodes    : Dict[str, Node]            = {}
        self._adj      : Dict[str, List[Edge]]      = {}
        self._geom     : Dict[str, List[List[float]]] = {}

    def add_node(self, node: Node) -> None:
        if not isinstance(node, Node):
            raise TypeError(f"Expected Node, got {type(node).__name__}")
        if node.node_id in self._nodes:
            return
        self._nodes[node.node_id] = node
        self._adj[node.node_id]   = []

    def add_edge(self, edge: Edge) -> None:
        if not isinstance(edge, Edge):
            raise TypeError(f"Expected Edge, got {type(edge).__name__}")
        fid = edge.from_node.node_id
        tid = edge.to_node.node_id
        if fid not in self._nodes:
            raise KeyError(f"Source node '{fid}' not in graph — add the node first.")
        if tid not in self._nodes:
            raise KeyError(f"Destination node '{tid}' not in graph — add the node first.")
        self._adj[fid].append(edge)

    def get_node(self, node_id: str) -> Node:
        nid = str(node_id).strip()
        if nid not in self._nodes:
            raise KeyError(
                f"Node '{nid}' not found in graph. "
                f"Total nodes: {len(self._nodes)}. "
                f"Use graph.find_node_by_name() to search by name."
            )
        return self._nodes[nid]

    def find_node_by_name(self, name: str) -> Optional[Node]:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Search name must be a non-empty string.")
        target = name.strip().lower()
        exact  = [n for n in self._nodes.values() if n.name.strip().lower() == target]
        if exact:
            return exact[0]
        partial = [n for n in self._nodes.values() if target in n.name.strip().lower()]
        return partial[0] if partial else None

    def get_neighbors(self, node_id: str) -> List[Edge]:
        nid = str(node_id).strip()
        if nid not in self._adj:
            raise KeyError(f"Node '{nid}' not in graph.")
        return self._adj[nid]

    def node_count(self) -> int: return len(self._nodes)
    def edge_count(self) -> int: return sum(len(v) for v in self._adj.values())

    def summary(self) -> None:
        from collections import Counter
        type_counts = Counter(n.node_type for n in self._nodes.values())
        print(f"{'═'*55}")
        print(f"  Transit Graph Summary")
        print(f"{'═'*55}")
        print(f"  Total nodes : {self.node_count():>6,}")
        print(f"  Total edges : {self.edge_count():>6,}")
        print(f"  Geometry    : {len(self._geom):>6,} road polylines loaded")
        print(f"  Node types  :")
        for t, c in sorted(type_counts.items()):
            print(f"    {t:<14} : {c:>4,}")
        print(f"{'═'*55}")

    @classmethod
    def from_csvs(cls,
                  stops_csv    : str,
                  edges_csv    : str,
                  transfers_csv: str,
                  bus_geom_json: str) -> 'TransitGraph':

        for label, path in [
            ('stops CSV',         stops_csv),
            ('edges CSV',         edges_csv),
            ('transfers CSV',     transfers_csv),
            ('bus geometry JSON', bus_geom_json),
        ]:
            if not os.path.isfile(path):
                raise FileNotFoundError(
                    f"{label} not found: '{path}'\n"
                    "Place all data files in a 'Data/' folder next to this script."
                )

        graph = cls()

        bus_geom: Dict[str, List[List[float]]] = {}
        try:
            with open(bus_geom_json, 'r', encoding='utf-8') as f:
                raw_geom = json.load(f)
            if not isinstance(raw_geom, dict):
                raise ValueError("bus_geometries.json must be a JSON object (dict).")
            for key, pts in raw_geom.items():
                if not isinstance(pts, list):
                    continue
                valid_pts = []
                for pt in pts:
                    if (isinstance(pt, (list, tuple)) and len(pt) >= 2
                            and all(isinstance(c, (int, float)) for c in pt[:2])):
                        valid_pts.append([float(pt[0]), float(pt[1])])
                if valid_pts:
                    bus_geom[key] = valid_pts
            graph._geom = bus_geom
            print(f"  Geometry : {len(bus_geom):,} polylines loaded.")
        except json.JSONDecodeError as e:
            raise ValueError(f"bus_geometries.json is not valid JSON: {e}")

        stops_df = pd.read_csv(stops_csv, dtype=str)
        stops_df.columns = stops_df.columns.str.strip().str.lstrip('\ufeff')

        required_stop_cols = {'stop_id', 'stop_name', 'latitude', 'longitude', 'transport_type'}
        missing = required_stop_cols - set(stops_df.columns)
        if missing:
            raise ValueError(
                f"stops CSV is missing required columns: {missing}. "
                f"Found columns: {list(stops_df.columns)}"
            )

        node_errors = []
        for idx, row in stops_df.iterrows():
            try:
                raw_lat  = str(row.get('latitude', '')).strip()
                raw_lon  = str(row.get('longitude', '')).strip()
                raw_type = str(row.get('transport_type', '')).strip().lower()
                raw_hub  = str(row.get('is_hub', 'False')).strip().lower()

                if not raw_lat or not raw_lon:
                    raise ValueError("latitude or longitude is empty.")
                if not raw_type:
                    raise ValueError("transport_type is empty.")

                node = Node(
                    node_id   = str(row['stop_id']).strip(),
                    name      = str(row['stop_name']).strip(),
                    node_type = raw_type,
                    lat       = float(raw_lat),
                    lon       = float(raw_lon),
                    is_hub    = raw_hub in ('true', '1', 'yes'),
                )
                graph.add_node(node)
            except Exception as e:
                node_errors.append(f"  Row {idx} ({row.get('stop_id','?')}): {e}")

        if node_errors:
            print(f"  Nodes : {len(node_errors)} row(s) skipped:")
            for err in node_errors[:10]:
                print(err)
            if len(node_errors) > 10:
                print(f"  ... and {len(node_errors)-10} more.")
        print(f"  Nodes : {graph.node_count():,} loaded.")

        edges_df = pd.read_csv(edges_csv, dtype=str)
        edges_df.columns = edges_df.columns.str.strip().str.lstrip('\ufeff')

        required_edge_cols = {'from_stop_id', 'to_stop_id', 'distance_km',
                              'time_min', 'transport_type'}
        missing = required_edge_cols - set(edges_df.columns)
        if missing:
            raise ValueError(
                f"edges CSV is missing required columns: {missing}. "
                f"Found columns: {list(edges_df.columns)}"
            )

        edge_errors = []
        edge_count_ok = 0
        for idx, row in edges_df.iterrows():
            try:
                fid      = str(row['from_stop_id']).strip()
                tid      = str(row['to_stop_id']).strip()
                mode_str = str(row['transport_type']).strip()
                dist_str = str(row.get('distance_km', '0')).strip()
                time_str = str(row.get('time_min', '0')).strip()
                co2_str  = str(row.get('co2_g', '0')).strip()
                route_id = str(row.get('route_id', '')).strip()

                if fid not in graph._nodes:
                    raise KeyError(f"from_stop_id '{fid}' not in nodes.")
                if tid not in graph._nodes:
                    raise KeyError(f"to_stop_id '{tid}' not in nodes.")
                if fid == tid:
                    raise ValueError("Self-loop edge skipped.")

                mode     = TransportMode.from_string(mode_str)
                dist     = float(dist_str) if dist_str not in ('', 'nan') else 0.0
                time_min = float(time_str) if time_str not in ('', 'nan') else 0.0
                co2      = float(co2_str)  if co2_str  not in ('', 'nan') else 0.0
                price    = PRICE_DA.get(mode.value, 0.0)

                geom_key = f"{fid}|{tid}|{route_id}"
                geometry = bus_geom.get(geom_key, [])

                edge = Edge(
                    from_node   = graph._nodes[fid],
                    to_node     = graph._nodes[tid],
                    mode        = mode,
                    distance_km = max(0.0, dist),
                    time_min    = max(0.0, time_min),
                    price_da    = price,
                    co2_g       = max(0.0, co2),
                    route_id    = route_id,
                    geometry    = geometry,
                )
                graph.add_edge(edge)
                edge_count_ok += 1
            except Exception as e:
                edge_errors.append(f"  Row {idx}: {e}")

        if edge_errors:
            print(f"  Edges : {len(edge_errors)} row(s) skipped:")
            for err in edge_errors[:10]:
                print(err)
            if len(edge_errors) > 10:
                print(f"  ... and {len(edge_errors)-10} more.")
        print(f"  Edges : {edge_count_ok:,} loaded.")

        transfers_df = pd.read_csv(transfers_csv, dtype=str)
        transfers_df.columns = transfers_df.columns.str.strip().str.lstrip('\ufeff')

        required_tr_cols = {'from_stop_id', 'to_stop_id', 'total_time_min', 'distance_km'}
        missing = required_tr_cols - set(transfers_df.columns)
        if missing:
            raise ValueError(
                f"transfers CSV is missing required columns: {missing}. "
                f"Found columns: {list(transfers_df.columns)}"
            )

        tr_errors  = 0
        tr_count   = 0
        for idx, row in transfers_df.iterrows():
            try:
                fid      = str(row['from_stop_id']).strip()
                tid      = str(row['to_stop_id']).strip()
                time_str = str(row.get('total_time_min', '0')).strip()
                dist_str = str(row.get('distance_km', '0')).strip()

                if fid == tid:
                    continue
                if fid not in graph._nodes or tid not in graph._nodes:
                    continue

                time_min = float(time_str) if time_str not in ('', 'nan') else 0.0
                dist     = float(dist_str) if dist_str not in ('', 'nan') else 0.0

                edge = Edge(
                    from_node   = graph._nodes[fid],
                    to_node     = graph._nodes[tid],
                    mode        = TransportMode.WALK,
                    distance_km = max(0.0, dist),
                    time_min    = max(0.0, time_min),
                    price_da    = 0.0,
                    co2_g       = 0.0,
                    route_id    = 'TRANSFER',
                    geometry    = [],
                )
                graph.add_edge(edge)
                tr_count += 1
            except Exception as e:
                tr_errors += 1

        if tr_errors:
            print(f"  Transfers : {tr_errors} row(s) skipped.")
        print(f"  Transfers : {tr_count:,} walk links loaded.")

        return graph


@dataclass
class BFSState:
    current_node  : Node
    path_edges    : List[Edge] = field(default_factory=list)
    total_time    : float = 0.0
    total_price   : float = 0.0
    total_co2     : float = 0.0
    num_transfers : int   = 0

    @property
    def hops(self) -> int:
        return len(self.path_edges)

    @property
    def current_mode(self) -> Optional[TransportMode]:
        return self.path_edges[-1].mode if self.path_edges else None

    @property
    def path_nodes(self) -> List[Node]:
        if not self.path_edges:
            return [self.current_node]
        nodes = [self.path_edges[0].from_node]
        for e in self.path_edges:
            nodes.append(e.to_node)
        return nodes


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

    def print_summary(self) -> None:
        sep = '─' * 65
        print(sep)
        print(f"  BFS  {self.start.name!r}  →  {self.goal.name!r}")
        print(sep)
        if not self.found:
            print("  ❌  No path found — nodes may be disconnected.")
            print(f"  Nodes expanded : {self.nodes_expanded:,}")
            print(f"  Nodes visited  : {self.nodes_visited:,}")
            print(sep)
            return
        print(f"  ✅  {self.hops} hop(s)  |  {self.num_transfers} transfer(s)")
        print()
        for i, edge in enumerate(self.path_edges, 1):
            icon = MODE_ICONS.get(edge.mode.value, '?')
            print(f"  {i:>3}.  {icon} [{edge.mode.value.upper():<12}]  "
                  f"{edge.from_node.name:<28} →  {edge.to_node.name}")
            print(f"         {edge.time_min:6.1f} min  |  "
                  f"{edge.price_da:5.0f} DA  |  "
                  f"{edge.co2_g:6.1f} g CO₂  |  "
                  f"{edge.distance_km:.2f} km  |  "
                  f"route: {edge.route_id or 'WALK'}")
        print()
        print(f"  TOTAL   {self.total_time:7.1f} min  |  "
              f"{self.total_price:5.0f} DA  |  "
              f"{self.total_co2:6.1f} g CO₂")
        print(f"  Nodes expanded : {self.nodes_expanded:,}")
        print(f"  Nodes visited  : {self.nodes_visited:,}")
        print(sep)


class BFSRouter:
    def __init__(self, graph: TransitGraph):
        if not isinstance(graph, TransitGraph):
            raise TypeError(f"Expected TransitGraph, got {type(graph).__name__}")
        self.graph = graph

    def _resolve(self, node_ref) -> Node:
        if isinstance(node_ref, Node):
            return node_ref
        nid = str(node_ref).strip()
        try:
            return self.graph.get_node(nid)
        except KeyError:
            result = self.graph.find_node_by_name(nid)
            if result is None:
                raise KeyError(
                    f"'{nid}' not found as a node_id or stop name. "
                    "Check spelling or use the node_id from stops.csv."
                )
            return result

    @staticmethod
    def _is_transfer(prev_mode: Optional[TransportMode],
                     next_mode: TransportMode) -> bool:
        if prev_mode is None:
            return False
        if prev_mode == TransportMode.WALK or next_mode == TransportMode.WALK:
            return False
        return prev_mode != next_mode

    def bfs_min_hops(
        self,
        start_ref,
        goal_ref,
        allowed_modes: Optional[Set[TransportMode]] = None,
    ) -> BFSResult:
        start_node = self._resolve(start_ref)
        goal_node  = self._resolve(goal_ref)

        if start_node.node_id == goal_node.node_id:
            raise ValueError(
                f"Start and goal are the same node: '{start_node.name}'. "
                "Provide two different stops."
            )

        if allowed_modes is not None:
            if not isinstance(allowed_modes, set):
                raise TypeError("allowed_modes must be a set of TransportMode values.")
            if not allowed_modes:
                raise ValueError("allowed_modes is empty — no mode allowed means no path possible.")

        queue   : deque[BFSState] = deque()
        visited : Set[str]        = {start_node.node_id}
        queue.append(BFSState(current_node=start_node))
        nodes_expanded = 0

        while queue:
            state = queue.popleft()
            nodes_expanded += 1

            for edge in self.graph.get_neighbors(state.current_node.node_id):
                if allowed_modes and edge.mode not in allowed_modes:
                    continue

                nid = edge.to_node.node_id
                if nid in visited:
                    continue

                is_tr = self._is_transfer(state.current_mode, edge.mode)

                new_state = BFSState(
                    current_node  = edge.to_node,
                    path_edges    = state.path_edges + [edge],
                    total_time    = state.total_time  + edge.time_min,
                    total_price   = state.total_price + edge.price_da,
                    total_co2     = state.total_co2   + edge.co2_g,
                    num_transfers = state.num_transfers + (1 if is_tr else 0),
                )

                if nid == goal_node.node_id:
                    return BFSResult(
                        found          = True,
                        start          = start_node,
                        goal           = goal_node,
                        path_edges     = new_state.path_edges,
                        total_time     = new_state.total_time,
                        total_price    = new_state.total_price,
                        total_co2      = new_state.total_co2,
                        num_transfers  = new_state.num_transfers,
                        nodes_expanded = nodes_expanded,
                        nodes_visited  = len(visited),
                    )

                visited.add(nid)
                queue.append(new_state)

        return BFSResult(
            found=False, start=start_node, goal=goal_node,
            nodes_expanded=nodes_expanded, nodes_visited=len(visited),
        )

    def bfs_min_transfers(self, start_ref, goal_ref) -> BFSResult:
        start_node = self._resolve(start_ref)
        goal_node  = self._resolve(goal_ref)

        if start_node.node_id == goal_node.node_id:
            raise ValueError("Start and goal must be different nodes.")

        visited : Set[Tuple[str, Optional[str]]] = set()
        queue   : deque[BFSState]                = deque()
        queue.append(BFSState(current_node=start_node))
        visited.add((start_node.node_id, None))

        nodes_expanded = 0
        best: Optional[BFSResult] = None

        while queue:
            state = queue.popleft()
            nodes_expanded += 1

            if best and state.num_transfers >= best.num_transfers:
                continue

            for edge in self.graph.get_neighbors(state.current_node.node_id):
                nid      = edge.to_node.node_id
                mode_key = edge.mode.value
                vkey     = (nid, mode_key)

                if vkey in visited:
                    continue

                is_tr = self._is_transfer(state.current_mode, edge.mode)

                new_state = BFSState(
                    current_node  = edge.to_node,
                    path_edges    = state.path_edges + [edge],
                    total_time    = state.total_time  + edge.time_min,
                    total_price   = state.total_price + edge.price_da,
                    total_co2     = state.total_co2   + edge.co2_g,
                    num_transfers = state.num_transfers + (1 if is_tr else 0),
                )

                if nid == goal_node.node_id:
                    candidate = BFSResult(
                        found=True, start=start_node, goal=goal_node,
                        path_edges=new_state.path_edges,
                        total_time=new_state.total_time,
                        total_price=new_state.total_price,
                        total_co2=new_state.total_co2,
                        num_transfers=new_state.num_transfers,
                        nodes_expanded=nodes_expanded,
                        nodes_visited=len(visited),
                    )
                    if best is None or candidate.num_transfers < best.num_transfers:
                        best = candidate
                    continue

                visited.add(vkey)
                queue.append(new_state)

        if best:
            best.nodes_expanded = nodes_expanded
            best.nodes_visited  = len(visited)
            return best

        return BFSResult(
            found=False, start=start_node, goal=goal_node,
            nodes_expanded=nodes_expanded, nodes_visited=len(visited),
        )

    def bfs_all_paths(
        self,
        start_ref,
        goal_ref,
        max_hops : int = 10,
        max_paths: int = 20,
    ) -> List[BFSResult]:
        if not isinstance(max_hops, int) or max_hops < 1:
            raise ValueError("max_hops must be a positive integer.")
        if max_hops > 20:
            raise ValueError(
                "max_hops > 20 risks exponential explosion. "
                "Lower max_hops or use max_paths to cap results."
            )
        if not isinstance(max_paths, int) or max_paths < 1:
            raise ValueError("max_paths must be a positive integer.")

        start_node = self._resolve(start_ref)
        goal_node  = self._resolve(goal_ref)

        if start_node.node_id == goal_node.node_id:
            raise ValueError("Start and goal must differ.")

        queue   : deque[Tuple[BFSState, FrozenSet[str]]] = deque()
        results : List[BFSResult]                         = []
        queue.append((BFSState(current_node=start_node), frozenset({start_node.node_id})))
        nodes_expanded = 0

        while queue and len(results) < max_paths:
            state, path_visited = queue.popleft()
            nodes_expanded += 1

            if state.hops >= max_hops:
                continue

            for edge in self.graph.get_neighbors(state.current_node.node_id):
                nid = edge.to_node.node_id
                if nid in path_visited:
                    continue

                is_tr = self._is_transfer(state.current_mode, edge.mode)

                new_state = BFSState(
                    current_node  = edge.to_node,
                    path_edges    = state.path_edges + [edge],
                    total_time    = state.total_time  + edge.time_min,
                    total_price   = state.total_price + edge.price_da,
                    total_co2     = state.total_co2   + edge.co2_g,
                    num_transfers = state.num_transfers + (1 if is_tr else 0),
                )
                new_visited = path_visited | {nid}

                if nid == goal_node.node_id:
                    results.append(BFSResult(
                        found=True, start=start_node, goal=goal_node,
                        path_edges=new_state.path_edges,
                        total_time=new_state.total_time,
                        total_price=new_state.total_price,
                        total_co2=new_state.total_co2,
                        num_transfers=new_state.num_transfers,
                        nodes_expanded=nodes_expanded,
                        nodes_visited=0,
                    ))
                    if len(results) >= max_paths:
                        break
                else:
                    queue.append((new_state, new_visited))

        results.sort(key=lambda r: (r.num_transfers, r.hops, r.total_time))
        return results

    def reachable_from(
        self,
        start_ref,
        allowed_modes: Optional[Set[TransportMode]] = None,
    ) -> Dict[str, int]:
        start_node = self._resolve(start_ref)
        visited    : Dict[str, int]       = {start_node.node_id: 0}
        queue      : deque[Tuple[Node, int]] = deque([(start_node, 0)])

        while queue:
            node, depth = queue.popleft()
            for edge in self.graph.get_neighbors(node.node_id):
                if allowed_modes and edge.mode not in allowed_modes:
                    continue
                nid = edge.to_node.node_id
                if nid not in visited:
                    visited[nid] = depth + 1
                    queue.append((edge.to_node, depth + 1))

        return visited


def _style_ax(ax) -> None:
    ax.set_facecolor(BG_PANEL)
    ax.tick_params(colors=TEXT_DIM, labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COL)
    ax.yaxis.label.set_color(TEXT_DIM)
    ax.xaxis.label.set_color(TEXT_DIM)
    ax.title.set_color(TEXT)
    ax.grid(True, color=GRID_COL, linewidth=0.5, alpha=0.5)


def plot_route(
    graph   : TransitGraph,
    result  : BFSResult,
    title   : str = '',
    save_to : str = 'bfs_route.png',
) -> None:
    if not result.found:
        print(f"[plot_route] No path found — skipping plot for '{save_to}'.")
        return

    fig, ax = plt.subplots(figsize=(14, 9), facecolor=BG_DARK)
    ax.set_facecolor(BG_DARK)

    path_node_ids = {n.node_id for n in result.path_nodes}
    path_edge_set: Set[Tuple[str, str, str]] = set()
    for e in result.path_edges:
        path_edge_set.add((e.from_node.node_id, e.to_node.node_id, e.route_id))

    drawn_bg: Set[Tuple] = set()
    for nid, edges in graph._adj.items():
        for edge in edges:
            fid = edge.from_node.node_id
            tid = edge.to_node.node_id
            key = (min(fid, tid), max(fid, tid), edge.mode.value)
            if key in drawn_bg:
                continue
            drawn_bg.add(key)
            color = MODE_COLORS.get(edge.mode.value, '#444')
            lw    = 1.8 if edge.mode in (TransportMode.METRO, TransportMode.TRAM, TransportMode.TRAIN) else 0.8
            ax.plot(
                edge.road_lons(), edge.road_lats(),
                color=color, lw=lw, alpha=0.18, zorder=1,
                solid_capstyle='round',
            )

    for edge in result.path_edges:
        color = MODE_COLORS.get(edge.mode.value, '#FFD700')
        ax.plot(
            edge.road_lons(), edge.road_lats(),
            color='#FFD700', lw=5.5, alpha=0.95, zorder=4,
            solid_capstyle='round', solid_joinstyle='round',
        )
        ax.plot(
            edge.road_lons(), edge.road_lats(),
            color=color, lw=3.0, alpha=0.9, zorder=5,
            solid_capstyle='round', solid_joinstyle='round',
        )

    last_edge = result.path_edges[-1]
    lons = last_edge.road_lons()
    lats = last_edge.road_lats()
    if len(lons) >= 2:
        ax.annotate(
            '', xy=(lons[-1], lats[-1]),
            xytext=(lons[-2], lats[-2]),
            arrowprops=dict(arrowstyle='->', color='#FFD700', lw=2.5),
            zorder=6,
        )

    for nid, node in graph._nodes.items():
        if nid in path_node_ids:
            continue
        color  = MODE_COLORS.get(node.node_type, '#888')
        marker = {'metro': 'D', 'tram': 's', 'train': 'P',
                  'telepherique': 'h', 'bus': 'o'}.get(node.node_type, 'o')
        size   = 30 if node.is_hub else 10
        ax.scatter(node.lon, node.lat, c=color, s=size,
                   marker=marker, zorder=2, alpha=0.3,
                   edgecolors='none')

    for i, node in enumerate(result.path_nodes):
        color  = MODE_COLORS.get(node.node_type, '#FFD700')
        is_end = (i == 0 or i == len(result.path_nodes) - 1)
        ax.scatter(node.lon, node.lat,
                   c='#00FF9F' if i == 0 else ('#FF4545' if is_end else '#FFD700'),
                   s=220 if is_end else 80,
                   zorder=7,
                   edgecolors='white', linewidths=1.2,
                   marker='*' if is_end else 'o')
        if is_end or node.is_hub:
            ax.annotate(
                node.name,
                (node.lon, node.lat),
                fontsize=7.5, color=TEXT, fontweight='bold' if is_end else 'normal',
                xytext=(5, 7), textcoords='offset points', zorder=8,
                bbox=dict(boxstyle='round,pad=0.25', fc=BG_CARD, alpha=0.85, ec='none'),
            )

    legend_elements = [
        Line2D([0],[0], color=MODE_COLORS['metro'],        lw=2.5, label='Metro'),
        Line2D([0],[0], color=MODE_COLORS['tram'],         lw=2.5, label='Tram'),
        Line2D([0],[0], color=MODE_COLORS['bus'],          lw=2,   label='Bus'),
        Line2D([0],[0], color=MODE_COLORS['train'],        lw=2,   label='Train'),
        Line2D([0],[0], color=MODE_COLORS['telepherique'], lw=2,   label='Télépherique'),
        Line2D([0],[0], color=MODE_COLORS['walk'],         lw=1.5, label='Walk / Transfer'),
        Line2D([0],[0], color='#FFD700',                   lw=5,   label='BFS Path'),
    ]
    ax.legend(handles=legend_elements, loc='upper left',
              facecolor=BG_CARD, labelcolor=TEXT, fontsize=8,
              edgecolor=GRID_COL, framealpha=0.92)

    stats = (
        f"Hops: {result.hops}   Transfers: {result.num_transfers}\n"
        f"Time: {result.total_time:.0f} min   "
        f"Price: {result.total_price:.0f} DA   "
        f"CO₂: {result.total_co2:.0f} g"
    )
    ax.text(0.99, 0.02, stats, transform=ax.transAxes,
            fontsize=8, color=TEXT_DIM, ha='right', va='bottom',
            bbox=dict(boxstyle='round,pad=0.4', fc=BG_CARD, alpha=0.88, ec='none'))

    plot_title = title or f"BFS: {result.start.name} → {result.goal.name}"
    ax.set_title(plot_title, color=TEXT, fontsize=12, fontweight='bold', pad=12)
    ax.set_xlabel('Longitude', color=TEXT_DIM, fontsize=9)
    ax.set_ylabel('Latitude',  color=TEXT_DIM, fontsize=9)
    ax.tick_params(colors=TEXT_DIM)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COL)

    plt.tight_layout()
    plt.savefig(save_to, dpi=150, bbox_inches='tight', facecolor=BG_DARK)
    print(f"[Route Map] Saved → {save_to}")
    plt.close()


def plot_bfs_frontier(
    graph    : TransitGraph,
    start_ref,
    save_to  : str = 'bfs_frontier.png',
) -> None:
    router    = BFSRouter(graph)
    start_node = router._resolve(start_ref)
    reachable  = router.reachable_from(start_node)
    max_depth  = max(reachable.values()) if reachable else 1

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
            ax.plot(
                edge.road_lons(), edge.road_lats(),
                color=GRID_COL, lw=0.5, alpha=0.35, zorder=1,
            )

    for nid, depth in reachable.items():
        node   = graph.get_node(nid)
        colour = cmap(depth / max_depth)
        size   = 220 if nid == start_node.node_id else (50 if node.is_hub else 18)
        ax.scatter(node.lon, node.lat, c=[colour], s=size,
                   zorder=5, edgecolors='none', alpha=0.88)

    ax.scatter(start_node.lon, start_node.lat, c='#00FFFF', s=420,
               zorder=7, edgecolors='white', linewidths=1.5, marker='*')
    ax.annotate(
        start_node.name, (start_node.lon, start_node.lat),
        fontsize=9, color='#00FFFF', ha='center', fontweight='bold',
        xytext=(0, 13), textcoords='offset points', zorder=8,
        bbox=dict(boxstyle='round,pad=0.3', fc=BG_CARD, alpha=0.85, ec='none'),
    )

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=max_depth))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, pad=0.02, shrink=0.85)
    cbar.set_label('BFS Depth (hops from start)', color=TEXT_DIM, fontsize=9)
    cbar.ax.yaxis.set_tick_params(color=TEXT_DIM)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=TEXT_DIM)
    cbar.outline.set_edgecolor(GRID_COL)

    ax.set_title(
        f"BFS Frontier — '{start_node.name}'\n"
        f"{len(reachable):,} nodes reachable  |  max depth: {max_depth} hops",
        color=TEXT, fontsize=12, fontweight='bold', pad=14,
    )
    ax.set_xlabel('Longitude', color=TEXT_DIM, fontsize=9)
    ax.set_ylabel('Latitude',  color=TEXT_DIM, fontsize=9)
    ax.tick_params(colors=TEXT_DIM)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COL)

    plt.tight_layout()
    plt.savefig(save_to, dpi=150, bbox_inches='tight', facecolor=BG_DARK)
    print(f"[Frontier] Saved → {save_to}")
    plt.close()


def plot_paths_comparison(
    paths   : List[BFSResult],
    save_to : str = 'bfs_paths_comparison.png',
) -> None:
    if not paths:
        print("[plot_paths_comparison] No paths provided — skipping.")
        return
    if not all(p.found for p in paths):
        paths = [p for p in paths if p.found]
        if not paths:
            print("[plot_paths_comparison] All paths are 'not found' — skipping.")
            return

    labels   = [f"Path {i+1}\n({r.hops} hops, {r.num_transfers} xfer)" for i, r in enumerate(paths)]
    times    = [r.total_time  for r in paths]
    prices   = [r.total_price for r in paths]
    co2_vals = [r.total_co2   for r in paths]

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), facecolor=BG_DARK)
    fig.suptitle(
        f"BFS Alternative Paths — {paths[0].start.name} → {paths[0].goal.name}",
        color=TEXT, fontsize=13, fontweight='bold', y=1.01,
    )

    bar_colors = [ACCENT, '#F97316', '#22C55E', ACCENT2, '#FB7185', '#FACC15']
    datasets = [
        (axes[0], times,    'Time (min)', '⏱  Travel Time'),
        (axes[1], prices,   'Price (DA)', '💰  Ticket Cost'),
        (axes[2], co2_vals, 'CO₂ (g)',    '🌿  Emissions'),
    ]

    for ax, data, ylabel, ttl in datasets:
        _style_ax(ax)
        xs     = range(len(labels))
        colors = [bar_colors[i % len(bar_colors)] for i in xs]
        bars   = ax.bar(xs, data, color=colors, alpha=0.88,
                        edgecolor=BG_DARK, linewidth=0.8, width=0.6)
        ax.bar_label(bars, fmt='%.0f', color=TEXT, fontsize=9,
                     padding=4, fontweight='bold')
        ax.set_xticks(list(xs))
        ax.set_xticklabels(labels, fontsize=8, color=TEXT_DIM)
        ax.set_ylabel(ylabel, color=TEXT_DIM, fontsize=9)
        ax.set_title(ttl, color=TEXT, fontsize=11, fontweight='bold', pad=10)

    plt.tight_layout()
    plt.savefig(save_to, dpi=150, bbox_inches='tight', facecolor=BG_DARK)
    print(f"[Comparison] Saved → {save_to}")
    plt.close()


def run_bfs_benchmark(graph: TransitGraph) -> None:
    router = BFSRouter(graph)

    queries = [
        ("Place des Martyrs → El Harrach Gare",  'M1_MARTYRS',  'M1_H_GARE'),
        ("Tafourah → Bachdjarah",                 'M1_TAFOURAH', 'M1_BACHJA'),
        ("1er Mai → Aïssat Idir",                 'M1_1MAI',     'M1_AISSAT'),
        ("El Hamma → Haï El Badr",                'M1_HAMMA',    'M1_HAI_BADR'),
        ("Les Fusillés → Gué de Constantine",     'M1_FUSILLES', 'M1_GUE_CON'),
        ("Ruisseau (Tram) → USTHB",               'TR01',        'TR18'),
    ]

    print(f"\n{'═'*90}")
    print(f"  BFS BENCHMARK — Algiers Transit")
    print(f"{'═'*90}")
    hdr = f"  {'Query':<42} {'Variant':<16} {'Hops':>5} {'Time':>8} {'DA':>7} {'CO₂':>7} {'Xfer':>5} {'Exp.':>9}"
    print(hdr)
    print(f"  {'─'*85}")

    for label, s, g in queries:
        for variant_name, fn in [
            ('min-hops',      lambda a, b: router.bfs_min_hops(a, b)),
            ('min-transfers', lambda a, b: router.bfs_min_transfers(a, b)),
        ]:
            try:
                r = fn(s, g)
                if r.found:
                    print(f"  {label:<42} {variant_name:<16} {r.hops:>5d} "
                          f"{r.total_time:>6.0f}m {r.total_price:>5.0f}DA "
                          f"{r.total_co2:>5.0f}g {r.num_transfers:>5d} "
                          f"{r.nodes_expanded:>9,}")
                else:
                    print(f"  {label:<42} {variant_name:<16} {'NO PATH':>5}")
            except Exception as e:
                print(f"  {label:<42} {variant_name:<16} ERROR: {e}")
        print(f"  {'─'*85}")

    print(f"{'═'*90}\n")


def main():
    stops_csv     = STOPS_CSV
    edges_csv     = EDGES_CSV
    transfers_csv = TRANSFERS_CSV
    bus_geom_json = BUS_GEOM_JSON

    if not os.path.isfile(stops_csv):
        base          = '/mnt/user-data/uploads'
        stops_csv     = os.path.join(base, 'stops.csv')
        edges_csv     = os.path.join(base, 'edges.csv')
        transfers_csv = os.path.join(base, 'transfers.csv')
        bus_geom_json = os.path.join(base, 'bus_geometries.json')
        if not os.path.isfile(stops_csv):
            print(
                "ERROR: Data files not found.\n"
                f"Expected in '{DATA_DIR}' or '/mnt/user-data/uploads/'.\n"
                "Place stops.csv, edges.csv, transfers.csv, bus_geometries.json "
                "in a 'Data/' folder next to this script.",
                file=sys.stderr,
            )
            sys.exit(1)

    print("Loading transit graph...")
    graph = TransitGraph.from_csvs(stops_csv, edges_csv, transfers_csv, bus_geom_json)
    graph.summary()

    router = BFSRouter(graph)

    print("\n── BFS min-hops: Place des Martyrs → El Harrach Gare ──")
    r1 = router.bfs_min_hops('M1_MARTYRS', 'M1_H_GARE')
    r1.print_summary()

    print("\n── BFS min-hops: Tafourah → USTHB (tram) ──")
    r2 = router.bfs_min_hops('M1_TAFOURAH', 'TR18')
    r2.print_summary()

    print("\n── BFS min-hops: metro only filter ──")
    r3 = router.bfs_min_hops(
        'M1_MARTYRS', 'M1_H_GARE',
        allowed_modes={TransportMode.METRO},
    )
    r3.print_summary()

    print("\n── BFS min-transfers: Place des Martyrs → Bachdjarah ──")
    r4 = router.bfs_min_transfers('M1_MARTYRS', 'M1_BACHJA')
    r4.print_summary()

    print("\n── Reachability from Tafourah ──")
    reachable = router.reachable_from('M1_TAFOURAH')
    print(f"  Nodes reachable: {len(reachable):,} / {graph.node_count():,}")
    depth_dist: Dict[int, int] = {}
    for d in reachable.values():
        depth_dist[d] = depth_dist.get(d, 0) + 1
    for depth in sorted(depth_dist)[:8]:
        print(f"  depth {depth:>2} : {depth_dist[depth]:>4,} nodes")

    print("\n── All paths: 1er Mai → El Hamma (max 6 hops, top 4) ──")
    all_paths = router.bfs_all_paths('M1_1MAI', 'M1_HAMMA', max_hops=6, max_paths=4)
    print(f"  Found {len(all_paths)} path(s):")
    for i, p in enumerate(all_paths, 1):
        modes = ' → '.join(e.mode.value for e in p.path_edges)
        print(f"  Path {i}: {p.hops} hops | {p.total_time:.0f} min | "
              f"{p.total_price:.0f} DA | {p.num_transfers} xfer | {modes}")

    run_bfs_benchmark(graph)

    print("\nGenerating visualizations...")
    plot_route(graph, r1, title="BFS Min-Hops: Place des Martyrs → El Harrach Gare",
               save_to='bfs_route_martyrs_harrach.png')
    plot_route(graph, r2, title="BFS Min-Hops: Tafourah → USTHB",
               save_to='bfs_route_tafourah_usthb.png')
    plot_bfs_frontier(graph, 'M1_TAFOURAH', save_to='bfs_frontier.png')
    if all_paths:
        plot_paths_comparison(all_paths, save_to='bfs_paths_comparison.png')

    print("\nAll done.")
if __name__ == '__main__':
    main()