import { Heart, Clock, Coins, Leaf, Footprints, Cpu } from 'lucide-react';
import { useTransitStore } from '../store/transit-store';
import { useFavoriteRoutes } from '../hooks/useFavoriteRoutes';
import { formatDuration } from '../utils/time';
import { formatDistance } from '../utils/geo';
import type { Route } from '../utils/algorithms';
import { toast } from 'sonner';

const ROUTE_CONFIG = {
  fastest:  { icon: '⚡', label: 'Fastest',  color: 'var(--accent-amber)', glow: 'color-mix(in oklab, var(--accent-amber) 26%, transparent)' },
  cheapest: { icon: '💰', label: 'Cheapest', color: 'var(--accent-coral)', glow: 'color-mix(in oklab, var(--accent-coral) 26%, transparent)' },
  greenest: { icon: '🌿', label: 'Greenest', color: 'var(--accent-teal)',  glow: 'color-mix(in oklab, var(--accent-teal) 26%, transparent)' },
};

const MODE_ICONS: Record<string, string> = {
  walk: '🚶',
  bus: '🚌',
  tram: '🚊',
  metro: '🚇',
  telepherique: '🚡',
  escalator: '🛗',
};
const ALGO_COLOR: Record<string, string> = {
  'A*': 'var(--accent-teal)', 'Dijkstra': 'var(--accent-coral)', 'Bidirectional': 'var(--accent-blue)',
};

interface RouteCardProps { route: Route; index: number; }

export default function RouteCard({ route, index }: RouteCardProps) {
  const { selectedRoute, selectRoute } = useTransitStore();
  const { addFavorite, removeFavorite, isFavorite } = useFavoriteRoutes();

  const isSelected = selectedRoute?.id === route.id;
  const cfg = ROUTE_CONFIG[route.label] ?? ROUTE_CONFIG.fastest;
  const fav = isFavorite(route.id);

  const modeSequence = route.segments
    .map(s => s.mode)
    .filter((m, i, arr) => i === 0 || arr[i - 1] !== m);

  const savedPct = route.co2SavedVsCarG > 0
    ? Math.round((route.co2SavedVsCarG / (route.summary.totalCo2G + route.co2SavedVsCarG)) * 100)
    : 0;

  const handleFavorite = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (fav) { removeFavorite(route.id); toast('🗑 Route removed'); }
    else      { addFavorite(route);      toast('💚 Route saved');   }
  };

  return (
    <div
      className={`route-card animate-slide-up ${isSelected ? `selected route-${route.label}` : ''}`}
      style={{ animationDelay: `${index * 90}ms` }}
      onClick={() => selectRoute(route)}
      role="article"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && selectRoute(route)}
      aria-selected={isSelected}
    >
      {/* ── Colored top accent bar ── */}
      <div
        className="absolute top-0 left-0 right-0 h-0.5 rounded-t-[14px]"
        style={{ background: `linear-gradient(90deg, ${cfg.color}, transparent)` }}
      />

      {/* ── Header row ── */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center text-base flex-shrink-0"
            style={{ background: `${cfg.color}15`, border: `1px solid ${cfg.color}30` }}
          >
            {cfg.icon}
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-bold" style={{ color: cfg.color }}>
                {cfg.label}
              </span>
              <div
                className="badge"
                style={{
                  background: `${(ALGO_COLOR[route.algorithmUsed] || 'var(--accent-teal)')}15`,
                  color: ALGO_COLOR[route.algorithmUsed] || 'var(--accent-teal)',
                  border: `1px solid ${(ALGO_COLOR[route.algorithmUsed] || 'var(--accent-teal)')}30`,
                  fontSize: '0.55rem',
                }}
              >
                {route.algorithmUsed}
              </div>
            </div>
          </div>
        </div>

        <button
          onClick={handleFavorite}
          className="p-1.5 rounded-lg transition-all hover:bg-white/8"
          aria-label={fav ? 'Remove from favorites' : 'Add to favorites'}
          style={{ color: fav ? 'var(--accent-coral)' : 'var(--text-muted)' }}
        >
          <Heart className="w-3.5 h-3.5" fill={fav ? 'currentColor' : 'none'} />
        </button>
      </div>

      {/* ── Main metrics ── */}
      <div className="flex items-end justify-between mb-3">
        <div>
          <div
            className="text-2xl font-bold leading-none"
            style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--text-primary)' }}
          >
            {formatDuration(route.summary.totalTimeMin)}
          </div>
          <div className="flex items-center gap-3 mt-1.5">
            <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--accent-coral)' }}>
              <Coins className="w-3 h-3" />
              <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>{route.summary.totalCostDzd} DZD</span>
            </span>
            <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--accent-green)' }}>
              <Leaf className="w-3 h-3" />
              <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>{Math.round(route.summary.totalCo2G)}g</span>
            </span>
          </div>
        </div>

        {/* CO2 savings badge */}
        {savedPct > 0 && (
          <div
            className="px-2 py-1 rounded-xl text-center"
            style={{
              background: 'color-mix(in oklab, var(--accent-teal) 10%, transparent)',
              border: '1px solid color-mix(in oklab, var(--accent-teal) 22%, transparent)',
            }}
          >
            <div className="text-xs font-bold" style={{ color: 'var(--accent-teal)' }}>-{savedPct}%</div>
            <div style={{ fontSize: '0.55rem', color: 'var(--text-muted)' }}>vs car</div>
          </div>
        )}
      </div>

      {/* ── Mode sequence + bottom row ── */}
      <div
        className="flex items-center justify-between pt-2"
        style={{ borderTop: '1px solid var(--border-color)' }}
      >
        {/* Mode icons */}
        <div className="flex items-center gap-1">
          {modeSequence.map((mode, i) => (
            <div key={i} className="flex items-center gap-0.5">
              {i > 0 && <span style={{ color: 'var(--text-muted)', fontSize: '0.6rem' }}>›</span>}
              <span className="text-base">{MODE_ICONS[mode]}</span>
            </div>
          ))}
          <span className="text-xs ml-1" style={{ color: 'var(--text-muted)' }}>
            {route.summary.numTransfers}×
          </span>
        </div>

        {/* Walk + nodes */}
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--text-muted)' }}>
            <Footprints className="w-2.5 h-2.5" />
            {formatDistance(route.summary.walkingDistanceM)}
          </span>
          <span
            className="flex items-center gap-1 text-xs"
            style={{ color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '0.6rem' }}
          >
            <Cpu className="w-2.5 h-2.5" />
            {route.nodesExpanded}
          </span>
        </div>
      </div>

      {/* ── Selected indicator pulse ── */}
      {isSelected && (
        <div
          className="absolute inset-0 rounded-[14px] pointer-events-none"
          style={{ boxShadow: `inset 0 0 0 1.5px ${cfg.color}, 0 0 28px ${cfg.glow}` }}
        />
      )}
    </div>
  );
}
