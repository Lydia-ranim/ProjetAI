import { useTransitStore } from '../store/transit-store';
import { Activity } from 'lucide-react';

export default function StressHeatmap() {
  const { selectedRoute } = useTransitStore();

  if (!selectedRoute) return null;

  const getStressColor = (level: string) => {
    switch (level) {
      case 'low':
        return '#BEEEDB';
      case 'medium':
        return '#F2C4CE';
      case 'high':
        return '#670627';
      default:
        return '#8ea9c1';
    }
  };

  const stressFactors = [
    {
      label: 'Walking',
      value: selectedRoute.totalWalkingDistance / 1000,
      max: 2,
      unit: 'km',
      stress: selectedRoute.totalWalkingDistance > 1000 ? 'medium' : 'low',
    },
    {
      label: 'Transfers',
      value: selectedRoute.transfers,
      max: 4,
      unit: '',
      stress: selectedRoute.transfers > 2 ? 'high' : selectedRoute.transfers > 1 ? 'medium' : 'low',
    },
    {
      label: 'Waiting',
      value: selectedRoute.totalWaitingTime,
      max: 20,
      unit: 'min',
      stress: selectedRoute.totalWaitingTime > 10 ? 'medium' : 'low',
    },
  ];

  return (
    <div className="p-4 space-y-3 border-t border-border">
      <div className="flex items-center gap-2">
        <Activity className="w-4 h-4 text-primary" />
        <h4 className="text-sm text-foreground/90">Stress Analysis</h4>
      </div>

      <div className="space-y-3">
        {stressFactors.map((factor) => (
          <div key={factor.label}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-muted-foreground">{factor.label}</span>
              <span className="text-xs" style={{ color: getStressColor(factor.stress) }}>
                {factor.value.toFixed(factor.unit === 'km' ? 1 : 0)}{factor.unit}
              </span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${Math.min((factor.value / factor.max) * 100, 100)}%`,
                  backgroundColor: getStressColor(factor.stress),
                }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="p-3 rounded-lg bg-card border border-border">
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">Overall Stress</span>
          <span
            className="text-sm capitalize px-2 py-0.5 rounded"
            style={{
              backgroundColor: `${getStressColor(selectedRoute.stressLevel)}30`,
              color: getStressColor(selectedRoute.stressLevel),
            }}
          >
            {selectedRoute.stressLevel}
          </span>
        </div>
      </div>
    </div>
  );
}
