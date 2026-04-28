# ProjetAI — Algiers Multi-Transport Transit Network

Multi-modal transit dataset + UCS algorithm for route planning across **bus, metro, tram, train, and télépherique** in Algiers.

## Quick Start

```python
from ucs import TransitRouter

router = TransitRouter('data/')
result = router.find_route('M1_MARTYRS', 'TR01', metric='time')

print(f"Time: {result.total_time} min")
print(f"Distance: {result.total_dist} km")
print(f"Fare: {result.total_fare} DA")

for seg in result.segments:
    print(f"  {seg.transport_type.upper()}: {seg.from_stop} → {seg.to_stop} ({seg.time_min} min)")
```

## Dataset

All files in `data/`:

| File | Description |
|------|-------------|
| `stops.csv` | 1,314 stops (nodes) with coordinates |
| `edges.csv` | 19,139 directed edges (the graph) |
| `routes.csv` | 228 routes/lines |
| `transfers.csv` | 11,208 walking/transfer edges |
| `graph_adjacency.json` | Adjacency list — ready for any algorithm |
| `graph_edge_list.csv` | Simple edge list format |
| `transit_graph.graphml` | GraphML — for NetworkX |
| `bus_geometries.json` | GPS road geometry for bus paths (map rendering) |
| `schema.sql` | SQL CREATE TABLE statements |
| `inserts.sql` | SQL INSERT statements |

## Graph Structure

- **Nodes**: 1,314 stops across 5 transport types
- **Edges**: 19,139 directed weighted connections
- **Fully connected**: 100% of nodes reachable
- **Edge weights**: `distance_km` and `time_min`

### Loading the graph

```python
import json

with open('data/graph_adjacency.json') as f:
    graph = json.load(f)

# graph["M1_MARTYRS"] → [{"to": "M1_BOUMEN", "dist": 2.317, "time": 3.0, "type": "metro", "route": "METRO_L1"}, ...]
```

### For NetworkX

```python
import networkx as nx
G = nx.read_graphml('data/transit_graph.graphml')
path = nx.shortest_path(G, 'M1_MARTYRS', 'TR35', weight='time_min')
```

## UCS Algorithm (`ucs.py`)

- Binary heap priority queue
- Predecessor-based path reconstruction
- Fare calculation: bus charges only on line change
- Nearest-stop finder by coordinates
- Supports `time` and `distance` optimization

### CLI Mode

```bash
python ucs.py data/
```

## Fare Table (DA)

| Mode | Fare |
|------|------|
| Bus | 30 per line (only on line change) |
| Metro | 50 |
| Tram | 40 |
| Train | 50 |
| Télépherique | 30 |
| Walk | 0 |

## Bus Road Geometry

`bus_geometries.json` contains real GPS waypoints for bus edges (from 61K trace points). Use for map rendering:

```python
import json
geom = json.load(open('data/bus_geometries.json'))
# Key format: "from_stop_id|to_stop_id|route_id"
# Value: [[lat, lon], [lat, lon], ...] — road waypoints
```
