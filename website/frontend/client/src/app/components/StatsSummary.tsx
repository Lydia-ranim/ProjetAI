import { Clock, DollarSign, Leaf, TrendingDown } from 'lucide-react';
import { useTransitStore } from '../store/transit-store';

export default function StatsSummary() {
  const { routes } = useTransitStore();

  if (routes.length === 0) return null;

  const avgTime = Math.round(routes.reduce((sum, r) => sum + r.totalTime, 0) / routes.length);
  const avgCost = (routes.reduce((sum, r) => sum + r.totalCost, 0) / routes.length).toFixed(2);
  const avgCO2 = Math.round(routes.reduce((sum, r) => sum + r.totalCO2, 0) / routes.length);

  const stats = [
    { label: 'Avg Time', value: `${avgTime} min`, icon: Clock, color: '#C6B7E2' },
    { label: 'Avg Cost', value: `€${avgCost}`, icon: DollarSign, color: '#F2C4CE' },
    { label: 'Avg CO₂', value: `${avgCO2}g`, icon: Leaf, color: '#BEEEDB' },
  ];

  return (
    <div className="p-4 rounded-xl bg-card border border-border">
      <div className="flex items-center gap-2 mb-3">
        <TrendingDown className="w-4 h-4 text-primary" />
        <h4 className="text-sm text-foreground/90">Route Statistics</h4>
      </div>
      <div className="grid grid-cols-3 gap-3">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="text-center">
            <Icon className="w-4 h-4 mx-auto mb-1" style={{ color }} />
            <p className="text-xs text-muted-foreground mb-0.5">{label}</p>
            <p className="text-sm" style={{ color }}>{value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
