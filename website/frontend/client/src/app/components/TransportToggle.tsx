import { useTransitStore } from '../store/transit-store';

const MODES = [
  { key: 'walk' as const, icon: '🚶', label: 'Walk', tip: '5 km/h • Free • 0 CO₂' },
  { key: 'bus' as const, icon: '🚌', label: 'Bus', tip: '18 km/h • 50 DZD • 68g/km' },
  { key: 'tram' as const, icon: '🚊', label: 'Tram', tip: '20 km/h • 50 DZD • 4g/km' },
  { key: 'metro' as const, icon: '🚇', label: 'Metro', tip: '35 km/h • 70 DZD • 2.5g/km' },
  { key: 'telepherique' as const, icon: '🚡', label: 'Teleph.', tip: '14 km/h • 100 DZD • 3g/km' },
  { key: 'escalator' as const, icon: '🛗', label: 'Escal.', tip: 'Hub assist • Free • 0 CO₂' },
];

const MODE_COLORS: Record<string, string> = {
  walk: 'var(--accent-teal)',
  bus: 'var(--accent-coral)',
  tram: 'var(--accent-amber)',
  metro: 'var(--accent-blue)',
  telepherique: 'var(--accent-blue)',
  escalator: 'var(--accent-amber)',
};

export default function TransportToggle() {
  const { enabledModes, toggleMode } = useTransitStore();

  return (
    <div>
      <label className="text-xs mb-2 block" style={{ color: 'var(--text-secondary)' }}>
        TRANSPORT MODES
      </label>
      <div className="grid grid-cols-3 gap-2">
        {MODES.map(m => {
          const active = enabledModes[m.key];
          const color = MODE_COLORS[m.key];
          return (
            <button
              key={m.key}
              onClick={() => toggleMode(m.key)}
              className={`mode-toggle ${active ? 'active' : 'inactive'}`}
              style={{ ['--mode-color' as any]: color }}
              title={m.tip}
              aria-label={`Toggle ${m.label}`}
              aria-pressed={active}
            >
              <span style={{ fontSize: '1.1rem' }}>{m.icon}</span>
              <span className="text-xs font-medium" style={{ color: active ? color : 'var(--text-muted)', textDecoration: active ? 'none' : 'line-through' }}>
                {m.label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
