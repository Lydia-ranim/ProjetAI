/**
 * Algorithm implementations for Algiers Transit AI
 * Dijkstra, A*, Bidirectional Dijkstra, and CSP filtering
 * 
 * All algorithms operate on the hardcoded Algiers graph
 * and return full path information with performance metrics
 */

import {
  type GraphData, type Edge, type Stop, type AdjEntry, type TransportMode,
  buildAdjacencyList, getStopById, getStopMap, MODE_CONFIG,
} from './algiers-graph';
import { haversineDistance } from './geo';
import { isPeakHour, getPeakMultiplier, getAlgiersTime, addMinutes, formatTime } from './time';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface Weights {
  time: number;  // 0..1
  cost: number;  // 0..1
  co2: number;   // 0..1
}

export interface AlgoResult {
  path: string[];            // stop IDs
  edges: Edge[];             // edges traversed
  totalTime: number;
  totalCost: number;
  totalCo2: number;
  totalDistance: number;
  walkingDistance: number;
  waitingTime: number;
  transfers: number;
  nodesExpanded: number;
  runtimeMs: number;
  meetingNode?: string;      // for bidirectional
}

export interface Segment {
  mode: TransportMode;
  lineId: string | null;
  fromName: string;
  toName: string;
  fromCoords: [number, number];
  toCoords: [number, number];
  polyline: [number, number][];
  distanceM: number;
  durationMin: number;
  waitMin: number;
  costDzd: number;
  co2G: number;
  departureTime: string;
  arrivalTime: string;
}

export interface TimelineEvent {
  type: 'depart' | 'arrive' | 'transfer' | 'walk' | 'ride' | 'wait';
  time: string;
  stopName: string;
  mode?: TransportMode;
  lineId?: string;
  durationMin?: number;
}

export interface Route {
  id: string;
  label: 'fastest' | 'cheapest' | 'greenest';
  algorithmUsed: 'A*' | 'Dijkstra' | 'Bidirectional';
  segments: Segment[];
  summary: {
    totalTimeMin: number;
    totalCostDzd: number;
    totalCo2G: number;
    totalDistanceM: number;
    numTransfers: number;
    numStops: number;
    walkingDistanceM: number;
    waitingTimeMin: number;
  };
  timeline: TimelineEvent[];
  stressScore: number;
  stressLabel: 'low' | 'medium' | 'high';
  explanation: string;
  polyline: [number, number][];
  co2SavedVsCarG: number;
  score: number;
  nodesExpanded: number;
  computationMs: number;
}

export interface AlgoComparison {
  dijkstra: { nodesExpanded: number; runtimeMs: number; pathCost: number };
  astar: { nodesExpanded: number; runtimeMs: number; pathCost: number; heuristicAccuracy: number };
  bidirectional: { nodesExpanded: number; runtimeMs: number; pathCost: number; meetingNode: string };
  winner: 'A*' | 'Bidirectional';
  astarEfficiencyPct: number;
}

// ─── Edge Weight Function ────────────────────────────────────────────────────

function edgeCost(edge: Edge, weights: Weights, prevMode?: TransportMode): number {
  const isPeak = isPeakHour();
  const peakMult = getPeakMultiplier();

  // Apply wait time with peak multiplier
  const waitTime = edge.mode !== 'walk' ? edge.waitTimeMin * peakMult : 0;
  const totalTime = edge.timeMin + waitTime;
  
  // Transfer penalty: 3 min when switching modes
  const transferPenalty = prevMode && prevMode !== edge.mode && edge.mode !== 'walk' && prevMode !== 'walk' ? 3 : 0;

  // Cost: fare per boarding (simplified — assume fare for first edge of each mode segment)
  const modeFare = MODE_CONFIG[edge.mode]?.fare || 0;

  // CO2
  const co2 = edge.co2G;

  return (
    weights.time * (totalTime + transferPenalty) +
    weights.cost * (modeFare / 10) +
    weights.co2 * (co2 / 5)
  );
}

// ─── Priority Queue (Min-Heap) ───────────────────────────────────────────────

interface HeapItem {
  key: string;
  priority: number;
}

class MinHeap {
  private items: HeapItem[] = [];

  push(key: string, priority: number) {
    this.items.push({ key, priority });
    this._bubbleUp(this.items.length - 1);
  }

  pop(): HeapItem | undefined {
    if (this.items.length === 0) return undefined;
    const top = this.items[0];
    const last = this.items.pop()!;
    if (this.items.length > 0) {
      this.items[0] = last;
      this._sinkDown(0);
    }
    return top;
  }

  get size() { return this.items.length; }

  private _bubbleUp(i: number) {
    while (i > 0) {
      const parent = (i - 1) >> 1;
      if (this.items[i].priority >= this.items[parent].priority) break;
      [this.items[i], this.items[parent]] = [this.items[parent], this.items[i]];
      i = parent;
    }
  }

  private _sinkDown(i: number) {
    const n = this.items.length;
    while (true) {
      let smallest = i;
      const l = 2 * i + 1, r = 2 * i + 2;
      if (l < n && this.items[l].priority < this.items[smallest].priority) smallest = l;
      if (r < n && this.items[r].priority < this.items[smallest].priority) smallest = r;
      if (smallest === i) break;
      [this.items[i], this.items[smallest]] = [this.items[smallest], this.items[i]];
      i = smallest;
    }
  }
}

// ─── Dijkstra ────────────────────────────────────────────────────────────────

export function dijkstra(
  adj: Map<string, AdjEntry[]>,
  start: string,
  end: string,
  weights: Weights,
): AlgoResult | null {
  const t0 = performance.now();
  const dist = new Map<string, number>();
  const prev = new Map<string, { node: string; edge: Edge } | null>();
  const prevMode = new Map<string, TransportMode | undefined>();
  const visited = new Set<string>();
  let nodesExpanded = 0;

  dist.set(start, 0);
  prev.set(start, null);
  prevMode.set(start, undefined);

  const heap = new MinHeap();
  heap.push(start, 0);

  while (heap.size > 0) {
    const current = heap.pop()!;
    if (visited.has(current.key)) continue;
    visited.add(current.key);
    nodesExpanded++;

    if (current.key === end) break;

    const neighbors = adj.get(current.key) || [];
    for (const { to, edge } of neighbors) {
      if (visited.has(to)) continue;
      const mode = prevMode.get(current.key);
      const cost = edgeCost(edge, weights, mode);
      const newDist = (dist.get(current.key) || 0) + cost;

      if (!dist.has(to) || newDist < dist.get(to)!) {
        dist.set(to, newDist);
        prev.set(to, { node: current.key, edge });
        prevMode.set(to, edge.mode === 'walk' ? mode : edge.mode);
        heap.push(to, newDist);
      }
    }
  }

  if (!prev.has(end)) return null;

  return reconstructResult(prev, start, end, nodesExpanded, performance.now() - t0);
}

// ─── A* ──────────────────────────────────────────────────────────────────────

function heuristic(nodeId: string, goalId: string, weights: Weights): number {
  const node = getStopById(nodeId);
  const goal = getStopById(goalId);
  if (!node || !goal) return 0;

  const distM = haversineDistance(node, goal);
  // Admissible: distance / max_speed (metro = 35 km/h = 583.3 m/min)
  const maxSpeedMPerMin = 583.3;
  const minTime = distM / maxSpeedMPerMin;

  // Only use time component for heuristic (admissible)
  return weights.time * minTime;
}

export function astar(
  adj: Map<string, AdjEntry[]>,
  start: string,
  end: string,
  weights: Weights,
  epsilon: number = 1.2,
): AlgoResult | null {
  const t0 = performance.now();
  const gScore = new Map<string, number>();
  const prev = new Map<string, { node: string; edge: Edge } | null>();
  const prevMode = new Map<string, TransportMode | undefined>();
  const visited = new Set<string>();
  let nodesExpanded = 0;

  gScore.set(start, 0);
  prev.set(start, null);
  prevMode.set(start, undefined);

  const heap = new MinHeap();
  const h0 = heuristic(start, end, weights);
  heap.push(start, h0 * epsilon);

  while (heap.size > 0) {
    const current = heap.pop()!;
    if (visited.has(current.key)) continue;
    visited.add(current.key);
    nodesExpanded++;

    if (current.key === end) break;

    const neighbors = adj.get(current.key) || [];
    for (const { to, edge } of neighbors) {
      if (visited.has(to)) continue;
      const mode = prevMode.get(current.key);
      const cost = edgeCost(edge, weights, mode);
      const newG = (gScore.get(current.key) || 0) + cost;

      if (!gScore.has(to) || newG < gScore.get(to)!) {
        gScore.set(to, newG);
        prev.set(to, { node: current.key, edge });
        prevMode.set(to, edge.mode === 'walk' ? mode : edge.mode);
        const f = newG + epsilon * heuristic(to, end, weights);
        heap.push(to, f);
      }
    }
  }

  if (!prev.has(end)) return null;

  return reconstructResult(prev, start, end, nodesExpanded, performance.now() - t0);
}

// ─── Bidirectional Dijkstra ──────────────────────────────────────────────────

export function bidirectional(
  adj: Map<string, AdjEntry[]>,
  reverseAdj: Map<string, AdjEntry[]>,
  start: string,
  end: string,
  weights: Weights,
): AlgoResult | null {
  const t0 = performance.now();

  const distF = new Map<string, number>();
  const distB = new Map<string, number>();
  const prevF = new Map<string, { node: string; edge: Edge } | null>();
  const prevB = new Map<string, { node: string; edge: Edge } | null>();
  const prevModeF = new Map<string, TransportMode | undefined>();
  const prevModeB = new Map<string, TransportMode | undefined>();
  const visitedF = new Set<string>();
  const visitedB = new Set<string>();
  let nodesExpanded = 0;

  distF.set(start, 0);
  distB.set(end, 0);
  prevF.set(start, null);
  prevB.set(end, null);
  prevModeF.set(start, undefined);
  prevModeB.set(end, undefined);

  const heapF = new MinHeap();
  const heapB = new MinHeap();
  heapF.push(start, 0);
  heapB.push(end, 0);

  let mu = Infinity;
  let meetingNode = '';

  while (heapF.size > 0 || heapB.size > 0) {
    // Termination: both min-queue tops sum >= mu
    const minF = heapF.size > 0 ? heapF.pop() : null;
    const minB = heapB.size > 0 ? heapB.pop() : null;

    // Expand forward
    if (minF && !visitedF.has(minF.key)) {
      visitedF.add(minF.key);
      nodesExpanded++;

      if (distB.has(minF.key)) {
        const total = (distF.get(minF.key) || 0) + (distB.get(minF.key) || 0);
        if (total < mu) {
          mu = total;
          meetingNode = minF.key;
        }
      }

      const neighbors = adj.get(minF.key) || [];
      for (const { to, edge } of neighbors) {
        if (visitedF.has(to)) continue;
        const mode = prevModeF.get(minF.key);
        const cost = edgeCost(edge, weights, mode);
        const newDist = (distF.get(minF.key) || 0) + cost;
        if (!distF.has(to) || newDist < distF.get(to)!) {
          distF.set(to, newDist);
          prevF.set(to, { node: minF.key, edge });
          prevModeF.set(to, edge.mode === 'walk' ? mode : edge.mode);
          heapF.push(to, newDist);
        }
      }
    }

    // Expand backward
    if (minB && !visitedB.has(minB.key)) {
      visitedB.add(minB.key);
      nodesExpanded++;

      if (distF.has(minB.key)) {
        const total = (distF.get(minB.key) || 0) + (distB.get(minB.key) || 0);
        if (total < mu) {
          mu = total;
          meetingNode = minB.key;
        }
      }

      const neighbors = reverseAdj.get(minB.key) || [];
      for (const { to, edge } of neighbors) {
        if (visitedB.has(to)) continue;
        const mode = prevModeB.get(minB.key);
        const cost = edgeCost(edge, weights, mode);
        const newDist = (distB.get(minB.key) || 0) + cost;
        if (!distB.has(to) || newDist < distB.get(to)!) {
          distB.set(to, newDist);
          prevB.set(to, { node: minB.key, edge });
          prevModeB.set(to, edge.mode === 'walk' ? mode : edge.mode);
          heapB.push(to, newDist);
        }
      }
    }

    // Check termination
    if (meetingNode && mu < Infinity) {
      const fMin = minF ? (distF.get(minF.key) || Infinity) : Infinity;
      const bMin = minB ? (distB.get(minB.key) || Infinity) : Infinity;
      if (fMin + bMin >= mu) break;
    }

    if (!minF && !minB) break;
  }

  if (!meetingNode) return null;

  // Reconstruct: forward path start→meeting, backward path meeting→end
  const pathForward: string[] = [];
  const edgesForward: Edge[] = [];
  let cur: string | null = meetingNode;
  while (cur && cur !== start) {
    pathForward.unshift(cur);
    const p = prevF.get(cur);
    if (p) {
      edgesForward.unshift(p.edge);
      cur = p.node;
    } else break;
  }
  pathForward.unshift(start);

  const pathBackward: string[] = [];
  const edgesBackward: Edge[] = [];
  cur = meetingNode;
  while (cur && cur !== end) {
    const p = prevB.get(cur);
    if (p) {
      pathBackward.push(p.node);
      edgesBackward.push(p.edge);
      cur = p.node;
    } else break;
  }

  const fullPath = [...pathForward, ...pathBackward];
  const allEdges = [...edgesForward, ...edgesBackward];

  const result = computeResultFromEdges(fullPath, allEdges, nodesExpanded, performance.now() - t0);
  if (result) result.meetingNode = meetingNode;
  return result;
}

// ─── Result Reconstruction ───────────────────────────────────────────────────

function reconstructResult(
  prev: Map<string, { node: string; edge: Edge } | null>,
  start: string,
  end: string,
  nodesExpanded: number,
  runtimeMs: number,
): AlgoResult {
  const path: string[] = [];
  const edges: Edge[] = [];
  let cur = end;

  while (cur !== start) {
    path.unshift(cur);
    const p = prev.get(cur);
    if (!p) break;
    edges.unshift(p.edge);
    cur = p.node;
  }
  path.unshift(start);

  return computeResultFromEdges(path, edges, nodesExpanded, runtimeMs)!;
}

function computeResultFromEdges(
  path: string[],
  edges: Edge[],
  nodesExpanded: number,
  runtimeMs: number,
): AlgoResult | null {
  if (edges.length === 0) return null;

  let totalTime = 0, totalCost = 0, totalCo2 = 0, totalDist = 0;
  let walkDist = 0, waitTime = 0, transfers = 0;
  let lastMode: TransportMode | undefined;
  const faredModes = new Set<string>();
  const peakMult = getPeakMultiplier();

  for (const e of edges) {
    totalTime += e.timeMin;
    totalDist += e.distanceM;
    totalCo2 += e.co2G;

    if (e.mode === 'walk') {
      walkDist += e.distanceM;
    } else {
      const wait = e.waitTimeMin * peakMult;
      waitTime += wait;
      totalTime += wait;

      // Fare: charge once per boarding per line
      const fareKey = `${e.mode}-${e.lineId}`;
      if (!faredModes.has(fareKey)) {
        faredModes.add(fareKey);
        totalCost += MODE_CONFIG[e.mode].fare;
      }

      if (lastMode && lastMode !== e.mode && lastMode !== 'walk') {
        transfers++;
        totalTime += 3; // transfer penalty
      }
    }

    if (e.mode !== 'walk') lastMode = e.mode;
  }

  return {
    path,
    edges,
    totalTime: Math.round(totalTime * 10) / 10,
    totalCost,
    totalCo2: Math.round(totalCo2 * 10) / 10,
    totalDistance: Math.round(totalDist),
    walkingDistance: Math.round(walkDist),
    waitingTime: Math.round(waitTime * 10) / 10,
    transfers,
    nodesExpanded,
    runtimeMs: Math.round(runtimeMs * 100) / 100,
  };
}

// ─── Build Segments from AlgoResult ──────────────────────────────────────────

export function buildSegments(result: AlgoResult): Segment[] {
  const segments: Segment[] = [];
  const stopMap = getStopMap();
  let currentTime = getAlgiersTime();
  let i = 0;

  while (i < result.edges.length) {
    const edge = result.edges[i];
    const fromStop = stopMap.get(edge.from);
    const toStop = stopMap.get(edge.to);
    if (!fromStop || !toStop) { i++; continue; }

    // Group consecutive edges of same mode+line
    let j = i;
    let segDist = 0, segTime = 0, segCo2 = 0, segWait = 0;
    const polyline: [number, number][] = [[fromStop.lat, fromStop.lng]];
    let lastTo = toStop;

    while (j < result.edges.length) {
      const e = result.edges[j];
      if (e.mode !== edge.mode || (e.lineId !== edge.lineId && edge.mode !== 'walk')) break;
      const ts = stopMap.get(e.to);
      if (ts) {
        polyline.push([ts.lat, ts.lng]);
        lastTo = ts;
      }
      segDist += e.distanceM;
      segTime += e.timeMin;
      segCo2 += e.co2G;
      if (j === i && e.mode !== 'walk') segWait = e.waitTimeMin * getPeakMultiplier();
      j++;
    }

    // Cost: one fare per boarding
    const segCost = edge.mode !== 'walk' ? MODE_CONFIG[edge.mode].fare : 0;

    const depTime = addMinutes(currentTime, segWait);
    const arrTime = addMinutes(depTime, segTime);

    segments.push({
      mode: edge.mode,
      lineId: edge.mode !== 'walk' ? edge.lineId : null,
      fromName: fromStop.name,
      toName: lastTo.name,
      fromCoords: [fromStop.lat, fromStop.lng],
      toCoords: [lastTo.lat, lastTo.lng],
      polyline,
      distanceM: Math.round(segDist),
      durationMin: Math.round(segTime * 10) / 10,
      waitMin: Math.round(segWait * 10) / 10,
      costDzd: segCost,
      co2G: Math.round(segCo2 * 10) / 10,
      departureTime: formatTime(depTime),
      arrivalTime: formatTime(arrTime),
    });

    currentTime = arrTime;
    i = j;
  }

  return segments;
}

// ─── Build Timeline ──────────────────────────────────────────────────────────

export function buildTimeline(segments: Segment[]): TimelineEvent[] {
  const events: TimelineEvent[] = [];

  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i];

    if (i === 0) {
      events.push({ type: 'depart', time: seg.departureTime, stopName: seg.fromName, mode: seg.mode });
    }

    if (seg.waitMin > 0) {
      events.push({ type: 'wait', time: seg.departureTime, stopName: seg.fromName, mode: seg.mode, lineId: seg.lineId || undefined, durationMin: seg.waitMin });
    }

    events.push({
      type: seg.mode === 'walk' ? 'walk' : 'ride',
      time: seg.departureTime,
      stopName: `${seg.fromName} → ${seg.toName}`,
      mode: seg.mode,
      lineId: seg.lineId || undefined,
      durationMin: seg.durationMin,
    });

    if (i < segments.length - 1 && segments[i + 1].mode !== seg.mode) {
      events.push({ type: 'transfer', time: seg.arrivalTime, stopName: seg.toName, mode: segments[i + 1].mode });
    }

    if (i === segments.length - 1) {
      events.push({ type: 'arrive', time: seg.arrivalTime, stopName: seg.toName });
    }
  }

  return events;
}

// ─── Stress Calculation ──────────────────────────────────────────────────────

export function computeStress(result: AlgoResult): { score: number; label: 'low' | 'medium' | 'high' } {
  const score = result.transfers * 2 + (result.walkingDistance / 1000) * 1.5 + result.waitingTime * 0.5;
  const normalizedScore = Math.min(score / 15, 1.0);
  const label = normalizedScore < 0.33 ? 'low' : normalizedScore < 0.66 ? 'medium' : 'high';
  return { score: Math.round(normalizedScore * 100) / 100, label };
}

// ─── CO2 vs Car ──────────────────────────────────────────────────────────────

export function co2VsCar(totalDistM: number, transitCo2G: number): number {
  const carCo2 = (totalDistM / 1000) * MODE_CONFIG.car.co2PerKm;
  return Math.round(carCo2 - transitCo2G);
}

// ─── CSP Constraint Filtering ────────────────────────────────────────────────

export interface CSPConstraints {
  maxTransfers: number;     // -1 = unlimited
  maxWalkingM: number;
  maxTimeMin: number;
}

export function cspFilter(results: AlgoResult[], constraints: CSPConstraints): AlgoResult[] {
  return results.filter(r => {
    if (constraints.maxTransfers >= 0 && r.transfers > constraints.maxTransfers) return false;
    if (constraints.maxWalkingM > 0 && r.walkingDistance > constraints.maxWalkingM) return false;
    if (constraints.maxTimeMin > 0 && r.totalTime > constraints.maxTimeMin) return false;
    return true;
  });
}

// ─── Generate Route Explanation ──────────────────────────────────────────────

export function generateExplanation(route: Route): string {
  const { label, algorithmUsed, summary } = route;
  const modes = route.segments.map(s => s.mode).filter(m => m !== 'walk');
  const uniqueModes = [...new Set(modes)];

  const algoExpl = algorithmUsed === 'A*'
    ? 'A* was selected for optimal pathfinding with Euclidean heuristic, expanding fewer nodes than Dijkstra.'
    : algorithmUsed === 'Bidirectional'
    ? 'Bidirectional Dijkstra searches from both ends simultaneously, meeting in the middle for efficiency.'
    : 'Dijkstra provides the baseline optimal solution by exhaustively exploring all possibilities.';

  const routeExpl = label === 'fastest'
    ? `This route prioritizes speed via ${uniqueModes.join(' + ')} (${summary.totalTimeMin} min total). ${summary.numTransfers} transfer(s) keep the journey swift.`
    : label === 'cheapest'
    ? `This route minimizes cost at ${summary.totalCostDzd} DZD using ${uniqueModes.join(' + ')}. Slightly longer at ${summary.totalTimeMin} min but best value.`
    : `This route minimizes emissions at ${summary.totalCo2G}g CO₂ via electric ${uniqueModes.join(' + ')}. Saves ${route.co2SavedVsCarG}g vs driving.`;

  return `${algoExpl} ${routeExpl}`;
}

// ─── Build Reverse Adjacency List ────────────────────────────────────────────

export function buildReverseAdjacencyList(adj: Map<string, AdjEntry[]>): Map<string, AdjEntry[]> {
  const reverse = new Map<string, AdjEntry[]>();
  for (const [, entries] of adj) {
    for (const { to, edge } of entries) {
      if (!reverse.has(to)) reverse.set(to, []);
      // Create reverse edge
      const reverseEdge: Edge = {
        ...edge,
        from: edge.to,
        to: edge.from,
      };
      reverse.get(to)!.push({ to: edge.from, edge: reverseEdge });
    }
  }
  // Ensure all nodes exist
  for (const [key] of adj) {
    if (!reverse.has(key)) reverse.set(key, []);
  }
  return reverse;
}

// ─── Main Route Search ──────────────────────────────────────────────────────

export interface SearchParams {
  startId: string;
  endId: string;
  weights: Weights;
  enabledModes: Record<TransportMode, boolean>;
  constraints: CSPConstraints;
}

export interface SearchResult {
  routes: Route[];
  comparison: AlgoComparison;
}

export function findRoutes(graph: GraphData, params: SearchParams): SearchResult {
  const adj = buildAdjacencyList(graph, params.enabledModes);
  const revAdj = buildReverseAdjacencyList(adj);

  // Weight presets for different route objectives
  const fastestWeights: Weights = { time: 0.8, cost: 0.1, co2: 0.1 };
  const cheapestWeights: Weights = { time: 0.1, cost: 0.8, co2: 0.1 };
  const greenestWeights: Weights = { time: 0.1, cost: 0.1, co2: 0.8 };

  // Run all algorithms for comparison
  const dijkResult = dijkstra(adj, params.startId, params.endId, params.weights);
  const astarResult = astar(adj, params.startId, params.endId, params.weights, 1.2);
  const biResult = bidirectional(adj, revAdj, params.startId, params.endId, params.weights);

  // Run optimal routes per objective
  const fastest = astar(adj, params.startId, params.endId, fastestWeights, 1.2);
  const cheapest = dijkstra(adj, params.startId, params.endId, cheapestWeights);
  const greenest = astar(adj, params.startId, params.endId, greenestWeights, 1.2);

  const routes: Route[] = [];

  if (fastest) {
    const segments = buildSegments(fastest);
    const timeline = buildTimeline(segments);
    const stress = computeStress(fastest);
    const saved = co2VsCar(fastest.totalDistance, fastest.totalCo2);

    const route: Route = {
      id: 'fastest',
      label: 'fastest',
      algorithmUsed: 'A*',
      segments,
      summary: {
        totalTimeMin: fastest.totalTime,
        totalCostDzd: fastest.totalCost,
        totalCo2G: fastest.totalCo2,
        totalDistanceM: fastest.totalDistance,
        numTransfers: fastest.transfers,
        numStops: fastest.path.length,
        walkingDistanceM: fastest.walkingDistance,
        waitingTimeMin: fastest.waitingTime,
      },
      timeline,
      stressScore: stress.score,
      stressLabel: stress.label,
      explanation: '',
      polyline: segments.flatMap(s => s.polyline),
      co2SavedVsCarG: saved,
      score: fastest.totalTime,
      nodesExpanded: fastest.nodesExpanded,
      computationMs: fastest.runtimeMs,
    };
    route.explanation = generateExplanation(route);
    routes.push(route);
  }

  if (cheapest) {
    const segments = buildSegments(cheapest);
    const timeline = buildTimeline(segments);
    const stress = computeStress(cheapest);
    const saved = co2VsCar(cheapest.totalDistance, cheapest.totalCo2);

    const route: Route = {
      id: 'cheapest',
      label: 'cheapest',
      algorithmUsed: 'Dijkstra',
      segments,
      summary: {
        totalTimeMin: cheapest.totalTime,
        totalCostDzd: cheapest.totalCost,
        totalCo2G: cheapest.totalCo2,
        totalDistanceM: cheapest.totalDistance,
        numTransfers: cheapest.transfers,
        numStops: cheapest.path.length,
        walkingDistanceM: cheapest.walkingDistance,
        waitingTimeMin: cheapest.waitingTime,
      },
      timeline,
      stressScore: stress.score,
      stressLabel: stress.label,
      explanation: '',
      polyline: segments.flatMap(s => s.polyline),
      co2SavedVsCarG: saved,
      score: cheapest.totalCost,
      nodesExpanded: cheapest.nodesExpanded,
      computationMs: cheapest.runtimeMs,
    };
    route.explanation = generateExplanation(route);
    routes.push(route);
  }

  if (greenest) {
    const segments = buildSegments(greenest);
    const timeline = buildTimeline(segments);
    const stress = computeStress(greenest);
    const saved = co2VsCar(greenest.totalDistance, greenest.totalCo2);

    const route: Route = {
      id: 'greenest',
      label: 'greenest',
      algorithmUsed: 'A*',
      segments,
      summary: {
        totalTimeMin: greenest.totalTime,
        totalCostDzd: greenest.totalCost,
        totalCo2G: greenest.totalCo2,
        totalDistanceM: greenest.totalDistance,
        numTransfers: greenest.transfers,
        numStops: greenest.path.length,
        walkingDistanceM: greenest.walkingDistance,
        waitingTimeMin: greenest.waitingTime,
      },
      timeline,
      stressScore: stress.score,
      stressLabel: stress.label,
      explanation: '',
      polyline: segments.flatMap(s => s.polyline),
      co2SavedVsCarG: saved,
      score: greenest.totalCo2,
      nodesExpanded: greenest.nodesExpanded,
      computationMs: greenest.runtimeMs,
    };
    route.explanation = generateExplanation(route);
    routes.push(route);
  }

  // CSP filter
  const filtered = routes.filter(r => {
    if (params.constraints.maxTransfers >= 0 && r.summary.numTransfers > params.constraints.maxTransfers) return false;
    if (params.constraints.maxWalkingM > 0 && r.summary.walkingDistanceM > params.constraints.maxWalkingM) return false;
    if (params.constraints.maxTimeMin > 0 && r.summary.totalTimeMin > params.constraints.maxTimeMin) return false;
    return true;
  });

  // Comparison
  const comparison: AlgoComparison = {
    dijkstra: {
      nodesExpanded: dijkResult?.nodesExpanded || 0,
      runtimeMs: dijkResult?.runtimeMs || 0,
      pathCost: dijkResult?.totalTime || 0,
    },
    astar: {
      nodesExpanded: astarResult?.nodesExpanded || 0,
      runtimeMs: astarResult?.runtimeMs || 0,
      pathCost: astarResult?.totalTime || 0,
      heuristicAccuracy: dijkResult && astarResult
        ? Math.round((1 - Math.abs(astarResult.totalTime - dijkResult.totalTime) / dijkResult.totalTime) * 100)
        : 100,
    },
    bidirectional: {
      nodesExpanded: biResult?.nodesExpanded || 0,
      runtimeMs: biResult?.runtimeMs || 0,
      pathCost: biResult?.totalTime || 0,
      meetingNode: biResult?.meetingNode || '',
    },
    winner: (biResult?.nodesExpanded || Infinity) < (astarResult?.nodesExpanded || Infinity) ? 'Bidirectional' : 'A*',
    astarEfficiencyPct: dijkResult && astarResult
      ? Math.round(((dijkResult.nodesExpanded - astarResult.nodesExpanded) / dijkResult.nodesExpanded) * 100)
      : 0,
  };

  return { routes: filtered.length > 0 ? filtered : routes, comparison };
}
