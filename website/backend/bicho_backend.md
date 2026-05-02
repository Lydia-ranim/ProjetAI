# Backend — What We Built and How

## Overview

We built a FastAPI backend that runs the real Algiers transit graph (1,314 stops) and exposes it to the frontend via a REST API. Before this, all routing happened in the browser using a hardcoded ~50-stop graph — wrong stops, straight lines instead of real roads, and no real data.

---

## Why We Needed a Backend

The frontend had a file `algiers-graph.ts` with ~50 manually typed stops and fake edges. The real dataset lives in `data/` and has:

- **1,314 stops** (bus, metro, tram, train, télépherique)
- **19,139 edges**
- **11,208 transfer links**
- **Real GPS road waypoints** for bus routes (`bus_geometries.json`)

Running that in the browser is not realistic. The backend loads it once at startup and serves results via API.

---

## Stack

| Tool | Version | Role |
|------|---------|------|
| FastAPI | 0.111.0 | Web framework |
| Uvicorn | 0.29.0 | ASGI server |
| Pydantic | 2.7.1 | Request/response validation |

---

## File Structure

```
website/backend/
├── main.py           ← the entire backend
├── requirements.txt
├── start.sh          ← runs uvicorn on port 8000
└── venv/             ← Python virtual environment
```

The algorithm files stay at the repo root (`ucs.py`, `A_star.py`, etc.) — `main.py` adds the repo root to `sys.path` so it can import them directly.

---

## How It Works

### Startup

When the server starts, it loads the graph **once** into memory:

```python
_router = TransitRouter(DATA_DIR)       # loads stops, edges, transfers
_astar  = AStarRouter.from_router(_router)
_bfs    = BFSRouter(DATA_DIR)
_bidir  = BidirectionalSearch(_router)
```

All four algorithm instances share the same graph data. No reload per request.

### Algorithms and What They Return

| Algorithm | Class | Label returned | Optimizes |
|-----------|-------|---------------|-----------|
| A* | `AStarRouter` | `fastest` | time |
| UCS / Dijkstra | `TransitRouter` | `cheapest` | weighted cost |
| Bidirectional A* | `BidirectionalSearch` | `greenest` | CO2 |

BFS is imported but not used in the route endpoint (kept for potential future use).

---

## Endpoints

### `POST /api/route`

Main endpoint. Takes start/end coordinates (or stop IDs), runs all three algorithms, returns all three routes.

**Request:**
```json
{
  "start": { "lat": 36.737, "lon": 3.086, "stopId": "optional" },
  "end":   { "lat": 36.752, "lon": 3.042 },
  "weights": { "time": 0.4, "cost": 0.3, "co2": 0.3 },
  "transportModes": { "bus": true, "metro": true, "tram": true, "walk": true, "telepherique": true, "escalator": true }
}
```

**Response:**
```json
{
  "routes": [
    {
      "id": "A*-fastest",
      "label": "fastest",
      "algorithmUsed": "A*",
      "found": true,
      "segments": [ ... ],
      "summary": {
        "totalTimeMin": 34,
        "totalCostDzd": 50,
        "totalCo2G": 120,
        "totalDistanceKm": 8.2,
        "numStops": 12,
        "nodesExplored": 340
      }
    }
  ]
}
```

Each **segment** represents one leg of the journey (e.g. "take bus 35 from Didouche to Tafourah"):

```json
{
  "mode": "bus",
  "lineId": "35",
  "fromStopId": "S0042",
  "toStopId": "S0198",
  "fromName": "Didouche Mourad",
  "toName": "Tafourah",
  "stops": ["S0042", "S0055", "S0198"],
  "polyline": [[36.737, 3.086], [36.741, 3.079], ...],
  "distanceKm": 2.1,
  "durationMin": 8,
  "costDzd": 25
}
```

The `polyline` field uses **real GPS road waypoints** from `bus_geometries.json` when available, falling back to straight lines between stops otherwise.

### `GET /api/stops`

Returns all 1,314 stops. Used by the frontend for the search/autocomplete dropdowns.

### `GET /api/nearest-stop?lat=&lon=&limit=5`

Finds the N closest stops to a map click. Used when the user picks a point on the map instead of typing a stop name.

---

## Stop Resolution

When a request comes in, we resolve start/end to actual stop IDs:

1. If `stopId` is provided and exists in the graph → use it directly
2. Otherwise → find the nearest stop by Haversine distance

---

## CORS

Set to allow all origins (`*`) so the frontend dev server on port 5173 can call the backend on port 8000 without browser errors.

---

## How to Run

```bash
cd website/backend
./start.sh
```

Or manually:
```bash
venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The `--reload` flag restarts the server automatically when you edit `main.py`.

---

## What the Frontend Needed to Change

The frontend already had `api.ts` with a `fetchRoutes()` function pointing to `POST /api/route` — it just had nothing answering it. Once the backend runs, the frontend calls it automatically. The `transit-store.ts` was updated to use the API response shape (segments with polylines) instead of the old in-browser algorithm output.
