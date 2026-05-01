import { useTransitStore } from '../store/transit-store';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend,
} from 'recharts';

const MODE_COLORS: Record<string, string> = {
  walk:         '#BEEEDB',
  bus:          '#670627',
  tram:         '#F2C4CE',
  metro:        '#C6B7E2',
  telepherique: '#C6B7E2',
  escalator:    '#BEEEDB',
};

const MODE_LABELS: Record<string, string> = {
  walk: 'Walk', bus: 'Bus', tram: 'Tram',
  metro: 'Metro', telepherique: 'Téléph.', escalator: 'Escal.',
};

const TOOLTIP_STYLE = {
  contentStyle: {
    background: 'rgba(10, 22, 40, 0.96)',
    border: '1px solid rgba(190, 238, 219, 0.18)',
    borderRadius: 10,
    fontSize: 11,
    color: 'rgba(190, 238, 219, 0.9)',
    boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
  },
  labelStyle: { color: 'rgba(190, 238, 219, 0.96)', fontWeight: 600 },
  itemStyle: { color: 'rgba(198, 183, 226, 0.86)' },
  cursor: { fill: 'rgba(190, 238, 219, 0.05)' },
};

export default function TripStatsChart() {
  const { selectedRoute } = useTransitStore();

  if (!selectedRoute) return null;

  const { segments, summary } = selectedRoute;

  // ── Time per mode ────────────────────────────────────────────────────────
  const timeByMode: Record<string, number> = {};
  for (const seg of segments) {
    timeByMode[seg.mode] = (timeByMode[seg.mode] || 0) + seg.durationMin;
  }

  const timeData = Object.entries(timeByMode).map(([mode, mins]) => ({
    mode: MODE_LABELS[mode] || mode,
    minutes: Math.round(mins * 10) / 10,
    color: MODE_COLORS[mode] || '#888',
  })).sort((a, b) => b.minutes - a.minutes);

  // ── Pie data: time breakdown ─────────────────────────────────────────────
  const totalMinutes = summary.totalTimeMin;
  const rideMin = Math.max(
    0,
    totalMinutes - summary.waitingTimeMin - (summary.walkingDistanceM / 83.3)
  );
  const walkMin = Math.round(summary.walkingDistanceM / 83.3);
  const waitMin = Math.round(summary.waitingTimeMin);

  const pieData = [
    { name: 'Ride', value: Math.round(rideMin), fill: 'var(--accent-blue)' },
    { name: 'Walk', value: walkMin, fill: 'var(--accent-teal)' },
    { name: 'Wait', value: waitMin, fill: 'var(--accent-amber)' },
  ].filter(d => d.value > 0);

  // ── Transfers ────────────────────────────────────────────────────────────
  const transfers = summary.numTransfers;
  const transferStress = transfers === 0 ? 'None'
    : transfers === 1 ? 'Low'
    : transfers === 2 ? 'Medium' : 'High';
  const transferColor = transfers === 0 ? 'var(--accent-teal)'
    : transfers <= 1 ? 'var(--accent-teal)'
    : transfers <= 2 ? 'var(--accent-amber)' : 'var(--accent-coral)';

  const avgWaitPerTransfer = transfers > 0
    ? Math.round((waitMin / (transfers + 1)) * 10) / 10
    : 0;

  const card: React.CSSProperties = {
    background: 'var(--bg-elevated)',
    border: '1px solid var(--border-color)',
    borderRadius: 12,
    padding: '10px 12px',
    marginBottom: 8,
  };

  const label: React.CSSProperties = {
    fontSize: 10,
    fontWeight: 700,
    color: 'var(--text-muted)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.08em',
    marginBottom: 8,
    display: 'block',
  };

  return (
    <div style={{ padding: '12px 12px 20px' }}>

      {/* ── Header ── */}
      <div
        className="flex items-center gap-2 mb-3 pb-2"
        style={{ borderBottom: '1px solid var(--border-color)' }}
      >
        <span style={{ fontSize: '1.1rem' }}>📊</span>
        <span
          className="text-xs font-bold tracking-widest uppercase"
          style={{ color: 'var(--accent-teal)' }}
        >
          Trip Breakdown
        </span>
        <span
          className="ml-auto text-xs font-mono font-bold"
          style={{ color: 'var(--text-primary)' }}
        >
          {Math.round(totalMinutes)} min total
        </span>
      </div>

      {/* ── Time per transport mode bar chart ── */}
      <div style={card}>
        <span style={label}>Time by transport mode</span>
        <ResponsiveContainer width="100%" height={timeData.length * 36 + 20}>
          <BarChart
            data={timeData}
            layout="vertical"
            margin={{ left: 0, right: 32, top: 0, bottom: 0 }}
            barSize={14}
          >
            <XAxis
              type="number"
              hide
              domain={[0, Math.max(...timeData.map(d => d.minutes)) * 1.15]}
            />
            <YAxis
              type="category"
              dataKey="mode"
              tick={{ fontSize: 10, fill: 'rgba(198,183,226,0.86)', fontWeight: 600 }}
              width={48}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={(v: number) => [`${v} min`, 'Duration']}
            />
            <Bar dataKey="minutes" radius={[0, 6, 6, 0]}
              label={{
                position: 'right',
                fontSize: 10,
                fill: 'rgba(198,183,226,0.7)',
                fontFamily: "'JetBrains Mono', monospace",
                formatter: (v: number) => `${v}m`,
              }}
            >
              {timeData.map((entry, i) => (
                <Cell key={i} fill={entry.color} opacity={0.88} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* ── Time category donut ── */}
      <div style={card}>
        <span style={label}>Journey time split</span>
        <ResponsiveContainer width="100%" height={120}>
          <PieChart>
            <Pie
              data={pieData}
              dataKey="value"
              cx="40%"
              cy="50%"
              innerRadius={32}
              outerRadius={50}
              paddingAngle={3}
              strokeWidth={0}
            >
              {pieData.map((d, i) => (
                <Cell key={i} fill={d.fill} opacity={0.9} />
              ))}
            </Pie>
            <Legend
              layout="vertical"
              align="right"
              verticalAlign="middle"
              iconSize={8}
              iconType="circle"
              formatter={(value, entry: any) => (
                <span style={{ fontSize: 10, color: 'rgba(198,183,226,0.86)' }}>
                  {value} <strong style={{ color: 'rgba(190,238,219,0.96)' }}>
                    {entry.payload.value}m
                  </strong>
                </span>
              )}
            />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={(v: number) => [`${v} min`, '']}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* ── Transfers + avg wait stat tiles ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        
        {/* Transfers */}
        <div style={{ ...card, marginBottom: 0 }}>
          <span style={label}>Transfers</span>
          <div
            className="text-3xl font-bold font-mono"
            style={{ color: transferColor, lineHeight: 1 }}
          >
            {transfers}
          </div>
          <div
            className="text-xs mt-1 font-semibold"
            style={{ color: transferColor, opacity: 0.8 }}
          >
            {transferStress} complexity
          </div>
          {/* Transfer dots */}
          <div className="flex gap-1 mt-2">
            {[0, 1, 2, 3].map(i => (
              <div
                key={i}
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: i < transfers
                    ? transferColor
                    : 'rgba(190,238,219,0.15)',
                  border: `1.5px solid ${i < transfers ? transferColor : 'rgba(190,238,219,0.2)'}`,
                  transition: 'all 0.3s ease',
                }}
              />
            ))}
          </div>
        </div>

        {/* Avg wait */}
        <div style={{ ...card, marginBottom: 0 }}>
          <span style={label}>Avg wait / stop</span>
          <div
            className="text-3xl font-bold font-mono"
            style={{ color: 'var(--accent-amber)', lineHeight: 1 }}
          >
            {avgWaitPerTransfer > 0 ? `${avgWaitPerTransfer}` : waitMin}
          </div>
          <div
            className="text-xs mt-1"
            style={{ color: 'rgba(242,196,206,0.7)', fontWeight: 600 }}
          >
            min {avgWaitPerTransfer > 0 ? 'per boarding' : 'total wait'}
          </div>
          {/* Wait bar */}
          <div
            style={{
              marginTop: 8,
              height: 4,
              borderRadius: 2,
              background: 'rgba(190,238,219,0.1)',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                height: '100%',
                width: `${Math.min((waitMin / 20) * 100, 100)}%`,
                background: 'var(--accent-amber)',
                borderRadius: 2,
                opacity: 0.8,
                transition: 'width 0.6s ease',
              }}
            />
          </div>
          <div
            className="text-xs mt-1"
            style={{ color: 'rgba(198,183,226,0.5)' }}
          >
            {waitMin} min total
          </div>
        </div>
      </div>

    </div>
  );
}
