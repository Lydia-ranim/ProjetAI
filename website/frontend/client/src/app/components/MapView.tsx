import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useTransitStore } from '../store/transit-store';
import { type Stop } from '../utils/algiers-graph';
import { haversineDistance } from '../utils/geo';

const ALGIERS_CENTER: [number, number] = [36.7538, 3.0588];
const ALGIERS_BOUNDS: L.LatLngBoundsExpression = [[36.60, 2.80], [36.90, 3.35]];

// Premium dark map tile that complements the teal/navy palette
const DARK_TILES  = 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';
const LIGHT_TILES = 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';
const ATTRIBUTION = '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> © <a href="https://carto.com/">CARTO</a>';

function cssVar(name: string, fallback: string) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

function createStopIcon(type: string, isTransfer?: boolean): L.DivIcon {
  const color =
    type === 'metro' ? cssVar('--accent-blue', '#C6B7E2')
    : type === 'tram' ? cssVar('--accent-amber', '#F2C4CE')
    : type === 'bus' ? cssVar('--accent-coral', '#670627')
    : cssVar('--accent-teal', '#BEEEDB');
  const size  = isTransfer ? 13 : 8;
  const shape = isTransfer
    ? `border-radius: 3px; transform: rotate(45deg);`
    : `border-radius: 50%;`;
  const stroke = cssVar('--bg-void', '#0A1628');

  return L.divIcon({
    html: `<div style="
      width:${size}px; height:${size}px;
      background:${color};
      ${shape}
      border: 2px solid ${stroke};
      box-shadow: 0 0 8px ${color}70, 0 2px 4px rgba(0,0,0,0.5);
      transition: transform 0.15s;
    "></div>`,
    className: '',
    iconSize:   [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function createEndpointIcon(color: string, isStart: boolean): L.DivIcon {
  const innerColor = color;
  const label = isStart ? 'A' : 'B';
  const stroke = cssVar('--bg-void', '#0A1628');
  return L.divIcon({
    html: `
    <div style="position:relative; width:28px; height:28px;">
      <div style="
        position:absolute; inset:0;
        border-radius:50%;
        background:${innerColor};
        opacity:0.18;
        animation:pulse-ring 2s ease-out infinite;
      "></div>
      <div style="
        position:absolute; top:4px; left:4px;
        width:20px; height:20px;
        background:${innerColor};
        border-radius:50%;
        border:2.5px solid ${stroke};
        box-shadow:0 0 16px ${innerColor}90, 0 2px 8px rgba(0,0,0,0.6);
        display:flex; align-items:center; justify-content:center;
        font-family:'Space Mono',monospace;
        font-size:9px; font-weight:700;
        color:${stroke};
      ">${label}</div>
    </div>`,
    className: '',
    iconSize:   [28, 28],
    iconAnchor: [14, 14],
  });
}

export default function MapView() {
  const mapRef          = useRef<HTMLDivElement>(null);
  const mapInstance     = useRef<L.Map | null>(null);
  const tileLayerRef    = useRef<L.TileLayer | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const routeLayerRef   = useRef<L.LayerGroup | null>(null);
  const endpointLayerRef= useRef<L.LayerGroup | null>(null);

  const { startStop, endStop, routes, selectedRoute, isDarkMode, stops, loadStops } = useTransitStore();

  // ── Init map ────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapRef.current || mapInstance.current) return;

    const map = L.map(mapRef.current, {
      center:              ALGIERS_CENTER,
      zoom:                13,
      minZoom:             11,
      maxZoom:             17,
      maxBounds:           ALGIERS_BOUNDS,
      maxBoundsViscosity:  1.0,
      zoomControl:         false,
    });

    L.control.zoom({ position: 'topright' }).addTo(map);
    L.control.scale({ imperial: false, position: 'bottomleft' }).addTo(map);

    const tiles = L.tileLayer(DARK_TILES, {
      attribution: ATTRIBUTION,
      subdomains: 'abcd',
      maxZoom: 19,
    }).addTo(map);
    tileLayerRef.current = tiles;
    const style = document.createElement('style');
    style.innerHTML = `
      .leaflet-tile-pane {
        filter: brightness(0.72) saturate(0.85) contrast(1.08);
      }
    `;
    document.head.appendChild(style);

    const markersLayer = L.layerGroup().addTo(map);
    markersLayerRef.current = markersLayer;

    const panelBg = cssVar('--bg-panel', 'rgba(10, 22, 40, 0.88)');
    const border = cssVar('--border-color', 'rgba(190, 238, 219, 0.16)');
    const muted = cssVar('--text-muted', 'rgba(198, 183, 226, 0.62)');
    const textPrimary = cssVar('--text-primary', 'rgba(190, 238, 219, 0.96)');

    useTransitStore.getState().loadStops();

    routeLayerRef.current   = L.layerGroup().addTo(map);
    endpointLayerRef.current = L.layerGroup().addTo(map);

    map.on('click', (e: L.LeafletMouseEvent) => {
      let nearest: Stop | null = null;
      let minDist = Infinity;
      for (const stop of useTransitStore.getState().stops) {
        const d = haversineDistance({ lat: e.latlng.lat, lng: e.latlng.lng }, stop);
        if (d < minDist && d < 2000) { minDist = d; nearest = stop; }
      }
      if (!nearest) return;

      const state = useTransitStore.getState();
      if (!state.startStop)       state.setStartStop(nearest);
      else if (!state.endStop)    state.setEndStop(nearest);
      else { state.setStartStop(nearest); state.setEndStop(null); }
    });

    mapInstance.current = map;
    return () => { map.remove(); mapInstance.current = null; };
  }, []);

  useEffect(() => {
    tileLayerRef.current?.setUrl(isDarkMode ? DARK_TILES : LIGHT_TILES);
  }, [isDarkMode]);

  // Re-render stop markers whenever stops load from API
  useEffect(() => {
    const layer = markersLayerRef.current;
    if (!layer || stops.length === 0) return;
    layer.clearLayers();
    const panelBg = cssVar('--bg-panel', 'rgba(10, 22, 40, 0.88)');
    const border = cssVar('--border-color', 'rgba(190, 238, 219, 0.16)');
    const muted = cssVar('--text-muted', 'rgba(198, 183, 226, 0.62)');
    const textPrimary = cssVar('--text-primary', 'rgba(190, 238, 219, 0.96)');
    stops.forEach(stop => {
      const icon = createStopIcon(stop.type, stop.isTransfer);
      const marker = L.marker([stop.lat, stop.lng], { icon }).addTo(layer);
      const typeColor =
        stop.type === 'metro' ? cssVar('--accent-blue', '#C6B7E2')
        : stop.type === 'tram' ? cssVar('--accent-amber', '#F2C4CE')
        : stop.type === 'bus' ? cssVar('--accent-coral', '#670627')
        : cssVar('--accent-teal', '#BEEEDB');
      marker.bindTooltip(
        `<div style="font-family:'DM Sans',sans-serif;font-size:12px;background:${panelBg};border:1px solid ${border};border-radius:8px;padding:8px 12px;color:${textPrimary};box-shadow:0 8px 24px rgba(0,0,0,0.5);backdrop-filter:blur(14px);">
          <div style="font-weight:700;margin-bottom:2px;">${stop.name}</div>
          <div style="font-size:10px;color:${typeColor};font-weight:700;text-transform:uppercase;letter-spacing:0.08em;">${stop.type}</div>
        </div>`,
        { className: 'custom-tooltip', direction: 'top', offset: [0, -8] }
      );
    });
  }, [stops]);

  useEffect(() => {
    const layer = endpointLayerRef.current;
    if (!layer) return;
    layer.clearLayers();

    const startColor = cssVar('--accent-teal', '#BEEEDB');
    const endColor = cssVar('--accent-blue', '#C6B7E2');

    if (startStop) {
      L.marker([startStop.lat, startStop.lng], { icon: createEndpointIcon(startColor, true) })
        .bindTooltip(`<b>Start:</b> ${startStop.name}`, { direction: 'top', offset: [0,-14] })
        .addTo(layer);
    }
    if (endStop) {
      L.marker([endStop.lat, endStop.lng], { icon: createEndpointIcon(endColor, false) })
        .bindTooltip(`<b>End:</b> ${endStop.name}`, { direction: 'top', offset: [0,-14] })
        .addTo(layer);
    }

    if (startStop && endStop && mapInstance.current) {
      const bounds = L.latLngBounds([startStop.lat, startStop.lng], [endStop.lat, endStop.lng]);
      mapInstance.current.flyToBounds(bounds.pad(0.35), { duration: 0.9 });
    } else if (startStop && mapInstance.current) {
      mapInstance.current.flyTo([startStop.lat, startStop.lng], 14, { duration: 0.7 });
    }
  }, [startStop, endStop]);

  useEffect(() => {
    const layer = routeLayerRef.current;
    if (!layer) return;
    layer.clearLayers();

    const walk = cssVar('--accent-teal', '#BEEEDB');
    const bus = cssVar('--accent-coral', '#670627');
    const tram = cssVar('--accent-amber', '#F2C4CE');
    const metro = cssVar('--accent-blue', '#C6B7E2');
    const telepherique = cssVar('--accent-amber', '#F2C4CE');
    const escalator = cssVar('--accent-teal', '#BEEEDB');
    const modeColor = (mode: string) =>
      mode === 'metro' ? metro
      : mode === 'tram' ? tram
      : mode === 'bus' ? bus
      : mode === 'telepherique' ? telepherique
      : mode === 'escalator' ? escalator
      : walk;

    routes.forEach(route => {
      const isSelected = selectedRoute?.id === route.id;

      route.segments.forEach(segment => {
        if (segment.polyline.length < 2) return;
        const positions = segment.polyline.map(p => [p[0], p[1]] as L.LatLngExpression);
        const color  = modeColor(segment.mode);
        const weight = segment.mode === 'metro' ? 6 : segment.mode === 'telepherique' ? 5.5 : 5;
        const dash   =
          segment.mode === 'walk' ? '6 10'
          : segment.mode === 'telepherique' ? '1 10'
          : segment.mode === 'escalator' ? '2 7'
          : undefined;

        if (!isSelected) {
          L.polyline(positions, { color, weight: 2.5, opacity: 0.12, dashArray: dash }).addTo(layer);
          return;
        }

        // Glow halo
        L.polyline(positions, { color, weight: weight + 8, opacity: 0.12 }).addTo(layer);
        L.polyline(positions, { color, weight: weight + 3, opacity: 0.25 }).addTo(layer);
        // Main line
        L.polyline(positions, {
          color, weight,
          opacity: 0.95,
          dashArray: dash,
          lineCap: 'round',
          lineJoin: 'round',
        }).addTo(layer);
      });
    });
  }, [routes, selectedRoute]);

  return (
    <div className="h-full w-full relative scanlines" style={{ background: 'var(--bg-void)' }}>
      <div ref={mapRef} className="h-full w-full" />

      <div
        className="absolute bottom-10 right-3 z-[999] glass-panel px-3 py-2.5"
        style={{ fontSize: '0.65rem' }}
      >
        <div className="space-y-1.5">
          {[
            { label: 'Metro', color: 'var(--accent-blue)' },
            { label: 'Tram',  color: 'var(--accent-amber)' },
            { label: 'Bus',   color: 'var(--accent-coral)' },
            { label: 'Téléphérique', color: 'var(--accent-amber)' },
            { label: 'Escalator', color: 'var(--accent-teal)' },
            { label: 'Walk',  color: 'var(--accent-teal)' },
          ].map(l => (
            <div key={l.label} className="flex items-center gap-2">
              <div style={{ width: 18, height: 3, background: `color-mix(in oklab, ${l.color} 88%, transparent)`, borderRadius: 2, boxShadow: `0 0 10px color-mix(in oklab, ${l.color} 35%, transparent)` }} />
              <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{l.label}</span>
            </div>
          ))}
        </div>
      </div>

      <div
        className="absolute inset-0 pointer-events-none z-[1]"
        style={{
          background: 'radial-gradient(ellipse at top-left, rgba(190, 238, 219, 0.045) 0%, transparent 55%), radial-gradient(ellipse at bottom-right, rgba(198, 183, 226, 0.05) 0%, transparent 55%)',
        }}
      />
    </div>
  );
}
