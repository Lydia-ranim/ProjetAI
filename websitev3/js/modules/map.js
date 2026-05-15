/* ═══════════════════════════════════════════════════════════
   LYHLYH — Map: Leaflet init, markers, route polylines
   Depends on: stations.js, notifications.js, autocomplete.js, api.js
═══════════════════════════════════════════════════════════ */

/* ── State ── */
let dashMap = null;
let heroMap = null;
let expMap = null;
let dashMapInited = false;
let heroMapInited = false;
let originMarker = null;
let destMarker = null;
let routeLayer = null;
let networkVisible = false;
let networkLayerGroup = null;
let heroRoutePreviewLayer = null;

/* ── Map config ── */
const TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const TILE_OPT = { attribution: '© OpenStreetMap contributors', maxZoom: 19, subdomains: 'abc' };
const ALG_BOUNDS = [[36.48, 2.75], [36.98, 3.55]];
const ALG_CENTER = [36.737, 3.086];

let clickMode = 'origin';

function polylineColorForMode(mode) {
  const k = normalizeModeKey(mode);
  return MODE_LINE_COLOR_HEX[k] || MODE_LINE_COLOR_HEX.default;
}

/* ── Custom pin markers ── */
function makeIcon(color, emoji) {
  return L.divIcon({
    className: '',
    html: `<div style="width:34px;height:40px;position:relative;filter:drop-shadow(0 3px 8px rgba(0,0,0,.4))">
      <div style="width:34px;height:34px;border-radius:50% 50% 50% 0;background:${color};transform:rotate(-45deg);border:2.5px solid rgba(255,255,255,.4)"></div>
      <div style="position:absolute;top:5px;left:50%;transform:translateX(-50%);font-size:15px;line-height:1">${emoji}</div>
    </div>`,
    iconSize: [34, 40],
    iconAnchor: [17, 40],
    popupAnchor: [0, -42],
  });
}
const originIcon = makeIcon('#3DAB82', '📍');
const destIcon = makeIcon('#8A0A35', '🎯');

/* ─────────────────────────────────────────────
   HERO MAP (landing)
───────────────────────────────────────────── */
function initHeroMap() {
  heroMapInited = true;
  heroMap = L.map('hero-map', {
    center: ALG_CENTER,
    zoom: 12,
    maxBounds: ALG_BOUNDS,
    maxBoundsViscosity: 0.7,
    zoomControl: false,
    scrollWheelZoom: false,
    dragging: true,
    attributionControl: false,
  });
  L.tileLayer(TILE_URL, TILE_OPT).addTo(heroMap);
  drawNetwork(heroMap);
  refreshHeroSampleRoute();
  setTimeout(() => heroMap.invalidateSize(), 200);
}

/** Redraw landing map stop dots after GET /api/stops completes. */
function refreshHeroMapAfterStops() {
  if (!heroMap) return;
  heroMap.eachLayer(layer => {
    if (layer instanceof L.CircleMarker) heroMap.removeLayer(layer);
  });
  drawNetwork(heroMap);
  refreshHeroSampleRoute();
}

/** Preview polyline on landing map once `/api/stops` has been loaded. */
function refreshHeroSampleRoute() {
  if (!heroMap) return;
  if (heroRoutePreviewLayer) {
    heroMap.removeLayer(heroRoutePreviewLayer);
    heroRoutePreviewLayer = null;
  }
  if (STATIONS.length < 2) return;

  const a = STATIONS[0];
  const b = STATIONS[Math.min(50, STATIONS.length - 1)];
  const coords = [a.coords, b.coords];
  heroRoutePreviewLayer = L.layerGroup();
  L.polyline(coords, {
    color: 'rgba(92,107,192,.25)',
    weight: 14,
    lineCap: 'round',
    lineJoin: 'round',
  }).addTo(heroRoutePreviewLayer);
  L.polyline(coords, {
    color: 'rgba(255,255,255,.6)',
    weight: 8,
    lineCap: 'round',
    lineJoin: 'round',
  }).addTo(heroRoutePreviewLayer);
  L.polyline(coords, {
    color: '#5C6BC0',
    weight: 5,
    lineCap: 'round',
    lineJoin: 'round',
  }).addTo(heroRoutePreviewLayer);
  L.marker(a.coords, { icon: originIcon }).addTo(heroRoutePreviewLayer);
  L.marker(b.coords, { icon: destIcon }).addTo(heroRoutePreviewLayer);
  heroRoutePreviewLayer.addTo(heroMap);
}

/* ─────────────────────────────────────────────
   DASHBOARD MAP
───────────────────────────────────────────── */
function initDashMap() {
  dashMapInited = true;
  dashMap = L.map('dash-map', {
    center: ALG_CENTER,
    zoom: 12,
    maxBounds: ALG_BOUNDS,
    maxBoundsViscosity: 0.85,
    minZoom: 10,
    maxZoom: 17,
  });
  L.tileLayer(TILE_URL, TILE_OPT).addTo(dashMap);
  refreshDashStationMarkers();
  dashMap.on('click', onMapClick);
  setTimeout(() => dashMap.invalidateSize(), 300);
}

function refreshDashStationMarkers() {
  if (!dashMap) return;
  dashMap.eachLayer(layer => {
    if (layer instanceof L.CircleMarker) dashMap.removeLayer(layer);
  });
  addStationMarkers(dashMap);
}

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
    lbl.textContent = t('map.hide-network');
  } else {
    if (networkLayerGroup) dashMap.removeLayer(networkLayerGroup);
    ind.style.background = '#ccc';
    lbl.textContent = t('map.show-network');
  }
}

/* ── Station markers ── */
function addStationMarkers(map) {
  STATIONS.forEach(s => {
    // Hide stops whose transport mode is outside operating hours
    if (!isStopInService(normalizeModeKey(s.type))) return;

    const c = L.circleMarker(s.coords, {
      radius: s.type === 'train' ? 5 : 4,
      fillColor: TYPE_COLOR[s.type] || TYPE_COLOR.default,
      color: 'rgba(255,255,255,.9)',
      weight: 2,
      fillOpacity: 0.85,
    }).addTo(map);
    const safeId = String(s.id).replace(/'/g, "\\'");
    c.bindPopup(
      `<div style="font-family:'DM Sans',sans-serif;padding:2px">
      <div style="font-weight:600;margin-bottom:4px">${s.icon} ${s.name}</div>
      <div style="font-size:.78rem;color:#888;margin-bottom:8px">${s.line}</div>
      <button onclick="selectStation('origin','${safeId}')" style="margin-right:6px;padding:4px 10px;border-radius:6px;background:#BEEEDB22;color:#3DAB82;border:1px solid #BEEEDB44;cursor:pointer;font-size:.75rem;font-weight:600">${t('map.origin-btn')}</button>
      <button onclick="selectStation('dest','${safeId}')"   style="padding:4px 10px;border-radius:6px;background:#67062722;color:#cc3355;border:1px solid #67062744;cursor:pointer;font-size:.75rem;font-weight:600">${t('map.dest-btn')}</button>
    </div>`,
      { className: 'route-popup', closeButton: true }
    );
    c.on('click', e => {
      e.originalEvent.stopPropagation();
    });
  });
}

/* Hardcoded line geometry removed — network overlay is optional / empty. */
function drawNetworkLines(_target) {
  /* No client-side graph; full topology lives on the API. */
}

function drawNetwork(map) {
  drawNetworkLines(map);
  STATIONS.forEach(s => {
    // Hide stops whose transport mode is outside operating hours
    if (!isStopInService(normalizeModeKey(s.type))) return;

    const c = L.circleMarker(s.coords, {
      radius: s.type === 'train' ? 6 : 4,
      fillColor: TYPE_COLOR[s.type] || TYPE_COLOR.default,
      color: 'rgba(255,255,255,.85)',
      weight: 1.5,
      fillOpacity: 0.88,
    }).addTo(map);
    const safeId = String(s.id).replace(/'/g, "\\'");
    c.bindPopup(
      `<div style="font-family:'DM Sans',sans-serif">
      <div style="font-weight:600;margin-bottom:4px">${s.icon} ${s.name}</div>
      <div style="font-size:.78rem;color:#888">${s.line}</div>
      <button onclick="selectStation('origin','${safeId}')" style="margin-top:8px;padding:4px 10px;border-radius:6px;background:#BEEEDB22;color:#3DAB82;border:1px solid #BEEEDB44;cursor:pointer;font-size:.75rem;margin-right:6px">${t('map.origin-btn')}</button>
      <button onclick="selectStation('dest','${safeId}')"   style="padding:4px 10px;border-radius:6px;background:#67062722;color:#cc3355;border:1px solid #67062744;cursor:pointer;font-size:.75rem">${t('map.dest-btn')}</button>
    </div>`,
      { className: 'route-popup', closeButton: true }
    );
    c.on('click', e => {
      e.originalEvent.stopPropagation();
    });
  });
}

function fallbackNearestStation(lat, lng) {
  let best = null;
  let bestD = Infinity;
  STATIONS.forEach(s => {
    const d = Math.hypot(s.coords[0] - lat, s.coords[1] - lng);
    if (d < bestD) {
      bestD = d;
      best = s;
    }
  });
  return best && bestD < 0.08 ? best : null;
}

async function onMapClick(e) {
  const { lat, lng } = e.latlng;
  let stop = null;

  try {
    const nearest = await fetchNearestStop(lat, lng, 5);
    const first = Array.isArray(nearest) && nearest.length ? nearest[0] : null;
    if (first) {
      stop = normalizeApiStop(first);
      ensureStopInRegistry(stop);
    }
  } catch (err) {
    console.warn('nearest-stop failed', err);
  }

  if (!stop) stop = fallbackNearestStation(lat, lng);

  if (stop) {
    selectStation(clickMode, stop.id);
    const ptLbl = clickMode === 'origin' ? t('notif.pt-origin') : t('notif.pt-dest');
    notif(`${ptLbl} ${t('notif.pt-set-title')}`, stop.name, 'success');
  } else {
    const lbl = clickMode === 'origin' ? t('map.custom-origin') : t('map.custom-dest');
    const synthetic = {
      id: null,
      name: `${lat.toFixed(5)}, ${lng.toFixed(5)}`,
      short: 'Point',
      coords: [lat, lng],
      type: 'walk',
      line: '—',
      icon: '📌',
    };
    acSel[clickMode] = synthetic;
    document.getElementById(clickMode === 'origin' ? 'origin-input' : 'dest-input').value = synthetic.name;
    placeMarker(clickMode, [lat, lng], synthetic.name);
    notif(lbl, t('notif.nearest-fallback-msg'), 'info');
  }

  if (clickMode === 'origin') setClickMode('dest');
  setStatus();
}

function setClickMode(m) {
  clickMode = m;
  document.getElementById('btn-set-origin').className = 'mode-btn' + (m === 'origin' ? ' origin-active' : '');
  document.getElementById('btn-set-dest').className = 'mode-btn' + (m === 'dest' ? ' dest-active' : '');
  const hint = document.getElementById('click-hint');
  if (hint) hint.textContent = m === 'origin' ? t('map.click-origin') : t('map.click-dest');
}

function placeMarker(which, coords, label) {
  if (!dashMap) return;
  if (which === 'origin') {
    if (originMarker) dashMap.removeLayer(originMarker);
    originMarker = L.marker(coords, { icon: originIcon })
      .addTo(dashMap)
      .bindPopup(`<b>${t('map.origin-btn')}:</b> ${label}`);
    dashMap.setView(coords, 13, { animate: true });
  } else {
    if (destMarker) dashMap.removeLayer(destMarker);
    destMarker = L.marker(coords, { icon: destIcon })
      .addTo(dashMap)
      .bindPopup(`<b>${t('map.dest-btn')}:</b> ${label}`);
    if (originMarker) {
      dashMap.fitBounds(L.latLngBounds([originMarker.getLatLng(), destMarker.getLatLng()]), {
        padding: [60, 60],
        animate: true,
      });
    } else {
      dashMap.setView(coords, 13, { animate: true });
    }
  }
}

function swapPoints() {
  const oi = document.getElementById('origin-input');
  const di = document.getElementById('dest-input');
  [oi.value, di.value] = [di.value, oi.value];
  [acSel.origin, acSel.dest] = [acSel.dest, acSel.origin];
  if (originMarker && destMarker && dashMap) {
    const oc = originMarker.getLatLng();
    const dc = destMarker.getLatLng();
    dashMap.removeLayer(originMarker);
    dashMap.removeLayer(destMarker);
    originMarker = L.marker(dc, { icon: originIcon }).addTo(dashMap);
    destMarker = L.marker(oc, { icon: destIcon }).addTo(dashMap);
  }
}

/**
 * Draw each API segment polyline with mode colour (bus / metro / tram / walk / téléphérique).
 * @param {Object} origin
 * @param {Object} dest
 * @param {Array<{mode:string,polyline?:Array<[number,number]>}>} segments
 */
function drawRouteSegments(origin, dest, segments) {
  if (!dashMap) return;
  if (routeLayer) dashMap.removeLayer(routeLayer);

  const rg = L.layerGroup();
  const allLatLngs = [];

  (segments || []).forEach(seg => {
    const raw = seg.polyline;
    if (!raw || raw.length < 2) return;
    const latlngs = raw.map(p => {
      const lat = p[0];
      const lon = p[1];
      return [lat, lon];
    });
    // Smooth simple polylines so they follow roads more naturally when
    // only stop nodes are available. Uses a lightweight Chaikin subdivision.
    function smoothLatLngs(points, iterations = 2) {
      if (!points || points.length < 2) return points;
      let pts = points.map(p => [Number(p[0]), Number(p[1])]);
      for (let it = 0; it < iterations; it++) {
        const out = [];
        out.push(pts[0]);
        for (let i = 0; i < pts.length - 1; i++) {
          const p0 = pts[i];
          const p1 = pts[i + 1];
          const q = [(0.75 * p0[0] + 0.25 * p1[0]), (0.75 * p0[1] + 0.25 * p1[1])];
          const r = [(0.25 * p0[0] + 0.75 * p1[0]), (0.25 * p0[1] + 0.75 * p1[1])];
          out.push(q);
          out.push(r);
        }
        out.push(pts[pts.length - 1]);
        pts = out;
      }
      return pts;
    }
    const smooth = smoothLatLngs(latlngs, 2);
    // Use smoothed points for bounds so the viewport fits the visible curve
    smooth.forEach(ll => allLatLngs.push(ll));
    const color = polylineColorForMode(seg.mode);
    L.polyline(smooth, {
      color: 'rgba(255,255,255,.35)',
      weight: 10,
      lineCap: 'round',
      lineJoin: 'round',
    }).addTo(rg);
    L.polyline(smooth, {
      color,
      weight: 6,
      opacity: 0.92,
      lineCap: 'round',
      lineJoin: 'round',
    }).addTo(rg);
  });

  rg.addTo(dashMap);
  routeLayer = rg;

  const boundsPts = [...allLatLngs];
  if (origin && origin.coords) boundsPts.push(origin.coords);
  if (dest && dest.coords) boundsPts.push(dest.coords);
  if (boundsPts.length >= 2) {
    dashMap.fitBounds(boundsPts, { padding: [100, 80], animate: true });
  }
}
