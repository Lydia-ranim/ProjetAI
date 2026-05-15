from __future__ import annotations
import sys
if sys.stdout and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError: pass
import heapq
import math
import time as time_module
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from ucs import TransitRouter, Stop as UCSStop, Edge as UCSEdge, RouteResult, Segment, FARES
from A_star import AStarRouter
from BFS_Yanis_ZA3IM import BFSRouter
from bidirectional_ranim_bomba import BidirectionalSearch, BiDirResult
from schedule import in_service, MAX_WALK_KM, WORKING_HOURS
RADIUS_KM = 2.0
WALK_SPEED_KMH = 5.0
WALK_SPEED_KPM = WALK_SPEED_KMH / 60.0
EARTH_RADIUS_KM = 6371.0
WALK_CO2_G_PER_KM = 0.0
_SAME_COORD_M = 0.01
_TMP_PREFIX = '__TMP__'

class AlgorithmName(str, Enum):
    UCS = 'ucs'
    ASTAR = 'astar'
    BFS = 'bfs'
    BIDIR_UCS = 'bidir_ucs'
    BIDIR_ASTAR = 'bidir_astar'
    BIDIR_BFS = 'bidir_bfs'

class FallbackTier(Enum):
    TIER_1 = auto()
    TIER_2 = auto()
    TIER_3 = auto()

@dataclass
class DynamicStop:
    stop_id: str
    name: str
    lat: float
    lon: float
    transport_type: str = 'walk'
    is_hub: bool = False
    city: str = 'Algiers'
    is_temporary: bool = True
    label: str = ''

@dataclass(order=True)
class StopCandidate:
    distance_km: float
    stop_id: str
    transport_type: str = field(compare=False)
    stop: Any = field(compare=False)

@dataclass
class NearbyPool:
    anchor_lat: float
    anchor_lon: float
    priority_queue: List[StopCandidate]
    type_index: Dict[str, List[StopCandidate]]

    def best(self) -> Optional[StopCandidate]:
        return self.priority_queue[0] if self.priority_queue else None

    def by_type(self, transport_type: str) -> List[StopCandidate]:
        return self.type_index.get(transport_type, [])

    def all_types(self) -> Set[str]:
        return set(self.type_index.keys())

    def is_empty(self) -> bool:
        return len(self.priority_queue) == 0

@dataclass
class WalkLeg:
    from_lat: float
    from_lon: float
    to_lat: float
    to_lon: float
    distance_km: float
    time_min: float
    label: str = ''

@dataclass
class RoutingResponse:
    found: bool
    algorithm: AlgorithmName
    metric: str
    fallback_tier: FallbackTier
    raw_result: Any
    segments: List[Segment]
    start_walk: Optional[WalkLeg]
    end_walk: Optional[WalkLeg]
    resolved_start_id: str
    resolved_end_id: str
    resolved_start_name: str
    resolved_end_id_name: str
    total_time_min: float
    total_dist_km: float
    total_co2_g: float
    total_fare_da: int
    nodes_explored: int
    runtime_ms: float

    def __str__(self) -> str:
        sep = '─' * 70
        lines = [sep, f'  RoutingResponse [{self.algorithm.value.upper()}] metric={self.metric}  tier={self.fallback_tier.name}', f"  Found: {('✅' if self.found else '❌')}"]
        if not self.found:
            lines.append('  No path found after applying fallback strategy.')
            lines.append(sep)
            return '\n'.join(lines)
        lines += [f'  Start : {self.resolved_start_name} ({self.resolved_start_id})', f'  End   : {self.resolved_end_id_name} ({self.resolved_end_id})', f'  Time  : {self.total_time_min:.1f} min', f'  Dist  : {self.total_dist_km:.2f} km', f'  CO₂   : {self.total_co2_g:.1f} g', f'  Fare  : {self.total_fare_da} DA', f'  Nodes : {self.nodes_explored:,}', f'  RT    : {self.runtime_ms:.2f} ms', f'  Tier  : {self.fallback_tier.name}']
        if self.start_walk:
            lines.append(f'  🚶 Walk IN  : {self.start_walk.distance_km:.3f} km  {self.start_walk.time_min:.1f} min  → {self.start_walk.label}')
        if self.end_walk:
            lines.append(f'  🚶 Walk OUT : {self.end_walk.distance_km:.3f} km  {self.end_walk.time_min:.1f} min  ← {self.end_walk.label}')
        icons = {'metro': '🚇', 'tram': '🚊', 'bus': '🚌', 'train': '🚂', 'telepherique': '🚡', 'walk': '🚶'}
        for seg in self.segments:
            icon = icons.get(seg.transport_type, '•')
            fare_str = f' | {seg.fare} DA' if seg.fare else ''
            lines.append(f'  {icon} {seg.transport_type.upper():12s} {seg.from_stop} → {seg.to_stop} | {seg.distance_km:.2f} km | {seg.time_min:.1f} min{fare_str}')
        lines.append(sep)
        return '\n'.join(lines)

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    φ1, λ1, φ2, λ2 = map(math.radians, (lat1, lon1, lat2, lon2))
    Δφ = φ2 - φ1
    Δλ = λ2 - λ1
    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return EARTH_RADIUS_KM * 2 * math.asin(math.sqrt(max(0.0, min(1.0, a))))

def walking_time_min(distance_km: float) -> float:
    return distance_km / WALK_SPEED_KPM

def make_walk_edge(from_id: str, to_id: str, from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> UCSEdge:
    dist = haversine(from_lat, from_lon, to_lat, to_lon)
    return UCSEdge(to_id=to_id, distance_km=round(dist, 4), time_min=round(walking_time_min(dist), 2), co2_g=0.0, transport_type='walk', route_id='WALK')

class NearbyStopFinder:

    def __init__(self, router: TransitRouter) -> None:
        self._router = router

    def find(self, lat: float, lon: float, radius_km: float=RADIUS_KM, exclude_ids: Optional[Set[str]]=None) -> NearbyPool:
        exclude = exclude_ids or set()
        raw: List[StopCandidate] = []
        type_index: Dict[str, List[StopCandidate]] = defaultdict(list)
        for sid, stop in self._router.stops.items():
            if sid in exclude:
                continue
            d = haversine(lat, lon, stop.lat, stop.lon)
            if d > radius_km:
                continue
            candidate = StopCandidate(distance_km=round(d, 4), stop_id=sid, transport_type=stop.transport_type, stop=stop)
            raw.append(candidate)
            type_index[stop.transport_type].append(candidate)
        heapq.heapify(raw)
        for mode in type_index:
            type_index[mode].sort()
        return NearbyPool(anchor_lat=lat, anchor_lon=lon, priority_queue=raw, type_index=dict(type_index))

class DynamicTransitRouter(AStarRouter):

    def __init__(self, data_dir: str) -> None:
        super().__init__(data_dir)
        self._extra_stops: Dict[str, Any] = {}
        self._extra_edges: Dict[str, List[UCSEdge]] = defaultdict(list)
        self._injected_ids: List[str] = []

    def inject_stop(self, dyn_stop: DynamicStop) -> None:
        self._extra_stops[dyn_stop.stop_id] = dyn_stop
        self._injected_ids.append(dyn_stop.stop_id)
        self.stops = {**self.stops, dyn_stop.stop_id: dyn_stop}

    def inject_edge(self, from_id: str, edge: UCSEdge) -> None:
        if from_id not in self.graph:
            self.graph[from_id] = []
        self.graph[from_id].append(edge)
        self._extra_edges[from_id].append(edge)

    def inject_temporary_node(self, dyn_stop: DynamicStop, nearby_pool: NearbyPool, max_connections: int=10) -> None:
        self.inject_stop(dyn_stop)
        connected = 0
        for candidate in nearby_pool.priority_queue:
            if connected >= max_connections:
                break
            real_stop = candidate.stop
            fwd = make_walk_edge(dyn_stop.stop_id, candidate.stop_id, dyn_stop.lat, dyn_stop.lon, real_stop.lat, real_stop.lon)
            self.inject_edge(dyn_stop.stop_id, fwd)
            rev = make_walk_edge(candidate.stop_id, dyn_stop.stop_id, real_stop.lat, real_stop.lon, dyn_stop.lat, dyn_stop.lon)
            self.inject_edge(candidate.stop_id, rev)
            connected += 1

    def _reconstruct(self, best: dict, goal_state: tuple, start_id: str=None):
        if start_id is not None:
            path, edges = ([], [])
            cur = goal_state
            while cur is not None:
                cost, prev_state, edge = best[cur]
                if prev_state is not None:
                    path.append(edge.to_id)
                    edges.append(edge)
                cur = prev_state
            path.append(start_id)
            path.reverse()
            edges.reverse()
            return (path, edges)
        else:
            path, edges = ([], [])
            state = goal_state
            while best[state][1] is not None:
                _, prev, edge = best[state]
                path.append(state[0])
                edges.append(edge)
                state = prev
            path.append(state[0])
            path.reverse()
            edges.reverse()
            return (path, edges)

    def clear_injected(self) -> None:
        for sid in self._injected_ids:
            self.stops.pop(sid, None)
        self._injected_ids.clear()
        for from_id, injected in self._extra_edges.items():
            if from_id in self.graph:
                injected_set = set((id(e) for e in injected))
                self.graph[from_id] = [e for e in self.graph[from_id] if id(e) not in injected_set]
            if from_id.startswith(_TMP_PREFIX) and from_id in self.graph:
                del self.graph[from_id]
        self._extra_stops.clear()
        self._extra_edges.clear()

class TransportMatcher:

    def resolve(self, start_pool: NearbyPool, end_pool: NearbyPool, router: TransitRouter) -> Tuple[Optional[str], Optional[str], FallbackTier]:
        if not start_pool.is_empty() and (not end_pool.is_empty()):
            result = self._tier1_type_match(start_pool, end_pool)
            if result is not None:
                return (result[0], result[1], FallbackTier.TIER_1)
        if not start_pool.is_empty() and (not end_pool.is_empty()):
            s = start_pool.best()
            e = end_pool.best()
            if s and e:
                return (s.stop_id, e.stop_id, FallbackTier.TIER_2)
        s_id = self._global_nearest(start_pool.anchor_lat, start_pool.anchor_lon, router)
        e_id = self._global_nearest(end_pool.anchor_lat, end_pool.anchor_lon, router, exclude={s_id} if s_id else None)
        return (s_id, e_id, FallbackTier.TIER_3)

    def _tier1_type_match(self, start_pool: NearbyPool, end_pool: NearbyPool) -> Optional[Tuple[str, str]]:
        for end_candidate in end_pool.priority_queue:
            mode = end_candidate.transport_type
            start_matches = start_pool.by_type(mode)
            if start_matches:
                return (start_matches[0].stop_id, end_candidate.stop_id)
        return None

    def _global_nearest(self, lat: float, lon: float, router: TransitRouter, exclude: Optional[Set[str]]=None) -> Optional[str]:
        exclude = exclude or set()
        best_id, best_d = (None, float('inf'))
        for sid, stop in router.stops.items():
            if sid in exclude:
                continue
            d = haversine(lat, lon, stop.lat, stop.lon)
            if d < best_d:
                best_d = d
                best_id = sid
        return best_id

class SearchStrategy(ABC):

    @abstractmethod
    def execute(self, router: DynamicTransitRouter, start_id: str, end_id: str, metric: str, depart: Optional[float], w1: float, w2: float, w3: float) -> Any:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

class UCSStrategy(SearchStrategy):

    @property
    def name(self) -> str:
        return 'UCS'

    def execute(self, router, start_id, end_id, metric, depart, w1, w2, w3):
        return router.find_route(start_id, end_id, metric=metric, depart=depart, w1=w1, w2=w2, w3=w3)

class AStarStrategy(SearchStrategy):

    @property
    def name(self) -> str:
        return 'A*'

    def execute(self, router, start_id, end_id, metric, depart, w1, w2, w3):
        return router.find_route_astar(start_id, end_id, metric=metric, depart=depart, w1=w1, w2=w2, w3=w3)

class BFSStrategy(SearchStrategy):

    def __init__(self, data_dir: str) -> None:
        self._bfs = BFSRouter(data_dir)

    @property
    def name(self) -> str:
        return 'BFS'

    def _sync_graph(self, router) -> None:
        from BFS_Yanis_ZA3IM import Stop as BFSStop, Edge as BFSEdge
        for sid, stop in router.stops.items():
            if sid.startswith(_TMP_PREFIX) and sid not in self._bfs.stops:
                self._bfs.stops[sid] = BFSStop(stop_id=sid, name=getattr(stop, 'name', sid), lat=stop.lat, lon=stop.lon, transport_type=getattr(stop, 'transport_type', 'walk'), is_hub=False)
        for from_id, edges in router.graph.items():
            if from_id.startswith(_TMP_PREFIX):
                self._bfs.graph[from_id] = [BFSEdge(to_id=e.to_id, time_min=e.time_min, distance_km=e.distance_km, transport_type=e.transport_type, route_id=e.route_id, co2_g=e.co2_g) for e in edges]
            else:
                for e in edges:
                    if e.to_id.startswith(_TMP_PREFIX):
                        existing = self._bfs.graph.get(from_id, [])
                        if not any((x.to_id == e.to_id for x in existing)):
                            self._bfs.graph.setdefault(from_id, []).append(BFSEdge(to_id=e.to_id, time_min=e.time_min, distance_km=e.distance_km, transport_type=e.transport_type, route_id=e.route_id, co2_g=e.co2_g))

    def _unsync_graph(self) -> None:
        for sid in [k for k in list(self._bfs.stops.keys()) if k.startswith(_TMP_PREFIX)]:
            del self._bfs.stops[sid]
            self._bfs.graph.pop(sid, None)
        for fid in list(self._bfs.graph.keys()):
            self._bfs.graph[fid] = [e for e in self._bfs.graph[fid] if not e.to_id.startswith(_TMP_PREFIX)]

    def execute(self, router, start_id, end_id, metric, depart, w1, w2, w3):
        dep = depart if depart is not None else 8.0
        self._sync_graph(router)
        try:
            return self._bfs.search(start_id, end_id, depart=dep)
        finally:
            self._unsync_graph()

class BidirUCSStrategy(SearchStrategy):

    def __init__(self, bidir: BidirectionalSearch) -> None:
        self._bidir = bidir

    @property
    def name(self) -> str:
        return 'Bidir-UCS'

    def execute(self, router, start_id, end_id, metric, depart, w1, w2, w3):
        return self._bidir.search(start_id, end_id, metric=metric, algorithm='ucs', w1=w1, w2=w2, w3=w3, depart=depart)

class BidirAStarStrategy(SearchStrategy):

    def __init__(self, bidir: BidirectionalSearch) -> None:
        self._bidir = bidir

    @property
    def name(self) -> str:
        return 'Bidir-A*'

    def execute(self, router, start_id, end_id, metric, depart, w1, w2, w3):
        return self._bidir.search(start_id, end_id, metric=metric, algorithm='astar', w1=w1, w2=w2, w3=w3, depart=depart)

class BidirBFSStrategy(SearchStrategy):

    def __init__(self, bidir: BidirectionalSearch) -> None:
        self._bidir = bidir

    @property
    def name(self) -> str:
        return 'Bidir-BFS'

    def _sync_bfs(self, router) -> None:
        from BFS_Yanis_ZA3IM import Stop as BFSStop, Edge as BFSEdge
        bfs = self._bidir.bfs_router
        if bfs is None:
            return
        for sid, stop in router.stops.items():
            if sid.startswith(_TMP_PREFIX) and sid not in bfs.stops:
                bfs.stops[sid] = BFSStop(stop_id=sid, name=getattr(stop, 'name', sid), lat=stop.lat, lon=stop.lon, transport_type=getattr(stop, 'transport_type', 'walk'), is_hub=False)
        for from_id, edges in router.graph.items():
            if from_id.startswith(_TMP_PREFIX):
                bfs.graph[from_id] = [BFSEdge(to_id=e.to_id, time_min=e.time_min, distance_km=e.distance_km, transport_type=e.transport_type, route_id=e.route_id, co2_g=e.co2_g) for e in edges]
            else:
                for e in edges:
                    if e.to_id.startswith(_TMP_PREFIX):
                        existing = bfs.graph.get(from_id, [])
                        if not any((x.to_id == e.to_id for x in existing)):
                            bfs.graph.setdefault(from_id, []).append(BFSEdge(to_id=e.to_id, time_min=e.time_min, distance_km=e.distance_km, transport_type=e.transport_type, route_id=e.route_id, co2_g=e.co2_g))

    def _unsync_bfs(self) -> None:
        bfs = self._bidir.bfs_router
        if bfs is None:
            return
        for sid in [k for k in list(bfs.stops.keys()) if k.startswith(_TMP_PREFIX)]:
            del bfs.stops[sid]
            bfs.graph.pop(sid, None)
        for fid in list(bfs.graph.keys()):
            bfs.graph[fid] = [e for e in bfs.graph[fid] if not e.to_id.startswith(_TMP_PREFIX)]

    def execute(self, router, start_id, end_id, metric, depart, w1, w2, w3):
        dep = depart if depart is not None else 8.0
        self._sync_bfs(router)
        try:
            return self._bidir.search_bfs(start_id, end_id, depart=dep)
        finally:
            self._unsync_bfs()

class ResultNormaliser:

    @staticmethod
    def normalise(raw_result: Any) -> Dict[str, Any]:
        if isinstance(raw_result, RouteResult):
            return {'found': raw_result.found, 'segments': raw_result.segments, 'total_time': raw_result.total_time, 'total_dist': raw_result.total_dist, 'total_co2': raw_result.total_co2, 'total_fare': raw_result.total_fare, 'nodes_explored': raw_result.nodes_explored}
        elif isinstance(raw_result, BiDirResult):
            return {'found': raw_result.found, 'segments': raw_result.segments or [], 'total_time': raw_result.total_time, 'total_dist': raw_result.total_dist, 'total_co2': raw_result.total_co2, 'total_fare': raw_result.total_fare, 'nodes_explored': raw_result.nodes_explored}
        else:
            found = getattr(raw_result, 'found', False)
            return {'found': found, 'segments': [], 'total_time': getattr(raw_result, 'total_journey_time', 0.0), 'total_dist': 0.0, 'total_co2': getattr(raw_result, 'total_co2', 0.0), 'total_fare': int(getattr(raw_result, 'total_price', 0)), 'nodes_explored': getattr(raw_result, 'nodes_expanded', 0)}
Location = Union[Tuple[float, float], str]
_tmp_counter = 0

def _new_tmp_id() -> str:
    global _tmp_counter
    _tmp_counter += 1
    return f'{_TMP_PREFIX}{_tmp_counter}'

class RoutingPipeline:

    def __init__(self, data_dir: str, radius_km: float=RADIUS_KM) -> None:
        self._data_dir = data_dir
        self._radius = radius_km
        print(f'[RoutingPipeline] Loading graph from {data_dir!r} ...')
        t0 = time_module.time()
        self._router = DynamicTransitRouter(data_dir)
        elapsed = time_module.time() - t0
        print(f'[RoutingPipeline] Loaded in {elapsed:.2f}s — {self._router.num_stops:,} stops, {self._router.num_edges:,} edges')
        self._finder = NearbyStopFinder(self._router)
        self._matcher = TransportMatcher()
        self._bfs_router = BFSRouter(data_dir)
        self._bidir = BidirectionalSearch(self._router, bfs_router=self._bfs_router)
        self._strategies: Dict[AlgorithmName, SearchStrategy] = {AlgorithmName.UCS: UCSStrategy(), AlgorithmName.ASTAR: AStarStrategy(), AlgorithmName.BFS: BFSStrategy(data_dir), AlgorithmName.BIDIR_UCS: BidirUCSStrategy(self._bidir), AlgorithmName.BIDIR_ASTAR: BidirAStarStrategy(self._bidir), AlgorithmName.BIDIR_BFS: BidirBFSStrategy(self._bidir)}

    def route(self, start: Location, end: Location, algo: AlgorithmName=AlgorithmName.ASTAR, metric: str='time', depart: Optional[float]=None, w1: float=0.33, w2: float=0.33, w3: float=0.34) -> RoutingResponse:
        t0 = time_module.time()
        try:
            start_lat, start_lon, start_stop_id = self._parse_location(start)
            end_lat, end_lon, end_stop_id = self._parse_location(end)
            if start_stop_id and start_stop_id == end_stop_id:
                return self._empty_response(start_stop_id, algo, metric, FallbackTier.TIER_1, runtime_ms=(time_module.time() - t0) * 1000)
            if haversine(start_lat, start_lon, end_lat, end_lon) < _SAME_COORD_M:
                pool = self._finder.find(start_lat, start_lon, radius_km=self._radius)
                nearest = pool.best()
                sid = nearest.stop_id if nearest else self._matcher._global_nearest(start_lat, start_lon, self._router)
                return self._empty_response(sid or '', algo, metric, FallbackTier.TIER_1, runtime_ms=(time_module.time() - t0) * 1000)
            start_dyn_id = self._maybe_inject(start_lat, start_lon, start_stop_id, label='User Start')
            end_dyn_id = self._maybe_inject(end_lat, end_lon, end_stop_id, label='User End')
            start_pool = self._finder.find(start_lat, start_lon, radius_km=self._radius, exclude_ids={start_dyn_id} if start_dyn_id else set())
            end_pool = self._finder.find(end_lat, end_lon, radius_km=self._radius, exclude_ids={end_dyn_id} if end_dyn_id else set())
            s_id, e_id, tier = self._matcher.resolve(start_pool, end_pool, self._router)
            if s_id and e_id and (s_id == e_id):
                return self._empty_response(s_id, algo, metric, tier, runtime_ms=(time_module.time() - t0) * 1000)
            if not s_id or not e_id:
                return self._no_route_response(algo, metric, tier, runtime_ms=(time_module.time() - t0) * 1000)
            start_walk = self._make_walk_leg(start_lat, start_lon, self._router.stops[s_id], direction='to')
            end_walk = self._make_walk_leg(end_lat, end_lon, self._router.stops[e_id], direction='from')
            strategy = self._strategies[algo]
            raw = strategy.execute(self._router, s_id, e_id, metric=metric, depart=depart, w1=w1, w2=w2, w3=w3)
            normed = ResultNormaliser.normalise(raw)
            runtime = (time_module.time() - t0) * 1000
            route_found = normed['found']
            if route_found:
                walk_time = (start_walk.time_min if start_walk else 0.0) + (end_walk.time_min if end_walk else 0.0)
                walk_dist = (start_walk.distance_km if start_walk else 0.0) + (end_walk.distance_km if end_walk else 0.0)
            else:
                walk_time = 0.0
                walk_dist = 0.0
            s_stop = self._router.stops[s_id]
            e_stop = self._router.stops[e_id]
            return RoutingResponse(found=route_found, algorithm=algo, metric=metric, fallback_tier=tier, raw_result=raw, segments=normed['segments'], start_walk=start_walk if route_found else None, end_walk=end_walk if route_found else None, resolved_start_id=s_id, resolved_end_id=e_id, resolved_start_name=getattr(s_stop, 'name', s_id), resolved_end_id_name=getattr(e_stop, 'name', e_id), total_time_min=round(normed['total_time'] + walk_time, 2), total_dist_km=round(normed['total_dist'] + walk_dist, 4), total_co2_g=round(normed['total_co2'], 2), total_fare_da=normed['total_fare'], nodes_explored=normed['nodes_explored'], runtime_ms=round(runtime, 2))
        finally:
            self._router.clear_injected()

    def compare_all_algos(self, start: Location, end: Location, metric: str='time', depart: Optional[float]=None, w1: float=0.33, w2: float=0.33, w3: float=0.34) -> Dict[AlgorithmName, RoutingResponse]:
        results: Dict[AlgorithmName, RoutingResponse] = {}
        for algo in AlgorithmName:
            try:
                results[algo] = self.route(start, end, algo=algo, metric=metric, depart=depart, w1=w1, w2=w2, w3=w3)
            except Exception as exc:
                print(f'[compare_all] {algo.value} raised: {exc}')
        return results

    def print_comparison_table(self, comparison: Dict[AlgorithmName, RoutingResponse]) -> None:
        sep = '=' * 100
        dash = '-' * 100
        print(f'\n{sep}')
        print('  ALGORITHM COMPARISON -- Routing Engine')
        print(sep)
        print(f"  {'Algorithm':<18} {'Found':>6} {'Tier':>7} {'Time(min)':>10} {'Dist(km)':>9} {'CO2(g)':>8} {'Fare(DA)':>9} {'Nodes':>8} {'RT(ms)':>9}")
        print(dash)
        for algo, resp in comparison.items():
            print(f"  {algo.value:<18} {('Y' if resp.found else 'N'):>6} {resp.fallback_tier.name:>7} {resp.total_time_min:>10.1f} {resp.total_dist_km:>9.3f} {resp.total_co2_g:>8.1f} {resp.total_fare_da:>9} {resp.nodes_explored:>8,} {resp.runtime_ms:>9.2f}")
        print(sep)

    def _parse_location(self, loc: Location) -> Tuple[float, float, Optional[str]]:
        if isinstance(loc, str):
            stop = self._router.stops.get(loc)
            if stop is not None:
                return (stop.lat, stop.lon, loc)
            raise ValueError(f'String location {loc!r} is not a known stop ID. Pass (lat, lon) instead.')
        lat, lon = (float(loc[0]), float(loc[1]))
        return (lat, lon, None)

    def _maybe_inject(self, lat: float, lon: float, existing_stop_id: Optional[str], label: str) -> Optional[str]:
        if existing_stop_id is not None:
            return existing_stop_id
        tmp_id = _new_tmp_id()
        dyn = DynamicStop(stop_id=tmp_id, name=label, lat=lat, lon=lon, label=label)
        pool = self._finder.find(lat, lon, radius_km=self._radius)
        self._router.inject_temporary_node(dyn, pool)
        return tmp_id

    def _make_walk_leg(self, user_lat: float, user_lon: float, stop: Any, direction: str) -> Optional[WalkLeg]:
        dist = haversine(user_lat, user_lon, stop.lat, stop.lon)
        if dist < 0.005:
            return None
        t = walking_time_min(dist)
        if direction == 'to':
            return WalkLeg(from_lat=user_lat, from_lon=user_lon, to_lat=stop.lat, to_lon=stop.lon, distance_km=round(dist, 4), time_min=round(t, 2), label=f"Walk to {getattr(stop, 'name', stop.stop_id)}")
        return WalkLeg(from_lat=stop.lat, from_lon=stop.lon, to_lat=user_lat, to_lon=user_lon, distance_km=round(dist, 4), time_min=round(t, 2), label=f"Walk from {getattr(stop, 'name', stop.stop_id)}")

    def _empty_response(self, stop_id: str, algo: AlgorithmName, metric: str, tier: FallbackTier, runtime_ms: float) -> RoutingResponse:
        empty = RouteResult(found=True, path=[stop_id], edges=[], segments=[], total_time=0, total_dist=0, total_co2=0, total_fare=0, nodes_explored=0)
        stop = self._router.stops.get(stop_id)
        name = getattr(stop, 'name', stop_id) if stop else stop_id
        return RoutingResponse(found=True, algorithm=algo, metric=metric, fallback_tier=tier, raw_result=empty, segments=[], start_walk=None, end_walk=None, resolved_start_id=stop_id, resolved_end_id=stop_id, resolved_start_name=name, resolved_end_id_name=name, total_time_min=0, total_dist_km=0, total_co2_g=0, total_fare_da=0, nodes_explored=0, runtime_ms=runtime_ms)

    def _no_route_response(self, algo: AlgorithmName, metric: str, tier: FallbackTier, runtime_ms: float) -> RoutingResponse:
        empty = RouteResult(found=False, path=[], edges=[], segments=[], total_time=0, total_dist=0, total_co2=0, total_fare=0, nodes_explored=0)
        return RoutingResponse(found=False, algorithm=algo, metric=metric, fallback_tier=tier, raw_result=empty, segments=[], start_walk=None, end_walk=None, resolved_start_id='', resolved_end_id='', resolved_start_name='', resolved_end_id_name='', total_time_min=0, total_dist_km=0, total_co2_g=0, total_fare_da=0, nodes_explored=0, runtime_ms=runtime_ms)

def _demo(data_dir: str) -> None:
    print('\n' + '=' * 70)
    print('  ENSIA AI Project — Routing Engine Demo')
    print('=' * 70)
    pipeline = RoutingPipeline(data_dir)
    DEMO_QUERIES = [{'label': 'GPS → GPS (near Place des Martyrs → near USTHB)', 'start': (36.7732, 3.0607), 'end': (36.7213, 3.1612), 'algo': AlgorithmName.ASTAR, 'metric': 'time'}, {'label': 'StopID → GPS (M1_MARTYRS → near El Harrach)', 'start': 'M1_MARTYRS', 'end': (36.7167, 3.1333), 'algo': AlgorithmName.BIDIR_ASTAR, 'metric': 'time'}, {'label': 'StopID → StopID (Martyrs → TR01) — all algos comparison', 'start': 'M1_MARTYRS', 'end': 'TR01', 'algo': AlgorithmName.ASTAR, 'metric': 'time', 'compare': True}]
    for q in DEMO_QUERIES:
        print(f"\n{'─' * 70}")
        print(f"  Query: {q['label']}")
        print(f"{'─' * 70}")
        if q.get('compare'):
            comparison = pipeline.compare_all_algos(q['start'], q['end'], metric=q.get('metric', 'time'), depart=8.0)
            pipeline.print_comparison_table(comparison)
        else:
            resp = pipeline.route(q['start'], q['end'], algo=q.get('algo', AlgorithmName.ASTAR), metric=q.get('metric', 'time'), depart=8.0)
            print(resp)
    print('\n' + '=' * 70)
    print('  Interactive Mode')
    print('=' * 70)
    print('  Enter locations as:  stop_id  OR  lat,lon  (e.g. 36.77,3.06)')
    print("  Type 'q' to quit.\n")
    while True:
        raw_start = input('From [stop_id or lat,lon]: ').strip()
        if raw_start.lower() == 'q':
            break
        raw_end = input('To   [stop_id or lat,lon]: ').strip()
        if raw_end.lower() == 'q':
            break
        metric = input('Metric (time/distance/co2/weighted) [time]: ').strip() or 'time'
        algo_s = input(f"Algorithm ({'/'.join((a.value for a in AlgorithmName))}) [astar]: ").strip() or 'astar'
        try:
            algo = AlgorithmName(algo_s.lower())
        except ValueError:
            print(f'  Unknown algorithm {algo_s!r}. Defaulting to A*.')
            algo = AlgorithmName.ASTAR

        def parse_loc(s: str) -> Location:
            if ',' in s:
                parts = s.split(',')
                return (float(parts[0]), float(parts[1]))
            return s
        try:
            resp = pipeline.route(parse_loc(raw_start), parse_loc(raw_end), algo=algo, metric=metric, depart=8.0)
            print(resp)
        except Exception as exc:
            print(f'  Error: {exc}')

if __name__ == '__main__':
    import sys
    data_dir = sys.argv[1] if len(sys.argv) > 1 else 'data'
    _demo(data_dir)
