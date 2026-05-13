/* ═══════════════════════════════════════════════════════════
   LYHLYH — Results: API route display, charts, stats
   Depends on: routing.js (getEffectiveParams), map.js (drawRouteSegments),
               notifications.js (notif), stations.js (normalizeModeKey, MODE_ICON)
═══════════════════════════════════════════════════════════ */

/** Localized Pareto label (fastest / cheapest / greenest). */
function labelLocalized(label) {
  const key = { fastest: 'res.label-fastest', cheapest: 'res.label-cheapest', greenest: 'res.label-greenest' }[label];
  return key ? t(key) : label || '—';
}

function modeChipColorByKey(k) {
  const map = {
    metro: 'var(--mint)',
    bus: '#FF9800',
    tram: 'var(--purple)',
    walk: 'var(--text-s)',
    train: 'var(--pink)',
    telepherique: '#9C27B0',
    cable: '#9C27B0',
    escalator: 'var(--text-t)',
  };
  return map[k] || 'var(--text-s)';
}

function formatSegmentModeTitle(seg) {
  const k = normalizeModeKey(seg.mode);
  const labels = {
    walk: 'Marche',
    metro: 'Métro',
    bus: 'Bus',
    tram: 'Tram',
    train: 'Train',
    telepherique: 'Téléphérique',
    escalator: 'Escalier',
  };
  return labels[k] || (seg.mode ? String(seg.mode) : '—');
}

/**
 * Build step rows for charts / sidebar from API segments.
 * @param {Array<Object>} segments
 * @param {number} [totalCo2G]
 */
function segmentsToDisplaySteps(segments, totalCo2G) {
  const segs = segments || [];
  const rides = segs.filter(s => normalizeModeKey(s.mode) !== 'walk');
  const shareCo2 = rides.length && totalCo2G ? totalCo2G / rides.length : 0;

  return segs.map(seg => {
    const rawMode = normalizeModeKey(seg.mode);
    const isWalk = rawMode === 'walk';
    return {
      icon: MODE_ICON[rawMode] || MODE_ICON.default,
      from: seg.fromName || seg.fromStopId || '—',
      to: seg.toName || seg.toStopId || '—',
      mode: formatSegmentModeTitle(seg),
      line: seg.lineId || '—',
      time: Math.round(seg.durationMin != null ? seg.durationMin : 0),
      cost: Math.round(seg.costDzd != null ? seg.costDzd : 0),
      co2: isWalk ? 0 : Math.round(shareCo2),
      col: modeChipColorByKey(rawMode),
      rawMode,
    };
  });
}

function estimateTransfersFromSegments(segments) {
  const segs = segments || [];
  let n = 0;
  for (let i = 1; i < segs.length; i++) {
    const a = normalizeModeKey(segs[i - 1].mode);
    const b = normalizeModeKey(segs[i].mode);
    if (a !== 'walk' && b !== 'walk' && a !== b) n++;
  }
  return n;
}

function fillParetoAlgoCards(routes) {
  const order = ['fastest', 'cheapest', 'greenest'];
  const titles = [t('res.card-fast'), t('res.card-cheap'), t('res.card-green')];
  const colors = ['var(--mint)', 'var(--purple)', 'var(--pink)'];
  const cards = document.querySelectorAll('#results-panel .algo-card');
  order.forEach((lbl, i) => {
    const r = routes.find(x => x.label === lbl);
    const card = cards[i];
    if (card && card.firstElementChild) {
      card.firstElementChild.textContent = titles[i];
      card.firstElementChild.style.color = colors[i];
    }
    const nodes = r?.summary?.nodesExplored;
    const algo = r?.algorithmUsed ?? '—';
    const ids = [
      ['p-dij', 'p-dij-ms'],
      ['p-ast', 'p-ast-ms'],
      ['p-bid', 'p-bid-ms'],
    ][i];
    const ne = document.getElementById(ids[0]);
    const sub = document.getElementById(ids[1]);
    if (ne) ne.textContent = nodes != null ? String(nodes) : '—';
    if (sub) sub.textContent = r ? `${algo}` : '—';
  });
}

function renderRouteVariantTabs(routes) {
  const wrap = document.getElementById('route-variant-tabs');
  if (!wrap) return;
  if (!routes || routes.length <= 1) {
    wrap.style.display = 'none';
    wrap.innerHTML = '';
    return;
  }
  wrap.style.display = 'flex';
  const idx = transitStoreSelectedIndex();
  wrap.innerHTML = routes
    .map((r, i) => {
      const tw =
        r.summary && r.summary.totalTimeMin != null ? Math.round(r.summary.totalTimeMin) : '—';
      const active = i === idx ? 'chip-m' : '';
      const bg = i === idx ? 'var(--bg-3)' : 'var(--bg-2)';
      return `
    <button type="button" class="chip ${active}" style="cursor:pointer;border:1px solid var(--border);background:${bg};font-size:.72rem"
      onclick="selectRouteVariant(${i})">
      ${labelLocalized(r.label)} · ${tw} ${t('time.min')}
    </button>`;
    })
    .join('');
}

/**
 * Main results renderer — called after POST /api/route succeeds.
 */
function showResultsFromApi(origin, dest, routes, elapsedMs) {
  renderRouteVariantTabs(routes);
  fillParetoAlgoCards(routes);
  refreshRouteResultsView(origin, dest, elapsedMs);

  const panel = document.getElementById('results-panel');
  if (panel) panel.style.maxHeight = '900px';
}

function selectRouteVariant(i) {
  transitStoreSelectRoute(i);
  const { origin, dest } = transitStoreGetPlanningContext();
  renderRouteVariantTabs(transitStoreGetRoutes());
  refreshRouteResultsView(origin, dest, transitStoreLastElapsedMs());
}

function refreshRouteResultsView(origin, dest, elapsedMs) {
  const routes = transitStoreGetRoutes();
  const sel = routes[transitStoreSelectedIndex()];
  const params = getEffectiveParams();

  if (!sel || sel.found === false) {
    renderSearchError(t('res.no-route'), t('res.no-path-server'));
    return;
  }

  const sum = sel.summary || {};
  const steps = segmentsToDisplaySteps(sel.segments, sum.totalCo2G);
  const tf = estimateTransfersFromSegments(sel.segments);
  const dist = sum.totalDistanceKm != null ? Number(sum.totalDistanceKm) : 0;
  const totalMin = Math.round(sum.totalTimeMin || 0);
  const c = Math.round(sum.totalCostDzd || 0);
  const co2 = Math.round(sum.totalCo2G || 0);
  const ms = elapsedMs != null ? elapsedMs : transitStoreLastElapsedMs();

  document.getElementById('res-title').textContent = `${origin.short} → ${dest.short}`;
  const algoBits = routes.map(r => `${labelLocalized(r.label)}: ${r.algorithmUsed || '—'}`).join(' · ');
  document.getElementById('res-algo-used').textContent = algoBits;

  document.getElementById('res-chips').innerHTML = `
    <div class="chip chip-m">${totalMin} ${t('time.min')}</div>
    <div class="chip chip-p">${c} DA</div>
    <div class="chip chip-k">${co2}g CO₂</div>
    <div class="chip chip-c">${labelLocalized(sel.label)}</div>`;

  document.getElementById('itin-steps').innerHTML = steps
    .map(
      (s, i) => `
    <div class="itin-step">
      <div class="step-icon-col">
        <div class="step-icon">${s.icon}</div>
        ${i < steps.length - 1 ? '<div class="step-connector"></div>' : ''}
      </div>
      <div style="flex:1;min-width:0;padding-top:4px">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:6px">
          <div>
            <div style="font-weight:600;font-size:.88rem">${s.from} → ${s.to}</div>
            <div style="font-size:.75rem;margin-top:2px;color:${s.col}">${s.mode} · ${s.line}</div>
          </div>
          <div style="text-align:right;flex-shrink:0">
            <div style="font-size:.84rem;font-weight:500">${s.time} ${t('time.min')}</div>
            <div style="font-size:.73rem;color:var(--text-t);margin-top:2px">
              ${s.cost > 0 ? `${s.cost} DA` : t('res.free')}${s.co2 > 0 ? ` · ${s.co2}g` : ''}
            </div>
          </div>
        </div>
      </div>
    </div>`
    )
    .join('');

  renderRouteChart(steps, { t: totalMin, c, co2, tf, dist });
  renderPathStats(steps, {
    origin,
    dest,
    dist,
    t: totalMin,
    c,
    co2,
    tf,
    algo: sel.algorithmUsed || '',
    ms,
    params,
    nodesExplored: sum.nodesExplored,
  });
  drawRouteSegments(origin, dest, sel.segments || []);
  renderSearchResult(origin, dest, c, tf, steps);
}

/* ───────────────────────────────────────────────────────────
   In-sidebar compact route summary
─────────────────────────────────────────────────────────── */

function searchResultLegendColor(modeStr) {
  if (!modeStr) return 'var(--text-s)';
  if (modeStr.includes('Métro')) return '#2196F3';
  if (modeStr.includes('Tram')) return '#4CAF50';
  if (modeStr.includes('Train')) return '#F2C4CE';
  if (modeStr.includes('Téléph') || modeStr.includes('éléph')) return '#9C27B0';
  if (modeStr.includes('Bus')) return '#FF9800';
  return 'var(--text-s)';
}

function renderSearchResult(origin, dest, totalCost, transferCount, steps) {
  const panel = document.getElementById('search-result');
  if (!panel) return;
  panel.hidden = true;
  panel.innerHTML = '';
  const hiddenStatus = document.getElementById('map-status');
  if (hiddenStatus) hiddenStatus.style.display = 'none';
  return;

  const isRide = s =>
    normalizeModeKey(s.rawMode || s.mode) !== 'walk' &&
    s.mode !== 'Marche' &&
    s.mode !== 'Transfert';
  const rideTime = steps.filter(isRide).reduce((a, b) => a + b.time, 0);
  const waitTime = steps.filter(s => s.mode === 'Transfert').reduce((a, b) => a + b.time, 0);
  const walkTime = steps.filter(s => normalizeModeKey(s.rawMode) === 'walk' || s.mode === 'Marche').reduce(
    (a, b) => a + b.time,
    0
  );
  const totalTime = rideTime + waitTime + walkTime;

  const seen = {};
  const used = [];
  steps.filter(isRide).forEach(s => {
    if (seen[s.mode]) {
      seen[s.mode].time += s.time;
    } else {
      seen[s.mode] = { mode: s.mode, time: s.time, color: searchResultLegendColor(s.mode) };
      used.push(seen[s.mode]);
    }
  });

  const oLabel = origin.name || origin.short || '—';
  const dLabel = dest.name || dest.short || '—';
  const transfersText =
    transferCount === 0
      ? t('res.no-transfer')
      : `${transferCount} ${t('res.transfer-s')}`;

  const chartSegments = [
    { label: t('res.ride-time'), value: rideTime, color: '#BEEEDB' },
    { label: t('res.wait-time'), value: waitTime, color: '#F2C4CE' },
    { label: t('res.walk'), value: walkTime, color: '#8AAAC8' },
  ].filter(s => s.value > 0);
  const cx = 50;
  const cy = 50;
  const r = 36;
  const circ = 2 * Math.PI * r;
  let off = circ / 4;
  const donutPaths = chartSegments.map((seg, i) => {
    const pct = seg.value / Math.max(totalTime, 1);
    const dash = pct * circ;
    const dashOffset = circ - off;
    off += dash;
    return `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none"
              stroke="${seg.color}" stroke-width="12"
              stroke-dasharray="${dash} ${circ - dash}"
              stroke-dashoffset="${dashOffset}" stroke-linecap="butt"
              style="animation:donutFadeIn .55s ease ${i * 0.12}s both"/>`;
  }).join('');
  const chartHtml =
    totalTime > 0
      ? `
    <div class="sr-chart">
      <div class="sr-donut-wrap">
        <svg class="sr-donut" viewBox="0 0 100 100">
          <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--bg-3)" stroke-width="12"/>
          <g style="transform:rotate(-90deg);transform-origin:50% 50%">${donutPaths}</g>
        </svg>
        <div class="sr-donut-center">
          <span class="sr-donut-total">${totalTime}</span>
          <span class="sr-donut-unit">${t('time.min')}</span>
        </div>
      </div>
      <div class="sr-chart-legend">
        ${chartSegments
          .map(seg => {
            const pct = Math.round((seg.value / Math.max(totalTime, 1)) * 100);
            return `
            <div class="sr-chart-row">
              <span class="sr-chart-key">
                <span class="sr-dot" style="background:${seg.color};color:${seg.color}"></span>
                ${seg.label}
              </span>
              <span class="sr-chart-val">${seg.value} <span class="sr-chart-pct">(${pct}%)</span></span>
            </div>`;
          })
          .join('')}
      </div>
    </div>`
      : '';

  panel.innerHTML = `
    <div class="sidebar-label" style="padding:0;margin-bottom:4px">${t('res.summary-title')}</div>
    <div class="sr-route">${oLabel}<span class="sr-arrow">→</span>${dLabel}</div>

    <div class="sr-stats">
      <div class="sr-stat" title="${t('res.price-total')}">
        <span class="sr-stat-icon">💰</span>
        <div class="sr-stat-val">${totalCost} DA</div>
        <div class="sr-stat-lbl">${t('res.price-total')}</div>
      </div>
      <div class="sr-stat" title="${t('res.ride-time')}">
        <span class="sr-stat-icon">⏱</span>
        <div class="sr-stat-val">${rideTime} ${t('time.min')}</div>
        <div class="sr-stat-lbl">${t('res.ride-time')}</div>
      </div>
      <div class="sr-stat" title="${t('res.wait-time')}">
        <span class="sr-stat-icon">⏳</span>
        <div class="sr-stat-val">${waitTime} ${t('time.min')}</div>
        <div class="sr-stat-lbl">${t('res.wait-time')}</div>
      </div>
    </div>

    ${chartHtml}

    ${
      used.length
        ? `
    <div class="sr-modes">
      ${used
        .map(
          u => `
        <div class="sr-mode-row">
          <span class="sr-dot" style="background:${u.color};color:${u.color}"></span>
          <span class="sr-mode-name">${u.mode}</span>
          <span class="sr-mode-time">${u.time} ${t('time.min')}</span>
        </div>`
        )
        .join('')}
    </div>`
        : ''
    }

    <div class="sr-transfers">${transfersText}</div>
  `;
  panel.hidden = false;

  const status = document.getElementById('map-status');
  if (status) status.style.display = 'none';
}

function renderSearchError(title, hint) {
  const panel = document.getElementById('search-result');
  if (!panel) return;
  panel.innerHTML = `
    <div class="sr-error">
      ${title || t('res.no-route')}
      ${hint ? `<div class="sr-error-hint">${hint}</div>` : ''}
    </div>
  `;
  panel.hidden = false;
  const status = document.getElementById('map-status');
  if (status) status.style.display = 'none';
}

/* ── Donut + bar chart ── */
function renderRouteChart(steps, meta) {
  const section = document.getElementById('route-chart-section');
  if (!section) return;
  section.style.display = 'block';
  section.classList.remove('route-chart-section');
  void section.offsetWidth;
  section.classList.add('route-chart-section');

  const walkTime = steps
    .filter(s => normalizeModeKey(s.rawMode) === 'walk' || s.mode === 'Marche')
    .reduce((a, b) => a + b.time, 0);
  const waitTime = steps.filter(s => s.mode === 'Transfert').reduce((a, b) => a + b.time, 0);
  const rideTime = steps
    .filter(
      s =>
        normalizeModeKey(s.rawMode) !== 'walk' &&
        s.mode !== 'Marche' &&
        s.mode !== 'Transfert'
    )
    .reduce((a, b) => a + b.time, 0);
  const totalTime = walkTime + waitTime + rideTime;

  const segments = [
    { label: t('res.ride-time'), value: rideTime, color: '#BEEEDB', colorDark: '#3DAB82' },
    { label: t('res.wait-time'), value: waitTime, color: '#F2C4CE', colorDark: '#cc3355' },
    { label: t('res.walk'), value: walkTime, color: '#8AAAC8', colorDark: '#4A7090' },
  ].filter(s => s.value > 0);

  const cx = 75;
  const cy = 75;
  const r = 52;
  const circ = 2 * Math.PI * r;
  let offset = circ / 4;
  const svgSegments = segments
    .map((seg, i) => {
      const pct = seg.value / Math.max(totalTime, 1);
      const dash = pct * circ;
      const gap = circ - dash;
      const dashOffset = circ - offset;
      offset += dash;
      return `<circle class="chart-segment" cx="${cx}" cy="${cy}" r="${r}"
      fill="none" stroke="${seg.color}" stroke-width="18"
      stroke-dasharray="${dash} ${gap}" stroke-dashoffset="${dashOffset}" stroke-linecap="butt"
      style="transition:stroke-width .2s ease,opacity .3s ease;animation:donutFadeIn .6s ease ${i * 0.15}s both;opacity:0"
      title="${seg.label}: ${seg.value} ${t('time.min')}"/>`;
    })
    .join('');
  document.getElementById('donut-segments').innerHTML = svgSegments;
  document.getElementById('donut-total').textContent = totalTime;
  setTimeout(() => document.querySelectorAll('#donut-segments circle').forEach(c => (c.style.opacity = '1')), 50);

  document.getElementById('chart-legend-bars').innerHTML = segments
    .map((seg, i) => {
      const pct = Math.round((seg.value / Math.max(totalTime, 1)) * 100);
      return `<div style="animation:chartFadeIn .5s ease ${i * 0.12 + 0.2}s both;opacity:0" id="bar-item-${i}">
      <div style="display:flex;justify-content:space-between;font-size:.8rem;margin-bottom:5px;align-items:center">
        <div style="display:flex;align-items:center;gap:8px">
          <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${seg.color};flex-shrink:0;box-shadow:0 0 6px ${seg.color}44"></span>
          <span style="font-weight:500">${seg.label}</span>
        </div>
        <span style="font-family:'DM Mono',monospace;color:${seg.colorDark};font-weight:600">${seg.value} ${t('time.min')} <span style="color:var(--text-t);font-size:.72rem">(${pct}%)</span></span>
      </div>
      <div style="background:var(--bg-4);border-radius:99px;overflow:hidden;height:6px">
        <div class="bar-fill" style="width:${pct}%;background:linear-gradient(90deg,${seg.color},${seg.colorDark});animation-delay:${i * 0.12 + 0.3}s"></div>
      </div>
    </div>`;
    })
    .join('');
  setTimeout(() => document.querySelectorAll('[id^="bar-item-"]').forEach(el => (el.style.opacity = '1')), 50);

  const costSection = document.getElementById('cost-bars-section');
  const costBreakdown = steps.filter(s => s.cost > 0 && normalizeModeKey(s.rawMode) !== 'walk');
  const totalCostBreak = costBreakdown.reduce((a, b) => a + b.cost, 0);
  if (costSection && costBreakdown.length) {
    costSection.innerHTML = `
      <div style="font-size:.78rem;font-weight:700;color:var(--text-s);margin-bottom:10px;letter-spacing:.04em">${t('res.cost-dist')}</div>
      <div style="display:flex;flex-direction:column;gap:8px">
        ${costBreakdown
          .map((s, i) => {
            const pct = Math.round((s.cost / Math.max(totalCostBreak, 1)) * 100);
            const col =
              s.mode.includes('Train') ? 'var(--pink)' : s.mode.includes('Tram') ? 'var(--purple)' : 'var(--mint)';
            return `<div style="display:flex;align-items:center;gap:10px;font-size:.78rem">
            <div style="width:90px;color:var(--text-s);flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${s.mode}</div>
            <div style="flex:1;background:var(--bg-4);border-radius:99px;overflow:hidden;height:5px">
              <div style="height:100%;width:${pct}%;background:${col};border-radius:99px;animation:barGrow .6s cubic-bezier(.34,1.2,.64,1) ${i * 0.1 + 0.4}s both;transform-origin:left"></div>
            </div>
            <div style="font-family:'DM Mono',monospace;color:${col};font-weight:600;width:44px;text-align:right">${s.cost} DA</div>
          </div>`;
          })
          .join('')}
        <div style="display:flex;justify-content:flex-end;padding-top:6px;border-top:1px solid var(--border);margin-top:2px">
          <span style="font-family:'DM Mono',monospace;font-size:.82rem;font-weight:700;color:var(--purple)">${t('res.total')}: ${totalCostBreak} DA</span>
        </div>
      </div>`;
  } else if (costSection) {
    costSection.innerHTML = '';
  }
}

/* ── Path statistics table ── */
function renderPathStats(steps, meta) {
  const statsPanel = document.getElementById('path-stats');
  if (!statsPanel) return;

  const totalCost = steps.reduce((s, x) => s + x.cost, 0);
  const waitTime = steps.filter(x => x.mode === 'Transfert').reduce((s, x) => s + x.time, 0);
  const walkTime = steps
    .filter(x => normalizeModeKey(x.rawMode) === 'walk' || x.mode === 'Marche')
    .reduce((s, x) => s + x.time, 0);
  const rideTime = steps
    .filter(
      x =>
        normalizeModeKey(x.rawMode) !== 'walk' &&
        x.mode !== 'Marche' &&
        x.mode !== 'Transfert'
    )
    .reduce((s, x) => s + x.time, 0);
  const modeSet = [
    ...new Set(
      steps
        .filter(
          x =>
            normalizeModeKey(x.rawMode) !== 'walk' &&
            x.mode !== 'Marche' &&
            x.mode !== 'Transfert'
        )
        .map(x => x.mode)
    ),
  ];
  const distKm =
    meta.dist != null ? Number(meta.dist).toFixed(2) : meta.distKmApprox || '—';

  document.getElementById('path-summary-grid').innerHTML = [
    { label: t('res.price-total'), val: `${totalCost} DA`, col: 'var(--purple)' },
    { label: t('res.ride-time'), val: `${rideTime} ${t('time.min')}`, col: 'var(--mint)' },
    { label: t('res.wait-time'), val: `${waitTime} ${t('time.min')}`, col: 'var(--pink)' },
    { label: t('res.walk'), val: `${walkTime} ${t('time.min')}`, col: 'var(--text-s)' },
    { label: t('res.modes'), val: `${modeSet.length || 1}`, col: 'var(--mint)' },
    { label: t('res.dist'), val: `${distKm} km`, col: 'var(--text-s)' },
  ]
    .map(
      d => `
    <div class="res-stat-card">
      <div class="res-stat-val" style="color:${d.col}">${d.val}</div>
      <div class="res-stat-lbl">${d.label}</div>
    </div>`
    )
    .join('');

  const transitRows = steps;
  document.getElementById('path-segment-rows').innerHTML = transitRows
    .map(
      (s, i) => `
    <div style="display:grid;grid-template-columns:1.5fr 1fr 1fr 1fr 1fr;gap:6px;padding:9px 14px;border-bottom:${i < transitRows.length - 1 ? '1px solid var(--border)' : 'none'};font-size:.78rem;align-items:center;transition:background var(--tr)"
         onmouseenter="this.style.background='var(--bg-3)'" onmouseleave="this.style.background='transparent'">
      <span style="font-weight:500">${s.from} → ${s.to}</span>
      <span style="text-align:center"><span class="chip" style="font-size:.65rem;background:${modeChipColorByKey(normalizeModeKey(s.rawMode || s.mode))}22;color:${modeChipColorByKey(normalizeModeKey(s.rawMode || s.mode))}">${s.icon} ${s.mode}</span></span>
      <span style="text-align:right;font-family:'DM Mono',monospace">${s.mode === 'Transfert' ? '—' : `${s.time} ${t('time.min')}`}</span>
      <span style="text-align:right;font-family:'DM Mono',monospace;color:var(--text-t)">${s.mode === 'Transfert' ? `${s.time} ${t('time.min')}` : '—'}</span>
      <span style="text-align:right;font-family:'DM Mono',monospace;color:var(--purple)">${s.cost > 0 ? `${s.cost} DA` : '—'}</span>
    </div>`
    )
    .join('');

  const algoLabel = meta.algo || '—';
  const efficiency = Math.round(100 - (meta.tf / Math.max(steps.length, 1)) * 30);
  const paramNote = meta.params.maxCost ? `${t('map.cost-lbl')} ${meta.params.maxCost} DA · ` : '';
  document.getElementById('path-global-stats').innerHTML = `
    <span>📦 <b>${steps.length}</b> ${t('res.segments-tot')}</span>
    <span>🛣️ <b>${distKm}</b> km</span>
    <span>🔄 <b>${meta.tf}</b> ${t('res.transfer-s')}</span>
    <span>⚡ <b>${algoLabel}</b> · <b>${meta.ms.toFixed(0)} ms</b></span>
    ${meta.nodesExplored != null ? `<span>🔍 <b>${meta.nodesExplored}</b> ${t('res.nodes')}</span>` : ''}
    <span>🎯 ${t('res.efficiency')}: <b>${efficiency}%</b></span>
    <span style="color:var(--text-t);font-size:.72rem">${paramNote}${t('res.profile')}: ${meta.params.profile}</span>`;

  statsPanel.style.display = 'block';
}

document.addEventListener('lang-changed', () => {
  if (typeof transitStoreGetRoutes === 'function' && transitStoreGetRoutes().length) {
    const { origin, dest } = transitStoreGetPlanningContext();
    if (origin && dest) {
      renderRouteVariantTabs(transitStoreGetRoutes());
      refreshRouteResultsView(origin, dest, transitStoreLastElapsedMs());
    }
  }
});
