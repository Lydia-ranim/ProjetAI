"""
ucs.py — Uniform Cost Search for Algiers Multi-Transport Transit Network

Usage:
    from ucs import TransitRouter
    
    router = TransitRouter('output/')
    result = router.find_route('M1_MARTYRS', 'TR35', metric='time')
    
    print(result['total_time'])    # minutes
    print(result['total_dist'])    # km
    print(result['total_fare'])    # DA
    print(result['segments'])      # step-by-step breakdown
"""

import heapq
import json
import csv
import os
import math
from dataclasses import dataclass, field
from typing import Optional


# ═══════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════

@dataclass
class Stop:
    stop_id: str
    name: str
    lat: float
    lon: float
    transport_type: str
    is_hub: bool
    city: str


@dataclass
class Edge:
    to_id: str
    distance_km: float
    time_min: float
    transport_type: str
    route_id: str


@dataclass
class Segment:
    """One leg of a journey on a single transport mode/line."""
    transport_type: str
    route_id: str
    from_stop: str
    to_stop: str
    stops: list
    distance_km: float
    time_min: float
    fare: int


@dataclass
class RouteResult:
    """Complete result of a route search."""
    found: bool
    path: list                     # ordered stop IDs
    edges: list                    # Edge objects along path
    segments: list                 # grouped Segment objects
    total_time: float              # minutes
    total_dist: float              # km
    total_fare: int                # DA
    nodes_explored: int            # UCS stats


# ═══════════════════════════════════════════
# FARE TABLE (DA)
# ═══════════════════════════════════════════

FARES = {
    'metro': 50,
    'tram': 40,
    'bus': 30,         # per line (only on line change)
    'train': 50,
    'telepherique': 30,
    'walk': 0,
}


# ═══════════════════════════════════════════
# TRANSIT ROUTER
# ═══════════════════════════════════════════

class TransitRouter:
    """
    Multi-modal transit router using Uniform Cost Search.
    
    Supports 5 transport modes: metro, tram, bus, train, telepherique.
    Walking/transfer edges connect modes.
    
    Bus fare is charged ONLY when switching to a different bus line.
    Other modes charge once per boarding.
    """

    def __init__(self, data_dir: str):
        """
        Load graph data from CSV or JSON files.
        
        Args:
            data_dir: path to directory containing stops.csv + edges.csv
                      OR stops.json + graph.json
        """
        self.stops = {}      # stop_id → Stop
        self.graph = {}      # stop_id → [Edge, ...]
        self._load(data_dir)

    def _load(self, data_dir: str):
        """Load from JSON (web/data/) or CSV (output/)."""
        json_stops = os.path.join(data_dir, 'stops.json')
        json_graph = os.path.join(data_dir, 'graph.json')
        csv_stops = os.path.join(data_dir, 'stops.csv')
        csv_edges = os.path.join(data_dir, 'edges.csv')

        # Prefer JSON (faster to load)
        if os.path.exists(json_stops) and os.path.exists(json_graph):
            self._load_json(json_stops, json_graph)
        elif os.path.exists(csv_stops) and os.path.exists(csv_edges):
            self._load_csv(csv_stops, csv_edges)
        else:
            raise FileNotFoundError(f"No data files found in {data_dir}")

    def _load_json(self, stops_path: str, graph_path: str):
        with open(stops_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        for sid, s in raw.items():
            self.stops[sid] = Stop(
                stop_id=sid, name=s['name'], lat=s['lat'], lon=s['lon'],
                transport_type=s['type'], is_hub=s.get('hub', False),
                city=s.get('city', '')
            )

        with open(graph_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        for from_id, edges in raw.items():
            self.graph[from_id] = [
                Edge(to_id=e['t'], distance_km=e['d'], time_min=e['m'],
                     transport_type=e['y'], route_id=e['r'])
                for e in edges
            ]

    def _load_csv(self, stops_path: str, edges_path: str):
        with open(stops_path, 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                sid = str(row['stop_id'])
                self.stops[sid] = Stop(
                    stop_id=sid, name=row['stop_name'],
                    lat=float(row['latitude']), lon=float(row['longitude']),
                    transport_type=row['transport_type'],
                    is_hub=str(row.get('is_hub', '')).lower() == 'true',
                    city=row.get('city', '')
                )

        with open(edges_path, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                fid = str(row['from_stop_id'])
                if fid not in self.graph:
                    self.graph[fid] = []
                self.graph[fid].append(Edge(
                    to_id=str(row['to_stop_id']),
                    distance_km=float(row['distance_km']),
                    time_min=float(row['time_min']),
                    transport_type=row['transport_type'],
                    route_id=row['route_id']
                ))

    # ───────────────────────────────────────
    # NEAREST STOP FINDER
    # ───────────────────────────────────────

    def find_nearest(self, lat: float, lon: float, 
                     transport_type: str = None, limit: int = 1) -> list:
        """
        Find nearest stop(s) to a coordinate.
        
        Args:
            lat, lon: query coordinates
            transport_type: filter by type (optional)
            limit: number of results
            
        Returns:
            list of (stop_id, distance_km) tuples
        """
        results = []
        for sid, stop in self.stops.items():
            if transport_type and stop.transport_type != transport_type:
                continue
            d = self._haversine(lat, lon, stop.lat, stop.lon)
            results.append((sid, d))
        results.sort(key=lambda x: x[1])
        return results[:limit]

    # ───────────────────────────────────────
    # UCS — UNIFORM COST SEARCH
    # ───────────────────────────────────────

    def find_route(self, start_id: str, goal_id: str,
                   metric: str = 'time') -> RouteResult:
        """
        Find optimal route using Uniform Cost Search.
        
        Args:
            start_id: origin stop ID
            goal_id: destination stop ID
            metric: 'time' (minutes) or 'distance' (km)
            
        Returns:
            RouteResult with path, segments, totals, and fare
        """
        if start_id not in self.stops:
            raise ValueError(f"Unknown start stop: {start_id}")
        if goal_id not in self.stops:
            raise ValueError(f"Unknown goal stop: {goal_id}")
        if start_id == goal_id:
            return RouteResult(
                found=True, path=[start_id], edges=[], segments=[],
                total_time=0, total_dist=0, total_fare=0, nodes_explored=0
            )

        # Priority queue: (cost, counter, node_id)
        # counter breaks ties to maintain FIFO order
        counter = 0
        pq = [(0.0, counter, start_id)]
        
        # Best known cost + predecessor for path reconstruction
        best = {start_id: (0.0, None, None)}   # node → (cost, prev_node, edge)
        visited = set()
        nodes_explored = 0

        while pq:
            cost, _, node = heapq.heappop(pq)

            if node in visited:
                continue
            visited.add(node)
            nodes_explored += 1

            # Goal reached
            if node == goal_id:
                path, edges = self._reconstruct(best, goal_id)
                segments = self._build_segments(path, edges)
                total_time = sum(e.time_min for e in edges)
                total_dist = sum(e.distance_km for e in edges)
                total_fare = self._compute_fare(edges)

                return RouteResult(
                    found=True, path=path, edges=edges,
                    segments=segments, total_time=round(total_time, 2),
                    total_dist=round(total_dist, 4),
                    total_fare=total_fare,
                    nodes_explored=nodes_explored
                )

            # Expand neighbors
            for edge in self.graph.get(node, []):
                if edge.to_id in visited:
                    continue

                edge_cost = edge.time_min if metric == 'time' else edge.distance_km
                new_cost = cost + edge_cost

                if edge.to_id not in best or new_cost < best[edge.to_id][0]:
                    best[edge.to_id] = (new_cost, node, edge)
                    counter += 1
                    heapq.heappush(pq, (new_cost, counter, edge.to_id))

        # No path found
        return RouteResult(
            found=False, path=[], edges=[], segments=[],
            total_time=0, total_dist=0, total_fare=0,
            nodes_explored=nodes_explored
        )

    # ───────────────────────────────────────
    # PATH RECONSTRUCTION
    # ───────────────────────────────────────

    def _reconstruct(self, best: dict, goal_id: str):
        """Reconstruct path from predecessor map."""
        path = []
        edges = []
        cur = goal_id

        while cur is not None:
            path.append(cur)
            cost, prev, edge = best[cur]
            if edge is not None:
                edges.append(edge)
            cur = prev

        path.reverse()
        edges.reverse()
        return path, edges

    # ───────────────────────────────────────
    # SEGMENT GROUPING
    # ───────────────────────────────────────

    def _build_segments(self, path: list, edges: list) -> list:
        """Group consecutive edges of same type+route into segments."""
        if not edges:
            return []

        segments = []
        cur = None

        for i, edge in enumerate(edges):
            if cur and cur.transport_type == edge.transport_type and cur.route_id == edge.route_id:
                # Extend current segment
                cur.stops.append(path[i + 1])
                cur.distance_km += edge.distance_km
                cur.time_min += edge.time_min
                cur.to_stop = path[i + 1]
            else:
                # Finalize previous segment
                if cur:
                    cur.distance_km = round(cur.distance_km, 4)
                    cur.time_min = round(cur.time_min, 2)
                    segments.append(cur)

                # Start new segment
                cur = Segment(
                    transport_type=edge.transport_type,
                    route_id=edge.route_id,
                    from_stop=path[i],
                    to_stop=path[i + 1],
                    stops=[path[i], path[i + 1]],
                    distance_km=edge.distance_km,
                    time_min=edge.time_min,
                    fare=0  # computed later
                )

        if cur:
            cur.distance_km = round(cur.distance_km, 4)
            cur.time_min = round(cur.time_min, 2)
            segments.append(cur)

        # Assign fares to segments
        last_bus_route = None
        last_nonwalk_type = None

        for seg in segments:
            if seg.transport_type == 'bus':
                if seg.route_id != last_bus_route:
                    seg.fare = FARES['bus']
                    last_bus_route = seg.route_id
                else:
                    seg.fare = 0
            elif seg.transport_type == 'walk':
                seg.fare = 0
            else:
                if seg.transport_type != last_nonwalk_type:
                    seg.fare = FARES.get(seg.transport_type, 0)
                    last_nonwalk_type = seg.transport_type
                else:
                    seg.fare = 0

        return segments

    # ───────────────────────────────────────
    # FARE CALCULATION
    # ───────────────────────────────────────

    def _compute_fare(self, edges: list) -> int:
        """
        Compute total fare.
        Bus: charge only on line change.
        Other modes: charge once per boarding.
        Walk: free.
        """
        total = 0
        last_bus_route = None
        last_nonwalk_type = None

        for e in edges:
            if e.transport_type == 'bus':
                if e.route_id != last_bus_route:
                    total += FARES['bus']
                    last_bus_route = e.route_id
            elif e.transport_type != 'walk':
                if e.transport_type != last_nonwalk_type:
                    total += FARES.get(e.transport_type, 0)
                    last_nonwalk_type = e.transport_type

        return total

    # ───────────────────────────────────────
    # UTILITIES
    # ───────────────────────────────────────

    @staticmethod
    def _haversine(lat1, lon1, lat2, lon2):
        """Haversine distance in km."""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 6371 * 2 * math.asin(math.sqrt(a))

    def get_stop(self, stop_id: str) -> Optional[Stop]:
        """Get stop info by ID."""
        return self.stops.get(stop_id)

    def get_stop_name(self, stop_id: str) -> str:
        """Get stop name by ID."""
        s = self.stops.get(stop_id)
        return s.name if s else stop_id

    @property
    def num_stops(self) -> int:
        return len(self.stops)

    @property
    def num_edges(self) -> int:
        return sum(len(v) for v in self.graph.values())


# ═══════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════

if __name__ == '__main__':
    import sys
    import time

    data_dir = sys.argv[1] if len(sys.argv) > 1 else 'output'
    
    print(f"Loading graph from {data_dir}...")
    t0 = time.time()
    router = TransitRouter(data_dir)
    print(f"  Loaded in {time.time()-t0:.2f}s: {router.num_stops} stops, {router.num_edges} edges")

    # Interactive mode
    while True:
        print("\n" + "=" * 50)
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

        metric = input("Metric (time/distance) [time]: ").strip() or 'time'

        print(f"\nSearching {start} → {goal} (optimize: {metric})...")
        t0 = time.time()
        result = router.find_route(start, goal, metric)
        elapsed = time.time() - t0

        if not result.found:
            print("  No route found!")
            continue

        print(f"\n  ✅ Route found in {elapsed*1000:.1f}ms ({result.nodes_explored} nodes explored)")
        print(f"  ⏱  Time:     {result.total_time:.1f} min")
        print(f"  📏 Distance: {result.total_dist:.2f} km")
        print(f"  💰 Fare:     {result.total_fare} DA")
        print(f"  📍 Stops:    {len(result.path)}")
        print(f"\n  Path:")
        for seg in result.segments:
            from_name = router.get_stop_name(seg.from_stop)
            to_name = router.get_stop_name(seg.to_stop)
            icon = {'metro':'🚇','tram':'🚊','bus':'🚌','train':'🚂',
                     'telepherique':'🚡','walk':'🚶'}.get(seg.transport_type,'•')
            fare_str = f" | {seg.fare} DA" if seg.fare > 0 else ""
            print(f"    {icon} {from_name} → {to_name}")
            print(f"       {seg.transport_type.upper()} {seg.route_id} | "
                  f"{len(seg.stops)} stops | {seg.distance_km:.2f} km | "
                  f"{seg.time_min:.1f} min{fare_str}")
