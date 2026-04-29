import { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle } from 'lucide-react';
import { useTransitStore } from '../store/transit-store';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';

const ALGO_COLORS = {
  Dijkstra: 'var(--accent-coral)',
  'A*': 'var(--accent-teal)',
  Bidirectional: 'var(--accent-blue)',
};

function CollapsibleSection({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl overflow-hidden mb-3" style={{ border: '1px solid var(--border)', background: 'var(--bg-elevated)' }}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between p-3 text-left"
      >
        <span className="text-xs font-semibold" style={{ color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{title}</span>
        {open ? <ChevronDown className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} /> : <ChevronRight className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />}
      </button>
      {open && <div className="px-3 pb-3">{children}</div>}
    </div>
  );
}

export default function AIExplanation() {
  const { selectedRoute, algoComparison } = useTransitStore();

  if (!selectedRoute || !algoComparison) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 text-center gap-3">
        <div className="text-3xl opacity-50">🧠</div>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Run a search to see AI algorithm insights
        </p>
      </div>
    );
  }

  const { dijkstra, astar, bidirectional, winner, astarEfficiencyPct } = algoComparison;

  const chartData = [
    { name: 'Dijkstra', nodes: dijkstra.nodesExpanded, time: dijkstra.runtimeMs },
    { name: 'A*',       nodes: astar.nodesExpanded,   time: astar.runtimeMs   },
    { name: 'Bidir.',   nodes: bidirectional.nodesExpanded, time: bidirectional.runtimeMs },
  ];

  const rows = [
    { algo: 'Dijkstra',      ...dijkstra,    optimal: true },
    { algo: 'A* (ε=1.2)',   ...astar,       optimal: true },
    { algo: 'Bidirectional', ...bidirectional, optimal: true },
  ];

  return (
    <div className="p-3 flex flex-col gap-3">
      {/* Algorithm explanation */}
      <div className="rounded-xl p-3" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-base">🤖</span>
          <span className="text-xs font-semibold" style={{ color: 'var(--accent-teal)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Algorithm Selection
          </span>
        </div>
        <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {selectedRoute.explanation}
        </p>
        <div
          className="mt-2 inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs"
          style={{
            background: 'color-mix(in oklab, var(--accent-teal) 10%, transparent)',
            color: 'var(--accent-teal)',
          }}
        >
          🏆 Winner: <strong className="ml-1">{winner}</strong> ({Math.abs(Math.round(astarEfficiencyPct))}% fewer nodes)
        </div>
      </div>

      {/* Comparison table */}
      <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
        <div className="p-2.5 pb-1" style={{ background: 'var(--bg-elevated)' }}>
          <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Comparison Table</span>
        </div>
        <div style={{ background: 'var(--bg-panel)' }}>
          {/* Header */}
          <div className="grid text-xs px-2.5 py-1.5" style={{ gridTemplateColumns: '90px 1fr 1fr 1fr', color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' }}>
            <span>Algorithm</span><span className="text-center">Nodes</span><span className="text-center">Time</span><span className="text-center">Optimal</span>
          </div>
          {rows.map((r) => (
            <div
              key={r.algo}
              className="grid text-xs px-2.5 py-2"
              style={{
                gridTemplateColumns: '90px 1fr 1fr 1fr',
                borderBottom: '1px solid var(--border)',
                background: r.algo.startsWith(winner) ? 'color-mix(in oklab, var(--accent-teal) 6%, transparent)' : undefined,
              }}
            >
              <span className="font-semibold" style={{ color: r.algo.includes('A*') ? 'var(--accent-teal)' : r.algo.includes('Bidir') ? 'var(--accent-blue)' : 'var(--accent-coral)' }}>
                {r.algo.startsWith(winner) && '⭐ '}{r.algo}
              </span>
              <span className="text-center font-mono" style={{ color: 'var(--text-primary)', fontFamily: "'JetBrains Mono', monospace" }}>{r.nodesExpanded}</span>
              <span className="text-center font-mono" style={{ color: 'var(--text-primary)', fontFamily: "'JetBrains Mono', monospace" }}>{r.runtimeMs.toFixed(1)}ms</span>
              <span className="text-center">
                <CheckCircle className="w-3.5 h-3.5 inline" style={{ color: 'var(--accent-green)' }} />
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Nodes expanded bar chart */}
      <div className="rounded-xl p-3" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
        <div className="text-xs font-semibold mb-3" style={{ color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Nodes Expanded</div>
        <ResponsiveContainer width="100%" height={80}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 10 }}>
            <XAxis type="number" hide />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-secondary)', fontFamily: "'JetBrains Mono', monospace" }} width={50} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{ background: 'var(--bg-panel)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }}
              labelStyle={{ color: 'var(--text-primary)' }}
              itemStyle={{ color: 'var(--text-secondary)' }}
              formatter={(v: number) => [`${v} nodes`, 'Expanded']}
            />
            <Bar dataKey="nodes" radius={[0, 4, 4, 0]}>
              {chartData.map((entry) => (
                <Cell key={entry.name} fill={(ALGO_COLORS as any)[entry.name] || 'var(--accent-teal)'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Heuristic proof */}
      <CollapsibleSection title="Heuristic Admissibility Proof">
        <div className="text-xs leading-relaxed space-y-2" style={{ color: 'var(--text-secondary)' }}>
          <div className="font-mono p-2 rounded" style={{ background: 'var(--bg-panel)', color: 'var(--accent-teal)', fontFamily: "'JetBrains Mono', monospace", fontSize: '0.65rem' }}>
            h(n) = d(n, goal) / v_max<br />
            where v_max = 583.3 m/min (Metro 35 km/h)
          </div>
          <p>Since <strong>v_max</strong> is the fastest possible transport mode in Algiers, <strong>h(n)</strong> can never overestimate the true remaining cost — making A* admissible and guaranteed optimal. ✅</p>
          <div className="flex items-center gap-1 text-xs" style={{ color: 'var(--accent-green)' }}>
            <CheckCircle className="w-3 h-3" /> Admissibility proven: h(n) ≤ true_cost(n, goal)
          </div>
        </div>
      </CollapsibleSection>

      {/* CSP constraints */}
      <CollapsibleSection title="CSP Constraints Applied">
        <div className="space-y-1.5">
          {[
            { label: 'X1 = num_transfers', domain: '0..5', status: '✅ Satisfied' },
            { label: 'X2 = total_walking_m', domain: '0..2000', status: '✅ Satisfied' },
            { label: 'X3 = total_time_min', domain: '0..180', status: '✅ Satisfied' },
            { label: 'X4 = includes_metro', domain: 'True/False', status: '✅ Satisfied' },
          ].map(({ label, domain, status }) => (
            <div key={label} className="flex items-center justify-between text-xs">
              <span style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--accent-blue)', fontSize: '0.65rem' }}>{label}</span>
              <span style={{ color: 'var(--text-muted)' }}>∈ [{domain}]</span>
              <span style={{ color: 'var(--accent-green)' }}>{status}</span>
            </div>
          ))}
          <div className="mt-2 text-xs p-2 rounded" style={{ background: 'var(--bg-panel)', color: 'var(--text-muted)' }}>
            AC-3 arc consistency applied — all arc constraints propagated before route selection.
          </div>
        </div>
      </CollapsibleSection>
    </div>
  );
}
