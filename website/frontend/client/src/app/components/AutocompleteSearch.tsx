import { useState, useRef, useEffect, useMemo } from 'react';
import { ArrowLeftRight, Navigation } from 'lucide-react';
import { type Stop } from '../utils/algiers-graph';
import { useTransitStore } from '../store/transit-store';
import { haversineDistance } from '../utils/geo';

interface AutocompleteProps {
  label: string;
  value: Stop | null;
  onChange: (stop: Stop | null) => void;
  placeholder: string;
  id: string;
  accentColor: string;
  icon: string;
  recentStops: Stop[];
  allStops: Stop[];
}

function Autocomplete({ label, value, onChange, placeholder, id, accentColor, icon, recentStops, allStops }: AutocompleteProps) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const base = q.length > 0
      ? allStops.filter(s =>
          s.name.toLowerCase().includes(q) ||
          s.district?.toLowerCase().includes(q)
        )
      : [...recentStops, ...allStops];
    const seen = new Set<string>();
    return base.filter(s => {
      if (seen.has(s.id)) return false;
      seen.add(s.id);
      return true;
    }).slice(0, 10);
  }, [query, recentStops]);

  const handleSelect = (stop: Stop) => {
    onChange(stop);
    setQuery('');
    setIsOpen(false);
    setActiveIdx(-1);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIdx(i => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIdx(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && activeIdx >= 0) {
      e.preventDefault();
      handleSelect(filtered[activeIdx]);
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node) &&
          inputRef.current && !inputRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const modeIcon = (type: string) => {
    switch (type) {
      case 'metro': return '🚇';
      case 'tram': return '🚊';
      case 'bus': return '🚌';
      default: return '📍';
    }
  };

  const modeColor = (type: string) => {
    switch (type) {
      case 'metro': return 'var(--accent-blue)';
      case 'tram': return 'var(--accent-amber)';
      case 'bus': return 'var(--accent-coral)';
      default: return 'var(--text-muted)';
    }
  };

  return (
    <div className="relative">
      <div className="flex items-center justify-between mb-1">
        <label className="text-xs block font-semibold tracking-wide" style={{ color: accentColor }}>
          {label}
        </label>
        {recentStops.length > 0 && query.trim().length === 0 && !value && (
          <span className="text-[10px] font-semibold tracking-[0.18em] uppercase" style={{ color: 'var(--text-muted)' }}>
            Recent
          </span>
        )}
      </div>
      {value ? (
        <div
          className="flex items-center gap-2 px-3 py-2.5 rounded-2xl cursor-pointer transition-all hover:opacity-90"
          style={{
            background: 'color-mix(in oklab, var(--bg-elevated) 88%, transparent)',
            border: `1px solid color-mix(in oklab, ${accentColor} 40%, transparent)`,
            boxShadow: `0 0 0 0 ${accentColor}00`,
          }}
          onClick={() => { onChange(null); setIsOpen(true); setTimeout(() => inputRef.current?.focus(), 50); }}
        >
          <span style={{ fontSize: '1.05rem' }}>{modeIcon(value.type)}</span>
          <div className="flex-1 min-w-0">
            <span className="text-sm font-medium truncate block" style={{ color: 'var(--text-primary)' }}>
              {value.name}
            </span>
            <span className="text-xs truncate block" style={{ color: 'var(--text-muted)' }}>
              {value.district} • {value.type.charAt(0).toUpperCase() + value.type.slice(1)}
            </span>
          </div>
          <span className="badge" style={{ background: `${modeColor(value.type)}18`, color: modeColor(value.type), fontSize: '0.6rem' }}>
            {value.type.toUpperCase()}
          </span>
        </div>
      ) : (
        <div
          className="flex items-center gap-2 px-3 py-2.5 rounded-2xl"
          style={{
            border: '1px solid var(--border-color)',
            background: 'color-mix(in oklab, var(--bg-elevated) 78%, transparent)',
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
          }}
        >
          <span className="text-base" style={{ color: accentColor }}>{icon}</span>
          <input
            ref={inputRef}
            id={id}
            type="text"
            className="w-full bg-transparent outline-none text-sm"
            placeholder={placeholder}
            value={query}
            onChange={e => { setQuery(e.target.value); setIsOpen(true); setActiveIdx(-1); }}
            onFocus={() => setIsOpen(true)}
            onKeyDown={handleKeyDown}
            autoComplete="off"
            style={{ color: 'var(--text-primary)' }}
          />
        </div>
      )}

      {isOpen && !value && (
        <div ref={dropdownRef} className="dropdown scrollbar-custom">
          {filtered.map((stop, i) => (
            <div
              key={stop.id}
              className={`dropdown-item ${i === activeIdx ? 'active' : ''}`}
              onClick={() => handleSelect(stop)}
              onMouseEnter={() => setActiveIdx(i)}
            >
              <span style={{ fontSize: '1.1rem' }}>{modeIcon(stop.type)}</span>
              <div className="flex-1 min-w-0">
                <span className="text-sm font-medium block truncate" style={{ color: 'var(--text-primary)' }}>
                  {stop.name}
                </span>
                <span className="text-xs block truncate" style={{ color: 'var(--text-muted)' }}>
                  {stop.district} • {stop.lines.join(', ')}
                </span>
              </div>
              <span className="badge" style={{ background: `${modeColor(stop.type)}18`, color: modeColor(stop.type), fontSize: '0.6rem' }}>
                {stop.type.toUpperCase()}
              </span>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="p-4 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
              No stops found
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const RECENTS_KEY = 'lyhlyh_recent_stop_ids';
function loadRecentIds(): string[] {
  try {
    const raw = localStorage.getItem(RECENTS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter(x => typeof x === 'string') : [];
  } catch {
    return [];
  }
}

function saveRecentId(id: string) {
  const next = [id, ...loadRecentIds().filter(x => x !== id)].slice(0, 6);
  try {
    localStorage.setItem(RECENTS_KEY, JSON.stringify(next));
  } catch {}
}

export default function AutocompleteSearch() {
  const { startStop, endStop, setStartStop, setEndStop, swapStops, stops } = useTransitStore();

  const recentStops = useMemo(() => {
    const ids = loadRecentIds();
    const byId = new Map(stops.map(s => [s.id, s]));
    return ids.map(id => byId.get(id)).filter(Boolean) as Stop[];
  }, [startStop, endStop, stops]);

  const handleLocate = () => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const userLoc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        let nearest = stops[0];
        let minDist = Infinity;
        for (const stop of stops) {
          const d = haversineDistance(userLoc, stop);
          if (d < minDist) { minDist = d; nearest = stop; }
        }
        setStartStop(nearest);
      },
      () => {},
      { enableHighAccuracy: true }
    );
  };

  return (
    <div className="space-y-2">
      <div className="flex items-start gap-2">
        <div className="flex-1 space-y-2">
          <Autocomplete
            label="Starting Point"
            value={startStop}
            onChange={(s) => { setStartStop(s); if (s) saveRecentId(s.id); }}
            placeholder="Search or choose a recent stop…"
            id="search-from"
            accentColor="var(--accent-teal)"
            icon="📍"
            recentStops={recentStops}
            allStops={stops}
          />
          <Autocomplete
            label="Destination"
            value={endStop}
            onChange={(s) => { setEndStop(s); if (s) saveRecentId(s.id); }}
            placeholder="Where are you going…"
            id="search-to"
            accentColor="var(--accent-blue)"
            icon="🎯"
            recentStops={recentStops}
            allStops={stops}
          />
        </div>
        <div className="flex flex-col gap-1 pt-5">
          <button
            onClick={swapStops}
            className="p-2 rounded-lg transition-all hover:bg-white/5 active:scale-90"
            style={{ color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }}
            aria-label="Swap stops"
          >
            <ArrowLeftRight className="w-4 h-4" />
          </button>
          <button
            onClick={handleLocate}
            className="p-2 rounded-lg transition-all hover:bg-white/5 active:scale-90"
            style={{ color: 'var(--accent-teal)', border: '1px solid var(--border-color)' }}
            aria-label="Use current location"
          >
            <Navigation className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
