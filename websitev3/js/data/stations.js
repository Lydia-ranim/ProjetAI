/* LYHLYH stop registry. Populated from GET /api/stops. */

const STATIONS = [];
const SMAP = {};

const TYPE_COLOR = {
  metro: '#2196F3',
  bus: '#FF9800',
  tram: '#4CAF50',
  train: '#E91E63',
  walk: '#9E9E9E',
  telepherique: '#9C27B0',
  cable: '#9C27B0',
  escalator: '#78909C',
  default: '#BEEEDB',
};

const MODE_ICON = {
  metro: 'M',
  bus: 'B',
  tram: 'T',
  train: 'R',
  walk: 'W',
  telepherique: 'C',
  cable: 'C',
  escalator: 'E',
  default: 'P',
};

function normalizeModeKey(m) {
  const k = String(m || '').toLowerCase().trim();
  if (k === 'telepherique' || k === 'téléphérique' || k === 'cable') return 'telepherique';
  return k;
}

function formatLineLabel(type) {
  const t = normalizeModeKey(type);
  const labels = {
    metro: 'Metro',
    bus: 'Bus',
    tram: 'Tram',
    train: 'Train',
    walk: 'Walk',
    telepherique: 'Telepherique',
    escalator: 'Escalator',
  };
  return labels[t] || (type ? String(type) : 'Stop');
}

function normalizeApiStop(raw) {
  const id = String(raw.id);
  const name = raw.name || id;
  const lat = Number(raw.lat);
  const lon = Number(raw.lon);
  const type = normalizeModeKey(raw.type || 'metro');
  const short = name.length > 22 ? `${name.slice(0, 20)}...` : name;
  const hub = !!raw.isHub;
  const map = raw.map || {};
  return {
    id,
    name,
    short,
    coords: [lat, lon],
    type,
    line: hub ? `${formatLineLabel(type)} - hub` : formatLineLabel(type),
    icon: map.icon || MODE_ICON[type] || MODE_ICON.default,
    color: map.color || TYPE_COLOR[type] || TYPE_COLOR.default,
    map,
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
