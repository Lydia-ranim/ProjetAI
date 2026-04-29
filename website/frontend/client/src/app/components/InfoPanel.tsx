import { useTransitStore } from '../store/transit-store';

export default function InfoPanel() {
  const { graphStats, algoComparison } = useTransitStore();

  return (
    <div
      className="absolute bottom-3 left-1/2 -translate-x-1/2 z-[999] flex items-center gap-3 px-4 py-2 rounded-full"
      style={{
        background: 'rgba(13,27,53,0.9)',
        backdropFilter: 'blur(16px)',
        border: '1px solid color-mix(in oklab, var(--accent-teal) 18%, transparent)',
        boxShadow: '0 4px 24px rgba(0,0,0,0.4), 0 0 0 1px color-mix(in oklab, var(--accent-teal) 10%, transparent)',
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '0.65rem',
        whiteSpace: 'nowrap',
        userSelect: 'none',
      }}
    >
      {/* Graph stats */}
      <span style={{ color: 'var(--text-muted)' }}>
        {graphStats.nodes} nodes · {graphStats.edges} edges · Algiers DZ
      </span>

      <span style={{ color: 'color-mix(in oklab, var(--accent-teal) 22%, transparent)' }}>│</span>

      {/* Last search metrics */}
      {algoComparison ? (
        <span style={{ color: 'var(--accent-teal)' }}>
          A* · {algoComparison.astar.nodesExpanded} expanded · {algoComparison.astar.runtimeMs.toFixed(1)}ms
        </span>
      ) : (
        <span style={{ color: 'var(--text-muted)' }}>Select stops to route</span>
      )}

      <span style={{ color: 'color-mix(in oklab, var(--accent-teal) 22%, transparent)' }}>│</span>

      {/* API status */}
      <span style={{ color: 'var(--accent-amber)' }}>
        🟡 Offline · mock data
      </span>
    </div>
  );
}
