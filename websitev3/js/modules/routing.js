/* ═══════════════════════════════════════════════════════════
   LYHLYH — Routing: doRoute, weights, transport modes
   Depends on: stations.js, notifications.js, map.js,
               autocomplete.js (acSel), results.js (showResultsFromApi),
               api.js, transit-store.js
═══════════════════════════════════════════════════════════ */

/* Preset profile weight vectors → normalized as time / cost / co₂ 
   LYHLYH — Routing: FastAPI client + weights (i18n)
   Depends on: stations.js, notifications.js, map.js, autocomplete.js,
               results.js (showResultsFromApi), api.js, transit-store.js, i18n.js
═══════════════════════════════════════════════════════════ */

const ALGO_PROFILES = {
  fastest: { w1: 0.8, w2: 0.1, w3: 0.1 },
  cheapest: { w1: 0.1, w2: 0.8, w3: 0.1 },
  greenest: { w1: 0.1, w2: 0.1, w3: 0.8 },
  balanced: { w1: 0.33, w2: 0.33, w3: 0.34 },
};

function getGlobalWeights() {
  return {
    w1: parseFloat(document.getElementById('sw1')?.textContent) || 0.33,
    w2: parseFloat(document.getElementById('sw2')?.textContent) || 0.33,
    w3: parseFloat(document.getElementById('sw3')?.textContent) || 0.34,
  };
}

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

function toggleSearchParams() {
  const panel = document.getElementById('search-params-panel');
  const arrow = document.getElementById('toggle-params-arrow');
  const open = panel.style.display !== 'none';
  panel.style.display = open ? 'none' : 'block';
  if (arrow) arrow.style.transform = open ? '' : 'rotate(180deg)';
}

function updateSearchParamDisplay() {
  const costEl = document.getElementById('search-cost');
  const weightEl = document.getElementById('search-weight');
  const hint = document.getElementById('search-param-hint');
  const parts = [];
  if (costEl && costEl.value) parts.push(`${t('map.cost-lbl')}: ${costEl.value}`);
  if (weightEl && weightEl.value) parts.push(`${t('map.weight-lbl').split(' ')[0]}: ${weightEl.value}`);
  if (hint) hint.textContent = parts.length ? `✓ ${parts.join(', ')}` : '';
}

function resetSearchParams() {
  const costEl = document.getElementById('search-cost');
  const weightEl = document.getElementById('search-weight');
  if (costEl) costEl.value = '';
  if (weightEl) weightEl.value = '';
  updateSearchParamDisplay();
  notif(t('notif.settings-reset-title'), t('notif.settings-reset-msg'), 'info');
}

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

function getApiWeights() {
  const p = getEffectiveParams();
  return { time: p.w1, cost: p.w2, co2: p.w3 };
}

function samePlanningStop(a, b) {
  if (a.id && b.id && a.id === b.id) return true;
  if (!a.coords || !b.coords) return false;
  return Math.hypot(a.coords[0] - b.coords[0], a.coords[1] - b.coords[1]) < 1e-4;
}

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

function setStatus() {
  const st = document.getElementById('map-status');
  if (!st) return;
  const o = acSel.origin || document.getElementById('origin-input').value;
  const d = acSel.dest || document.getElementById('dest-input').value;
  if (!o && !d) st.textContent = t('map.status');
  else if (o && !d) st.textContent = t('map.dest-ph');
  else if (!o && d) st.textContent = t('map.origin-ph');
  else st.textContent = '✓ ' + t('map.plan-btn');
}

async function doRoute() {
  const origin = acSel.origin;
  const dest = acSel.dest;
  if (!origin || !dest) {
    renderSearchError(t('res.no-route'), t('res.no-route-hint'));
    notif(t('notif.missing-pts-title'), t('notif.missing-pts-msg'), 'error');
    return;
  }
  if (samePlanningStop(origin, dest)) {
    renderSearchError(t('res.no-route'), t('res.no-route-same'));
    notif(t('notif.same-pt-title'), t('notif.same-pt-msg'), 'error');
    return;
  }

  const ld = document.getElementById('map-loading');
  const loadingText = document.getElementById('loading-text');
  ld.style.display = 'flex';
  if (loadingText) loadingText.textContent = t('map.loading-api');

  const t0 = performance.now();
  try {
    const body = buildRouteRequestPayload(origin, dest);
    const data = await fetchRoutes(body);
    const elapsed = performance.now() - t0;
    const routes = data && Array.isArray(data.routes) ? data.routes : [];
    if (!routes.length) {
      renderSearchError(t('res.no-route'), t('res.no-route-empty'));
      notif(t('notif.empty-result-title'), t('notif.empty-result-msg'), 'warning');
      return;
    }
    transitStoreSetPlanningContext(origin, dest);
    transitStoreSetRoutes(routes, elapsed);
    showResultsFromApi(origin, dest, routes, elapsed);
    notif(t('notif.route-found-title'), t('notif.route-variants').replace('{n}', String(routes.length)) + ` · ${elapsed.toFixed(0)} ms`, 'success');
  } catch (err) {
    console.error(err);
    renderSearchError(t('notif.network-error-title'), (err && err.message) || t('notif.network-error-msg'));
    notif(t('notif.network-error-title'), t('notif.network-error-msg'), 'error');
  } finally {
    ld.style.display = 'none';
  }
}

function quickRoute(oId, dId) {
  goTo('dashboard');
  setTimeout(() => {
    selectStation('origin', oId);
    selectStation('dest', dId);
    setTimeout(doRoute, 400);
  }, 300);
}
