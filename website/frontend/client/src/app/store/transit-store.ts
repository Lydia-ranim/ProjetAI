import { create } from 'zustand';
import {
  type Route, type AlgoComparison, type SearchResult,
  findRoutes, type Weights, type CSPConstraints,
} from '../utils/algorithms';
import { type Stop, type TransportMode, getAlgiersGraph } from '../utils/algiers-graph';

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

const PRESETS: Record<string, Weights> = {
  fastest:  { time: 0.8, cost: 0.1, co2: 0.1 },
  cheapest: { time: 0.1, cost: 0.8, co2: 0.1 },
  greenest: { time: 0.1, cost: 0.1, co2: 0.8 },
  balanced: { time: 0.34, cost: 0.33, co2: 0.33 },
};

const graph = getAlgiersGraph();

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

  graphStats: { nodes: graph.stops.length, edges: graph.edges.length, loaded: true },

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

    setTimeout(() => {
      try {
        const result = findRoutes(graph, {
          startId: state.startStop!.id,
          endId: state.endStop!.id,
          weights: state.weights,
          enabledModes: state.enabledModes as Record<TransportMode, boolean>,
          constraints: state.constraints,
        });

        set({
          routes: result.routes,
          selectedRoute: result.routes[0] || null,
          algoComparison: result.comparison,
          isLoading: false,
        });
      } catch (e) {
        set({
          error: 'No route found with current settings. Try relaxing constraints.',
          isLoading: false,
          routes: [],
          selectedRoute: null,
        });
      }
    }, 100);
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
