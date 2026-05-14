"""
schedule.py — Shared transport schedule constants and utilities.
Extracted from BFS_Yanis_ZA3IM.py for cross-algorithm reuse.

All routing algorithms (UCS, A*, BFS, Bidirectional) import from this
module to ensure consistent schedule enforcement.
"""

import bisect
import csv
import os
from collections import defaultdict
from typing import Dict, List, Tuple


# ═══════════════════════════════════════════
# OPERATING HOURS  (fractional hours, 24h)
# ═══════════════════════════════════════════

WORKING_HOURS: Dict[str, Tuple[float, float]] = {
    'metro':        (5.0,  23.0),
    'tram':         (5.0,  23.0),
    'train':        (5.5,  22.0),
    'telepherique': (8.0,  19.0),
    'bus':          (5.5,  22.5),
    'walk':         (0.0,  24.0),
}

# ═══════════════════════════════════════════
# HEADWAY / FREQUENCY  (minutes)
# ═══════════════════════════════════════════

HEADWAY_MIN: Dict[str, float] = {
    'metro':        5.0,
    'tram':         8.0,
    'train':        30.0,
    'telepherique': 10.0,
    'bus':          15.0,
}

# ═══════════════════════════════════════════
# WALKING CONSTRAINT
# ═══════════════════════════════════════════

MAX_WALK_KM = 1.0   # Max intermediate walk distance (km)
                     # Exception: final-destination walks are unlimited


# ═══════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════

def in_service(mode: str, clock_hour: float) -> bool:
    """
    Check if a transport mode is operating at the given clock hour.

    Args:
        mode:       transport type string (metro, tram, bus, train, etc.)
        clock_hour: fractional hour (e.g. 8.5 = 08:30)

    Returns:
        True if the mode is in service, False otherwise.
    """
    if mode == "walk":
        return True
    o, c = WORKING_HOURS.get(mode, (0.0, 24.0))
    return o <= clock_hour < c


def avg_wait(mode: str) -> float:
    """
    Average waiting time (minutes) for a mode, computed as headway / 2.

    For trains, prefer train_wait() with exact schedule when available.
    """
    return HEADWAY_MIN.get(mode, 0.0) / 2.0


def train_wait(schedule: Dict[str, List[float]],
               stop_id: str, clock_hour: float) -> float:
    """
    Compute exact waiting time (minutes) for a train at stop_id.

    Uses binary search on the sorted departure list from stop_times.csv.

    Returns:
        Wait in minutes, or float('inf') if past the last train.
    """
    departures = schedule.get(stop_id)
    if not departures:
        # No schedule data — fall back to average headway
        return HEADWAY_MIN.get('train', 30.0) / 2.0

    idx = bisect.bisect_left(departures, clock_hour)
    if idx >= len(departures):
        # Past the last train of the day
        return float('inf')

    next_dep = departures[idx]
    wait_min = (next_dep - clock_hour) * 60.0
    return max(0.0, round(wait_min, 2))


def load_train_schedule(data_dir: str) -> Dict[str, List[float]]:
    """
    Load train departure times from stop_times.csv.

    Returns:
        Dict mapping stop_id → sorted list of departure hours.
        Empty dict if file not found.
    """
    schedule: Dict[str, List[float]] = {}
    path = os.path.join(data_dir, "stop_times.csv")
    if not os.path.isfile(path):
        return schedule

    raw: Dict[str, List[float]] = defaultdict(list)
    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                sid = row.get("stop_id", "").strip()
                dep = row.get("departure_time", "").strip()
                if not sid or not dep:
                    continue
                parts = dep.split(":")
                if len(parts) != 3:
                    continue
                try:
                    h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
                    raw[sid].append(h + m / 60.0 + s / 3600.0)
                except ValueError:
                    continue
    except Exception:
        pass

    for sid, times in raw.items():
        schedule[sid] = sorted(times)
    return schedule
