import { useCallback, useRef } from 'react';
import { Clock, Coins, Leaf } from 'lucide-react';
import { useTransitStore } from '../store/transit-store';

const PRESETS = [
  { key: 'fastest' as const, label: '⚡ Fastest', w: { time: 0.8, cost: 0.1, co2: 0.1 } },
  { key: 'cheapest' as const, label: '💰 Cheapest', w: { time: 0.1, cost: 0.8, co2: 0.1 } },
  { key: 'greenest' as const, label: '🌿 Greenest', w: { time: 0.1, cost: 0.1, co2: 0.8 } },
  { key: 'balanced' as const, label: '⚖️ Balanced', w: { time: 0.34, cost: 0.33, co2: 0.33 } },
];

const SLIDERS = [
  { key: 'time' as const, label: 'Time', icon: Clock, color: 'var(--accent-amber)', emoji: '⏱' },
  { key: 'cost' as const, label: 'Cost', icon: Coins, color: 'var(--accent-coral)', emoji: '💰' },
  { key: 'co2' as const, label: 'Eco', icon: Leaf, color: 'var(--accent-teal)', emoji: '🌿' },
];

export default function WeightSliders() {
  const { weights, setWeight, applyPreset } = useTransitStore();
  const debounceRef = useRef<number>();

  const handleSliderChange = useCallback((key: 'time' | 'cost' | 'co2', raw: number) => {
    const value = raw / 100;
    if (debounceRef.current) cancelAnimationFrame(debounceRef.current);
    debounceRef.current = requestAnimationFrame(() => {
      setWeight(key, Math.max(0.01, Math.min(0.98, value)));
    });
  }, [setWeight]);

  return (
    <div className="space-y-3">
      {/* Preset Buttons */}
      <div>
        <label className="text-xs mb-2 block" style={{ color: 'var(--text-secondary)' }}>
          QUICK PRESETS
        </label>
        <div className="grid grid-cols-2 gap-1.5">
          {PRESETS.map(p => {
            const isActive =
              Math.abs(weights.time - p.w.time) < 0.05 &&
              Math.abs(weights.cost - p.w.cost) < 0.05 &&
              Math.abs(weights.co2 - p.w.co2) < 0.05;
            return (
              <button
                key={p.key}
                onClick={() => applyPreset(p.key)}
                className="px-3 py-2 rounded-lg text-xs font-medium transition-all hover:scale-[1.02] active:scale-95"
                style={{
                  background: isActive ? 'color-mix(in oklab, var(--accent-teal) 10%, transparent)' : 'var(--bg-elevated)',
                  border: `1px solid ${isActive ? 'var(--accent-teal)' : 'var(--border-color)'}`,
                  color: isActive ? 'var(--accent-teal)' : 'var(--text-secondary)',
                }}
              >
                {p.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Weight Sliders */}
      <div>
        <label className="text-xs mb-2 block" style={{ color: 'var(--text-secondary)' }}>
          WEIGHT DISTRIBUTION
        </label>
        <div className="space-y-3">
          {SLIDERS.map(s => {
            const pct = Math.round(weights[s.key] * 100);
            return (
              <div key={s.key}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-1.5">
                    <span style={{ fontSize: '0.85rem' }}>{s.emoji}</span>
                    <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>{s.label}</span>
                  </div>
                  <span className="text-xs font-bold" style={{ color: s.color, fontFamily: "'JetBrains Mono', monospace" }}>
                    {pct}%
                  </span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="98"
                  value={pct}
                  onChange={e => handleSliderChange(s.key, parseInt(e.target.value))}
                  className="weight-slider w-full h-1.5 rounded-full cursor-pointer"
                  style={{
                    background: `linear-gradient(to right, ${s.color} ${pct}%, var(--bg-elevated) ${pct}%)`,
                    accentColor: s.color,
                  }}
                />
              </div>
            );
          })}
        </div>

        {/* Formula Display */}
        <div className="mt-2 px-3 py-2 rounded-lg" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-color)' }}>
          <span className="text-xs" style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--text-muted)' }}>
            Score = {weights.time.toFixed(2)}T + {weights.cost.toFixed(2)}C + {weights.co2.toFixed(2)}E
          </span>
        </div>
      </div>
    </div>
  );
}
