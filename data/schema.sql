-- Algiers Multi-Transport Transit Database Schema
-- Generated automatically

CREATE TABLE IF NOT EXISTS stops (
    stop_id       TEXT PRIMARY KEY,
    stop_name     TEXT NOT NULL,
    latitude      REAL NOT NULL,
    longitude     REAL NOT NULL,
    transport_type TEXT NOT NULL,  -- metro, tram, bus, train, telepherique
    is_hub        INTEGER DEFAULT 0,
    city          TEXT
);

CREATE TABLE IF NOT EXISTS routes (
    route_id       TEXT PRIMARY KEY,
    route_name     TEXT NOT NULL,
    transport_type TEXT NOT NULL,
    direction      TEXT
);

CREATE TABLE IF NOT EXISTS edges (
    edge_id        INTEGER PRIMARY KEY,
    from_stop_id   TEXT NOT NULL REFERENCES stops(stop_id),
    to_stop_id     TEXT NOT NULL REFERENCES stops(stop_id),
    distance_km    REAL NOT NULL,
    time_min       REAL NOT NULL,
    transport_type TEXT NOT NULL,
    route_id       TEXT REFERENCES routes(route_id)
);

CREATE TABLE IF NOT EXISTS transfers (
    transfer_id       TEXT PRIMARY KEY,
    from_stop_id      TEXT NOT NULL REFERENCES stops(stop_id),
    to_stop_id        TEXT NOT NULL REFERENCES stops(stop_id),
    distance_km       REAL NOT NULL,
    walk_time_min     REAL NOT NULL,
    transfer_penalty_min INTEGER DEFAULT 3,
    total_time_min    REAL NOT NULL,
    from_type         TEXT,
    to_type           TEXT
);

-- Performance indexes for pathfinding
CREATE INDEX idx_edges_from ON edges(from_stop_id);
CREATE INDEX idx_edges_to ON edges(to_stop_id);
CREATE INDEX idx_edges_type ON edges(transport_type);
CREATE INDEX idx_transfers_from ON transfers(from_stop_id);
CREATE INDEX idx_transfers_to ON transfers(to_stop_id);
CREATE INDEX idx_stops_type ON stops(transport_type);
CREATE INDEX idx_stops_coords ON stops(latitude, longitude);
