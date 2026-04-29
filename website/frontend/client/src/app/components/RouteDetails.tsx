import { Clock, Coins, Leaf, Footprints, AlertTriangle, ArrowRight, Zap } from 'lucide-react';
import { useTransitStore } from '../store/transit-store';
import { formatDuration } from '../utils/time';
import { formatDistance } from '../utils/geo';
import type { Segment } from '../utils/algorithms';

const MODE_COLORS: Record<string, string> = {
  walk: 'var(--accent-teal)',
  bus: 'var(--accent-coral)',
  tram: 'var(--accent-amber)',
  metro: 'var(--accent-blue)',
  telepherique: 'var(--accent-amber)',
  escalator: 'var(--accent-teal)',
};
const MODE_ICONS: Record<string, string> = {
  walk: '🚶', bus: '🚌', tram: '🚊', metro: '🚇', telepherique: '🚡', escalator: '🛗',
};
const MODE_NAMES: Record<string, string> = {
  walk: 'Walking',
  bus: 'Bus',
  tram: 'Tram',
  metro: 'Metro Ligne 1',
  telepherique: 'Téléphérique',
  escalator: 'Escalator',
};

function SegmentCard({ seg, totalTime, index }: { seg: Segment; totalTime: number; index: number }) {
  const pct = totalTime > 0 ? Math.round((seg.durationMin / totalTime) * 100) : 0;
  const color = MODE_COLORS[seg.mode];

  return (
    <div
      className="mx-3 mb-2 rounded-xl border"
      style={{ background: 'var(--bg-elevated)', borderColor: `${color}30` }}
    >
      <div className="p-3">
        <div className="flex items-start gap-3">
          {/* Mode icon */}
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 text-lg"
            style={{ background: `${color}18`, border: `1px solid ${color}40` }}
          >
            {MODE_ICONS[seg.mode]}
          </div>

          <div className="flex-1 min-w-0">
            {/* Line name */}
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-xs font-semibold" style={{ color }}>
                {seg.lineId || MODE_NAMES[seg.mode]}
              </span>
              {seg.waitMin > 5 && (
                <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: 'var(--accent-amber)20', color: 'var(--accent-amber)', fontSize: '0.6rem' }}>
                  ⏳ Wait {Math.round(seg.waitMin)} min
                </span>
              )}
            </div>

            {/* From → To */}
            <div className="flex items-center gap-1 flex-wrap">
              <span className="text-xs font-medium truncate" style={{ color: 'var(--text-primary)', maxWidth: 110 }}>{seg.fromName}</span>
              <ArrowRight className="w-3 h-3 flex-shrink-0" style={{ color: 'var(--text-muted)' }} />
              <span className="text-xs font-medium truncate" style={{ color: 'var(--text-primary)', maxWidth: 110 }}>{seg.toName}</span>
            </div>

            {/* Times */}
            <div className="text-xs mt-0.5" style={{ color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>
              {seg.departureTime} → {seg.arrivalTime}
            </div>
          </div>

          {/* Duration */}
          <div className="text-right flex-shrink-0">
            <div className="text-sm font-bold" style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--text-primary)' }}>
              {formatDuration(seg.durationMin)}
            </div>
            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {formatDistance(seg.distanceM)}
            </div>
          </div>
        </div>

        {/* Progress + metrics row */}
        <div className="mt-2">
          <div className="h-1 rounded-full overflow-hidden mb-2" style={{ background: 'var(--bg-panel)' }}>
            <div
              className="h-full rounded-full transition-all"
              style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${color}, ${color}88)` }}
            />
          </div>
          <div className="flex gap-3">
            <span className="text-xs flex items-center gap-1" style={{ color: 'var(--accent-coral)' }}>
              <Coins className="w-3 h-3" />{seg.costDzd} DZD
            </span>
            <span className="text-xs flex items-center gap-1" style={{ color: 'var(--accent-green)' }}>
              <Leaf className="w-3 h-3" />{Math.round(seg.co2G)}g CO₂
            </span>
            {seg.mode === 'walk' && (
              <span className="text-xs flex items-center gap-1" style={{ color: 'var(--accent-teal)' }}>
                <Footprints className="w-3 h-3" />{formatDistance(seg.distanceM)}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function RouteDetails() {
  const { selectedRoute } = useTransitStore();

  if (!selectedRoute) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 text-center gap-3">
        <div className="text-3xl opacity-50">🗺️</div>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Select a route to see step-by-step details
        </p>
      </div>
    );
  }

  const { segments, summary, stressLabel, co2SavedVsCarG } = selectedRoute;
  const hasLongWalk = summary.walkingDistanceM > 800;
  const hasManyTransfers = summary.numTransfers >= 3;

  return (
    <div className="flex flex-col pb-4">
      {/* Route header */}
      <div className="p-3 mx-3 mt-3 mb-2 rounded-xl" style={{ background: 'var(--bg-panel)', border: '1px solid var(--border)' }}>
        <div className="grid grid-cols-3 gap-2 text-center">
          <div>
            <div className="text-lg font-bold" style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--text-primary)' }}>
              {formatDuration(summary.totalTimeMin)}
            </div>
            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>Total Time</div>
          </div>
          <div>
            <div className="text-lg font-bold" style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--accent-coral)' }}>
              {summary.totalCostDzd} DZD
            </div>
            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>Cost</div>
          </div>
          <div>
            <div className="text-lg font-bold" style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--accent-green)' }}>
              {Math.round(summary.totalCo2G)}g
            </div>
            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>CO₂</div>
          </div>
        </div>
        <div className="flex items-center justify-between mt-2 pt-2" style={{ borderTop: '1px solid var(--border)' }}>
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            {summary.numTransfers} transfer{summary.numTransfers !== 1 ? 's' : ''} • {formatDistance(summary.walkingDistanceM)} walk
          </span>
          <span
            className="text-xs px-2 py-0.5 rounded-full font-semibold"
            style={{
              background: stressLabel === 'low' ? 'var(--accent-green)20' : stressLabel === 'medium' ? 'var(--accent-amber)20' : 'var(--accent-coral)20',
              color: stressLabel === 'low' ? 'var(--accent-green)' : stressLabel === 'medium' ? 'var(--accent-amber)' : 'var(--accent-coral)',
            }}
          >
            {stressLabel === 'low' ? '😌' : stressLabel === 'medium' ? '😐' : '😤'} {stressLabel} stress
          </span>
        </div>
      </div>

      {/* Warnings */}
      {(hasLongWalk || hasManyTransfers) && (
        <div
          className="mx-3 mb-2 p-2 rounded-lg flex items-start gap-2"
          style={{
            background: 'color-mix(in oklab, var(--accent-amber) 10%, transparent)',
            border: '1px solid color-mix(in oklab, var(--accent-amber) 24%, transparent)',
          }}
        >
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" style={{ color: 'var(--accent-amber)' }} />
          <div className="text-xs" style={{ color: 'var(--accent-amber)' }}>
            {hasLongWalk && `Long walk (${formatDistance(summary.walkingDistanceM)}). `}
            {hasManyTransfers && `${summary.numTransfers} transfers adds complexity.`}
          </div>
        </div>
      )}

      {/* CO2 saved */}
      {co2SavedVsCarG > 0 && (
        <div
          className="mx-3 mb-2 p-2 rounded-lg flex items-center gap-2"
          style={{
            background: 'color-mix(in oklab, var(--accent-teal) 10%, transparent)',
            border: '1px solid color-mix(in oklab, var(--accent-teal) 24%, transparent)',
          }}
        >
          <Zap className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--accent-teal)' }} />
          <span className="text-xs" style={{ color: 'var(--accent-teal)' }}>
            Saves {co2SavedVsCarG}g CO₂ vs driving ({Math.round(co2SavedVsCarG / 12.8)} smartphone charges)
          </span>
        </div>
      )}

      {/* Segments */}
      <div className="text-xs font-semibold px-3 mb-2" style={{ color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        Route Steps
      </div>

      {segments.map((seg, i) => (
        <div key={i}>
          <SegmentCard seg={seg} totalTime={summary.totalTimeMin} index={i} />
          {i < segments.length - 1 && segments[i + 1].mode !== seg.mode && (
            <div className="flex items-center gap-2 px-6 mb-2">
              <div className="w-1 h-4 rounded-full" style={{ background: 'var(--border)', marginLeft: 18 }} />
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Transfer</span>
            </div>
          )}
        </div>
      ))}

      {/* Total summary */}
      <div className="mx-3 mt-2 p-3 rounded-xl" style={{ background: 'var(--bg-panel)', border: '1px solid var(--border)' }}>
        <div className="text-xs font-semibold mb-2" style={{ color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Summary</div>
        <div className="grid grid-cols-2 gap-y-1.5">
          {[
            ['Total Time', formatDuration(summary.totalTimeMin), 'var(--text-primary)'],
            ['Total Cost', `${summary.totalCostDzd} DZD`, 'var(--accent-coral)'],
            ['Total CO₂', `${Math.round(summary.totalCo2G)}g`, 'var(--accent-green)'],
            ['Distance', formatDistance(summary.totalDistanceM), 'var(--accent-blue)'],
            ['Walking', formatDistance(summary.walkingDistanceM), 'var(--accent-teal)'],
            ['Waiting', formatDuration(summary.waitingTimeMin), 'var(--accent-amber)'],
          ].map(([label, val, color]) => (
            <div key={label} className="flex justify-between pr-3">
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{label}</span>
              <span className="text-xs font-semibold" style={{ fontFamily: "'JetBrains Mono', monospace", color }}>{val}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
