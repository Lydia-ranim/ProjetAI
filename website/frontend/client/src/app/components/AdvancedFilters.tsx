import { useState } from 'react';
import { SlidersHorizontal, RotateCcw } from 'lucide-react';
import { useTransitStore } from '../store/transit-store';

export default function AdvancedFilters() {
  const { constraints, setConstraint } = useTransitStore();

  const handleReset = () => {
    setConstraint('maxTransfers', -1);
    setConstraint('maxWalkingM', 2000);
    setConstraint('maxTimeMin', 180);
  };

  return (
    <div className="space-y-4 p-3 rounded-lg" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-color)' }}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-3.5 h-3.5" style={{ color: 'var(--accent-teal)' }} />
          <span className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>Constraints (CSP)</span>
        </div>
        <button
          onClick={handleReset}
          className="flex items-center gap-1 text-xs px-2 py-1 rounded hover:bg-white/5 transition-all"
          style={{ color: 'var(--text-muted)' }}
        >
          <RotateCcw className="w-3 h-3" />
          Reset
        </button>
      </div>

      {/* Max Transfers */}
      <div>
        <label className="text-xs mb-1.5 block" style={{ color: 'var(--text-secondary)' }}>
          Max Transfers
        </label>
        <div className="flex gap-1.5">
          {[0, 1, 2, 3, -1].map(v => (
            <button
              key={v}
              onClick={() => setConstraint('maxTransfers', v)}
              className="flex-1 py-1.5 rounded-md text-xs font-medium transition-all"
              style={{
                background: constraints.maxTransfers === v ? 'color-mix(in oklab, var(--accent-teal) 14%, transparent)' : 'var(--bg-panel)',
                border: `1px solid ${constraints.maxTransfers === v ? 'var(--accent-teal)' : 'var(--border-color)'}`,
                color: constraints.maxTransfers === v ? 'var(--accent-teal)' : 'var(--text-muted)',
              }}
            >
              {v === -1 ? 'Any' : v}
            </button>
          ))}
        </div>
      </div>

      {/* Max Walking Distance */}
      <div>
        <div className="flex justify-between mb-1.5">
          <label className="text-xs" style={{ color: 'var(--text-secondary)' }}>Max Walking</label>
          <span className="text-xs font-mono" style={{ color: 'var(--accent-teal)' }}>
            {constraints.maxWalkingM}m
          </span>
        </div>
        <input
          type="range"
          min="200"
          max="2000"
          step="100"
          value={constraints.maxWalkingM}
          onChange={e => setConstraint('maxWalkingM', parseInt(e.target.value))}
          className="weight-slider w-full"
          style={{
            background: `linear-gradient(to right, var(--accent-teal) ${((constraints.maxWalkingM - 200) / 1800) * 100}%, var(--bg-panel) ${((constraints.maxWalkingM - 200) / 1800) * 100}%)`,
          }}
        />
      </div>

      {/* Max Travel Time */}
      <div>
        <div className="flex justify-between mb-1.5">
          <label className="text-xs" style={{ color: 'var(--text-secondary)' }}>Max Time</label>
          <span className="text-xs font-mono" style={{ color: 'var(--accent-amber)' }}>
            {constraints.maxTimeMin} min
          </span>
        </div>
        <input
          type="range"
          min="10"
          max="180"
          step="5"
          value={constraints.maxTimeMin}
          onChange={e => setConstraint('maxTimeMin', parseInt(e.target.value))}
          className="weight-slider w-full"
          style={{
            background: `linear-gradient(to right, var(--accent-amber) ${((constraints.maxTimeMin - 10) / 170) * 100}%, var(--bg-panel) ${((constraints.maxTimeMin - 10) / 170) * 100}%)`,
          }}
        />
      </div>
    </div>
  );
}
