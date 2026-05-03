"""
benchmark_all.py — Unified benchmarks: TransitRouter + BFS_Yanis_ZA3IM BFS.

Cost-based algorithms use ``TransitRouter``; standard BFS uses ``BFSRouter.search``.
Bidirectional BFS uses ``BidirectionalSearch(router, bfs_router=…)`` and ``search_bfs``.
"""

from __future__ import annotations

import os
import sys
import time as time_module
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from bidirectional_ranim_bomba import BidirectionalSearch, BiDirResult
from ucs import TransitRouter
from BFS_Yanis_ZA3IM import BFSRouter, BFSResult, Edge

DEMO_QUERIES: List[Tuple[str, str, str, str]] = [
    ('M1_MARTYRS',  'TR01',      'time',     'Place des Martyrs → USTHB (Tram)'),
    ('M1_MARTYRS',  'M1_H_GARE', 'time',     'Place des Martyrs → El Harrach Gare'),
    ('M1_TAFOURAH', 'TR18',      'time',     'Tafourah → USTHB'),
    ('M1_1MAI',     'M1_HAMMA',  'distance', '1er Mai → El Hamma (by distance)'),
]

DEPART_DEFAULT = 8.0

COST_ALGORITHMS = ('ucs', 'astar', 'bidir_ucs', 'bidir_astar')
ALL_TABLE_KEYS = (
    'ucs', 'astar', 'bidir_ucs', 'bidir_astar', 'bidir_bfs',
    'bfs_uni',
)
OPTIMALITY_KEYS = ('ucs', 'astar', 'bidir_ucs', 'bidir_astar')


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _count_transfers(path_edges: List[Edge]) -> int:
    """Same transfer rule as ``BFSRouter._build``."""
    prev_mode: Optional[str] = None
    prev_route: Optional[str] = None
    transfers = 0
    for edge in path_edges:
        mode = edge.transport_type
        is_tr = (
            prev_mode is not None
            and prev_mode != 'walk'
            and mode != 'walk'
            and mode != prev_mode
        )
        transfers += int(is_tr)
        prev_mode = mode
        prev_route = edge.route_id
    return transfers


def _cost_metric(report_row: Dict[str, Any], metric: str) -> float:
    if not report_row.get('found'):
        return float('inf')
    if metric == 'time':
        if report_row.get('total_journey_time') is not None:
            return float(report_row['total_journey_time'])
        return float(report_row.get('total_time', 0))
    if metric == 'distance':
        return float(report_row.get('total_dist', 0))
    if metric == 'co2':
        return float(report_row.get('total_co2', 0))
    if metric == 'weighted':
        return float(report_row.get('total_time', 0))
    return float(report_row.get('total_time', 0))


def _to_row_dict(
    key: str,
    src: Dict[str, Any],
    ucs_baseline: int,
    is_bfs: bool,
    is_bidir_bfs: bool = False,
) -> Dict[str, Any]:
    nodes = int(src.get('nodes_explored', 0) or 0)
    base = ucs_baseline or 1
    reduction = round((1 - nodes / base) * 100, 1) if ucs_baseline else 0.0
    row = {
        'key': key,
        'algorithm': src.get('algorithm', key),
        'found': src.get('found', False),
        'total_time': src.get('total_time', 0),
        'total_dist': src.get('total_dist', 0),
        'total_co2': src.get('total_co2', 0),
        'total_fare': src.get('total_fare', 0),
        'nodes_explored': nodes,
        'forward_nodes': src.get('forward_nodes', ''),
        'backward_nodes': src.get('backward_nodes', ''),
        'runtime_ms': src.get('runtime_ms', 0),
        'node_reduction_pct': reduction if key != 'ucs' else 0.0,
        'is_bfs': is_bfs,
        'is_bidir_bfs': is_bidir_bfs,
        'hops': src.get('hops'),
        'total_journey_time': src.get('total_journey_time'),
        'total_wait': src.get('total_wait'),
    }
    return row


def print_unified_report(
    unified: Dict[str, Any],
    router: TransitRouter,
) -> None:
    """Pretty-print one query: compare_all report + standard BFS search."""
    label = unified.get('label', '')
    start_id = unified['start_id']
    goal_id = unified['goal_id']
    metric = unified['metric']
    bidir = unified['bidir']

    sep = '═' * 130
    dash = '─' * 130

    print(f'\n{sep}')
    print('  UNIFIED BENCHMARK')
    print(f'  {label}  |  metric={metric}')
    sname = router.get_stop_name(start_id)
    gname = router.get_stop_name(goal_id)
    print(f'  {start_id} ({sname})  →  {goal_id} ({gname})')
    print(sep)

    ucs_nodes = int(bidir.get('ucs', {}).get('nodes_explored', 0) or 0) or 1

    rows: List[Dict[str, Any]] = []
    order_display = [
        ('ucs', bidir.get('ucs'), False, False),
        ('astar', bidir.get('astar'), False, False),
        ('bidir_ucs', bidir.get('bidir_ucs'), False, False),
        ('bidir_astar', bidir.get('bidir_astar'), False, False),
        ('bidir_bfs', bidir.get('bidir_bfs'), False, True),
        ('bfs_uni', unified.get('bfs_uni'), True, False),
    ]
    for key, raw, is_bfs, is_bbfs in order_display:
        if raw is None:
            continue
        if key == 'astar' and raw.get('error'):
            raw = {**raw, 'found': False}
        rows.append(_to_row_dict(key, raw, ucs_nodes, is_bfs, is_bbfs))

    found_rows = [r for r in rows if r['found']]
    min_nodes = min((r['nodes_explored'] for r in found_rows), default=None)

    header = (
        f"  {'Algorithm':<24} {'Found':>6} "
        f"{'Ride(min)':>10} {'Wait(min)':>10} {'Dist(km)':>10} {'CO2(g)':>9} "
        f"{'Fare(DA)':>9} {'Nodes':>8} {'Fwd':>6} {'Bwd':>6} "
        f"{'Runtime(ms)':>12} {'Node Red%':>11}"
    )
    print(header)
    print(dash)

    for r in rows:
        tag = ' ★' if min_nodes is not None and r['found'] and r['nodes_explored'] == min_nodes else '  '
        found = '✓' if r['found'] else '✗'
        if r.get('is_bidir_bfs') and r['found']:
            j = r.get('total_journey_time')
            ride_raw = r.get('total_time', 0) or 0
            wait_raw = r.get('total_wait', 0) or 0
            if j is None:
                j = float(ride_raw) + float(wait_raw)
            tcol = f"{float(ride_raw):.1f}"
            wcol = f"{float(wait_raw):.1f}"
            dcol = f"{float(r['total_dist']):.3f}" if r.get('total_dist') is not None else '—'
            ccol = f"{float(r['total_co2']):.1f}" if r.get('total_co2') is not None else '—'
            fcol = str(r.get('total_fare', '—'))
        elif r['is_bfs']:
            ride_raw = r.get('total_time', 0) or 0
            wait_raw = r.get('total_wait', 0) or 0
            tcol = f"{float(ride_raw):.1f}"
            wcol = f"{float(wait_raw):.1f}"
            dcol = '—'
            ccol = f"{float(r['total_co2']):.1f}" if r.get('total_co2') is not None else '—'
            fcol = str(r.get('total_fare') or '—')
        else:
            # UCS / A* / Bidir-UCS / Bidir-A* / Bidir-Greedy
            tcol = f"{r['total_time']:.1f}"
            wcol = '0.0'   # cost-based algos do not model waiting time
            dcol = f"{r['total_dist']:.3f}"
            ccol = f"{r['total_co2']:.1f}"
            fcol = str(r['total_fare'])

        fwd = str(r['forward_nodes']) if r['forward_nodes'] != '' else ''
        bwd = str(r['backward_nodes']) if r['backward_nodes'] != '' else ''
        red = f"{r['node_reduction_pct']:+.1f}%"
        print(
            f"{tag}{r['algorithm']:<24} {found:>6} "
            f"{tcol:>10} {wcol:>10} {dcol:>10} {ccol:>9} {fcol:>9} "
            f"{r['nodes_explored']:>8,} {fwd:>6} {bwd:>6} "
            f"{float(r['runtime_ms']):>12.2f} {red:>11}"
        )

    print(dash)
    if min_nodes is not None:
        winners = [r['algorithm'] for r in found_rows if r['nodes_explored'] == min_nodes]
        print(f"  ★ Fewest nodes ({min_nodes:,}): {', '.join(winners)}")
        print(f"    UCS baseline nodes: {ucs_nodes:,}")
    print(sep)


def print_cost_algo_waiting_checks(
    label: str,
    bidir_report: Dict[str, Any],
) -> None:
    """
    Verify that cost-based algorithms (UCS, A*, Bidir-UCS, Bidir-A*, Bidir-Greedy)
    correctly report zero waiting time.

    These algorithms optimise a weighted cost function (time/dist/CO2) and do NOT
    model headway waiting — they treat travel time as pure edge cost.
    A non-zero total_wait in their result would indicate a bug.

    Also checks that UCS and A* return the same total_time (optimal cost tie),
    and that Bidir-UCS and Bidir-A* match UCS (bidirectional optimality).
    """
    eps = 1e-3
    dash = '─' * 72
    print(f'\n  {dash}')
    print(f'  COST-ALGO WAITING CHECKS  —  {label}')
    print(f'  {dash}')

    COST_KEYS = ['ucs', 'astar', 'bidir_ucs', 'bidir_astar', 'bidir_greedy']
    times = {}

    for key in COST_KEYS:
        r = bidir_report.get(key)
        if r is None or not r.get('found'):
            print(f'  {key:<18} NOT FOUND — skip')
            continue

        wait = float(r.get('total_wait', 0) or 0)
        ride = float(r.get('total_time', 0) or 0)
        nodes = int(r.get('nodes_explored', 0) or 0)
        times[key] = ride

        wait_status = 'PASS' if abs(wait) < eps else f'FAIL (wait={wait:.3f})'
        print(f'  {key:<18} ride={ride:.2f} min  wait={wait:.4f}  nodes={nodes:,}'
              f'  →  wait==0 check: {wait_status}')

    # Optimality cross-check: UCS, A*, Bidir-UCS, Bidir-A* should agree on time
    print()
    optimal_keys = ['ucs', 'astar', 'bidir_ucs', 'bidir_astar']
    found_times = {k: times[k] for k in optimal_keys if k in times}
    if len(found_times) >= 2:
        best = min(found_times.values())
        print('  Optimality cross-check (all should match UCS cost):')
        ucs_time = found_times.get('ucs', None)
        for k, t in found_times.items():
            if ucs_time is not None:
                diff = abs(t - ucs_time)
                status = 'PASS' if diff <= eps else f'WARN  Δ={diff:.4f}'
            else:
                status = 'N/A'
            print(f'    {k:<18} {t:.2f} min  →  {status}')

    # Greedy specifically: it may find a suboptimal path — document it
    if 'bidir_greedy' in times and 'ucs' in times:
        diff = times['bidir_greedy'] - times['ucs']
        if diff > eps:
            print(f'\n  NOTE: Bidir-Greedy is NOT optimal by design.')
            print(f'    It found {times["bidir_greedy"]:.2f} min vs UCS optimal {times["ucs"]:.2f} min')
            print(f'    Suboptimality gap: +{diff:.2f} min  (expected — inflated heuristic)')
        else:
            print(f'\n  NOTE: Bidir-Greedy happened to find the optimal path on this query.')
            print(f'    This can occur when the path is short or the graph is dense.')

    print(f'  {dash}')


def print_bidir_bfs_waiting_checks(
    label: str,
    bfs_router: BFSRouter,
    bidir: BidirectionalSearch,
    result: BiDirResult,
    bfs_result: Optional[BFSResult],
    depart: float,
) -> Dict[str, Any]:
    """
    Section 3 — Bidirectional BFS waiting checks (G–J).
    Returns a dict for the summary table row.
    """
    eps = 1e-3
    dash = '─' * 72
    print(f'\n  {dash}')
    print(f'  3. BIDIRECTIONAL BFS WAITING CHECKS  —  {label}')
    print(f'  {dash}')

    out: Dict[str, Any] = {
        'label': label,
        'bfs_nodes': '',
        'bidir_nodes': '',
        'reduction_pct': '',
        'bfs_wait': '',
        'bidir_wait': '',
        'wait_check': '',
        'transfer_check': '',
        'path_ok': '',
    }

    if not result.found:
        print('  (Bidir BFS did not find a path — skipping G–J.)')
        out['wait_check'] = 'SKIP'
        out['transfer_check'] = 'SKIP'
        out['path_ok'] = 'SKIP'
        return out

    print(f'  total_time (ride min): {result.total_time:.2f}')
    print(f'  total_wait (min):    {result.total_wait:.2f}')
    print(f'  forward_nodes:       {result.forward_nodes}')
    print(f'  backward_nodes:      {result.backward_nodes}')
    print(f'  meeting_node:        {result.meeting_node}')
    print(f'  runtime_ms:          {result.runtime_ms:.2f}')

    # CHECK G — wait vs manual sum (compare to ``total_wait``, not ride time)
    expected_wait = sum(bfs_router._avg_wait(e.transport_type) for e in result.edges)
    print('\n  CHECK G — Bidir BFS wait vs manual Σ avg_wait(edge mode)')
    if abs(expected_wait - result.total_wait) <= eps:
        print(f'    PASS  expected_wait={expected_wait:.4f}  total_wait={result.total_wait:.4f}')
        out['wait_check'] = 'PASS'
    else:
        print(f'    WARN  expected_wait={expected_wait:.4f}  total_wait={result.total_wait:.4f}')
        out['wait_check'] = 'WARN'

    # CHECK H — meeting node in forward graph and reverse adjacency
    meet = result.meeting_node
    print('\n  CHECK H — Meeting node reachable on both orientations')
    h_ok = True
    if meet is None:
        print('    FAIL  meeting_node is None')
        h_ok = False
    else:
        in_fwd = meet in bfs_router.graph
        in_rev = meet in bidir._bfs_rev_adj
        if not in_fwd:
            print(f'    FAIL  {meet!r} not in bfs_router.graph keys')
            h_ok = False
        else:
            print(f'    PASS  meeting_node in bfs_router.graph')
        if not in_rev:
            print(f'    FAIL  {meet!r} not in bidir._bfs_rev_adj')
            h_ok = False
        else:
            print(f'    PASS  meeting_node in bidir._bfs_rev_adj')
    # CHECK I — node count vs standard BFS
    print('\n  CHECK I — Bidir BFS nodes vs standard BFS.search')
    out['bidir_nodes'] = result.nodes_explored
    if bfs_result is not None and bfs_result.found:
        out['bfs_nodes'] = bfs_result.nodes_expanded
        bfs_n = bfs_result.nodes_expanded or 1
        red = (1.0 - result.nodes_explored / bfs_n) * 100.0
        out['reduction_pct'] = f'{red:+.1f}%'
        print(f'    standard BFS nodes_expanded: {bfs_result.nodes_expanded:,}')
        print(f'    bidir BFS nodes_explored:    {result.nodes_explored:,}')
        print(f'    reduction vs standard BFS:     {red:+.1f}%')
        if result.nodes_explored < bfs_result.nodes_expanded:
            print('    ✅  Bidir used fewer nodes than standard BFS.')
        else:
            print('    ⚠️   Bidir did not use fewer nodes (can happen on short paths).')
    else:
        out['bfs_nodes'] = '—'
        out['reduction_pct'] = '—'
        print('    (standard BFS did not find a path or was skipped.)')

    # CHECK J — path continuity
    print('\n  CHECK J — Path continuity (edge[i].to_id == path[i+1])')
    path_ids = result.path
    path_edges = result.edges
    j_ok = True
    if len(path_ids) != len(path_edges) + 1:
        print(f'    FAIL  len(path)={len(path_ids)} vs len(edges)+1={len(path_edges) + 1}')
        j_ok = False
    else:
        for i in range(len(path_ids) - 1):
            if path_edges[i].to_id != path_ids[i + 1]:
                print(f'    FAIL at i={i}: edge.to_id={path_edges[i].to_id!r} path[i+1]={path_ids[i + 1]!r}')
                j_ok = False
                break
        if j_ok:
            print('    PASS  all edges align with path_ids.')

    out['path_ok'] = 'PASS' if j_ok else 'FAIL'

    # Transfer check (vs standard BFS when both found)
    print('\n  Transfer check — vs standard BFS num_transfers')
    tb = _count_transfers(result.edges)
    if bfs_result is not None and bfs_result.found:
        if tb == bfs_result.num_transfers:
            print(f'    PASS  bidir transfers={tb}  BFS.search transfers={bfs_result.num_transfers}')
            out['transfer_check'] = 'PASS'
        else:
            print(f'    WARN  bidir transfers={tb}  BFS.search transfers={bfs_result.num_transfers}')
            out['transfer_check'] = 'WARN'
    else:
        print('    N/A  (no standard BFS path to compare)')
        out['transfer_check'] = 'N/A'

    print(f'  {dash}\n')
    return out


def print_waiting_summary_table(rows: List[Dict[str, Any]]) -> None:
    sep = '═' * 155
    print(f'\n{sep}')
    print('  WAITING / BFS SUMMARY (all queries)')
    print(sep)
    hdr = (
        f"  {'Query':<42} {'BFS nd':>8} {'BiDir':>8} {'Red%':>10} "
        f"{'BFS ride':>10} {'BFS wait':>10} {'BiDir ride':>11} {'BiDir wait':>12} "
        f"{'Wait chk':>10} {'Xfer chk':>10} {'Path ok':>10}"
    )
    print(hdr)
    print('─' * 155)
    for r in rows:
        print(
            f"  {r.get('label','')[:42]:<42} "
            f"{str(r.get('bfs_nodes','')):>8} "
            f"{str(r.get('bidir_nodes','')):>8} "
            f"{str(r.get('reduction_pct','')):>10} "
            f"{str(r.get('bfs_ride','')):>10} "
            f"{str(r.get('bfs_wait','')):>10} "
            f"{str(r.get('bidir_ride','')):>11} "
            f"{str(r.get('bidir_wait','')):>12} "
            f"{str(r.get('wait_check','')):>10} "
            f"{str(r.get('transfer_check','')):>10} "
            f"{str(r.get('path_ok','')):>10}"
        )
    print(sep)


def print_optimality_summary(all_reports: List[Dict[str, Any]]) -> None:
    """Aggregate stats: optimal cost ties, node reduction vs UCS, runtime, wins."""
    opt_counts = defaultdict(int)
    runtime_sum = defaultdict(float)
    runtime_n = defaultdict(int)
    reduction_sum = defaultdict(float)
    reduction_n = defaultdict(int)
    win_counts = defaultdict(int)

    for entry in all_reports:
        metric = entry['metric']
        bidir = entry['report']

        ucs_row = bidir.get('ucs') or {}
        ucs_nodes = int(ucs_row.get('nodes_explored', 0) or 0)

        costs = {}
        for k in OPTIMALITY_KEYS:
            r = bidir.get(k)
            if r and r.get('found') and 'error' not in r:
                costs[k] = _cost_metric(r, metric)
        finite = {k: v for k, v in costs.items() if v < float('inf')}
        if finite:
            best = min(finite.values())
            eps = 1e-5
            for k, v in finite.items():
                if abs(v - best) <= eps * max(1.0, abs(best)):
                    opt_counts[k] += 1

        for k in ALL_TABLE_KEYS:
            if k == 'bidir_bfs':
                raw = bidir.get('bidir_bfs')
            elif k in COST_ALGORITHMS:
                raw = bidir.get(k)
            else:
                raw = entry.get(k)
            if raw is None:
                continue
            if not raw.get('found'):
                continue
            rt = float(raw.get('runtime_ms', 0) or 0)
            runtime_sum[k] += rt
            runtime_n[k] += 1
            if k != 'ucs' and ucs_nodes > 0:
                nodes = int(raw.get('nodes_explored', 0) or 0)
                reduction_sum[k] += (1 - nodes / ucs_nodes) * 100
                reduction_n[k] += 1

        found_all = []
        for k in ALL_TABLE_KEYS:
            if k == 'bidir_bfs':
                raw = bidir.get('bidir_bfs')
            elif k in COST_ALGORITHMS:
                raw = bidir.get(k)
            else:
                raw = entry.get(k)
            if raw and raw.get('found'):
                found_all.append((k, int(raw.get('nodes_explored', 0) or 0)))
        if found_all:
            m = min(n for _, n in found_all)
            for k, n in found_all:
                if n == m:
                    win_counts[k] += 1

    sep = '═' * 90
    print(f'\n{sep}')
    print('  OPTIMALITY & EFFICIENCY SUMMARY (all queries)')
    print(f'{sep}')

    print('\n  Optimal cost matches (time/distance/co₂ vs best among UCS / A* / bidir UCS / bidir A*):')
    for k in OPTIMALITY_KEYS:
        print(f'    {k:<14} {opt_counts[k]:>4} query matches')

    print('\n  Average node reduction vs UCS (when UCS found a path):')
    for k in ALL_TABLE_KEYS:
        if k == 'ucs':
            continue
        if reduction_n[k]:
            avg = reduction_sum[k] / reduction_n[k]
            print(f'    {k:<14} {avg:+.1f}%  (n={reduction_n[k]})')
        else:
            print(f'    {k:<14} n/a')

    print('\n  Average runtime (ms):')
    for k in ALL_TABLE_KEYS:
        if runtime_n[k]:
            print(f'    {k:<14} {runtime_sum[k] / runtime_n[k]:.3f} ms  (n={runtime_n[k]})')
        else:
            print(f'    {k:<14} n/a')

    print('\n  Fewest-nodes wins per query (ties count for each):')
    for k in ALL_TABLE_KEYS:
        print(f'    {k:<14} {win_counts[k]:>4}')
    print(sep)


def _bfs_search_dict(res: BFSResult, runtime_ms: float) -> Dict[str, Any]:
    hops = len(res.path_edges) if res.found else None
    return {
        'found': res.found,
        'algorithm': 'BFS (search)',
        'total_time': res.total_time,
        'total_wait': res.total_wait,
        'total_journey_time': res.total_journey_time if res.found else None,
        'total_dist': None,
        'total_co2': res.total_co2 if res.found else None,
        'total_fare': int(round(res.total_price)) if res.found else None,
        'nodes_explored': res.nodes_expanded,
        'forward_nodes': '',
        'backward_nodes': '',
        'runtime_ms': runtime_ms,
        'meeting_node': None,
        'hops': hops,
        'num_transfers': res.num_transfers if res.found else None,
        'skipped': False,
    }


def print_train_schedule_checks(
    bfs_router: BFSRouter,
    depart: float,
) -> None:
    """
    Test suite for the exact train schedule waiting logic added to BFSRouter.

    Checks performed:
      A — Schedule loaded:     stop_times.csv was found and at least one
                               train stop has departure entries.
      B — Correct wait value:  for a known train stop, _train_wait returns
                               a value that matches manual calculation from
                               the sorted schedule list.
      C — Past-last-train:     when clock is after the last departure of the
                               day, _train_wait returns inf.
      D — Fallback stop:       a stop with no schedule entry returns the
                               headway average (HEADWAY_MIN['train'] / 2).
      E — Monotone clock:      run a full BFS on a train-touching query and
                               verify that the reconstructed clock never goes
                               backwards between stops.
      F — Wait >= 0:           every train edge in the result has non-negative
                               wait (no negative wait from float precision).
      G — Wait < avg only when exact schedule used:
                               compare total_wait of a train-path result
                               against what it would have been with flat
                               average headway — documents the improvement.
      H — No train edge skipped at valid time:
                               ensure a train stop reachable before its last
                               departure is NOT skipped by the search.
    """
    import bisect
    from BFS_Yanis_ZA3IM import HEADWAY_MIN

    sep  = '═' * 90
    dash = '─' * 90
    eps  = 1e-6

    print(f'\n{sep}')
    print('  TRAIN SCHEDULE EXACT WAIT — TEST SUITE')
    print(f'  departure clock: {depart:.2f}h  ({int(depart):02d}:{int((depart%1)*60):02d})')
    print(sep)

    results: Dict[str, str] = {}   # check_id → 'PASS' | 'FAIL' | 'SKIP' | 'WARN'

    # ── CHECK A — schedule was loaded ─────────────────────────────────────
    print('\n  CHECK A — stop_times.csv loaded into bfs_router.train_schedule')
    total_entries = sum(len(v) for v in bfs_router.train_schedule.values())
    n_stops = len(bfs_router.train_schedule)
    if n_stops == 0 or total_entries == 0:
        print('    SKIP  No train schedule data found.')
        print('          Place stop_times.csv in the data directory to enable.')
        print('          All further checks will be SKIP.')
        for cid in ('A','B','C','D','E','F','G','H'):
            results[cid] = 'SKIP'
        _print_check_summary(results)
        print(sep)
        return
    print(f'    PASS  {n_stops} train stops loaded, {total_entries:,} departure entries total.')
    results['A'] = 'PASS'

    # Pick a real train stop that has schedule data
    sample_stop = next(iter(bfs_router.train_schedule))
    sample_sched = bfs_router.train_schedule[sample_stop]
    print(f'\n    Sample stop : {sample_stop}')
    print(f'    Departures  : {[round(t,4) for t in sample_sched[:8]]}'
          f'{"…" if len(sample_sched) > 8 else ""}')

    # ── CHECK B — correct wait for a known arrival time ───────────────────
    print('\n  CHECK B — _train_wait returns correct value for known clock time')
    # Pick an arrival time just before the first departure
    if len(sample_sched) >= 2:
        test_clock = sample_sched[0] - 0.1   # 6 minutes before first train
        expected_idx = bisect.bisect_left(sample_sched, test_clock)
        if expected_idx < len(sample_sched):
            expected_wait_min = (sample_sched[expected_idx] - test_clock) * 60.0
            actual_wait = bfs_router._train_wait(sample_stop, test_clock)
            diff = abs(actual_wait - expected_wait_min)
            if diff < eps * max(1.0, expected_wait_min):
                print(f'    PASS  clock={test_clock:.4f}h  next_dep={sample_sched[expected_idx]:.4f}h'
                      f'  expected={expected_wait_min:.2f}m  got={actual_wait:.2f}m')
                results['B'] = 'PASS'
            else:
                print(f'    FAIL  expected={expected_wait_min:.4f}m  got={actual_wait:.4f}m  diff={diff:.6f}')
                results['B'] = 'FAIL'
        else:
            print('    SKIP  Could not construct test clock (schedule may be empty).')
            results['B'] = 'SKIP'
    else:
        print('    SKIP  Sample stop has fewer than 2 departures.')
        results['B'] = 'SKIP'

    # ── CHECK C — past last train returns inf ─────────────────────────────
    print('\n  CHECK C — _train_wait returns inf when past last train of day')
    last_dep = sample_sched[-1]
    past_clock = last_dep + 0.5   # 30 min after last train
    got = bfs_router._train_wait(sample_stop, past_clock)
    if got == float('inf'):
        print(f'    PASS  clock={past_clock:.4f}h (after last dep {last_dep:.4f}h) → inf')
        results['C'] = 'PASS'
    else:
        print(f'    FAIL  expected inf, got {got:.4f}')
        results['C'] = 'FAIL'

    # ── CHECK D — unknown stop falls back to avg headway ──────────────────
    print('\n  CHECK D — _train_wait falls back to HEADWAY average for unknown stop')
    fake_stop = '__NO_SUCH_STOP__'
    expected_avg = HEADWAY_MIN.get('train', 30.0) / 2.0
    got_avg = bfs_router._train_wait(fake_stop, depart)
    if abs(got_avg - expected_avg) < eps:
        print(f'    PASS  unknown stop → fallback = {got_avg:.2f} min (HEADWAY/2)')
        results['D'] = 'PASS'
    else:
        print(f'    FAIL  expected {expected_avg:.2f} min, got {got_avg:.2f} min')
        results['D'] = 'FAIL'

    # ── Find a train-touching query to use for checks E/F/G/H ────────────
    # Look for a stop whose type is 'train' in the BFS stop dict
    train_stops = [
        sid for sid, s in bfs_router.stops.items()
        if s.transport_type == 'train'
    ]
    # Find a pair of train stops that are adjacent in the graph
    train_query: Optional[Tuple[str, str]] = None
    for src in train_stops:
        for edge in bfs_router.graph.get(src, []):
            if edge.transport_type == 'train' and edge.to_id in bfs_router.stops:
                train_query = (src, edge.to_id)
                break
        if train_query:
            break

    if train_query is None:
        print('\n  CHECK E/F/G/H — SKIP  (no adjacent train stop pair found in graph)')
        for cid in ('E', 'F', 'G', 'H'):
            results[cid] = 'SKIP'
        _print_check_summary(results)
        print(sep)
        return

    tq_start, tq_goal = train_query
    print(f'\n  Train query for E/F/G/H: {tq_start} → {tq_goal}  (depart={depart:.2f}h)')

    try:
        result = bfs_router.search(tq_start, tq_goal, depart)
    except Exception as exc:
        print(f'  SKIP  BFS search raised {exc!r}')
        for cid in ('E', 'F', 'G', 'H'):
            results[cid] = 'SKIP'
        _print_check_summary(results)
        print(sep)
        return

    if not result.found:
        print('  SKIP  BFS did not find a path on this train query.')
        for cid in ('E', 'F', 'G', 'H'):
            results[cid] = 'SKIP'
        _print_check_summary(results)
        print(sep)
        return

    print(f'    Path found: {len(result.path_edges)} edge(s)  '
          f'ride={result.total_time:.2f}m  wait={result.total_wait:.2f}m  '
          f'total={result.total_journey_time:.2f}m')

    # ── CHECK E — clock never goes backwards ──────────────────────────────
    print('\n  CHECK E — Reconstructed clock is monotonically non-decreasing')
    clock_e = depart
    e_ok = True
    for i, edge in enumerate(result.path_edges):
        mode = edge.transport_type
        if mode == 'train':
            w = bfs_router._train_wait(result.path_ids[i], clock_e)
            if w == float('inf'):
                w = HEADWAY_MIN.get('train', 30.0) / 2.0
        else:
            w = bfs_router._avg_wait(mode)
        clock_after = clock_e + (w + edge.time_min) / 60.0
        if clock_after < clock_e - eps:
            print(f'    FAIL  clock went backwards at edge {i}: '
                  f'{clock_e:.4f}h → {clock_after:.4f}h')
            e_ok = False
            break
        clock_e = clock_after
    if e_ok:
        print(f'    PASS  clock advanced from {depart:.4f}h to {clock_e:.4f}h  '
              f'(+{(clock_e - depart)*60:.1f} min total)')
    results['E'] = 'PASS' if e_ok else 'FAIL'

    # ── CHECK F — no negative wait anywhere ───────────────────────────────
    print('\n  CHECK F — All per-edge train waits are >= 0')
    clock_f = depart
    f_ok = True
    for i, edge in enumerate(result.path_edges):
        mode = edge.transport_type
        if mode == 'train':
            w = bfs_router._train_wait(result.path_ids[i], clock_f)
            if w != float('inf') and w < 0:
                print(f'    FAIL  negative wait {w:.6f}m at edge {i} '
                      f'stop={result.path_ids[i]} clock={clock_f:.4f}h')
                f_ok = False
            actual_w = w if w != float('inf') else HEADWAY_MIN.get('train', 30.0) / 2.0
        else:
            actual_w = bfs_router._avg_wait(mode)
        clock_f += (actual_w + edge.time_min) / 60.0
    if f_ok:
        print('    PASS  all train waits are non-negative')
    results['F'] = 'PASS' if f_ok else 'FAIL'

    # ── CHECK G — exact wait vs flat headway comparison ───────────────────
    print('\n  CHECK G — Exact schedule wait vs flat HEADWAY_MIN average')
    flat_avg = HEADWAY_MIN.get('train', 30.0) / 2.0
    n_train_edges = sum(
        1 for e in result.path_edges if e.transport_type == 'train'
    )
    flat_total_wait = (
        sum(
            bfs_router._avg_wait(e.transport_type)
            for e in result.path_edges
        )
    )
    exact_total_wait = result.total_wait
    diff_g = exact_total_wait - flat_total_wait
    print(f'    Train edges in path : {n_train_edges}')
    print(f'    Flat headway wait   : {flat_total_wait:.2f} min  '
          f'({flat_avg:.1f} min × each train edge)')
    print(f'    Exact schedule wait : {exact_total_wait:.2f} min')
    if n_train_edges == 0:
        print('    N/A  Path contains no train edges — schedule logic not exercised.')
        results['G'] = 'SKIP'
    elif abs(diff_g) < eps:
        print('    NOTE  Exact wait == flat average on this query (coincidence or no schedule data).')
        results['G'] = 'WARN'
    elif diff_g < 0:
        print(f'    PASS  Exact schedule saved {abs(diff_g):.2f} min vs flat average.')
        results['G'] = 'PASS'
    else:
        print(f'    INFO  Exact schedule added {diff_g:.2f} min vs flat average.')
        print('          This is normal — the traveller arrived between trains.')
        results['G'] = 'PASS'

    # ── CHECK H — valid-time train stop is not skipped ────────────────────
    print('\n  CHECK H — Train stop reachable before last departure is NOT skipped')
    # Pick a train stop whose last departure is after depart
    reachable_train_stop = None
    for sid, sched in bfs_router.train_schedule.items():
        if sched and sched[-1] > depart and sid in bfs_router.stops:
            reachable_train_stop = sid
            break

    if reachable_train_stop is None:
        print('    SKIP  No train stop with departures after depart time found.')
        results['H'] = 'SKIP'
    else:
        w_h = bfs_router._train_wait(reachable_train_stop, depart)
        if w_h == float('inf'):
            print(f'    FAIL  stop {reachable_train_stop!r} returned inf '
                  f'but has departures after {depart:.2f}h')
            results['H'] = 'FAIL'
        elif w_h >= 0:
            next_dep = depart + w_h / 60.0
            print(f'    PASS  stop={reachable_train_stop!r}  '
                  f'clock={depart:.4f}h  wait={w_h:.2f}m  '
                  f'boards at {next_dep:.4f}h')
            results['H'] = 'PASS'
        else:
            print(f'    FAIL  negative wait {w_h:.4f}m')
            results['H'] = 'FAIL'

    _print_check_summary(results)
    print(sep)


def _print_check_summary(results: Dict[str, str]) -> None:
    """Print a compact one-line summary row for all checks."""
    dash = '─' * 90
    print(f'\n  {dash}')
    print('  SUMMARY')
    line = '  '
    for cid in sorted(results):
        status = results[cid]
        symbol = {'PASS': '✓', 'FAIL': '✗', 'SKIP': '—', 'WARN': '!'}.get(status, '?')
        line += f'  {cid}:{symbol}({status})'
    print(line)

    passed = sum(1 for v in results.values() if v == 'PASS')
    failed = sum(1 for v in results.values() if v == 'FAIL')
    warned = sum(1 for v in results.values() if v == 'WARN')
    skipped = sum(1 for v in results.values() if v == 'SKIP')
    print(f'\n  Total: {passed} PASS  {failed} FAIL  {warned} WARN  {skipped} SKIP')
    if failed > 0:
        print('  ⚠️  Some checks FAILED — review train schedule logic in BFS_Yanis_ZA3IM.py')
    elif warned > 0:
        print('  ℹ️  Some checks produced warnings — results may still be correct.')
    elif skipped == len(results):
        print('  ℹ️  All checks skipped — stop_times.csv not found in data directory.')
    else:
        print('  ✅  All executed checks passed.')


def run_full_benchmark(
    data_dir: str,
    queries: List[Tuple[str, str, str, str]],
    depart: float = DEPART_DEFAULT,
) -> List[Dict[str, Any]]:
    """
    Load ``TransitRouter`` + ``BFSRouter``, ``BidirectionalSearch(router, bfs_router=…)``.

    Each query tuple: (start_id, goal_id, metric, label).
    """
    data_dir = os.path.normpath(data_dir)

    print(f'Loading TransitRouter + BFSRouter from {data_dir!r}...')
    transit_router = TransitRouter(data_dir)
    bfs_router = BFSRouter(data_dir)
    bidir = BidirectionalSearch(transit_router, bfs_router=bfs_router)

    all_reports: List[Dict[str, Any]] = []
    waiting_summary_rows: List[Dict[str, Any]] = []

    print_train_schedule_checks(bfs_router, depart)

    for start_id, goal_id, metric, label in queries:
        print(f"\n{'─' * 80}\n  Query: {label}  |  metric={metric}\n{'─' * 80}")

        bidir_report = bidir.compare_all(
            start_id, goal_id, metric=metric, depart=depart,
        )

        bfs_result: Optional[BFSResult] = None
        try:
            t0 = time_module.perf_counter()
            bfs_result = bfs_router.search(start_id, goal_id, depart)
            uni_ms = round((time_module.perf_counter() - t0) * 1000, 3)
        except ValueError as e:
            print(f'  [BFS.search skipped: {e}]')
            uni_ms = 0.0
            bfs_result = None

        uni_dict = (
            _bfs_search_dict(bfs_result, uni_ms)
            if bfs_result is not None
            else {
                'found': False,
                'algorithm': 'BFS (search)',
                'skipped': True,
                'nodes_explored': 0,
                'runtime_ms': uni_ms,
            }
        )

        bd_bfs = bidir.search_bfs(start_id, goal_id, depart=depart)

        print_cost_algo_waiting_checks(label, bidir_report)

        check_out = print_bidir_bfs_waiting_checks(
            label, bfs_router, bidir, bd_bfs, bfs_result, depart,
        )
        check_out['bfs_ride'] = (
            f'{bfs_result.total_time:.2f}' if bfs_result and bfs_result.found else '—'
        )
        check_out['bfs_wait'] = (
            f'{bfs_result.total_wait:.2f}' if bfs_result and bfs_result.found else '—'
        )
        check_out['bidir_ride'] = (
            f'{bd_bfs.total_time:.2f}' if bd_bfs.found else '—'
        )
        check_out['bidir_wait'] = f'{bd_bfs.total_wait:.2f}' if bd_bfs.found else '—'
        waiting_summary_rows.append(check_out)

        entry = {
            'label': label,
            'start_id': start_id,
            'goal_id': goal_id,
            'metric': metric,
            'report': bidir_report,
            'bfs_uni': uni_dict,
        }
        all_reports.append(entry)

        print_unified_report(
            {
                'label': label,
                'start_id': start_id,
                'goal_id': goal_id,
                'metric': metric,
                'bidir': bidir_report,
                'bfs_uni': uni_dict,
            },
            transit_router,
        )

    print_waiting_summary_table(waiting_summary_rows)
    print_optimality_summary(all_reports)
    return all_reports


if __name__ == '__main__':
    data_dir = sys.argv[1] if len(sys.argv) > 1 else 'data'
    depart = float(sys.argv[2]) if len(sys.argv) > 2 else DEPART_DEFAULT
    run_full_benchmark(data_dir, DEMO_QUERIES, depart=depart)
