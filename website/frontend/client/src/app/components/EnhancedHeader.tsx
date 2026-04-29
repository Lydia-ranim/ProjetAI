import { useState, useEffect } from 'react';
import { Moon, Sun, Activity } from 'lucide-react';
import { useTransitStore } from '../store/transit-store';
import { usePeakHour } from '../hooks/usePeakHour';
import logoUrl from '../../assets/lyhlyh-logo.png';

const ALGO_BADGES = [
  { label: 'A*',            color: 'var(--accent-teal)'  },
  { label: 'Dijkstra',      color: 'var(--accent-amber)' },
  { label: 'Best Route',    color: 'var(--accent-blue)'  },
];

export default function EnhancedHeader() {
  const { isDarkMode, toggleDarkMode, graphStats } = useTransitStore();
  const { clock, isPeak, label } = usePeakHour();
  const [algoIdx, setAlgoIdx] = useState(0);
  const [algoVisible, setAlgoVisible] = useState(true);

  useEffect(() => {
    const interval = setInterval(() => {
      setAlgoVisible(false);
      setTimeout(() => {
        setAlgoIdx(i => (i + 1) % ALGO_BADGES.length);
        setAlgoVisible(true);
      }, 200);
    }, 2800);
    return () => clearInterval(interval);
  }, []);

  const currentBadge = ALGO_BADGES[algoIdx];

  return (
    <header className="app-header" role="banner">
      <div className="flex items-center gap-3">
        <button
          type="button"
          className="group relative w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0 overflow-hidden"
          style={{
            background: 'color-mix(in oklab, var(--accent-teal) 12%, transparent)',
            border: '1px solid color-mix(in oklab, var(--accent-teal) 35%, transparent)',
            boxShadow: '0 0 0 0 rgba(190,238,219,0)',
            transition: 'transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease',
          }}
          onMouseEnter={(e) => { (e.currentTarget.style.boxShadow = '0 0 24px rgba(190,238,219,0.22)'); }}
          onMouseLeave={(e) => { (e.currentTarget.style.boxShadow = '0 0 0 0 rgba(190,238,219,0)'); }}
          aria-label="LYHLYH"
        >
          <img src={logoUrl} alt="LYHLYH" className="w-8 h-8 object-contain transition-transform duration-200 group-hover:scale-[1.03]" />
          <div
            className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
            style={{ background: 'radial-gradient(circle at 30% 30%, rgba(190,238,219,0.16), transparent 60%)' }}
          />
        </button>

        <div>
          <h1
            className="text-sm font-bold leading-tight tracking-wide"
            style={{ fontFamily: "'Space Mono', monospace", color: 'var(--text-primary)' }}
          >
            LYHLYH
          </h1>
          <div className="flex items-center gap-2 mt-0.5">
            <span
              className="badge"
              style={{
                background: `${currentBadge.color}15`,
                color: currentBadge.color,
                border: `1px solid ${currentBadge.color}30`,
                opacity: algoVisible ? 1 : 0,
                transform: algoVisible ? 'translateY(0)' : 'translateY(-4px)',
                transition: 'all 0.2s ease',
                fontSize: '0.6rem',
              }}
            >
              {currentBadge.label}
            </span>

            {graphStats.loaded && (
              <span
                className="flex items-center gap-1"
                style={{ fontSize: '0.6rem', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}
              >
                <span style={{ color: 'var(--accent-green)' }}>●</span>
                {graphStats.nodes} nodes · {graphStats.edges} edges
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {isPeak && (
          <div
            className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full"
            style={{ background: 'color-mix(in oklab, var(--accent-amber) 14%, transparent)', border: '1px solid color-mix(in oklab, var(--accent-amber) 35%, transparent)' }}
          >
            <span style={{ fontSize: '0.65rem', color: 'var(--accent-amber)', fontWeight: 600 }}>{label}</span>
          </div>
        )}

        <div
          className="hidden md:flex items-center gap-1.5 px-3 py-1 rounded-full"
          style={{ background: 'color-mix(in oklab, var(--accent-teal) 10%, transparent)', border: '1px solid color-mix(in oklab, var(--accent-teal) 26%, transparent)' }}
        >
          <Activity className="w-3 h-3" style={{ color: 'var(--accent-teal)' }} />
          <span
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '0.72rem',
              color: 'var(--accent-teal)',
              fontWeight: 600,
            }}
          >
            {clock}
          </span>
        </div>

        <button
          onClick={toggleDarkMode}
          className="btn-icon"
          aria-label={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          style={{ width: 36, height: 36 }}
        >
          {isDarkMode
            ? <Sun  className="w-4 h-4" style={{ color: 'var(--accent-amber)' }} />
            : <Moon className="w-4 h-4" style={{ color: 'var(--accent-blue)'  }} />
          }
        </button>
      </div>
    </header>
  );
}
