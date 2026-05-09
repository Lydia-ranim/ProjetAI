const ALGO_PROFILES = {
  fastest:  {w1:.80, w2:.10, w3:.10},
  cheapest: {w1:.10, w2:.80, w3:.10},
  greenest: {w1:.10, w2:.10, w3:.80},
  balanced: {w1:.33, w2:.33, w3:.34},
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
  const open  = panel.style.display !== 'none';
  panel.style.display = open ? 'none' : 'block';
  if (arrow) arrow.style.transform = open ? '' : 'rotate(180deg)';
}

function updateSearchParamDisplay() {
  const costEl   = document.getElementById('search-cost');
  const weightEl = document.getElementById('search-weight');
  const hint     = document.getElementById('search-param-hint');
  const parts    = [];
  if (costEl   && costEl.value)   parts.push(`${t('map.cost-lbl')}: ${costEl.value}`);
  if (weightEl && weightEl.value) parts.push(`${t('map.weight-lbl').split(' ')[0]}: ${weightEl.value}`);
  if (hint) hint.textContent = parts.length ? `✓ ${parts.join(', ')}` : '';
}

function resetSearchParams() {
  const costEl   = document.getElementById('search-cost');
  const weightEl = document.getElementById('search-weight');
  if (costEl)   costEl.value   = '';
  if (weightEl) weightEl.value = '';
  updateSearchParamDisplay();
  notif(t('notif.settings-reset-title'), t('notif.settings-reset-msg'), 'info');
}

function getEffectiveParams() {
  const profile      = document.getElementById('dash-profile')?.value || 'balanced';
  const global       = ALGO_PROFILES[profile] || getGlobalWeights();
  const costEl       = document.getElementById('search-cost');
  const weightEl     = document.getElementById('search-weight');
  const overrideCost = costEl   && costEl.value   !== '' ? parseFloat(costEl.value)   : null;
  const overrideW    = weightEl && weightEl.value !== '' ? parseFloat(weightEl.value) : null;
  return {
    w1: global.w1,
    w2: overrideW !== null ? overrideW : global.w2,
    w3: global.w3,
    maxCost: overrideCost,
    profile,
  };
}

function setStatus() {
  const st = document.getElementById('map-status');
  if (!st) return;
  const o = acSel.origin || document.getElementById('origin-input').value;
  const d = acSel.dest   || document.getElementById('dest-input').value;
  if      (!o && !d) st.textContent = t('map.status');
  else if ( o && !d) st.textContent = t('map.dest-ph');
  else if (!o &&  d) st.textContent = t('map.origin-ph');
  else               st.textContent = '✓ ' + t('map.plan-btn');
}

function doRoute() {
  const origin = acSel.origin;
  const dest   = acSel.dest;
  if (!origin || !dest) {
    renderSearchError(t('res.no-route'), t('res.no-route-hint'));
    notif(t('notif.missing-pts-title'), t('notif.missing-pts-msg'), 'error');
    return;
  }
  if (origin.id === dest.id) {
    renderSearchError(t('res.no-route'), t('res.no-route-same'));
    notif(t('notif.same-pt-title'), t('notif.same-pt-msg'), 'error');
    return;
  }
  const params = getEffectiveParams();
  const ld     = document.getElementById('map-loading');
  const algo   = document.querySelector('input[name="algo"]:checked')?.value || 'astar';
  ld.style.display = 'flex';
  document.getElementById('loading-text').textContent = t('map.loading');
  const t1 = Date.now();
  setTimeout(() => {
    ld.style.display = 'none';
    showResults(origin, dest, algo, Date.now() - t1, params);
  }, 1200 + Math.random() * 600);
}

function quickRoute(oId, dId) {
  goTo('dashboard');
  setTimeout(() => {
    selectStation('origin', oId);
    selectStation('dest',   dId);
    setTimeout(doRoute, 400);
  }, 300);
}

function findPath(oId, dId) {
  const metro_idx = {};
  METRO_L1.forEach((id, i) => { metro_idx[id] = i; });
  const oi = metro_idx[oId], di = metro_idx[dId];
  if (oi !== undefined && di !== undefined) {
    const slice = oi < di ? METRO_L1.slice(oi, di+1) : METRO_L1.slice(di, oi+1).reverse();
    return slice.map(id => ({station:SMAP[id], mode:'metro', line:'Métro L1'}));
  }
  const path = [];
  path.push({station: SMAP[oId], mode:'origin', line:'Départ'});
  if (oId !== 'M_MARTYRS') {
    const near = nearestOfType(SMAP[oId]?.coords || [36.737,3.086], 'metro');
    if (near) {
      path.push({station:near, mode:'walk',  line:'Marche'});
      path.push({station:near, mode:'metro', line:'Métro L1'});
    }
  }
  path.push({station:SMAP[dId], mode:'dest', line:'Arrivée'});
  return path;
}

function nearestOfType(coords, type) {
  let best = null, bestD = Infinity;
  STATIONS.filter(s => s.type === type).forEach(s => {
    const d = Math.hypot(s.coords[0]-coords[0], s.coords[1]-coords[1]);
    if (d < bestD) { bestD = d; best = s; }
  });
  return best;
}

function buildItinSteps(origin, dest, dist) {
  const steps    = [];
  const needTrain = (origin.type === 'train' || dest.type === 'train' || dist > 15);

  steps.push({icon:'🚶', from:t('res.walk-to'), to:origin.short, mode:'Marche', line:'—', time:4, cost:0, co2:0, col:'var(--text-s)'});

  if (origin.type === 'metro' || origin.type === 'tram') {
    steps.push({icon:origin.icon, from:origin.short, to:dest.type==='metro'?dest.short:'Grande Poste',
      mode:origin.line, line:origin.line, time:Math.round(8+dist*1.5), cost:50, co2:Math.round(dist*5), col:'var(--mint)'});
  } else if (origin.type === 'train') {
    steps.push({icon:'🚆', from:origin.short, to:dest.short,
      mode:'Train banlieue', line:'Ligne banlieue', time:Math.round(10+dist*1.2), cost:35, co2:Math.round(dist*14), col:'var(--pink)'});
  } else {
    const nm = nearestOfType(origin.coords, 'metro');
    if (nm) {
      steps.push({icon:'🚶', from:origin.short, to:nm.short, mode:'Marche',  line:'—', time:6, cost:0, co2:0, col:'var(--text-s)'});
      steps.push({icon:'🚇', from:nm.short, to:dest.type==='metro'?dest.short:'Correspondance',
        mode:'Métro L1', line:'Métro L1', time:Math.round(6+dist*1.8), cost:50, co2:Math.round(dist*5), col:'var(--mint)'});
    }
  }

  if (needTrain && origin.type !== 'train') {
    steps.push({icon:'🔄', from:'Correspondance', to:'Gare', mode:'Transfert', line:'Métro→Train', time:15, cost:25, co2:0, col:'var(--text-t)'});
    steps.push({icon:'🚆', from:'Gare', to:dest.short, mode:'Train banlieue', line:'Ligne banlieue', time:Math.round(8+dist*.8), cost:35, co2:Math.round(dist*14), col:'var(--pink)'});
  }

  steps.push({icon:'🚶', from:dest.short, to:t('res.walk-to-dest'), mode:'Marche', line:'—', time:3, cost:0, co2:0, col:'var(--text-s)'});
  return steps;
}
