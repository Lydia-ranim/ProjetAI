/* ═══════════════════════════════════════════════════════════
   LYHLYH — api.js  Backend client (FastAPI)
═══════════════════════════════════════════════════════════ */

const API_BASE = 'http://localhost:8000';

/**
 * @param {string} path
 * @param {RequestInit} [init]
 */
async function apiFetchJson(path, init) {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: { Accept: 'application/json', ...(init && init.headers) },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `HTTP ${res.status}`);
  }
  const ct = res.headers.get('content-type') || '';
  if (!ct.includes('application/json')) return null;
  return res.json();
}

/** @returns {Promise<Array<{id:string,name:string,lat:number,lon:number,type:string,isHub?:boolean}>>} */
function fetchStops() {
  return apiFetchJson('/api/stops');
}

/**
 * @param {number} lat
 * @param {number} lon
 * @param {number} [limit=5]
 */
async function fetchNearestStop(lat, lon, limit = 5) {
  const q = `lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}&limit=${encodeURIComponent(limit)}`;
  const data = await apiFetchJson(`/api/nearest-stop?${q}`);
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.stops)) return data.stops;
  if (data && Array.isArray(data.results)) return data.results;
  return [];
}

/**
 * POST /api/route
 * @param {{
 *   start: { lat:number, lon:number, stopId?: string },
 *   end: { lat:number, lon:number, stopId?: string },
 *   weights: { time:number, cost:number, co2:number },
 *   transportModes: Record<string, boolean>
 * }} body
 */
function fetchRoutes(body) {
  return apiFetchJson('/api/route', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

/**
 * GET /api/working-hours
 * @returns {Promise<Record<string, {open:number, close:number}>>}
 */
function fetchWorkingHours() {
  return apiFetchJson('/api/working-hours');
}
