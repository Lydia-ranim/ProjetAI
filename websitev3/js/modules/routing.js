/* ═══════════════════════════════════════════════════════════
   LYHLYH — Routing: doRoute, weights, transport modes
   Depends on: stations.js, notifications.js, map.js,
               autocomplete.js (acSel), results.js (showResultsFromApi),
               api.js, transit-store.js
═══════════════════════════════════════════════════════════ */

/* Preset profile weight vectors → normalized as time / cost / co₂ */
const ALGO_PROFILES = {
  fastest: { w1: 0.8, w2: 0.1, w3: 0.1 },
  cheapest: { w1: 0.1, w2: 0.8, w3: 0.1 },
  greenest: { w1: 0.1, w2: 0.1, w3: 0.8 },
  balanced: { w1: 0.33, w2: 0.33, w3: 0.34 },
};

/** Read custom weights from the settings sliders. */
function getGlobalWeights() {
  return {
    w1: parseFloat(document.getElementById('sw1')?.textContent) || 0.33,
    w2: parseFloat(document.getElementById('sw2')?.textContent) || 0.33,
    w3: parseFloat(document.getElementById('sw3')?.textContent) || 0.34,
  };
}

/** Sync the settings sliders when a profile card is clicked. */
function applyProfile(p) {
  const v = ALGO_PROFILES[p];
  if (!v) return;
  const sw1 = document.getElementById('sw1');
  const sw2 = document.getElementById('sw2');
  const sw3 = document.getElementById('sw3');
  if (sw1) sw1.textContent = v.w1.toFixed(2);
  if (sw2) sw2.textContent = v.w2.toFixed(2);
  if (sw3) sw3.textContent = v.w3.toFixed(2);
}

/** Toggle advanced search params panel. */
function toggleSearchParams() {
  const panel = document.getElementById('search-params-panel');
  const arrow = document.getElementById('toggle-params-arrow');
  const open = panel.style.display !== 'none';
  panel.style.display = open ? 'none' : 'block';
  if (arrow) arrow.style.transform = open ? '' : 'rotate(180deg)';
}

/** Update hint text when per-search params change. */
function updateSearchParamDisplay() {
  const costEl = document.getElementById('search-cost');
  const weightEl = document.getElementById('search-weight');
  const hint = document.getElementById('search-param-hint');
  const parts = [];
  if (costEl && costEl.value) parts.push(`coût max: ${costEl.value} DA`);
  if (weightEl && weightEl.value) parts.push(`poids: ${weightEl.value}`);
  if (hint) hint.textContent = parts.length ? `✓ Sera appliqué: ${parts.join(', ')}` : '';
}

/** Reset per-search overrides to global defaults. */
function resetSearchParams() {
  const costEl = document.getElementById('search-cost');
  const weightEl = document.getElementById('search-weight');
  if (costEl) costEl.value = '';
  if (weightEl) weightEl.value = '';
  updateSearchParamDisplay();
  notif('Paramètres réinitialisés', 'Valeurs globales utilisées', 'info');
}

/** Merge profile + per-search overrides into effective params. */
function getEffectiveParams() {
  const profile = document.getElementById('dash-profile')?.value || 'balanced';
  const global = ALGO_PROFILES[profile] || getGlobalWeights();
  const costEl = document.getElementById('search-cost');
  const weightEl = document.getElementById('search-weight');
  const overrideCost = costEl && costEl.value !== '' ? parseFloat(costEl.value) : null;
  const overrideW = weightEl && weightEl.value !== '' ? parseFloat(weightEl.value) : null;
  return {
    w1: global.w1,
    w2: overrideW !== null ? overrideW : global.w2,
    w3: global.w3,
    maxCost: overrideCost,
    profile,
  };
}

/** Map UI weights to POST /api/route body (time / cost / co₂). */
function getApiWeights() {
  const p = getEffectiveParams();
  return { time: p.w1, cost: p.w2, co2: p.w3 };
}

function samePlanningStop(a, b) {
  if (a.id && b.id && a.id === b.id) return true;
  if (!a.coords || !b.coords) return false;
  return Math.hypot(a.coords[0] - b.coords[0], a.coords[1] - b.coords[1]) < 1e-4;
}

/** Default transport toggles — extend the dashboard later with checkboxes if needed. */
function getTransportModesPayload() {
  return {
    bus: true,
    metro: true,
    tram: true,
    walk: true,
    telepherique: true,
    escalator: true,
  };
}

/**
 * Build JSON body for POST /api/route.
 * @param {Object} origin  { id?, coords:[lat,lon], ... }
 * @param {Object} dest
 */
function buildRouteRequestPayload(origin, dest) {
  const point = stop => {
    const [lat, lon] = stop.coords;
    const o = { lat, lon };
    if (stop.id) o.stopId = String(stop.id);
    return o;
  };
  return {
    start: point(origin),
    end: point(dest),
    weights: getApiWeights(),
    transportModes: getTransportModesPayload(),
  };
}

/** Status line below the search inputs. */
function setStatus() {
  const st = document.getElementById('map-status');
  const o = acSel.origin || document.getElementById('origin-input').value;
  const d = acSel.dest || document.getElementById('dest-input').value;
  if (!o && !d) st.textContent = '';
  else if (o && !d) st.textContent = 'Cliquez sur la carte ou entrez la destination';
  else if (!o && d) st.textContent = 'Cliquez sur la carte ou entrez le départ';
  else st.textContent = '✓ Prêt — cliquez sur Planifier';
}

/** Trigger route calculation via FastAPI. */
async function doRoute() {
  const origin = acSel.origin;
  const dest = acSel.dest;
  if (!origin || !dest) {
    renderSearchError('Aucun itinéraire trouvé', "Sélectionnez un départ et une arrivée pour planifier un trajet.");
    notif('Départ ou arrivée manquant', 'Sélectionnez les deux points', 'error');
    return;
  }
  if (samePlanningStop(origin, dest)) {
    renderSearchError('Aucun itinéraire trouvé', "Le départ et l'arrivée doivent être différents.");
    notif('Même arrêt', 'Les deux points doivent être différents', 'error');
    return;
  }

  const ld = document.getElementById('map-loading');
  const loadingText = document.getElementById('loading-text');
  ld.style.display = 'flex';
  if (loadingText) loadingText.textContent = 'Calcul du trajet sur le serveur…';

  const t0 = performance.now();
  try {
    const body = buildRouteRequestPayload(origin, dest);
    const data = await fetchRoutes(body);
    const elapsed = performance.now() - t0;
    const routes = data && Array.isArray(data.routes) ? data.routes : [];
    if (!routes.length) {
      renderSearchError('Aucun itinéraire trouvé', "Le serveur n'a renvoyé aucune variante.");
      notif('Résultat vide', 'Réessayez avec d’autres points', 'warning');
      return;
    }
    transitStoreSetPlanningContext(origin, dest);
    transitStoreSetRoutes(routes, elapsed);
    showResultsFromApi(origin, dest, routes, elapsed);
    notif(
      'Itinéraire trouvé',
      `${routes.length} variante(s) · ${elapsed.toFixed(0)} ms`,
      'success'
    );
  } catch (err) {
    console.error(err);
    renderSearchError('Erreur réseau', (err && err.message) || 'Impossible de joindre le serveur.');
    notif('Échec du calcul', 'Vérifiez que l’API tourne sur http://localhost:8000', 'error');
  } finally {
    ld.style.display = 'none';
  }
}

/**
 * Load a quick-route from the sidebar shortcuts.
 * @param {string} oId  Origin station id
 * @param {string} dId  Destination station id
 */
function quickRoute(oId, dId) {
  goTo('dashboard');
  setTimeout(() => {
    selectStation('origin', oId);
    selectStation('dest', dId);
    setTimeout(doRoute, 400);
  }, 300);
}
