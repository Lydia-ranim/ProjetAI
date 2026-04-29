import { Zap, DollarSign, Leaf } from 'lucide-react';
import { useTransitStore } from '../store/transit-store';

export default function PresetButtons() {
  const { setWeights } = useTransitStore();

  const presets = [
    {
      name: 'Fastest',
      icon: Zap,
      weights: { time: 0.7, price: 0.15, co2: 0.15 },
      color: '#C6B7E2',
    },
    {
      name: 'Cheapest',
      icon: DollarSign,
      weights: { time: 0.15, price: 0.7, co2: 0.15 },
      color: '#F2C4CE',
    },
    {
      name: 'Greenest',
      icon: Leaf,
      weights: { time: 0.15, price: 0.15, co2: 0.7 },
      color: '#BEEEDB',
    },
  ];

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">Quick Presets</p>
      <div className="grid grid-cols-3 gap-2">
        {presets.map(({ name, icon: Icon, weights, color }) => (
          <button
            key={name}
            onClick={() => setWeights(weights)}
            className="flex flex-col items-center gap-1 p-2 rounded-lg border border-border hover:border-opacity-60 transition-all hover:scale-105 active:scale-95"
            style={{
              borderColor: `${color}40`,
            }}
          >
            <Icon className="w-4 h-4" style={{ color }} />
            <span className="text-xs" style={{ color }}>
              {name}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
