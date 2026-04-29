import { useTransitStore } from '../store/transit-store';
import {
  BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Legend,
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
} from 'recharts';

const CHART_TOOLTIP_STYLE = {
  contentStyle: { background: 'var(--bg-panel)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 },
  labelStyle: { color: 'var(--text-primary)' },
  itemStyle: { color: 'var(--text-secondary)' },
};

export default function ChartPanel() {
  const { routes, algoComparison } = useTransitStore();

  if (routes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-6 text-center gap-2 h-full">
        <div className="text-2xl opacity-40">📊</div>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Search for routes to see analytics</p>
      </div>
    );
  }

  const fastest = routes.find(r => r.label === 'fastest');
  const greenest = routes.find(r => r.label === 'greenest');
  const cheapest = routes.find(r => r.label === 'cheapest');

  // CO2 comparison data
  const distKm = (fastest?.summary.totalDistanceM || 5000) / 1000;
  const carCo2 = Math.round(distKm * 192);
  const co2Data = [
    { name: 'Car 🚗',      co2: carCo2,                                       fill: '#FF4444' },
    { name: 'Fastest ⚡',   co2: Math.round(fastest?.summary.totalCo2G || 0),   fill: 'var(--accent-amber)' },
    { name: 'Cheapest 💰',  co2: Math.round(cheapest?.summary.totalCo2G || 0),  fill: 'var(--accent-coral)' },
    { name: 'Greenest 🌿',  co2: Math.round(greenest?.summary.totalCo2G || 0),  fill: 'var(--accent-green)' },
  ];

  // Time breakdown donut (fastest route)
  const r = fastest || routes[0];
  const walkT = r.summary.waitingTimeMin > 0 ? r.summary.waitingTimeMin : 0;
  const waitT = r.summary.waitingTimeMin;
  const rideT = r.summary.totalTimeMin - walkT - waitT;
  const pieData = [
    { name: 'Ride',  value: Math.max(0, Math.round(rideT)), fill: 'var(--accent-blue)'  },
    { name: 'Walk',  value: Math.round(r.summary.walkingDistanceM / 83.3), fill: 'var(--accent-teal)'  },
    { name: 'Wait',  value: Math.max(0, Math.round(waitT)), fill: 'var(--accent-amber)'  },
  ].filter(d => d.value > 0);

  // Radar data (normalised 0-100)
  const maxTime = Math.max(...routes.map(r => r.summary.totalTimeMin), 1);
  const maxCost = Math.max(...routes.map(r => r.summary.totalCostDzd), 1);
  const maxCo2  = Math.max(...routes.map(r => r.summary.totalCo2G),   1);
  const maxTx   = Math.max(...routes.map(r => r.summary.numTransfers + 1), 1);

  const radarData = [
    { metric: 'Time',      fastest: 100 - Math.round((fastest?.summary.totalTimeMin || 0) / maxTime * 100), cheapest: 100 - Math.round((cheapest?.summary.totalTimeMin || 0) / maxTime * 100), greenest: 100 - Math.round((greenest?.summary.totalTimeMin || 0) / maxTime * 100) },
    { metric: 'Cost',      fastest: 100 - Math.round((fastest?.summary.totalCostDzd || 0) / maxCost * 100), cheapest: 100 - Math.round((cheapest?.summary.totalCostDzd || 0) / maxCost * 100), greenest: 100 - Math.round((greenest?.summary.totalCostDzd || 0) / maxCost * 100) },
    { metric: 'Eco',       fastest: 100 - Math.round((fastest?.summary.totalCo2G || 0) / maxCo2 * 100), cheapest: 100 - Math.round((cheapest?.summary.totalCo2G || 0) / maxCo2 * 100), greenest: 100 - Math.round((greenest?.summary.totalCo2G || 0) / maxCo2 * 100) },
    { metric: 'Comfort',   fastest: 70, cheapest: 60, greenest: 80 },
    { metric: 'Transfers', fastest: 100 - Math.round(((fastest?.summary.numTransfers || 0) + 1) / maxTx * 100), cheapest: 100 - Math.round(((cheapest?.summary.numTransfers || 0) + 1) / maxTx * 100), greenest: 100 - Math.round(((greenest?.summary.numTransfers || 0) + 1) / maxTx * 100) },
  ];

  // Algo nodes chart
  const algoData = algoComparison ? [
    { name: 'Dijkstra', nodes: algoComparison.dijkstra.nodesExpanded,      fill: 'var(--accent-coral)' },
    { name: 'A*',       nodes: algoComparison.astar.nodesExpanded,          fill: 'var(--accent-teal)'  },
    { name: 'Bidir.',   nodes: algoComparison.bidirectional.nodesExpanded,  fill: 'var(--accent-blue)'  },
  ] : [];

  const sectionStyle: React.CSSProperties = {
    background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 12, padding: 12, marginBottom: 10,
  };
  const titleStyle: React.CSSProperties = {
    fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8, display: 'block',
  };

  return (
    <div className="p-3">
      {/* CO2 Comparison */}
      <div style={sectionStyle}>
        <span style={titleStyle}>CO₂ Comparison vs Car</span>
        <ResponsiveContainer width="100%" height={100}>
          <BarChart data={co2Data} layout="vertical" margin={{ left: 0, right: 20 }}>
            <XAxis type="number" hide />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} width={65} axisLine={false} tickLine={false} />
            <Tooltip {...CHART_TOOLTIP_STYLE} formatter={(v: number) => [`${v}g CO₂`, 'Emissions']} />
            <Bar dataKey="co2" radius={[0, 4, 4, 0]} label={{ position: 'right', fontSize: 9, fill: 'var(--text-muted)', formatter: (v: number) => `${v}g` }}>
              {co2Data.map((d, i) => <Cell key={i} fill={d.fill} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        {greenest && (
          <div className="text-xs mt-1" style={{ color: 'var(--accent-green)' }}>
            🌿 Greenest route saves {Math.round(carCo2 - greenest.summary.totalCo2G)}g CO₂ ({Math.round((1 - greenest.summary.totalCo2G / carCo2) * 100)}% vs car)
          </div>
        )}
      </div>

      {/* Time Breakdown Donut */}
      <div style={sectionStyle}>
        <span style={titleStyle}>Time Breakdown (Fastest Route)</span>
        <ResponsiveContainer width="100%" height={110}>
          <PieChart>
            <Pie data={pieData} dataKey="value" cx="50%" cy="50%" innerRadius={28} outerRadius={44} paddingAngle={3}>
              {pieData.map((d, i) => <Cell key={i} fill={d.fill} />)}
            </Pie>
            <Legend iconSize={8} wrapperStyle={{ fontSize: 10, color: 'var(--text-secondary)' }} />
            <Tooltip {...CHART_TOOLTIP_STYLE} formatter={(v: number) => [`${v} min`, '']} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Radar Chart */}
      {routes.length >= 2 && (
        <div style={sectionStyle}>
          <span style={titleStyle}>Route Comparison Radar</span>
          <ResponsiveContainer width="100%" height={140}>
            <RadarChart data={radarData} margin={{ top: 5, right: 20, bottom: 5, left: 20 }}>
              <PolarGrid stroke="var(--border)" />
              <PolarAngleAxis dataKey="metric" tick={{ fontSize: 9, fill: 'var(--text-muted)' }} />
              {fastest && <Radar name="Fastest" dataKey="fastest" stroke="var(--accent-amber)" fill="var(--accent-amber)" fillOpacity={0.15} />}
              {cheapest && <Radar name="Cheapest" dataKey="cheapest" stroke="var(--accent-coral)" fill="var(--accent-coral)" fillOpacity={0.15} />}
              {greenest && <Radar name="Greenest" dataKey="greenest" stroke="var(--accent-green)" fill="var(--accent-green)" fillOpacity={0.15} />}
              <Legend iconSize={7} wrapperStyle={{ fontSize: 9, color: 'var(--text-secondary)' }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Algorithm performance */}
      {algoData.length > 0 && (
        <div style={sectionStyle}>
          <span style={titleStyle}>Algorithm Performance (Nodes Expanded)</span>
          <ResponsiveContainer width="100%" height={80}>
            <BarChart data={algoData} margin={{ left: -10, right: 10 }}>
              <XAxis dataKey="name" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
              <YAxis hide />
              <Tooltip {...CHART_TOOLTIP_STYLE} formatter={(v: number) => [`${v} nodes`, 'Expanded']} />
              <Bar dataKey="nodes" radius={[4, 4, 0, 0]}>
                {algoData.map((d, i) => <Cell key={i} fill={d.fill} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
