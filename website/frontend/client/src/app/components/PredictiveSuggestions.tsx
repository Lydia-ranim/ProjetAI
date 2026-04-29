import { useTransitStore } from '../store/transit-store';
import { usePeakHour } from '../hooks/usePeakHour';

export default function PredictiveSuggestions() {
  const { routes, selectedRoute } = useTransitStore();
  const { isPeak, label } = usePeakHour();

  const fastest = routes.find(r => r.label === 'fastest');
  const cheapest = routes.find(r => r.label === 'cheapest');
  const greenest = routes.find(r => r.label === 'greenest');
  const now = new Date();
  const h = now.getHours();
  const isNight = h >= 22 || h < 5;

  const suggestions: { icon: string; text: string; color: string }[] = [];

  if (isPeak) {
    suggestions.push({ icon: '🚇', color: 'var(--accent-amber)', text: `Rush hour detected (${label}). Metro waits may be 6-8 min. Consider leaving 10 min earlier.` });
  }
  if (isNight) {
    suggestions.push({ icon: '🌙', color: 'var(--accent-blue)', text: 'Night service: Metro runs every 12 min. Bus services reduced after 23:00.' });
  }
  if (fastest && selectedRoute && selectedRoute.label !== 'fastest') {
    const diff = Math.round(selectedRoute.summary.totalTimeMin - fastest.summary.totalTimeMin);
    if (diff > 0) {
      suggestions.push({ icon: '⚡', color: 'var(--accent-amber)', text: `Switch to Fastest route to save ${diff} min (costs ${fastest.summary.totalCostDzd - selectedRoute.summary.totalCostDzd > 0 ? '+' : ''}${fastest.summary.totalCostDzd - selectedRoute.summary.totalCostDzd} DZD more).` });
    }
  }
  if (greenest && fastest && greenest.summary.totalCo2G < fastest.summary.totalCo2G) {
    const saved = Math.round(fastest.summary.totalCo2G - greenest.summary.totalCo2G);
    if (saved > 5) {
      suggestions.push({ icon: '🌿', color: 'var(--accent-green)', text: `Take Greenest route to save ${saved}g CO₂ (≈ charging a phone ${Math.round(saved / 12.8)}×).` });
    }
  }
  if (selectedRoute && selectedRoute.summary.numTransfers >= 2) {
    suggestions.push({ icon: '🔄', color: 'var(--accent-blue)', text: `This route has ${selectedRoute.summary.numTransfers} transfers. Try relaxing constraints to find a direct option.` });
  }

  if (suggestions.length === 0) return null;

  return (
    <div className="px-3 pb-3 space-y-2">
      {suggestions.map((s, i) => (
        <div
          key={i}
          className="flex items-start gap-2 p-2.5 rounded-xl text-xs"
          style={{ background: `${s.color}0D`, border: `1px solid ${s.color}25`, color: s.color }}
        >
          <span className="flex-shrink-0 text-base leading-none mt-0.5">{s.icon}</span>
          <span className="leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{s.text}</span>
        </div>
      ))}
    </div>
  );
}
