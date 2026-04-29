import { Download, Copy, Share2, Printer } from 'lucide-react';
import { toast } from 'sonner';
import { useTransitStore } from '../store/transit-store';
import type { Route } from '../utils/algorithms';

function exportJSON(route: Route) {
  const blob = new Blob([JSON.stringify(route, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `algiers-route-${route.label}-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function copyText(route: Route) {
  const segs = route.segments.map(s =>
    `  ${s.mode.toUpperCase()}: ${s.fromName} → ${s.toName} (${Math.round(s.durationMin)} min, ${s.costDzd} DZD)`
  ).join('\n');
  const text = [
    `Algiers Transit Route — ${route.label.toUpperCase()}`,
    `Algorithm: ${route.algorithmUsed}`,
    `Total: ${Math.round(route.summary.totalTimeMin)} min | ${route.summary.totalCostDzd} DZD | ${Math.round(route.summary.totalCo2G)}g CO₂`,
    ``,
    segs,
  ].join('\n');
  navigator.clipboard.writeText(text).then(() => toast('📋 Copied to clipboard'));
}

export default function RouteActions() {
  const { selectedRoute } = useTransitStore();

  if (!selectedRoute) return null;

  const actions = [
    { icon: Download, label: 'JSON', onClick: () => { exportJSON(selectedRoute); toast('⬇️ JSON downloaded'); } },
    { icon: Copy,     label: 'Copy',  onClick: () => copyText(selectedRoute) },
    { icon: Share2,   label: 'Share', onClick: () => {
      if (navigator.share) {
        navigator.share({ title: `Route ${selectedRoute.label}`, text: `Algiers transit: ${Math.round(selectedRoute.summary.totalTimeMin)} min` });
      } else {
        copyText(selectedRoute);
      }
    }},
    { icon: Printer,  label: 'Print', onClick: () => window.print() },
  ];

  return (
    <div
      className="flex items-center justify-around p-2 border-t"
      style={{ borderColor: 'var(--border)' }}
    >
      {actions.map(({ icon: Icon, label, onClick }) => (
        <button
          key={label}
          onClick={onClick}
          className="flex flex-col items-center gap-1 p-2 rounded-lg transition-all hover:bg-white/5"
          aria-label={label}
        >
          <Icon className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{label}</span>
        </button>
      ))}
    </div>
  );
}
