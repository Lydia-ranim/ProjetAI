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

    sep = '═' * 118
    dash = '─' * 118

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
        f"{'Time(min)':>10} {'Dist(km)':>10} {'CO2(g)':>9} "
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
            if j is None and r.get('total_time') is not None and r.get('total_wait') is not None:
                j = float(r['total_time']) + float(r['total_wait'])
            tcol = f"{j:.1f}" if j is not None else '—'
            dcol = f"{float(r['total_dist']):.3f}" if r.get('total_dist') is not None else '—'
            ccol = f"{float(r['total_co2']):.1f}" if r.get('total_co2') is not None else '—'
            fcol = str(r.get('total_fare', '—'))
        elif r['is_bfs']:
            tcol = f"{r.get('hops', 0)} hops"
            dcol = '—'
            ccol = '—'
            fcol = '—'
        else:
            tcol = f"{r['total_time']:.1f}"
            dcol = f"{r['total_dist']:.3f}"
            ccol = f"{r['total_co2']:.1f}"
            fcol = str(r['total_fare'])
        fwd = str(r['forward_nodes']) if r['forward_nodes'] != '' else ''
        bwd = str(r['backward_nodes']) if r['backward_nodes'] != '' else ''
        red = f"{r['node_reduction_pct']:+.1f}%"
        print(
            f"{tag}{r['algorithm']:<24} {found:>6} "
            f"{tcol:>10} {dcol:>10} {ccol:>9} {fcol:>9} "
            f"{r['nodes_explored']:>8,} {fwd:>6} {bwd:>6} "
            f"{float(r['runtime_ms']):>12.2f} {red:>11}"
        )

    print(dash)
    if min_nodes is not None:
        winners = [r['algorithm'] for r in found_rows if r['nodes_explored'] == min_nodes]
        print(f"  ★ Fewest nodes ({min_nodes:,}): {', '.join(winners)}")
        print(f"    UCS baseline nodes: {ucs_nodes:,}")
    print(sep)


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
    sep = '═' * 140
    print(f'\n{sep}')
    print('  WAITING / BFS SUMMARY (all queries)')
    print(sep)
    hdr = (
        f"  {'Query':<42} {'BFS nd':>8} {'BiDir':>8} {'Red%':>10} "
        f"{'BFS wait':>10} {'BiDir wait':>12} {'Wait chk':>10} {'Xfer chk':>10} {'Path ok':>10}"
    )
    print(hdr)
    print('─' * 140)
    for r in rows:
        print(
            f"  {r.get('label','')[:42]:<42} "
            f"{str(r.get('bfs_nodes','')):>8} "
            f"{str(r.get('bidir_nodes','')):>8} "
            f"{str(r.get('reduction_pct','')):>10} "
            f"{str(r.get('bfs_wait','')):>10} "
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

        check_out = print_bidir_bfs_waiting_checks(
            label, bfs_router, bidir, bd_bfs, bfs_result, depart,
        )
        check_out['bfs_wait'] = (
            f'{bfs_result.total_wait:.2f}' if bfs_result and bfs_result.found else '—'
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
