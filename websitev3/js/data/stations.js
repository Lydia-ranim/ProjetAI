/* ═══════════════════════════════════════════════════════════
   LYHLYH — stations.js  Stop registry (filled from GET /api/stops)
═══════════════════════════════════════════════════════════ */

/** @type {Array<Object>} Populated by loadAllStops() */
const STATIONS = [];

/** @type {Record<string, Object>} id → station */
const SMAP = {};

const TYPE_COLOR = {
  metro: '#2196F3',
  bus: '#FF9800',
  tram: '#4CAF50',
  train: '#F2C4CE',
  walk: '#9E9E9E',
  telepherique: '#9C27B0',
  cable: '#9C27B0',
  escalator: '#78909C',
  default: '#BEEEDB',
};

const MODE_ICON = {
  metro: '🚇',
  bus: '🚌',
  tram: '🚊',
  train: '🚆',
  walk: '🚶',
  telepherique: '🚡',
  cable: '🚡',
  escalator: '🛗',
  default: '📍',
};

/** Normalize backend mode strings for comparisons and colouring. */
function normalizeModeKey(m) {
  let k = String(m || '')
    .toLowerCase()
    .trim();
  if (k === 'téléphérique' || k === 'telepherique') return 'telepherique';
  if (k === 'cable') return 'telepherique';
  return k;
}

function formatLineLabel(type) {
  const t = (type || '').toLowerCase();
  const labels = {
    metro: 'Métro',
    bus: 'Bus',
    tram: 'Tram',
    train: 'Train',
    walk: 'Marche',
    telepherique: 'Téléphérique',
    cable: 'Téléphérique',
    escalator: 'Escalier mécanique',
  };
  return labels[t] || (type ? String(type) : 'Arrêt');
}

/**
 * Map a row from GET /api/stops into the shape used by the UI.
 * @param {{ id:string, name:string, lat:number, lon:number, type:string, isHub?:boolean }} raw
 */
function normalizeApiStop(raw) {
  const id = String(raw.id);
  const name = raw.name || id;
  const lat = Number(raw.lat);
  const lon = Number(raw.lon);
  const type = String(raw.type || 'metro').toLowerCase();
  const short = name.length > 22 ? `${name.slice(0, 20)}…` : name;
  const hub = !!raw.isHub;
  return {
    id,
    name,
    short,
    coords: [lat, lon],
    type,
    line: hub ? `${formatLineLabel(type)} · hub` : formatLineLabel(type),
    icon: MODE_ICON[type] || MODE_ICON.default,
    isHub: hub,
  };
}

function rebuildSMAP() {
  Object.keys(SMAP).forEach(k => {
    delete SMAP[k];
  });
  STATIONS.forEach(s => {
    SMAP[s.id] = s;
  });
}

/** Insert or update a single stop (e.g. from /api/nearest-stop) without rebuilding all ids. */
function ensureStopInRegistry(stopObj) {
  if (!stopObj || !stopObj.id) return;
  if (SMAP[stopObj.id]) {
    Object.assign(SMAP[stopObj.id], stopObj);
    const ix = STATIONS.findIndex(s => s.id === stopObj.id);
    if (ix >= 0) STATIONS[ix] = SMAP[stopObj.id];
    return;
  }
  STATIONS.push(stopObj);
  SMAP[stopObj.id] = stopObj;
}

/** Hex stroke color for map polylines by backend mode key. */
const MODE_LINE_COLOR_HEX = {
  bus: '#FF9800',
  metro: '#2196F3',
  tram: '#4CAF50',
  walk: '#9E9E9E',
  telepherique: '#9C27B0',
  cable: '#9C27B0',
  train: '#E91E63',
  escalator: '#78909C',
  default: '#5C6BC0',
};

/* ═══════════════════════════════════════════════════════════
   Working-hours schedule  (populated from GET /api/working-hours)
═══════════════════════════════════════════════════════════ */

/** @type {Record<string, {open:number, close:number}>} */
let WORKING_HOURS_MAP = {};

/** Store the schedule fetched from the API. */
function setWorkingHours(data) {
  WORKING_HOURS_MAP = data && typeof data === 'object' ? data : {};
}

/**
 * Check whether a transport mode is currently in service.
 * Walking is always allowed. Modes not present in the schedule are assumed in service.
 * @param {string} modeKey  normalized mode key (metro, bus, tram, train, telepherique, walk)
 * @param {number} [clockHour]  fractional hour (e.g. 8.5 = 08:30). Defaults to now.
 * @returns {boolean}
 */
function isStopInService(modeKey, clockHour) {
  if (modeKey === 'walk') return true;
  if (!Object.keys(WORKING_HOURS_MAP).length) return true;  // schedule not loaded yet → show all
  const entry = WORKING_HOURS_MAP[modeKey];
  if (!entry) return true;  // unknown mode → assume in service
  if (clockHour == null) {
    const now = new Date();
    clockHour = now.getHours() + now.getMinutes() / 60;
  }
  return clockHour >= entry.open && clockHour < entry.close;
}
