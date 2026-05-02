import { create } from 'zustand';
import {
  type Route, type AlgoComparison, type Weights, type CSPConstraints,
} from '../utils/algorithms';
import { type Stop, type TransportMode } from '../utils/algiers-graph';
import { fetchRoutes, fetchStops } from '../utils/api';

export interface EnabledModes {
  walk: boolean;
  bus: boolean;
  tram: boolean;
  metro: boolean;
  telepherique: boolean;
  escalator: boolean;
}

export interface TransitStore {
  startStop: Stop | null;
  endStop: Stop | null;

  weights: Weights;
  enabledModes: EnabledModes;
  constraints: CSPConstraints;
  departureTime: string;

  routes: Route[];
  selectedRoute: Route | null;
  algoComparison: AlgoComparison | null;

  isLoading: boolean;
  isDarkMode: boolean;
  activeRightTab: 'details' | 'timeline' | 'ai' | 'analytics';
  showShortcuts: boolean;
  error: string | null;

  graphStats: { nodes: number; edges: number; loaded: boolean };
  stops: Stop[];
  loadStops: () => void;

  setStartStop: (stop: Stop | null) => void;
  setEndStop: (stop: Stop | null) => void;
  swapStops: () => void;
  setWeight: (key: keyof Weights, value: number) => void;
  applyPreset: (preset: 'fastest' | 'cheapest' | 'greenest' | 'balanced') => void;
  toggleMode: (mode: keyof EnabledModes) => void;
  setConstraint: <K extends keyof CSPConstraints>(key: K, value: CSPConstraints[K]) => void;
  setDepartureTime: (time: string) => void;
  findRoutes: () => void;
  selectRoute: (route: Route | null) => void;
  reset: () => void;
  toggleDarkMode: () => void;
  setActiveTab: (tab: TransitStore['activeRightTab']) => void;
  setShowShortcuts: (show: boolean) => void;
}

export interface Coordinates {
  lat: number;
  lon: number;
  stopId?: string;
}

export type TransportModes = EnabledModes;

// Map API response segment → frontend Segment shape
function mapApiSegment(s: any) {
  return {
    mode: s.mode as TransportMode,
    lineId: s.lineId || null,
    fromName: s.fromName,
    toName: s.toName,
    fromCoords: s.polyline?.[0] ?? [0, 0] as [number, number],
    toCoords: s.polyline?.[s.polyline.length - 1] ?? [0, 0] as [number, number],
    polyline: (s.polyline ?? []) as [number, number][],
    distanceM: Math.round((s.distanceKm ?? 0) * 1000),
    durationMin: s.durationMin ?? 0,
    waitMin: 0,
    costDzd: s.costDzd ?? 0,
    co2G: 0,
    departureTime: '',
    arrivalTime: '',
  };
}

// Map API response route → frontend Route shape
function mapApiRoute(r: any): Route {
  const segments = (r.segments ?? []).map(mapApiSegment);
  const walkSegs = segments.filter((s: any) => s.mode === 'walk');
  const walkingM = walkSegs.reduce((acc: number, s: any) => acc + s.distanceM, 0);
  const transfers = Math.max(0, segments.filter((s: any) => s.mode !== 'walk').length - 1);
  const totalDistM = segments.reduce((acc: number, s: any) => acc + s.distanceM, 0);
  const CAR_CO2_PER_KM = 120; // g/km
  const co2SavedVsCarG = Math.round(CAR_CO2_PER_KM * totalDistM / 1000 - (r.summary?.totalCo2G ?? 0));

  return {
    id: r.id,
    label: r.label,
    algorithmUsed: r.algorithmUsed,
    segments,
    summary: {
      totalTimeMin: r.summary?.totalTimeMin ?? 0,
      totalCostDzd: r.summary?.totalCostDzd ?? 0,
      totalCo2G: r.summary?.totalCo2G ?? 0,
      totalDistanceM: totalDistM,
      numTransfers: transfers,
      numStops: r.summary?.numStops ?? 0,
      walkingDistanceM: walkingM,
      waitingTimeMin: 0,
    },
    timeline: [],
    stressScore: 0,
    stressLabel: 'low',
    explanation: '',
    polyline: segments.flatMap((s: any) => s.polyline),
    co2SavedVsCarG: Math.max(0, co2SavedVsCarG),
    score: 0,
    nodesExpanded: r.summary?.nodesExplored ?? 0,
    computationMs: 0,
  };
}

const PRESETS: Record<string, Weights> = {
  fastest:  { time: 0.8, cost: 0.1, co2: 0.1 },
  cheapest: { time: 0.1, cost: 0.8, co2: 0.1 },
  greenest: { time: 0.1, cost: 0.1, co2: 0.8 },
  balanced: { time: 0.34, cost: 0.33, co2: 0.33 },
};

export const useTransitStore = create<TransitStore>((set, get) => ({
  startStop: null,
  endStop: null,

  weights: { time: 0.4, cost: 0.3, co2: 0.3 },
  enabledModes: { walk: true, bus: true, tram: true, metro: true, telepherique: true, escalator: true },
  constraints: { maxTransfers: -1, maxWalkingM: 2000, maxTimeMin: 180 },
  departureTime: 'now',

  routes: [],
  selectedRoute: null,
  algoComparison: null,

  isLoading: false,
  isDarkMode: true,
  activeRightTab: 'details',
  showShortcuts: false,
  error: null,

  graphStats: { nodes: 1314, edges: 19139, loaded: true },
  stops: [],

  loadStops: () => {
    fetchStops().then(stops => set({ stops })).catch(() => {});
  },

  setStartStop: (stop) => set({ startStop: stop, error: null }),
  setEndStop: (stop) => set({ endStop: stop, error: null }),
  
  swapStops: () => set((state) => ({
    startStop: state.endStop,
    endStop: state.startStop,
  })),

  setWeight: (key, value) => set((state) => {
    const other1Key = key === 'time' ? 'cost' : key === 'cost' ? 'time' : 'time';
    const other2Key = key === 'time' ? 'co2' : key === 'cost' ? 'co2' : 'cost';
    
    const remaining = 1 - value;
    const otherSum = state.weights[other1Key] + state.weights[other2Key];
    
    let newWeights: Weights;
    if (otherSum === 0) {
      newWeights = { ...state.weights, [key]: value, [other1Key]: remaining / 2, [other2Key]: remaining / 2 };
    } else {
      const ratio = remaining / otherSum;
      newWeights = {
        ...state.weights,
        [key]: value,
        [other1Key]: state.weights[other1Key] * ratio,
        [other2Key]: state.weights[other2Key] * ratio,
      };
    }
    return { weights: newWeights };
  }),

  applyPreset: (preset) => set({ weights: { ...PRESETS[preset] } }),

  toggleMode: (mode) => set((state) => {
    const newModes = { ...state.enabledModes, [mode]: !state.enabledModes[mode] };
    const enabledCount = Object.values(newModes).filter(Boolean).length;
    if (enabledCount === 0) return state;
    return { enabledModes: newModes };
  }),

  setConstraint: (key, value) => set((state) => ({
    constraints: { ...state.constraints, [key]: value },
  })),

  setDepartureTime: (time) => set({ departureTime: time }),

  findRoutes: () => {
    const state = get();
    if (!state.startStop || !state.endStop) {
      set({ error: 'Please select start and end stops' });
      return;
    }

    set({ isLoading: true, error: null });

    fetchRoutes(
      { lat: state.startStop.lat, lon: state.startStop.lng, stopId: state.startStop.id },
      { lat: state.endStop.lat,   lon: state.endStop.lng,   stopId: state.endStop.id },
      state.weights,
      state.enabledModes,
    )
      .then((rawRoutes) => {
        const routes: Route[] = rawRoutes.map((r: any) => mapApiRoute(r));
        set({ routes, selectedRoute: routes[0] || null, algoComparison: null, isLoading: false });
      })
      .catch(() => {
        set({ error: 'No route found. Check that the backend is running.', isLoading: false, routes: [], selectedRoute: null });
      });
  },

  selectRoute: (route) => set({ selectedRoute: route }),
  
  reset: () => set({
    startStop: null,
    endStop: null,
    routes: [],
    selectedRoute: null,
    algoComparison: null,
    error: null,
  }),

  toggleDarkMode: () => set((state) => ({ isDarkMode: !state.isDarkMode })),
  setActiveTab: (tab) => set({ activeRightTab: tab }),
  setShowShortcuts: (show) => set({ showShortcuts: show }),
}));
