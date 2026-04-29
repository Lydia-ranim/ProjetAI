import { useMemo } from 'react';
import { ArrowRight } from 'lucide-react';
import { useTransitStore } from '../store/transit-store';

export default function StartNavigationButton() {
  const { startStop, endStop, routes, isLoading, findRoutes, setActiveTab } = useTransitStore();

  const isReady = useMemo(() => !!(startStop && endStop), [startStop, endStop]);
  const hasRoute = routes.length > 0;

  if (!isReady) return null;

  return (
    <div className="pointer-events-none absolute left-1/2 bottom-5 z-[1000] -translate-x-1/2 animate-scale-in">
      <button
        type="button"
        className="pointer-events-auto group flex items-center gap-2 rounded-[22px] px-5 py-3 font-semibold"
        style={{
          background: 'color-mix(in oklab, var(--accent-blue) 92%, transparent)',
          color: 'rgba(10, 22, 40, 0.96)',
          boxShadow: '0 10px 40px rgba(0,0,0,0.35), 0 0 22px rgba(198, 183, 226, 0.35)',
          border: '1px solid color-mix(in oklab, var(--accent-blue) 70%, transparent)',
          transition: 'transform 160ms ease, box-shadow 160ms ease, filter 160ms ease, opacity 160ms ease',
        }}
        onClick={() => {
          if (!hasRoute && !isLoading) findRoutes();
          setActiveTab('timeline');
        }}
        aria-label="Start Navigation"
        disabled={isLoading}
        onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-1px) scale(1.02)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0) scale(1)'; }}
      >
        <span className="tracking-wide">Start Navigation</span>
        <ArrowRight className="w-4 h-4 transition-transform duration-200 group-hover:translate-x-0.5" />
      </button>
    </div>
  );
}

