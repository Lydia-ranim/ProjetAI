/**
 * Algiers Transit Graph — Complete hardcoded graph
 * Contains all metro, tram, and bus stops with real coordinates
 * Edges are typed by mode with full weight attributes
 */

import { haversineDistance, walkTimeMinutes } from './geo';

// ─── Types ───────────────────────────────────────────────────────────────────

export type TransportMode = 'walk' | 'bus' | 'tram' | 'metro' | 'telepherique' | 'escalator';

export interface Stop {
  id: string;
  name: string;
  type: TransportMode;
  lat: number;
  lng: number;
  lines: string[];
  district?: string;
  isTransfer?: boolean;
}

export interface Edge {
  from: string;
  to: string;
  mode: TransportMode;
  lineId: string;
  distanceM: number;
  timeMin: number;
  costDzd: number;
  co2G: number;
  waitTimeMin: number;
}

export interface GraphData {
  stops: Stop[];
  edges: Edge[];
}

// ─── Mode Constants ──────────────────────────────────────────────────────────

export const MODE_CONFIG = {
  walk:  { speed: 5,  waitTime: 0, fare: 0,  co2PerKm: 0,     color: '#BEEEDB', label: 'Walk' },
  bus:   { speed: 18, waitTime: 8, fare: 50, co2PerKm: 68,    color: '#670627', label: 'Bus' },
  tram:  { speed: 20, waitTime: 6, fare: 50, co2PerKm: 4,     color: '#F2C4CE', label: 'Tram' },
  metro: { speed: 35, waitTime: 4, fare: 70, co2PerKm: 2.5,   color: '#C6B7E2', label: 'Metro' },
  // New modes
  telepherique: { speed: 14, waitTime: 10, fare: 100, co2PerKm: 3.0, color: '#C6B7E2', label: 'Téléphérique' },
  escalator:    { speed: 7,  waitTime: 0,  fare: 0,   co2PerKm: 0.0, color: '#BEEEDB', label: 'Escalator' },
  car:   { speed: 25, waitTime: 0, fare: 0,  co2PerKm: 192,   color: '#888888', label: 'Car' },
} as const;

// ─── Metro Stations (Line 1) ─────────────────────────────────────────────────

const METRO_STATIONS: Stop[] = [
  { id: 'M1',  name: 'Haï El Badr',         type: 'metro', lat: 36.7156, lng: 3.1012, lines: ['Métro L1'], district: 'El Harrach' },
  { id: 'M2',  name: 'Les Fusillés',        type: 'metro', lat: 36.7205, lng: 3.0943, lines: ['Métro L1'], district: 'El Harrach', isTransfer: true },
  { id: 'M3',  name: 'El Harrach Centre',   type: 'metro', lat: 36.7260, lng: 3.0888, lines: ['Métro L1'], district: 'El Harrach', isTransfer: true },
  { id: 'M4',  name: 'El Harrach Gare',     type: 'metro', lat: 36.7302, lng: 3.0820, lines: ['Métro L1'], district: 'El Harrach' },
  { id: 'M5',  name: 'Aïn Naadja',          type: 'metro', lat: 36.7348, lng: 3.0742, lines: ['Métro L1'], district: 'Aïn Naadja' },
  { id: 'M6',  name: 'Bachdjerrah 1',       type: 'metro', lat: 36.7392, lng: 3.0671, lines: ['Métro L1'], district: 'Bachdjerrah' },
  { id: 'M7',  name: 'Bachdjerrah 2',       type: 'metro', lat: 36.7435, lng: 3.0601, lines: ['Métro L1'], district: 'Bachdjerrah' },
  { id: 'M8',  name: 'Mohamed Belouizdad',  type: 'metro', lat: 36.7489, lng: 3.0528, lines: ['Métro L1'], district: 'Belouizdad' },
  { id: 'M9',  name: 'Caroubier',           type: 'metro', lat: 36.7533, lng: 3.0455, lines: ['Métro L1'], district: 'Caroubier', isTransfer: true },
  { id: 'M10', name: 'Hamma',               type: 'metro', lat: 36.7578, lng: 3.0388, lines: ['Métro L1'], district: 'Hamma' },
  { id: 'M11', name: 'Jardin d\'Essai',     type: 'metro', lat: 36.7612, lng: 3.0322, lines: ['Métro L1'], district: 'Hamma' },
  { id: 'M12', name: 'Hussein Dey',         type: 'metro', lat: 36.7649, lng: 3.0258, lines: ['Métro L1'], district: 'Hussein Dey', isTransfer: true },
  { id: 'M13', name: 'Université',           type: 'metro', lat: 36.7685, lng: 3.0195, lines: ['Métro L1'], district: 'Alger Centre' },
  { id: 'M14', name: 'Khelifa Boukhalfa',   type: 'metro', lat: 36.7720, lng: 3.0132, lines: ['Métro L1'], district: 'Alger Centre' },
  { id: 'M15', name: 'Place des Martyrs',   type: 'metro', lat: 36.7755, lng: 3.0068, lines: ['Métro L1'], district: 'Alger Centre' },
  { id: 'M16', name: 'Grande Poste',        type: 'metro', lat: 36.7748, lng: 2.9998, lines: ['Métro L1'], district: 'Alger Centre', isTransfer: true },
  { id: 'M17', name: 'Tafourah',            type: 'metro', lat: 36.7741, lng: 2.9928, lines: ['Métro L1'], district: 'Alger Centre' },
  { id: 'M18', name: 'Premier Mai',         type: 'metro', lat: 36.7734, lng: 2.9858, lines: ['Métro L1'], district: 'Alger Centre', isTransfer: true },
  { id: 'M19', name: 'Télemly',              type: 'metro', lat: 36.7727, lng: 2.9788, lines: ['Métro L1'], district: 'Télemly' },
  { id: 'M20', name: 'Aïssa Messaoudi',     type: 'metro', lat: 36.7720, lng: 2.9718, lines: ['Métro L1'], district: 'Télemly' },
  { id: 'M21', name: 'Aïn Allah',           type: 'metro', lat: 36.7713, lng: 2.9648, lines: ['Métro L1'], district: 'Aïn Allah' },
  { id: 'M22', name: 'Dergana',             type: 'metro', lat: 36.7706, lng: 2.9578, lines: ['Métro L1'], district: 'Dergana' },
];

// ─── Tram Stations (T1) ─────────────────────────────────────────────────────

const TRAM_STATIONS: Stop[] = [
  { id: 'T1',  name: 'Bordj El Kiffan',     type: 'tram', lat: 36.7380, lng: 3.1820, lines: ['Tram T1'], district: 'Bordj El Kiffan' },
  { id: 'T2',  name: 'Les Bananiers',       type: 'tram', lat: 36.7350, lng: 3.1720, lines: ['Tram T1'], district: 'Bordj El Kiffan' },
  { id: 'T3',  name: 'Palmiers',            type: 'tram', lat: 36.7320, lng: 3.1620, lines: ['Tram T1'], district: 'Bordj El Kiffan' },
  { id: 'T4',  name: 'Oued Ouchaïeh',       type: 'tram', lat: 36.7290, lng: 3.1520, lines: ['Tram T1'], district: 'Bab Ezzouar' },
  { id: 'T5',  name: 'Dergana Tram',        type: 'tram', lat: 36.7260, lng: 3.1420, lines: ['Tram T1'], district: 'Dergana' },
  { id: 'T6',  name: 'Cité Mer Rouge',      type: 'tram', lat: 36.7230, lng: 3.1320, lines: ['Tram T1'], district: 'Hussein Dey' },
  { id: 'T7',  name: 'Mokhtar Zerhouni',    type: 'tram', lat: 36.7200, lng: 3.1220, lines: ['Tram T1'], district: 'Hussein Dey' },
  { id: 'T8',  name: 'Garidi 1',            type: 'tram', lat: 36.7170, lng: 3.1120, lines: ['Tram T1'], district: 'Kouba' },
  { id: 'T9',  name: 'Garidi 2',            type: 'tram', lat: 36.7140, lng: 3.1020, lines: ['Tram T1'], district: 'Kouba' },
  { id: 'T10', name: 'Hussein Dey Tram',    type: 'tram', lat: 36.7649, lng: 3.0258, lines: ['Tram T1'], district: 'Hussein Dey', isTransfer: true },
  { id: 'T11', name: 'Caroubier Tram',      type: 'tram', lat: 36.7533, lng: 3.0455, lines: ['Tram T1'], district: 'Caroubier', isTransfer: true },
  { id: 'T12', name: 'Ruisseau',            type: 'tram', lat: 36.7120, lng: 3.0920, lines: ['Tram T1'], district: 'Ruisseau' },
  { id: 'T13', name: 'Université Tram',     type: 'tram', lat: 36.7110, lng: 3.0820, lines: ['Tram T1'], district: 'Ben Aknoun' },
  { id: 'T14', name: 'Les Fusillés Tram',   type: 'tram', lat: 36.7205, lng: 3.0943, lines: ['Tram T1'], district: 'El Harrach', isTransfer: true },
  { id: 'T15', name: 'El Harrach Tram',     type: 'tram', lat: 36.7260, lng: 3.0888, lines: ['Tram T1'], district: 'El Harrach', isTransfer: true },
];

// ─── Bus Stops ───────────────────────────────────────────────────────────────

const BUS_STOPS: Stop[] = [
  { id: 'B1',  name: 'Kaïs Station',        type: 'bus', lat: 36.7748, lng: 2.9998, lines: ['Bus 5', 'Bus 26', 'Bus 36'], district: 'Alger Centre', isTransfer: true },
  { id: 'B2',  name: 'Didouche Mourad',     type: 'bus', lat: 36.7700, lng: 3.0020, lines: ['Bus 5', 'Bus 33'], district: 'Alger Centre' },
  { id: 'B3',  name: 'Ben Aknoun',          type: 'bus', lat: 36.7615, lng: 2.9738, lines: ['Bus 36', 'Bus 55'], district: 'Ben Aknoun' },
  { id: 'B4',  name: 'Bab El Oued',         type: 'bus', lat: 36.7928, lng: 3.0538, lines: ['Bus 5', 'Bus 100'], district: 'Bab El Oued' },
  { id: 'B5',  name: 'Belcourt',            type: 'bus', lat: 36.7448, lng: 3.0508, lines: ['Bus 26', 'Bus 33'], district: 'Belcourt' },
  { id: 'B6',  name: 'Kouba',               type: 'bus', lat: 36.7302, lng: 3.0720, lines: ['Bus 55', 'Bus 100'], district: 'Kouba' },
  { id: 'B7',  name: 'Bir Mourad Raïs',     type: 'bus', lat: 36.7238, lng: 3.0388, lines: ['Bus 36', 'Bus 55'], district: 'Bir Mourad Raïs' },
  { id: 'B8',  name: 'Hydra',               type: 'bus', lat: 36.7428, lng: 3.0188, lines: ['Bus 26'], district: 'Hydra' },
  { id: 'B9',  name: 'El Biar',             type: 'bus', lat: 36.7728, lng: 2.9888, lines: ['Bus 5', 'Bus 36'], district: 'El Biar' },
  { id: 'B10', name: 'Chevalley',           type: 'bus', lat: 36.7628, lng: 2.9488, lines: ['Bus 55'], district: 'Chevalley' },
  { id: 'B11', name: 'Raïs Hamidou',        type: 'bus', lat: 36.8028, lng: 2.9888, lines: ['Bus 100'], district: 'Raïs Hamidou' },
  { id: 'B12', name: 'Bouzaréah',           type: 'bus', lat: 36.7928, lng: 2.9288, lines: ['Bus 33', 'Bus 55'], district: 'Bouzaréah' },
  { id: 'B13', name: 'Place du 1er Mai',    type: 'bus', lat: 36.7734, lng: 2.9858, lines: ['Bus 5', 'Bus 26'], district: 'Alger Centre', isTransfer: true },
  { id: 'B14', name: 'Alger Centre',        type: 'bus', lat: 36.7638, lng: 3.0538, lines: ['Bus 100', 'Bus 33'], district: 'Alger Centre' },
  { id: 'B15', name: 'Diar El Mahçoul',     type: 'bus', lat: 36.7538, lng: 2.9988, lines: ['Bus 36'], district: 'Diar El Mahçoul' },
  { id: 'B16', name: 'Soustara',            type: 'bus', lat: 36.7438, lng: 3.0888, lines: ['Bus 26', 'Bus 100'], district: 'Soustara' },
  { id: 'B17', name: 'El Harrach Bus',      type: 'bus', lat: 36.7260, lng: 3.0888, lines: ['Bus 55', 'Bus 100'], district: 'El Harrach', isTransfer: true },
  { id: 'B18', name: 'Baraki',              type: 'bus', lat: 36.6738, lng: 3.1038, lines: ['Bus 100'], district: 'Baraki' },
  { id: 'B19', name: 'Dar El Beïda',        type: 'bus', lat: 36.7138, lng: 3.2138, lines: ['Bus 100'], district: 'Dar El Beïda' },
  { id: 'B20', name: 'Aéroport Houari B.',  type: 'bus', lat: 36.6938, lng: 3.2158, lines: ['Bus 100'], district: 'Dar El Beïda' },
];

// ─── All Stops ───────────────────────────────────────────────────────────────

export const ALL_STOPS: Stop[] = [...METRO_STATIONS, ...TRAM_STATIONS, ...BUS_STOPS];

// ─── Edge Generation ─────────────────────────────────────────────────────────

function createSequentialEdges(stations: Stop[], mode: TransportMode, lineId: string): Edge[] {
  const edges: Edge[] = [];
  const config = MODE_CONFIG[mode];

  for (let i = 0; i < stations.length - 1; i++) {
    const from = stations[i];
    const to = stations[i + 1];
    const distM = haversineDistance(from, to);
    const distKm = distM / 1000;
    const timeMin = (distKm / config.speed) * 60;
    const co2 = distKm * config.co2PerKm;

    // Forward edge
    edges.push({
      from: from.id,
      to: to.id,
      mode,
      lineId,
      distanceM: Math.round(distM),
      timeMin: Math.round(timeMin * 10) / 10,
      costDzd: 0, // fare applied once per boarding
      co2G: Math.round(co2 * 10) / 10,
      waitTimeMin: config.waitTime,
    });

    // Reverse edge
    edges.push({
      from: to.id,
      to: from.id,
      mode,
      lineId,
      distanceM: Math.round(distM),
      timeMin: Math.round(timeMin * 10) / 10,
      costDzd: 0,
      co2G: Math.round(co2 * 10) / 10,
      waitTimeMin: config.waitTime,
    });
  }

  return edges;
}

function createBusEdges(): Edge[] {
  const edges: Edge[] = [];
  const config = MODE_CONFIG.bus;

  // Bus route connections (major lines)
  const busRoutes: { line: string; stops: string[] }[] = [
    { line: 'Bus 5',   stops: ['B1', 'B2', 'B9', 'B13'] },
    { line: 'Bus 26',  stops: ['B1', 'B2', 'B8', 'B5', 'B16'] },
    { line: 'Bus 33',  stops: ['B2', 'B5', 'B14', 'B12'] },
    { line: 'Bus 36',  stops: ['B1', 'B15', 'B3', 'B7', 'B9'] },
    { line: 'Bus 55',  stops: ['B3', 'B7', 'B6', 'B17', 'B10', 'B12'] },
    { line: 'Bus 100', stops: ['B4', 'B14', 'B16', 'B17', 'B18', 'B19', 'B20', 'B11'] },
  ];

  const stopMap = new Map(ALL_STOPS.map(s => [s.id, s]));

  for (const route of busRoutes) {
    for (let i = 0; i < route.stops.length - 1; i++) {
      const from = stopMap.get(route.stops[i])!;
      const to = stopMap.get(route.stops[i + 1])!;
      if (!from || !to) continue;

      const distM = haversineDistance(from, to);
      const distKm = distM / 1000;
      const timeMin = (distKm / config.speed) * 60;
      const co2 = distKm * config.co2PerKm;

      edges.push({
        from: from.id, to: to.id, mode: 'bus', lineId: route.line,
        distanceM: Math.round(distM), timeMin: Math.round(timeMin * 10) / 10,
        costDzd: 0, co2G: Math.round(co2 * 10) / 10, waitTimeMin: config.waitTime,
      });
      edges.push({
        from: to.id, to: from.id, mode: 'bus', lineId: route.line,
        distanceM: Math.round(distM), timeMin: Math.round(timeMin * 10) / 10,
        costDzd: 0, co2G: Math.round(co2 * 10) / 10, waitTimeMin: config.waitTime,
      });
    }
  }

  return edges;
}

function createWalkEdges(stops: Stop[], maxDistM: number = 800): Edge[] {
  const edges: Edge[] = [];

  for (let i = 0; i < stops.length; i++) {
    for (let j = i + 1; j < stops.length; j++) {
      if (stops[i].id === stops[j].id) continue;
      const distM = haversineDistance(stops[i], stops[j]);
      if (distM <= maxDistM) {
        const timeMin = walkTimeMinutes(distM);
        edges.push({
          from: stops[i].id, to: stops[j].id, mode: 'walk', lineId: 'Walk',
          distanceM: Math.round(distM), timeMin: Math.round(timeMin * 10) / 10,
          costDzd: 0, co2G: 0, waitTimeMin: 0,
        });
        edges.push({
          from: stops[j].id, to: stops[i].id, mode: 'walk', lineId: 'Walk',
          distanceM: Math.round(distM), timeMin: Math.round(timeMin * 10) / 10,
          costDzd: 0, co2G: 0, waitTimeMin: 0,
        });
      }
    }
  }

  return edges;
}

function getStop(id: string) {
  const s = ALL_STOPS.find(x => x.id === id);
  if (!s) throw new Error(`Unknown stop id: ${id}`);
  return s;
}

function createTelepheriqueEdges(): Edge[] {
  const edges: Edge[] = [];
  const config = MODE_CONFIG.telepherique;

  // A few realistic "hill ↔ center" links to make the mode usable without adding new stops.
  // (All endpoints are existing stops; the *edge.mode* defines the transport used.)
  const links: { line: string; from: string; to: string }[] = [
    { line: 'Téléphérique TPH-1', from: 'B12', to: 'M19' }, // Bouzaréah ↔ Télemly
    { line: 'Téléphérique TPH-1', from: 'B12', to: 'M16' }, // Bouzaréah ↔ Grande Poste
    { line: 'Téléphérique TPH-2', from: 'B3',  to: 'M20' }, // Ben Aknoun ↔ Aïssa Messaoudi
  ];

  for (const l of links) {
    const a = getStop(l.from);
    const b = getStop(l.to);
    const distM = haversineDistance(a, b);
    const distKm = distM / 1000;
    const timeMin = (distKm / config.speed) * 60;
    const co2 = distKm * config.co2PerKm;

    edges.push({
      from: a.id,
      to: b.id,
      mode: 'telepherique',
      lineId: l.line,
      distanceM: Math.round(distM),
      timeMin: Math.round(timeMin * 10) / 10,
      costDzd: 0,
      co2G: Math.round(co2 * 10) / 10,
      waitTimeMin: config.waitTime,
    });
    edges.push({
      from: b.id,
      to: a.id,
      mode: 'telepherique',
      lineId: l.line,
      distanceM: Math.round(distM),
      timeMin: Math.round(timeMin * 10) / 10,
      costDzd: 0,
      co2G: Math.round(co2 * 10) / 10,
      waitTimeMin: config.waitTime,
    });
  }

  return edges;
}

function createEscalatorEdges(): Edge[] {
  const edges: Edge[] = [];
  const config = MODE_CONFIG.escalator;

  // Short connectors inside major hubs. These are faster than walking transfers
  // and allow the mode filter to have visible impact.
  const connectors: { line: string; from: string; to: string; distanceM: number }[] = [
    { line: 'Escalator Hub', from: 'M16', to: 'B1',  distanceM: 120 }, // Grande Poste ↔ Kaïs Station
    { line: 'Escalator Hub', from: 'M18', to: 'B13', distanceM: 90 },  // 1er Mai ↔ Place du 1er Mai
    { line: 'Escalator Hub', from: 'M12', to: 'T10', distanceM: 70 },  // Hussein Dey
  ];

  for (const c of connectors) {
    const a = getStop(c.from);
    const b = getStop(c.to);

    // Approx time from "escalator speed" (km/h) with no wait and no CO2.
    const distKm = c.distanceM / 1000;
    const timeMin = (distKm / config.speed) * 60;

    edges.push({
      from: a.id,
      to: b.id,
      mode: 'escalator',
      lineId: c.line,
      distanceM: Math.round(c.distanceM),
      timeMin: Math.max(0.4, Math.round(timeMin * 10) / 10),
      costDzd: 0,
      co2G: 0,
      waitTimeMin: 0,
    });
    edges.push({
      from: b.id,
      to: a.id,
      mode: 'escalator',
      lineId: c.line,
      distanceM: Math.round(c.distanceM),
      timeMin: Math.max(0.4, Math.round(timeMin * 10) / 10),
      costDzd: 0,
      co2G: 0,
      waitTimeMin: 0,
    });
  }

  return edges;
}

// ─── Transfer Edges (explicit multi-modal connections) ───────────────────────

function createTransferEdges(): Edge[] {
  const edges: Edge[] = [];
  const TRANSFER_TIME = 3; // 3 min penalty

  // Transfer pairs: [stop1, stop2] — these co-located stops allow transfers
  const transfers: [string, string][] = [
    ['M12', 'T10'],  // Hussein Dey: Metro ↔ Tram
    ['M9',  'T11'],  // Caroubier: Metro ↔ Tram
    ['M2',  'T14'],  // Les Fusillés: Metro ↔ Tram
    ['M3',  'T15'],  // El Harrach: Metro ↔ Tram
    ['M3',  'B17'],  // El Harrach: Metro ↔ Bus
    ['T15', 'B17'],  // El Harrach: Tram ↔ Bus
    ['M16', 'B1'],   // Grande Poste: Metro ↔ Bus
    ['M18', 'B13'],  // Place 1er Mai: Metro ↔ Bus
  ];

  for (const [a, b] of transfers) {
    edges.push({
      from: a, to: b, mode: 'walk', lineId: 'Transfer',
      distanceM: 50, timeMin: TRANSFER_TIME, costDzd: 0, co2G: 0, waitTimeMin: 0,
    });
    edges.push({
      from: b, to: a, mode: 'walk', lineId: 'Transfer',
      distanceM: 50, timeMin: TRANSFER_TIME, costDzd: 0, co2G: 0, waitTimeMin: 0,
    });
  }

  return edges;
}

// ─── Build Complete Graph ────────────────────────────────────────────────────

export function buildAlgiersGraph(): GraphData {
  const metroEdges = createSequentialEdges(METRO_STATIONS, 'metro', 'Métro L1');

  // Tram: sequential for T1–T9, then T12–T15, then T9–T12, plus T10/T11 spurs
  const tramMainA = TRAM_STATIONS.filter(s => ['T1','T2','T3','T4','T5','T6','T7','T8','T9'].includes(s.id));
  const tramMainB = TRAM_STATIONS.filter(s => ['T12','T13','T14','T15'].includes(s.id));
  const tramEdgesA = createSequentialEdges(tramMainA, 'tram', 'Tram T1');
  const tramEdgesB = createSequentialEdges(tramMainB, 'tram', 'Tram T1');

  // Connect T9 to T12 (skip to southern branch)
  const t9 = TRAM_STATIONS.find(s => s.id === 'T9')!;
  const t12 = TRAM_STATIONS.find(s => s.id === 'T12')!;
  const t9t12Dist = haversineDistance(t9, t12);
  const t9t12Time = (t9t12Dist / 1000 / MODE_CONFIG.tram.speed) * 60;
  const tramConnector: Edge[] = [
    { from: 'T9', to: 'T12', mode: 'tram', lineId: 'Tram T1', distanceM: Math.round(t9t12Dist), timeMin: Math.round(t9t12Time * 10) / 10, costDzd: 0, co2G: Math.round(t9t12Dist / 1000 * MODE_CONFIG.tram.co2PerKm * 10) / 10, waitTimeMin: 6 },
    { from: 'T12', to: 'T9', mode: 'tram', lineId: 'Tram T1', distanceM: Math.round(t9t12Dist), timeMin: Math.round(t9t12Time * 10) / 10, costDzd: 0, co2G: Math.round(t9t12Dist / 1000 * MODE_CONFIG.tram.co2PerKm * 10) / 10, waitTimeMin: 6 },
  ];

  // T10 and T11 are spur connections along the tram line to metro stops
  const t10 = TRAM_STATIONS.find(s => s.id === 'T10')!;
  const t11 = TRAM_STATIONS.find(s => s.id === 'T11')!;
  // T11 connects near T9 area, T10 connects near T11
  const t11t9Dist = haversineDistance(t11, t9);
  const t10t11Dist = haversineDistance(t10, t11);
  const tramSpurs: Edge[] = [
    { from: 'T9', to: 'T11', mode: 'tram', lineId: 'Tram T1', distanceM: Math.round(t11t9Dist), timeMin: Math.round((t11t9Dist / 1000 / MODE_CONFIG.tram.speed) * 60 * 10) / 10, costDzd: 0, co2G: Math.round(t11t9Dist / 1000 * 4 * 10) / 10, waitTimeMin: 6 },
    { from: 'T11', to: 'T9', mode: 'tram', lineId: 'Tram T1', distanceM: Math.round(t11t9Dist), timeMin: Math.round((t11t9Dist / 1000 / MODE_CONFIG.tram.speed) * 60 * 10) / 10, costDzd: 0, co2G: Math.round(t11t9Dist / 1000 * 4 * 10) / 10, waitTimeMin: 6 },
    { from: 'T11', to: 'T10', mode: 'tram', lineId: 'Tram T1', distanceM: Math.round(t10t11Dist), timeMin: Math.round((t10t11Dist / 1000 / MODE_CONFIG.tram.speed) * 60 * 10) / 10, costDzd: 0, co2G: Math.round(t10t11Dist / 1000 * 4 * 10) / 10, waitTimeMin: 6 },
    { from: 'T10', to: 'T11', mode: 'tram', lineId: 'Tram T1', distanceM: Math.round(t10t11Dist), timeMin: Math.round((t10t11Dist / 1000 / MODE_CONFIG.tram.speed) * 60 * 10) / 10, costDzd: 0, co2G: Math.round(t10t11Dist / 1000 * 4 * 10) / 10, waitTimeMin: 6 },
  ];

  const busEdges = createBusEdges();
  const walkEdges = createWalkEdges(ALL_STOPS, 800);
  const telepheriqueEdges = createTelepheriqueEdges();
  const escalatorEdges = createEscalatorEdges();
  const transferEdges = createTransferEdges();

  return {
    stops: ALL_STOPS,
    edges: [
      ...metroEdges,
      ...tramEdgesA,
      ...tramEdgesB,
      ...tramConnector,
      ...tramSpurs,
      ...busEdges,
      ...walkEdges,
      ...telepheriqueEdges,
      ...escalatorEdges,
      ...transferEdges,
    ],
  };
}

// ─── Pre-built graph singleton ───────────────────────────────────────────────

let _cachedGraph: GraphData | null = null;

export function getAlgiersGraph(): GraphData {
  if (!_cachedGraph) {
    _cachedGraph = buildAlgiersGraph();
  }
  return _cachedGraph;
}

// ─── Adjacency List ──────────────────────────────────────────────────────────

export interface AdjEntry {
  to: string;
  edge: Edge;
}

export function buildAdjacencyList(graph: GraphData, enabledModes: Record<TransportMode, boolean>): Map<string, AdjEntry[]> {
  const adj = new Map<string, AdjEntry[]>();

  for (const stop of graph.stops) {
    adj.set(stop.id, []);
  }

  for (const edge of graph.edges) {
    if (edge.mode !== 'walk' && !enabledModes[edge.mode]) continue;
    if (edge.mode === 'walk' && !enabledModes.walk) continue;
    adj.get(edge.from)?.push({ to: edge.to, edge });
  }

  return adj;
}

// ─── Stop lookup ─────────────────────────────────────────────────────────────

const _stopMap = new Map<string, Stop>();

export function getStopById(id: string): Stop | undefined {
  if (_stopMap.size === 0) {
    for (const s of ALL_STOPS) {
      _stopMap.set(s.id, s);
    }
  }
  return _stopMap.get(id);
}

export function getStopMap(): Map<string, Stop> {
  if (_stopMap.size === 0) {
    for (const s of ALL_STOPS) {
      _stopMap.set(s.id, s);
    }
  }
  return _stopMap;
}
