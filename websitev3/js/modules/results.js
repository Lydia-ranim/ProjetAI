

let lastResultsArgs = null;


function showResults(origin, dest, algo, elapsed, params) {
  lastResultsArgs = {origin, dest, algo, elapsed, params};
  params = params || getEffectiveParams();
  const dist = Math.hypot(origin.coords[0]-dest.coords[0], origin.coords[1]-dest.coords[1]) * 111;
  let t   = Math.round(8 + dist*3.5 + Math.random()*6);
  let c   = [origin,dest].some(s => s.type==='train') ? 35 : 50;
  if (params.maxCost) c = Math.min(c, params.maxCost);
  const wf  = params.w2 || 0.33;
  c = Math.round(c * (0.7 + wf * 0.9));
  const co2 = Math.round(dist * 8);
  const tf  = dist > 10 ? 2 : 1;
  const dij = Math.floor(350 + dist*40);
  const ast = Math.floor(dij * .43);
  const bid = Math.floor(ast * .55);
  const ms  = elapsed;

  
  document.getElementById('p-dij').textContent    = dij;
  document.getElementById('p-dij-ms').textContent = `${t('res.nodes')} · ${(ms*1.4).toFixed(1)} ms`;
  document.getElementById('p-ast').textContent    = ast;
  document.getElementById('p-ast-ms').textContent = `${t('res.nodes')} · ${ms.toFixed(1)} ms`;
  document.getElementById('p-bid').textContent    = bid;
  document.getElementById('p-bid-ms').textContent = `${t('res.nodes')} · ${(ms*.55).toFixed(1)} ms`;

  
  document.getElementById('res-title').textContent    = `${origin.short} → ${dest.short}`;
  const paramNote = params.maxCost || params.w2 !== 0.33 ? ' · ' + t('res.custom-params') : '';
  document.getElementById('res-algo-used').textContent =
    `${t('res.calculated-with')} ${algo==='astar'?'A*':algo==='bidir'?'Bi-Directionnel':'Dijkstra'} · ${t('res.optimal')}${paramNote}`;

  document.getElementById('res-chips').innerHTML = `
    <div class="chip chip-m">${t} ${t('time.min')}</div>
    <div class="chip chip-p">${c} DA</div>
    <div class="chip chip-k">${co2}g CO₂</div>
    <div class="chip chip-c">${tf} ${t('res.transfers')}</div>`;

  
  const steps = buildItinSteps(origin, dest, dist);
  document.getElementById('itin-steps').innerHTML = steps.map((s, i) => `
    <div class="itin-step">
      <div class="step-icon-col">
        <div class="step-icon">${s.icon}</div>
        ${i < steps.length-1 ? '<div class="step-connector"></div>' : ''}
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
              ${s.cost > 0 ? s.cost+' DA' : 'Gratuit'}${s.co2 > 0 ? ' · '+s.co2+'g' : ''}
            </div>
          </div>
        </div>
      </div>
    </div>`).join('');

  renderRouteChart(steps, {t, c, co2, tf, dist});
  renderPathStats(steps, {origin, dest, dist, t, c, co2, tf, algo, ms, params});
  drawRoute(origin, dest, steps);
  renderSearchResult(origin, dest, c, tf, steps);

  const panel = document.getElementById('results-panel');
  panel.style.maxHeight = '900px';
  notif(t('notif.route-found-title'), `${t('notif.calc-in')} ${ms.toFixed(0)} ms · ${t} ${t('time.min')} · ${c} DA`, 'success');
}




function searchResultLegendColor(mode) {
  if (!mode) return 'var(--text-s)';
  if (mode.includes('Métro'))        return '#BEEEDB';   
  if (mode.includes('Tram'))         return '#C6B7E2';   
  if (mode.includes('Train'))        return '#F2C4CE';   
  if (mode.includes('Téléphérique')) return '#FF7043';   
  if (mode.includes('Bus'))          return '#FFD54F';   
  return 'var(--text-s)';
}


function renderSearchResult(origin, dest, totalCost, transferCount, steps) {
  const panel = document.getElementById('search-result');
  if (!panel) return;

  
  const isRide = s => s.mode !== 'Marche' && s.mode !== 'Transfert'
                   && s.mode !== 'origin' && s.mode !== 'dest';
  const rideTime = steps.filter(isRide).reduce((a, b) => a + b.time, 0);
  const waitTime = steps.filter(s => s.mode === 'Transfert').reduce((a, b) => a + b.time, 0);
  const walkTime = steps.filter(s => s.mode === 'Marche').reduce((a, b) => a + b.time, 0);
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
  const dLabel = dest.name   || dest.short   || '—';
  const transfersText = transferCount === 0
    ? t('res.no-transfer')
    : `${transferCount} ${t('res.transfer-s')}`;

  
  const chartSegments = [
    { label: t('res.ride-time'),  value: rideTime, color: '#BEEEDB' },
    { label: t('res.wait-time'), value: waitTime, color: '#F2C4CE' },
    { label: t('res.walk'),  value: walkTime, color: '#8AAAC8' },
  ].filter(s => s.value > 0);
  const cx = 50, cy = 50, r = 36, circ = 2 * Math.PI * r;
  let off = circ / 4;
  const donutPaths = chartSegments.map((seg, i) => {
    const pct  = seg.value / Math.max(totalTime, 1);
    const dash = pct * circ;
    const dashOffset = circ - off;
    off += dash;
    return `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none"
              stroke="${seg.color}" stroke-width="12"
              stroke-dasharray="${dash} ${circ - dash}"
              stroke-dashoffset="${dashOffset}" stroke-linecap="butt"
              style="animation:donutFadeIn .55s ease ${i * .12}s both"/>`;
  }).join('');
  const chartHtml = totalTime > 0 ? `
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
        ${chartSegments.map(seg => {
          const pct = Math.round(seg.value / Math.max(totalTime, 1) * 100);
          return `
            <div class="sr-chart-row">
              <span class="sr-chart-key">
                <span class="sr-dot" style="background:${seg.color};color:${seg.color}"></span>
                ${seg.label}
              </span>
              <span class="sr-chart-val">${seg.value} <span class="sr-chart-pct">(${pct}%)</span></span>
            </div>`;
        }).join('')}
      </div>
    </div>` : '';

  panel.innerHTML = `
    <div class="sidebar-label" style="padding:0;margin-bottom:4px">Résumé du trajet</div>
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

    ${used.length ? `
    <div class="sr-modes">
      ${used.map(u => `
        <div class="sr-mode-row">
          <span class="sr-dot" style="background:${u.color};color:${u.color}"></span>
          <span class="sr-mode-name">${u.mode}</span>
          <span class="sr-mode-time">${u.time} ${t('time.min')}</span>
        </div>`).join('')}
    </div>` : ''}

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


function renderRouteChart(steps, meta) {
  const section = document.getElementById('route-chart-section');
  if (!section) return;
  section.style.display = 'block';
  section.classList.remove('route-chart-section');
  void section.offsetWidth;
  section.classList.add('route-chart-section');

  const walkTime  = steps.filter(s => s.mode==='Marche').reduce((a,b) => a+b.time, 0);
  const waitTime  = steps.filter(s => s.mode==='Transfert').reduce((a,b) => a+b.time, 0);
  const rideTime  = steps.filter(s => s.mode!=='Marche'&&s.mode!=='Transfert'&&s.mode!=='origin'&&s.mode!=='dest').reduce((a,b) => a+b.time, 0);
  const totalTime = walkTime + waitTime + rideTime;

  const segments = [
    {label:t('res.ride-time'),  value:rideTime, color:'#BEEEDB', colorDark:'#3DAB82'},
    {label:t('res.wait-time'), value:waitTime, color:'#F2C4CE', colorDark:'#cc3355'},
    {label:t('res.walk'),  value:walkTime, color:'#8AAAC8', colorDark:'#4A7090'},
  ].filter(s => s.value > 0);

  
  const cx=75, cy=75, r=52, circ=2*Math.PI*r;
  let offset = circ/4;
  const svgSegments = segments.map((seg,i) => {
    const pct = seg.value / Math.max(totalTime,1);
    const dash = pct*circ, gap = circ-dash, dashOffset = circ-offset;
    offset += dash;
    return `<circle class="chart-segment" cx="${cx}" cy="${cy}" r="${r}"
      fill="none" stroke="${seg.color}" stroke-width="18"
      stroke-dasharray="${dash} ${gap}" stroke-dashoffset="${dashOffset}" stroke-linecap="butt"
      style="transition:stroke-width .2s ease,opacity .3s ease;animation:donutFadeIn .6s ease ${i*.15}s both;opacity:0"
      title="${seg.label}: ${seg.value} ${t('time.min')}"/>`;
  }).join('');
  document.getElementById('donut-segments').innerHTML = svgSegments;
  document.getElementById('donut-total').textContent  = totalTime;
  setTimeout(() => document.querySelectorAll('#donut-segments circle').forEach(c => c.style.opacity='1'), 50);

  
  document.getElementById('chart-legend-bars').innerHTML = segments.map((seg,i) => {
    const pct = Math.round(seg.value/Math.max(totalTime,1)*100);
    return `<div style="animation:chartFadeIn .5s ease ${i*.12+.2}s both;opacity:0" id="bar-item-${i}">
      <div style="display:flex;justify-content:space-between;font-size:.8rem;margin-bottom:5px;align-items:center">
        <div style="display:flex;align-items:center;gap:8px">
          <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${seg.color};flex-shrink:0;box-shadow:0 0 6px ${seg.color}44"></span>
          <span style="font-weight:500">${seg.label}</span>
        </div>
        <span style="font-family:'DM Mono',monospace;color:${seg.colorDark};font-weight:600">${seg.value} ${t('time.min')} <span style="color:var(--text-t);font-size:.72rem">(${pct}%)</span></span>
      </div>
      <div style="background:var(--bg-4);border-radius:99px;overflow:hidden;height:6px">
        <div class="bar-fill" style="width:${pct}%;background:linear-gradient(90deg,${seg.color},${seg.colorDark});animation-delay:${i*.12+.3}s"></div>
      </div>
    </div>`;
  }).join('');
  setTimeout(() => document.querySelectorAll('[id^="bar-item-"]').forEach(el => el.style.opacity='1'), 50);

  
  const costSection   = document.getElementById('cost-bars-section');
  const costBreakdown = steps.filter(s => s.cost>0 && s.mode!=='origin' && s.mode!=='dest');
  const totalCost     = costBreakdown.reduce((a,b) => a+b.cost, 0);
  if (costSection && costBreakdown.length) {
    costSection.innerHTML = `
      <div style="font-size:.78rem;font-weight:700;color:var(--text-s);margin-bottom:10px;letter-spacing:.04em">💰 ${t('res.cost-dist')}</div>
      <div style="display:flex;flex-direction:column;gap:8px">
        ${costBreakdown.map((s,i) => {
          const pct = Math.round(s.cost/Math.max(totalCost,1)*100);
          const col = s.mode.includes('Train')?'var(--pink)':s.mode.includes('Tram')?'var(--purple)':'var(--mint)';
          return `<div style="display:flex;align-items:center;gap:10px;font-size:.78rem">
            <div style="width:90px;color:var(--text-s);flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${s.mode}</div>
            <div style="flex:1;background:var(--bg-4);border-radius:99px;overflow:hidden;height:5px">
              <div style="height:100%;width:${pct}%;background:${col};border-radius:99px;animation:barGrow .6s cubic-bezier(.34,1.2,.64,1) ${i*.1+.4}s both;transform-origin:left"></div>
            </div>
            <div style="font-family:'DM Mono',monospace;color:${col};font-weight:600;width:44px;text-align:right">${s.cost} DA</div>
          </div>`;
        }).join('')}
        <div style="display:flex;justify-content:flex-end;padding-top:6px;border-top:1px solid var(--border);margin-top:2px">
          <span style="font-family:'DM Mono',monospace;font-size:.82rem;font-weight:700;color:var(--purple)">${t('res.total')}: ${totalCost} DA</span>
        </div>
      </div>`;
  }
}


function renderPathStats(steps, meta) {
  const statsPanel = document.getElementById('path-stats');
  if (!statsPanel) return;

  const totalCost  = steps.reduce((s,x) => s+x.cost, 0);
  const waitTime   = steps.filter(x => x.mode==='Transfert').reduce((s,x) => s+x.time, 0);
  const walkTime   = steps.filter(x => x.mode==='Marche').reduce((s,x) => s+x.time, 0);
  const rideTime   = steps.filter(x => x.mode!=='Marche'&&x.mode!=='Transfert'&&x.mode!=='origin'&&x.mode!=='dest').reduce((s,x) => s+x.time, 0);
  const modeSet    = [...new Set(steps.filter(x=>x.mode!=='Marche'&&x.mode!=='Transfert'&&x.mode!=='origin'&&x.mode!=='dest').map(x=>x.mode))];
  const distKm     = meta.dist.toFixed(2);

  document.getElementById('path-summary-grid').innerHTML = [
    {label:t('res.price-total'),    val:`${totalCost} DA`, col:'var(--purple)'},
    {label:t('res.ride-time'),  val:`${rideTime} ${t('time.min')}`, col:'var(--mint)'},
    {label:t('res.wait-time'), val:`${waitTime} ${t('time.min')}`, col:'var(--pink)'},
    {label:t('res.walk'),        val:`${walkTime} ${t('time.min')}`, col:'var(--text-s)'},
    {label:t('res.modes'),         val:`${modeSet.length||1}`, col:'var(--mint)'},
    {label:t('res.dist'),      val:`~${distKm} km`,   col:'var(--text-s)'},
  ].map(d => `
    <div class="res-stat-card">
      <div class="res-stat-val" style="color:${d.col}">${d.val}</div>
      <div class="res-stat-lbl">${d.label}</div>
    </div>`).join('');

  const modeColor = {
    'Marche':'var(--text-s)','Transfert':'var(--text-t)','Métro L1':'var(--mint)',
    'Tramway T1':'var(--purple)','Train banlieue':'var(--pink)','Téléphérique':'#FF7043',
  };
  const transitRows = steps.filter(x => x.mode!=='origin' && x.mode!=='dest');
  document.getElementById('path-segment-rows').innerHTML = transitRows.map((s,i) => `
    <div style="display:grid;grid-template-columns:1.5fr 1fr 1fr 1fr 1fr;gap:6px;padding:9px 14px;border-bottom:${i<transitRows.length-1?'1px solid var(--border)':'none'};font-size:.78rem;align-items:center;transition:background var(--tr)"
         onmouseenter="this.style.background='var(--bg-3)'" onmouseleave="this.style.background='transparent'">
      <span style="font-weight:500">${s.from} → ${s.to}</span>
      <span style="text-align:center"><span class="chip" style="font-size:.65rem;background:${(modeColor[s.mode]||'var(--text-s)')}22;color:${modeColor[s.mode]||'var(--text-s)'}">${s.icon} ${s.mode}</span></span>
      <span style="text-align:right;font-family:'DM Mono',monospace">${s.mode==='Transfert'?'—':s.time+' '+t('time.min')}</span>
      <span style="text-align:right;font-family:'DM Mono',monospace;color:var(--text-t)">${s.mode==='Transfert'?s.time+' '+t('time.min'):'—'}</span>
      <span style="text-align:right;font-family:'DM Mono',monospace;color:var(--purple)">${s.cost>0?s.cost+' DA':'—'}</span>
    </div>`).join('');

  const algoLabel  = meta.algo==='astar'?'A*':meta.algo==='bidir'?'Bi-Directionnel':'Dijkstra';
  const efficiency = Math.round(100 - (meta.tf / Math.max(steps.length,1)) * 30);
  const paramNote  = meta.params.maxCost ? `coût max ${meta.params.maxCost} DA · ` : '';
  document.getElementById('path-global-stats').innerHTML = `
    <span>📦 <b>${steps.length}</b> ${t('res.segments-tot')}</span>
    <span>🛣️ <b>~${distKm} km</b> ${t('res.dist').toLowerCase()}</span>
    <span>🔄 <b>${meta.tf}</b> ${t('res.transfer-s')}</span>
    <span>⚡ Algo: <b>${algoLabel}</b> · <b>${meta.ms.toFixed(0)} ms</b></span>
    <span>🎯 ${t('res.efficiency')}: <b>${efficiency}%</b></span>
    <span style="color:var(--text-t);font-size:.72rem">${paramNote}${t('res.profile')}: ${meta.params.profile}</span>`;

  statsPanel.style.display = 'block';
}

document.addEventListener('lang-changed', () => {
  if (lastResultsArgs) {
    showResults(lastResultsArgs.origin, lastResultsArgs.dest, lastResultsArgs.algo, lastResultsArgs.elapsed, lastResultsArgs.params);
  }
});
