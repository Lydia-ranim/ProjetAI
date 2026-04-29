import { useMemo } from 'react';
import { Clock, Coins, Footprints, Bus, Train, Zap, Leaf } from 'lucide-react';
import { useTransitStore } from '../store/transit-store';
import { formatDuration } from '../utils/time';
import { formatDistance } from '../utils/geo';

const MODE_COLORS: Record<string, string> = {
  walk:  'var(--accent-teal)',
  bus:   'var(--accent-coral)',
  tram:  'var(--accent-amber)',
  metro: 'var(--accent-blue)',
};
const MODE_ICONS: Record<string, string> = {
  walk: '🚶', bus: '🚌', tram: '🚊', metro: '🚇',
};

function StatCard({
  icon, label, value, sub, accentColor,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  accentColor: string;
}) {
  return (
    <div
      className="stat-card animate-scale-in"
      style={{ '--card-accent': accentColor } as React.CSSProperties}
    >
      <div className="flex items-start justify-between mb-2">
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center"
          style={{ background: `${accentColor}15`, border: `1px solid ${accentColor}25` }}
        >
          {icon}
        </div>
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{label}</span>
      </div>
      <div
        className="text-xl font-bold"
        style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--text-primary)', lineHeight: 1.2 }}
      >
        {value}
      </div>
      {sub && (
        <div className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{sub}</div>
      )}
    </div>
  );
}

export default function StatsDashboard() {
  const { routes } = useTransitStore();

  const stats = useMemo(() => {
    if (!routes.length) return null;

    const totalTimes  = routes.map(r => r.summary.totalTimeMin);
    const totalCosts  = routes.map(r => r.summary.totalCostDzd);
    const totalCo2    = routes.map(r => r.summary.totalCo2G);
    const totalDist   = routes.map(r => r.summary.totalDistanceM);

    const avgTime = totalTimes.reduce((a, b) => a + b, 0) / totalTimes.length;
    const minTime = Math.min(...totalTimes);
    const maxTime = Math.max(...totalTimes);
    const avgCost = totalCosts.reduce((a, b) => a + b, 0) / totalCosts.length;
    const avgCo2  = totalCo2.reduce((a, b) => a + b, 0) / totalCo2.length;

    // Mode usage across all routes
    const modeDistances: Record<string, number> = { walk: 0, bus: 0, tram: 0, metro: 0 };
    let totalSegmentDist = 0;
    routes.forEach(r => r.segments.forEach(s => {
      modeDistances[s.mode] = (modeDistances[s.mode] || 0) + s.distanceM;
      totalSegmentDist += s.distanceM;
    }));

    const modePcts = Object.entries(modeDistances).map(([mode, dist]) => ({
      mode,
      pct: totalSegmentDist > 0 ? Math.round((dist / totalSegmentDist) * 100) : 0,
      dist,
    })).filter(m => m.pct > 0).sort((a, b) => b.pct - a.pct);

    // CO2 vs car
    const carCo2 = routes.length > 0
      ? (routes[0].summary.totalDistanceM / 1000) * 192
      : 0;
    const savedPct = carCo2 > 0 && avgCo2 < carCo2
      ? Math.round((1 - avgCo2 / carCo2) * 100)
      : 0;

    return { avgTime, minTime, maxTime, avgCost, avgCo2, savedPct, modePcts, totalCo2, totalCosts, totalDist };
  }, [routes]);

  if (!stats) return null;

  return (
    <div className="space-y-4">
      <div className="section-label">
        <Zap className="w-3 h-3" style={{ color: 'var(--accent-amber)', flexShrink: 0 }} />
        Journey Statistics
      </div>

      {/* ─── Key Stats Grid ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-2">
        <StatCard
          icon={<Clock className="w-3.5 h-3.5" style={{ color: 'var(--accent-amber)' }} />}
          label="Avg Time"
          value={formatDuration(stats.avgTime)}
          sub={`${formatDuration(stats.minTime)} – ${formatDuration(stats.maxTime)}`}
          accentColor="var(--accent-amber)"
        />
        <StatCard
          icon={<Coins className="w-3.5 h-3.5" style={{ color: 'var(--accent-coral)' }} />}
          label="Avg Cost"
          value={`${Math.round(stats.avgCost)} DZD`}
          sub={`Min: ${Math.min(...stats.totalCosts)} DZD`}
          accentColor="var(--accent-coral)"
        />
        <StatCard
          icon={<Leaf className="w-3.5 h-3.5" style={{ color: 'var(--accent-green)' }} />}
          label="Avg CO₂"
          value={`${Math.round(stats.avgCo2)}g`}
          sub={stats.savedPct > 0 ? `-${stats.savedPct}% vs car` : undefined}
          accentColor="var(--accent-green)"
        />
        <StatCard
          icon={<Footprints className="w-3.5 h-3.5" style={{ color: 'var(--accent-teal)' }} />}
          label="Avg Distance"
          value={formatDistance(stats.totalDist.reduce((a, b) => a + b, 0) / stats.totalDist.length)}
          accentColor="var(--accent-teal)"
        />
      </div>

      {/* ─── Locomotion Breakdown ─────────────────────────────────────────── */}
      <div
        className="p-3 rounded-xl"
        style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-color)' }}
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-1.5">
            <Bus className="w-3.5 h-3.5" style={{ color: 'var(--accent-blue)' }} />
            <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
              Locomotion Usage
            </span>
          </div>
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>by distance</span>
        </div>

        {/* Stacked bar */}
        <div className="h-5 rounded-lg overflow-hidden flex mb-3" style={{ background: 'var(--bg-panel)' }}>
          {stats.modePcts.map(({ mode, pct }) => (
            <div
              key={mode}
              className="h-full transition-all"
              style={{ width: `${pct}%`, background: MODE_COLORS[mode] || '#888', opacity: 0.85 }}
              title={`${mode}: ${pct}%`}
            />
          ))}
        </div>

        {/* Mode bars */}
        <div className="space-y-2">
          {stats.modePcts.map(({ mode, pct, dist }) => {
            const color = MODE_COLORS[mode] || '#888';
            return (
              <div key={mode}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm leading-none">{MODE_ICONS[mode]}</span>
                    <span className="text-xs capitalize font-medium" style={{ color: 'var(--text-secondary)' }}>{mode}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs" style={{ color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>
                      {formatDistance(dist)}
                    </span>
                    <span className="text-xs font-bold" style={{ color, fontFamily: "'JetBrains Mono', monospace", minWidth: 32, textAlign: 'right' }}>
                      {pct}%
                    </span>
                  </div>
                </div>
                <div className="mode-stat-bar">
                  <div
                    className="mode-stat-fill animate-fill"
                    style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${color}, ${color}99)` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ─── Price Breakdown ──────────────────────────────────────────────── */}
      <div
        className="p-3 rounded-xl"
        style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-color)' }}
      >
        <div className="flex items-center gap-1.5 mb-3">
          <Coins className="w-3.5 h-3.5" style={{ color: 'var(--accent-coral)' }} />
          <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
            Price Comparison
          </span>
        </div>

        <div className="space-y-2">
          {routes.map((r) => {
            const maxCost = Math.max(...routes.map(x => x.summary.totalCostDzd), 1);
            const pct = Math.round((r.summary.totalCostDzd / maxCost) * 100);
            const colors: Record<string, string> = { fastest: 'var(--accent-amber)', cheapest: 'var(--accent-coral)', greenest: 'var(--accent-teal)' };
            const icons: Record<string, string> = { fastest: '⚡', cheapest: '💰', greenest: '🌿' };
            const color = colors[r.label] || 'var(--accent-blue)';
            return (
              <div key={r.id}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs capitalize" style={{ color: 'var(--text-secondary)' }}>
                    {icons[r.label]} {r.label}
                  </span>
                  <span className="text-xs font-bold" style={{ color, fontFamily: "'JetBrains Mono', monospace" }}>
                    {r.summary.totalCostDzd} DZD
                  </span>
                </div>
                <div className="mode-stat-bar">
                  <div className="mode-stat-fill" style={{ width: `${pct}%`, background: color }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
