/* ═══════════════════════════════════════════════════════════
   LYHLYH — transit-store.js  Route results + stops hydration
   Depends on: stations.js, api.js
═══════════════════════════════════════════════════════════ */

/** @type {Array<Object>} */
let transitRoutes = [];
let transitSelectedIdx = 0;
let transitLastRequestMs = 0;

/** Last trip endpoints for switching Pareto variants without re-fetching. */
let planningOrigin = null;
let planningDest = null;

function transitStoreSetPlanningContext(origin, dest) {
  planningOrigin = origin;
  planningDest = dest;
}

function transitStoreGetPlanningContext() {
  return { origin: planningOrigin, dest: planningDest };
}

function transitStoreSetRoutes(routes, elapsedMs) {
  transitRoutes = Array.isArray(routes) ? routes : [];
  transitSelectedIdx = 0;
  transitLastRequestMs = elapsedMs || 0;
}

function transitStoreGetRoutes() {
  return transitRoutes;
}

function transitStoreSelectedIndex() {
  return transitSelectedIdx;
}

function transitStoreSelectRoute(index) {
  const n = transitRoutes.length;
  if (!n) return;
  transitSelectedIdx = Math.max(0, Math.min(index, n - 1));
}

function transitStoreSelectedRoute() {
  return transitRoutes[transitSelectedIdx] || null;
}

function transitStoreLastElapsedMs() {
  return transitLastRequestMs;
}

/**
 * Load all stops into STATIONS / SMAP (see stations.js).
 * @returns {Promise<number>} number of stops loaded
 */
async function loadAllStops() {
  const raw = await fetchStops();
  if (!Array.isArray(raw)) throw new Error('Réponse /api/stops invalide');
  STATIONS.length = 0;
  raw.forEach(r => STATIONS.push(normalizeApiStop(r)));
  rebuildSMAP();
  return STATIONS.length;
}
