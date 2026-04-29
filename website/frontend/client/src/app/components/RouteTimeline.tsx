import { useTransitStore } from '../store/transit-store';
import type { TimelineEvent } from '../utils/algorithms';

const EVENT_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
  depart:   { icon: '🟢', color: 'var(--accent-teal)',  label: 'Depart'   },
  arrive:   { icon: '🏁', color: 'var(--accent-amber)', label: 'Arrive'   },
  transfer: { icon: '🔄', color: 'var(--accent-blue)',  label: 'Transfer' },
  walk:     { icon: '🚶', color: 'var(--accent-teal)',  label: 'Walk'     },
  ride:     { icon: '→',  color: 'var(--text-secondary)', label: 'Ride'   },
  wait:     { icon: '⏳', color: 'var(--accent-amber)', label: 'Wait'     },
};

const MODE_COLORS: Record<string, string> = {
  walk: 'var(--accent-teal)',
  bus: 'var(--accent-coral)',
  tram: 'var(--accent-amber)',
  metro: 'var(--accent-blue)',
};

function TimelineNode({ event, isLast }: { event: TimelineEvent; isLast: boolean }) {
  const cfg = EVENT_CONFIG[event.type] || EVENT_CONFIG.ride;
  const modeColor = event.mode ? MODE_COLORS[event.mode] || cfg.color : cfg.color;
  const isDuration = event.type === 'walk' || event.type === 'ride' || event.type === 'wait';

  return (
    <div className="flex gap-3">
      {/* Timeline rail */}
      <div className="flex flex-col items-center">
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center text-xs flex-shrink-0 font-bold"
          style={{
            background: `${modeColor}18`,
            border: `2px solid ${modeColor}60`,
            color: modeColor,
            fontSize: '0.75rem',
          }}
        >
          {event.icon || cfg.icon}
        </div>
        {!isLast && (
          <div
            className="w-0.5 flex-1 mt-1"
            style={{
              minHeight: 20,
              background: isDuration
                ? `linear-gradient(180deg, ${modeColor}60, ${modeColor}20)`
                : 'var(--border)',
            }}
          />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 pb-4 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold truncate" style={{ color: 'var(--text-primary)' }}>
              {event.stopName}
            </div>
            {event.lineId && (
              <div className="text-xs mt-0.5" style={{ color: modeColor }}>
                {event.lineId}
              </div>
            )}
            {event.durationMin !== undefined && (
              <div
                className="inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded-full text-xs"
                style={{ background: `${modeColor}15`, color: modeColor }}
              >
                {event.type === 'wait'
                  ? `Wait ${Math.round(event.durationMin)} min`
                  : event.type === 'walk'
                  ? `Walk ${Math.round(event.durationMin)} min`
                  : `${Math.round(event.durationMin)} min ride`}
              </div>
            )}
          </div>
          <div
            className="text-xs flex-shrink-0 font-mono"
            style={{ color: 'var(--accent-teal)', fontFamily: "'JetBrains Mono', monospace" }}
          >
            {event.time}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function RouteTimeline() {
  const { selectedRoute } = useTransitStore();

  if (!selectedRoute) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 text-center gap-3">
        <div className="text-3xl opacity-50">🕐</div>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Find a route to see the departure timeline
        </p>
      </div>
    );
  }

  const { timeline, segments } = selectedRoute;

  return (
    <div className="p-4">
      {/* Live journey header */}
      <div
        className="rounded-xl p-3 mb-4 flex items-center gap-3"
        style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
      >
        <div className="text-xl">🚀</div>
        <div>
          <div className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>
            {segments[0]?.fromName} → {segments[segments.length - 1]?.toName}
          </div>
          <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Depart {segments[0]?.departureTime} · Arrive {segments[segments.length - 1]?.arrivalTime}
          </div>
        </div>
      </div>

      {/* Timeline events */}
      <div>
        {timeline.map((event, i) => (
          <TimelineNode
            key={i}
            event={event}
            isLast={i === timeline.length - 1}
          />
        ))}
      </div>

      {/* Mode legend */}
      <div
        className="mt-4 p-3 rounded-xl"
        style={{ background: 'var(--bg-panel)', border: '1px solid var(--border)' }}
      >
        <div className="text-xs font-semibold mb-2" style={{ color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
          Color Key
        </div>
        <div className="flex flex-wrap gap-2">
          {Object.entries(MODE_COLORS).map(([mode, color]) => (
            <div key={mode} className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full" style={{ background: color }} />
              <span className="text-xs capitalize" style={{ color: 'var(--text-muted)' }}>{mode}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
