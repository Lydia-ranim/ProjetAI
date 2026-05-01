import { useMemo } from 'react';
import { ArrowRight } from 'lucide-react';
import { useTransitStore } from '../store/transit-store';

export default function StartNavigationButton() {
  const { startStop, endStop, routes, isLoading, findRoutes, setActiveTab } = useTransitStore();

  const isReady = useMemo(() => !!(startStop && endStop), [startStop, endStop]);
  const hasRoute = routes.length > 0;

  if (!isReady) return null;

  return (
    <div className="pointer-events-none absolute left-1/2 bottom-8 z-[1000] -translate-x-1/2 animate-scale-in">
      <button
        type="button"
        className="pointer-events-auto group flex items-center gap-3 rounded-[26px] px-7 py-4 font-bold text-base tracking-wide"
        style={{
          background: 'linear-gradient(135deg, #BEEEDB 0%, #8FD9BE 100%)',
          color: '#0A1628',
          boxShadow: '0 12px 40px rgba(190, 238, 219, 0.45), 0 4px 16px rgba(0,0,0,0.35)',
          border: '1.5px solid rgba(190, 238, 219, 0.6)',
          transition: 'transform 160ms ease, box-shadow 160ms ease',
          letterSpacing: '0.03em',
          minWidth: 220,
        }}
        onClick={() => {
          if (!hasRoute && !isLoading) findRoutes();
          setActiveTab('timeline');
        }}
        aria-label="Start Navigation"
        disabled={isLoading}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'translateY(-2px) scale(1.04)';
          e.currentTarget.style.boxShadow = '0 18px 50px rgba(190, 238, 219, 0.55), 0 6px 20px rgba(0,0,0,0.3)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'translateY(0) scale(1)';
          e.currentTarget.style.boxShadow = '0 12px 40px rgba(190, 238, 219, 0.45), 0 4px 16px rgba(0,0,0,0.35)';
        }}
      >
        <span>Plan my trip →</span>
        <ArrowRight
          className="w-4 h-4 transition-transform duration-200 group-hover:translate-x-0.5"
          style={{ color: '#0A1628', opacity: 0.7 }}
        />
      </button>
    </div>
  );
}

