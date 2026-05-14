/* LYHLYH Google Maps rendering. No route computation happens here. */

let dashMap = null;
let heroMap = null;
let expMap = null;
let dashMapInited = false;
let heroMapInited = false;
let originMarker = null;
let destMarker = null;
let routeLayer = [];
let networkVisible = false;
let networkLayerGroup = [];
let heroRoutePreviewLayer = [];
let stationMarkers = [];
let stationCluster = null;
let currentLocationMarker = null;
/*
 * ARCHITECTURAL NOTE — Google Directions API (DISPLAY-ONLY)
 * ─────────────────────────────────────────────────────────
 * This module uses google.maps.DirectionsService EXCLUSIVELY for
 * visual polyline refinement of bus / walk segments.  It is NEVER
 * used for routing decisions, path selection, or cost computation.
 *
 * Why keep it:
 *   Bus and walk segments from the backend contain only stop-to-stop
 *   straight lines.  DirectionsService provides a street-level path
 *   that follows real roads, giving a more accurate visual preview.
 *
 * What it does NOT do:
 *   - It does not select, rank, or filter routes.
 *   - It does not influence travel time, cost, or CO₂ computations.
 *   - All routing decisions are made by the LYHLYH custom engine
 *     (UCS, A*, Bidirectional) in the FastAPI backend.
 *
 * The flag  googleMapsConfig.visualDirections  (set via .env)
 * can disable this behavior entirely.  When disabled, the backend's
 * straight-line coordinates are drawn directly.
 */
let directionsService = null;
let networkLinesCache = null;

const ALG_CENTER = [36.737, 3.086];
const ALG_BOUNDS = [[36.48, 2.75], [36.98, 3.55]];

let clickMode = 'origin';

function latLngLiteral(coords) {
  return { lat: Number(coords[0]), lng: Number(coords[1]) };
}

function clearGoogleItems(items) {
  (items || []).forEach(item => {
    if (item && typeof item.setMap === 'function') item.setMap(null);
  });
}

function polylineColorForMode(mode) {
  const k = normalizeModeKey(mode);
  return MODE_LINE_COLOR_HEX[k] || MODE_LINE_COLOR_HEX.default;
}

function markerIcon(color, label) {
  const safe = encodeURIComponent(label || '');
  const svg = `
  <svg xmlns="http://www.w3.org/2000/svg" width="38" height="44" viewBox="0 0 38 44">
    <path d="M19 43S4 27.8 4 17.5C4 8.4 10.7 2 19 2s15 6.4 15 15.5C34 27.8 19 43 19 43z" fill="${color}" stroke="white" stroke-width="2"/>
    <text x="19" y="22" font-family="Arial" font-size="10" font-weight="700" fill="white" text-anchor="middle">${safe.slice(0, 2).toUpperCase()}</text>
  </svg>`;
  return {
    url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`,
    scaledSize: new google.maps.Size(38, 44),
    anchor: new google.maps.Point(19, 43),
  };
}

function modeMarkerIcon(mode) {
  return markerIcon(TYPE_COLOR[normalizeModeKey(mode)] || TYPE_COLOR.default, '');
}

function createMap(elId, options = {}) {
  const el = document.getElementById(elId);
  if (!el || !window.google || !google.maps) return null;
  const map = new google.maps.Map(el, {
    center: googleMapsCenterLiteral(),
    zoom: options.zoom || 12,
    mapTypeControl: false,
    streetViewControl: false,
    fullscreenControl: false,
    clickableIcons: true,
    restriction: {
      latLngBounds: googleMapsBoundsLiteral(),
      strictBounds: false,
    },
    styles: [
      { featureType: 'poi', elementType: 'labels', stylers: [{ visibility: 'off' }] },
      { featureType: 'transit.station', elementType: 'labels', stylers: [{ visibility: 'on' }] },
    ],
    ...options,
  });
  return map;
}

function initHeroMap() {
  if (heroMapInited) return;
  heroMapInited = true;
  heroMap = createMap('hero-map', {
    zoom: 12,
    zoomControl: false,
    gestureHandling: 'cooperative',
    disableDefaultUI: true,
  });
  if (!heroMap) return;
  drawNetwork(heroMap);
  refreshHeroSampleRoute();
}

function refreshHeroMapAfterStops() {
  if (!heroMap) return;
  clearGoogleItems(heroRoutePreviewLayer);
  heroRoutePreviewLayer = [];
  drawNetwork(heroMap);
  refreshHeroSampleRoute();
}

function refreshHeroSampleRoute() {
  if (!heroMap || STATIONS.length < 2) return;
  clearGoogleItems(heroRoutePreviewLayer);
  heroRoutePreviewLayer = [];
  const a = STATIONS[0];
  const b = STATIONS[Math.min(50, STATIONS.length - 1)];
  const path = [latLngLiteral(a.coords), latLngLiteral(b.coords)];
  const shadow = new google.maps.Polyline({
    map: heroMap,
    path,
    strokeColor: '#ffffff',
    strokeOpacity: 0.55,
    strokeWeight: 10,
  });
  const line = new google.maps.Polyline({
    map: heroMap,
    path,
    strokeColor: '#5C6BC0',
    strokeOpacity: 0.95,
    strokeWeight: 5,
  });
  const start = new google.maps.Marker({ map: heroMap, position: path[0], icon: markerIcon('#3DAB82', 'A') });
  const end = new google.maps.Marker({ map: heroMap, position: path[1], icon: markerIcon('#8A0A35', 'B') });
  heroRoutePreviewLayer.push(shadow, line, start, end);
}

function initDashMap() {
  if (dashMapInited) return;
  dashMapInited = true;
  dashMap = createMap('dash-map', { zoom: 12, zoomControl: true });
  if (!dashMap) return;
  directionsService = new google.maps.DirectionsService();
  refreshDashStationMarkers();
  dashMap.addListener('click', onMapClick);
  showCurrentLocation(false);
}

function refreshDashStationMarkers() {
  if (!dashMap) return;
  if (stationCluster && typeof stationCluster.clearMarkers === 'function') stationCluster.clearMarkers();
  clearGoogleItems(stationMarkers);
  stationMarkers = addStationMarkers(dashMap);
  if (window.markerClusterer && markerClusterer.MarkerClusterer) {
    stationCluster = new markerClusterer.MarkerClusterer({ map: dashMap, markers: stationMarkers });
  }
}

async function toggleNetwork() {
  networkVisible = !networkVisible;
  const ind = document.getElementById('network-indicator');
  const lbl = document.getElementById('network-lbl');
  if (networkVisible) {
    networkLayerGroup = await drawNetworkLines(dashMap);
    if (ind) ind.style.background = '#BEEEDB';
    if (lbl) lbl.textContent = t('map.hide-network');
  } else {
    clearGoogleItems(networkLayerGroup);
    networkLayerGroup = [];
    if (ind) ind.style.background = '#ccc';
    if (lbl) lbl.textContent = t('map.show-network');
  }
}

function stopInfoHtml(s) {
  const safeId = String(s.id).replace(/'/g, "\\'");
  return `
    <div style="font-family:'DM Sans',sans-serif;padding:4px;min-width:170px">
      <div style="font-weight:700;margin-bottom:4px">${s.name}</div>
      <div style="font-size:.78rem;color:#666;margin-bottom:8px">${s.line}</div>
      <button onclick="selectStation('origin','${safeId}')" style="margin-right:6px;padding:5px 10px;border-radius:6px;background:#E6F4EA;color:#137333;border:1px solid #C8E6C9;cursor:pointer;font-size:.75rem;font-weight:700">${t('map.origin-btn')}</button>
      <button onclick="selectStation('dest','${safeId}')" style="padding:5px 10px;border-radius:6px;background:#FCE8E6;color:#A50E0E;border:1px solid #F4C7C3;cursor:pointer;font-size:.75rem;font-weight:700">${t('map.dest-btn')}</button>
    </div>`;
}

function addStationMarkers(map) {
  const info = new google.maps.InfoWindow();
  return STATIONS.map(s => {
    const marker = new google.maps.Marker({
      map,
      position: latLngLiteral(s.coords),
      title: s.name,
      icon: modeMarkerIcon(s.type),
      optimized: true,
    });
    marker.addListener('click', () => {
      info.setContent(stopInfoHtml(s));
      info.open(map, marker);
    });
    return marker;
  });
}

async function drawNetworkLines(map) {
  if (!map) return [];
  if (!networkLinesCache) {
    try {
      networkLinesCache = await fetchNetworkLines(2500);
    } catch (err) {
      console.warn('LYHLYH: network overlay failed', err);
      networkLinesCache = [];
    }
  }

  return networkLinesCache
    .filter(line => Array.isArray(line.path) && line.path.length >= 2)
    .map(line => new google.maps.Polyline({
      map,
      path: line.path.map(p => ({ lat: Number(p[0]), lng: Number(p[1]) })),
      strokeColor: line.color || polylineColorForMode(line.mode),
      strokeOpacity: 0.38,
      strokeWeight: normalizeModeKey(line.mode) === 'bus' ? 2 : 3,
      zIndex: 5,
    }));
}

function drawNetwork(map) {
  if (!map) return;
  addStationMarkers(map);
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
  const lat = e.latLng.lat();
  const lng = e.latLng.lng();
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
    highlightNearestStop(stop);
  } else {
    const lbl = clickMode === 'origin' ? t('map.custom-origin') : t('map.custom-dest');
    const synthetic = {
      id: null,
      name: `${lat.toFixed(5)}, ${lng.toFixed(5)}`,
      short: 'Point',
      coords: [lat, lng],
      type: 'walk',
      line: '-',
      icon: 'pin',
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
  if (!dashMap || !window.google) return;
  const position = latLngLiteral(coords);
  const marker = new google.maps.Marker({
    map: dashMap,
    position,
    title: label,
    icon: markerIcon(which === 'origin' ? '#3DAB82' : '#8A0A35', which === 'origin' ? 'A' : 'B'),
    zIndex: 1000,
  });
  if (which === 'origin') {
    if (originMarker) originMarker.setMap(null);
    originMarker = marker;
    dashMap.panTo(position);
    dashMap.setZoom(Math.max(dashMap.getZoom(), 13));
  } else {
    if (destMarker) destMarker.setMap(null);
    destMarker = marker;
    if (originMarker) {
      const bounds = new google.maps.LatLngBounds();
      bounds.extend(originMarker.getPosition());
      bounds.extend(destMarker.getPosition());
      dashMap.fitBounds(bounds, 80);
    } else {
      dashMap.panTo(position);
      dashMap.setZoom(Math.max(dashMap.getZoom(), 13));
    }
  }
}

function swapPoints() {
  const oi = document.getElementById('origin-input');
  const di = document.getElementById('dest-input');
  [oi.value, di.value] = [di.value, oi.value];
  [acSel.origin, acSel.dest] = [acSel.dest, acSel.origin];
  if (acSel.origin) placeMarker('origin', acSel.origin.coords, acSel.origin.name);
  if (acSel.dest) placeMarker('dest', acSel.dest.coords, acSel.dest.name);
}

function shouldUseGoogleVisualPath(seg) {
  if (!googleMapsConfig?.visualDirections || !directionsService) return false;
  const mode = normalizeModeKey(seg.mode);
  return mode === 'bus' || mode === 'walk';
}

function travelModeForSegment(seg) {
  const mode = normalizeModeKey(seg.mode);
  if (mode === 'walk') return google.maps.TravelMode.WALKING;
  return google.maps.TravelMode.DRIVING;
}

/**
 * DISPLAY-ONLY — Refine visual polyline via Google Directions.
 *
 * This function is used SOLELY for rendering smoother street-level
 * paths on the map for bus/walk segments.  It does NOT participate
 * in any routing decision — origin/destination/stops are already
 * decided by the LYHLYH backend engine before this call runs.
 *
 * If the call fails, we gracefully fall back to the backend's
 * straight-line coordinates.  The route remains unchanged.
 */
function requestVisualDirections(seg, fallbackPath) {
  if (!shouldUseGoogleVisualPath(seg) || fallbackPath.length < 2) return Promise.resolve(null);
  const origin = fallbackPath[0];
  const destination = fallbackPath[fallbackPath.length - 1];
  const waypoints = fallbackPath
    .slice(1, -1)
    .filter((_, i, arr) => arr.length <= 8 || i % Math.ceil(arr.length / 8) === 0)
    .slice(0, 8)
    .map(location => ({ location, stopover: false }));

  return new Promise(resolve => {
    directionsService.route(
      {
        origin,
        destination,
        waypoints,
        travelMode: travelModeForSegment(seg),
        optimizeWaypoints: false,
        provideRouteAlternatives: false,
      },
      (response, status) => {
        if (status !== google.maps.DirectionsStatus.OK || !response?.routes?.[0]?.overview_path) {
          // Visual fallback failed — route is unaffected, we draw straight lines
          console.warn('LYHLYH: visual Google path fallback used', status);
          resolve(null);
          return;
        }
        resolve(response.routes[0].overview_path.map(p => ({ lat: p.lat(), lng: p.lng() })));
      }
    );
  });
}

function addSegmentPolyline(path, seg, idx, bounds) {
  path.forEach(p => bounds.extend(p));
  const color = seg.display?.color || polylineColorForMode(seg.mode);
  const shadow = new google.maps.Polyline({
    map: dashMap,
    path,
    strokeColor: '#ffffff',
    strokeOpacity: 0.55,
    strokeWeight: 11,
    zIndex: 20 + idx,
  });
  const line = new google.maps.Polyline({
    map: dashMap,
    path,
    strokeColor: color,
    strokeOpacity: 0.95,
    strokeWeight: seg.display?.isTransfer ? 4 : 6,
    zIndex: 30 + idx,
    icons: seg.display?.isTransfer
      ? [{ icon: { path: 'M 0,-1 0,1', strokeOpacity: 1, scale: 3 }, offset: '0', repeat: '14px' }]
      : undefined,
  });
  routeLayer.push(shadow, line);
}

async function drawRouteSegments(origin, dest, segments) {
  if (!dashMap || !window.google) return;
  clearGoogleItems(routeLayer);
  routeLayer = [];

  const bounds = new google.maps.LatLngBounds();
  let hasPoint = false;

  for (const [idx, seg] of (segments || []).entries()) {
    const raw = seg.polyline || [];
    if (raw.length < 2) continue;
    const path = raw.map(p => ({ lat: Number(p[0]), lng: Number(p[1]) }));
    const visualPath = await requestVisualDirections(seg, path);
    addSegmentPolyline(visualPath || path, seg, idx, bounds);
    hasPoint = true;

    const transfer = seg.display?.isTransfer || idx > 0;
    if (transfer && seg.markers?.start?.position) {
      routeLayer.push(new google.maps.Marker({
        map: dashMap,
        position: seg.markers.start.position,
        title: seg.fromName,
        icon: markerIcon('#5f6368', 'T'),
        zIndex: 900,
      }));
    }
  }

  if (origin && origin.coords) {
    bounds.extend(latLngLiteral(origin.coords));
    hasPoint = true;
  }
  if (dest && dest.coords) {
    bounds.extend(latLngLiteral(dest.coords));
    hasPoint = true;
  }
  if (hasPoint) dashMap.fitBounds(bounds, 80);
}

function highlightNearestStop(stop) {
  if (!dashMap || !stop) return;
  const marker = new google.maps.Marker({
    map: dashMap,
    position: latLngLiteral(stop.coords),
    title: stop.name,
    icon: markerIcon('#FFD54F', 'N'),
    zIndex: 1100,
  });
  routeLayer.push(marker);
  setTimeout(() => marker.setMap(null), 3500);
}

function showCurrentLocation(panToUser = true) {
  if (!dashMap || !navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition(
    pos => {
      const position = { lat: pos.coords.latitude, lng: pos.coords.longitude };
      if (currentLocationMarker) currentLocationMarker.setMap(null);
      currentLocationMarker = new google.maps.Marker({
        map: dashMap,
        position,
        title: 'Current location',
        icon: markerIcon('#1A73E8', 'ME'),
        zIndex: 1200,
      });
      if (panToUser) dashMap.panTo(position);
    },
    () => {},
    { enableHighAccuracy: true, timeout: 5000, maximumAge: 60000 }
  );
}
