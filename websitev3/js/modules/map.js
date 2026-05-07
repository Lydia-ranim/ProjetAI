/* ═══════════════════════════════════════════════════════════
   LYHLYH — Map: Leaflet init, markers, network, click
   Depends on: stations.js, notifications.js, autocomplete.js
═══════════════════════════════════════════════════════════ */

/* ── State ── */
let dashMap = null, heroMap = null, expMap = null;
let dashMapInited = false, heroMapInited = false;
let originMarker = null, destMarker = null, routeLayer = null;
let networkVisible = false, networkLayerGroup = null;

/* ── Map config ──
   Tiles: OpenStreetMap "Standard" (Mapnik) — colorful natural look with
   green parks/forests, blue water, and the classic red/orange/yellow
   road hierarchy. Used identically in light & dark site modes. */
const TILE_URL  = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const TILE_OPT  = { attribution:'© OpenStreetMap contributors', maxZoom:19, subdomains:'abc' };
const ALG_BOUNDS = [[36.48,2.75],[36.98,3.55]];
const ALG_CENTER = [36.737,3.086];

/* Current click mode: 'origin' | 'dest' */
let clickMode = 'origin';

/* ── Custom pin markers ── */
function makeIcon(color, emoji) {
  return L.divIcon({
    className: '',
    html: `<div style="width:34px;height:40px;position:relative;filter:drop-shadow(0 3px 8px rgba(0,0,0,.4))">
      <div style="width:34px;height:34px;border-radius:50% 50% 50% 0;background:${color};transform:rotate(-45deg);border:2.5px solid rgba(255,255,255,.4)"></div>
      <div style="position:absolute;top:5px;left:50%;transform:translateX(-50%);font-size:15px;line-height:1">${emoji}</div>
    </div>`,
    iconSize:[34,40], iconAnchor:[17,40], popupAnchor:[0,-42],
  });
}
const originIcon = makeIcon('#3DAB82','📍');
const destIcon   = makeIcon('#8A0A35','🎯');

/* ─────────────────────────────────────────────
   HERO MAP (landing page — read-only preview)
───────────────────────────────────────────── */
function initHeroMap() {
  heroMapInited = true;
  heroMap = L.map('hero-map', {
    center:ALG_CENTER, zoom:12,
    maxBounds:ALG_BOUNDS, maxBoundsViscosity:.7,
    zoomControl:false, scrollWheelZoom:false,
    dragging:true, attributionControl:false,
  });
  L.tileLayer(TILE_URL, TILE_OPT).addTo(heroMap);
  drawNetwork(heroMap);

  /* Sample route preview: Martyrs → Zeralda */
  const sample = ['M_MARTYRS','M_TAFOURAH','M_BOUMENDIL','M_PREMIER','M_EL_BADR','M_HARRACH','TR_HARRACH','TR_AGHA','TR_ALGER','TR_ZERALDA'].map(id => SMAP[id]);
  const coords = sample.map(s => s.coords);
  L.polyline(coords,{color:'rgba(92,107,192,.25)',weight:14,lineCap:'round',lineJoin:'round'}).addTo(heroMap);
  L.polyline(coords,{color:'rgba(255,255,255,.6)', weight:8, lineCap:'round',lineJoin:'round'}).addTo(heroMap);
  L.polyline(coords,{color:'#5C6BC0',             weight:5, lineCap:'round',lineJoin:'round'}).addTo(heroMap);
  L.marker(SMAP['M_MARTYRS'].coords, {icon:originIcon}).addTo(heroMap);
  L.marker(SMAP['TR_ZERALDA'].coords,{icon:destIcon  }).addTo(heroMap);
  setTimeout(() => heroMap.invalidateSize(), 200);
}

/* ─────────────────────────────────────────────
   DASHBOARD MAP (main interactive map)
───────────────────────────────────────────── */
function initDashMap() {
  dashMapInited = true;
  dashMap = L.map('dash-map', {
    center:ALG_CENTER, zoom:12,
    maxBounds:ALG_BOUNDS, maxBoundsViscosity:.85,
    minZoom:10, maxZoom:17,
  });
  L.tileLayer(TILE_URL, TILE_OPT).addTo(dashMap);
  addStationMarkers(dashMap);
  dashMap.on('click', onMapClick);
  setTimeout(() => dashMap.invalidateSize(), 300);
}

/* ── Network toggle (dashboard only) ── */
function toggleNetwork() {
  networkVisible = !networkVisible;
  const ind = document.getElementById('network-indicator');
  const lbl = document.getElementById('network-lbl');
  if (networkVisible) {
    if (!networkLayerGroup) {
      networkLayerGroup = L.layerGroup();
      drawNetworkLines(networkLayerGroup);
    }
    networkLayerGroup.addTo(dashMap);
    ind.style.background = '#BEEEDB';
    lbl.textContent = 'Masquer réseau';
  } else {
    if (networkLayerGroup) dashMap.removeLayer(networkLayerGroup);
    ind.style.background = '#ccc';
    lbl.textContent = 'Afficher réseau';
  }
}

/* ── Station markers (clickable, no network lines) ── */
function addStationMarkers(map) {
  STATIONS.forEach(s => {
    const c = L.circleMarker(s.coords, {
      radius: s.type === 'train' ? 8 : 6,
      fillColor: TYPE_COLOR[s.type],
      color: 'rgba(255,255,255,.9)',
      weight: 2, fillOpacity: .9,
    }).addTo(map);
    c.bindPopup(`<div style="font-family:'DM Sans',sans-serif;padding:2px">
      <div style="font-weight:600;margin-bottom:4px">${s.icon} ${s.name}</div>
      <div style="font-size:.78rem;color:#888;margin-bottom:8px">${s.line}</div>
      <button onclick="selectStation('origin','${s.id}')" style="margin-right:6px;padding:4px 10px;border-radius:6px;background:#BEEEDB22;color:#3DAB82;border:1px solid #BEEEDB44;cursor:pointer;font-size:.75rem;font-weight:600">📍 Départ</button>
      <button onclick="selectStation('dest','${s.id}')"   style="padding:4px 10px;border-radius:6px;background:#67062722;color:#cc3355;border:1px solid #67062744;cursor:pointer;font-size:.75rem;font-weight:600">🎯 Arrivée</button>
    </div>`, {className:'route-popup', closeButton:true});
    c.on('click', e => { e.originalEvent.stopPropagation(); });
  });
}

/* ── Network lines (reusable — adds to any Leaflet target) ── */
function drawNetworkLines(target) {
  const addLine = (ids, color, dash='') => {
    const pts = ids.filter(id => SMAP[id]).map(id => SMAP[id].coords);
    const opt = {color, weight:3, opacity:.7, lineCap:'round', lineJoin:'round'};
    if (dash) opt.dashArray = dash;
    L.polyline(pts, opt).addTo(target);
  };
  addLine(METRO_L1,   '#BEEEDB');
  addLine(TRAM_T1,    '#C6B7E2', '8,4');
  addLine(TRAIN_WEST, '#F2C4CE', '12,3');
  L.polyline([SMAP['C_HAMMA'].coords, SMAP['C_JARDIN'].coords],
    {color:'#FF7043', weight:2.5, opacity:.7, dashArray:'5,5'}).addTo(target);
}

/* ── Full network: lines + markers (hero + explorer maps) ── */
function drawNetwork(map) {
  drawNetworkLines(map);
  STATIONS.forEach(s => {
    const c = L.circleMarker(s.coords, {
      radius: s.type === 'train' ? 7 : 5.5,
      fillColor: TYPE_COLOR[s.type],
      color: 'rgba(255,255,255,.85)',
      weight: 1.8, fillOpacity: .92,
    }).addTo(map);
    c.bindPopup(`<div style="font-family:'DM Sans',sans-serif">
      <div style="font-weight:600;margin-bottom:4px">${s.icon} ${s.name}</div>
      <div style="font-size:.78rem;color:#888">${s.line}</div>
      <button onclick="selectStation('origin','${s.id}')" style="margin-top:8px;padding:4px 10px;border-radius:6px;background:#BEEEDB22;color:#3DAB82;border:1px solid #BEEEDB44;cursor:pointer;font-size:.75rem;margin-right:6px">Départ</button>
      <button onclick="selectStation('dest','${s.id}')"   style="padding:4px 10px;border-radius:6px;background:#67062722;color:#cc3355;border:1px solid #67062744;cursor:pointer;font-size:.75rem">Arrivée</button>
    </div>`, {className:'route-popup', closeButton:true});
    c.on('click', e => { e.originalEvent.stopPropagation(); });
  });
}

/* ── Map click: snap to nearest station or free-place ── */
function onMapClick(e) {
  const {lat, lng} = e.latlng;
  let best = null, bestD = Infinity;
  STATIONS.forEach(s => {
    const d = Math.hypot(s.coords[0]-lat, s.coords[1]-lng);
    if (d < bestD) { bestD = d; best = s; }
  });
  if (bestD < 0.05) {
    selectStation(clickMode, best.id);
    notif(`${clickMode === 'origin' ? 'Départ' : 'Arrivée'} défini`, best.name, 'success');
  } else {
    const lbl = clickMode === 'origin' ? 'Départ personnalisé' : 'Arrivée personnalisée';
    placeMarker(clickMode, [lat, lng], lbl);
    document.getElementById(clickMode === 'origin' ? 'origin-input' : 'dest-input').value =
      `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
    notif(lbl, 'Aucun arrêt proche — position libre', 'info');
  }
  if (clickMode === 'origin') setClickMode('dest');
  setStatus();
}

/* ── Click mode toggle ── */
function setClickMode(m) {
  clickMode = m;
  document.getElementById('btn-set-origin').className = 'mode-btn' + (m==='origin'?' origin-active':'');
  document.getElementById('btn-set-dest').className   = 'mode-btn' + (m==='dest'  ?' dest-active':'');
  document.getElementById('click-hint').textContent   = m==='origin'
    ? '📍 Cliquez sur la carte pour définir le départ'
    : "🎯 Cliquez sur la carte pour définir l'arrivée";
}

/* ── Place a pin marker on the dashboard map ── */
function placeMarker(which, coords, label) {
  if (!dashMap) return;
  if (which === 'origin') {
    if (originMarker) dashMap.removeLayer(originMarker);
    originMarker = L.marker(coords, {icon:originIcon}).addTo(dashMap).bindPopup(`<b>Départ:</b> ${label}`);
    dashMap.setView(coords, 13, {animate:true});
  } else {
    if (destMarker) dashMap.removeLayer(destMarker);
    destMarker = L.marker(coords, {icon:destIcon}).addTo(dashMap).bindPopup(`<b>Arrivée:</b> ${label}`);
    if (originMarker) {
      dashMap.fitBounds(L.latLngBounds([originMarker.getLatLng(), destMarker.getLatLng()]), {padding:[60,60], animate:true});
    } else {
      dashMap.setView(coords, 13, {animate:true});
    }
  }
}

/* ── Swap origin ↔ destination markers ── */
function swapPoints() {
  const oi = document.getElementById('origin-input');
  const di = document.getElementById('dest-input');
  [oi.value, di.value] = [di.value, oi.value];
  [acSel.origin, acSel.dest] = [acSel.dest, acSel.origin];
  if (originMarker && destMarker && dashMap) {
    const oc = originMarker.getLatLng(), dc = destMarker.getLatLng();
    dashMap.removeLayer(originMarker); dashMap.removeLayer(destMarker);
    originMarker = L.marker(dc, {icon:originIcon}).addTo(dashMap);
    destMarker   = L.marker(oc, {icon:destIcon  }).addTo(dashMap);
  }
}

/* ── Draw the calculated route (Google Maps nav style) ── */
function drawRoute(origin, dest, steps) {
  if (!dashMap) return;
  if (routeLayer) dashMap.removeLayer(routeLayer);

  const via = [
    origin.coords,
    ...steps
      .filter(s => s.mode !== 'Marche' && s.mode !== 'Transfert')
      .map(s => { const n = STATIONS.find(st => st.short===s.to || st.short===s.from); return n ? n.coords : null; })
      .filter(Boolean),
    dest.coords,
  ];
  const uniqueVia = [...new Map(via.map(c => c.join(','))).values()].map(k => k.split(',').map(Number));
  const smoothed  = addMidpoints(uniqueVia);

  const rg = L.layerGroup();
  L.polyline(smoothed,{color:'rgba(92,107,192,.18)',weight:18,lineCap:'round',lineJoin:'round'}).addTo(rg);
  L.polyline(smoothed,{color:'rgba(255,255,255,.85)',weight:9, lineCap:'round',lineJoin:'round'}).addTo(rg);
  L.polyline(smoothed,{color:'#5C6BC0',             weight:6, lineCap:'round',lineJoin:'round', className:'route-line'}).addTo(rg);
  rg.addTo(dashMap);
  routeLayer = rg;
  dashMap.fitBounds(L.latLngBounds([origin.coords, dest.coords, ...smoothed]), {padding:[100,80], animate:true});
}

/** Add midpoints between waypoints for a smoother rendered path. */
function addMidpoints(coords) {
  if (coords.length < 2) return coords;
  const result = [coords[0]];
  for (let i = 1; i < coords.length; i++) {
    const a = coords[i-1], b = coords[i];
    result.push([(a[0]+b[0])/2, (a[1]+b[1])/2]);
    result.push(b);
  }
  return result;
}
