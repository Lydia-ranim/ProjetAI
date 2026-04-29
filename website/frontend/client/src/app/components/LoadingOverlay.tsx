import { useEffect, useRef } from 'react';

const STEPS = [
  { icon: '🔍', text: 'Running A* on Algiers graph...' },
  { icon: '🔄', text: 'Comparing Dijkstra...' },
  { icon: '↔️', text: 'Running Bidirectional search...' },
  { icon: '✅', text: '3 routes found!' },
];

export default function LoadingOverlay() {
  const stepRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let i = 0;
    const el = stepRef.current;
    if (!el) return;
    const update = () => {
      if (!stepRef.current) return;
      const s = STEPS[Math.min(i, STEPS.length - 1)];
      stepRef.current.textContent = `${s.icon} ${s.text}`;
      i++;
    };
    update();
    const interval = setInterval(update, 320);
    return () => clearInterval(interval);
  }, []);

  return (
    <div
      className="absolute inset-0 z-50 flex flex-col items-center justify-center gap-4"
      style={{ background: 'color-mix(in oklab, var(--bg-void) 88%, transparent)', backdropFilter: 'blur(8px)' }}
    >
      {/* Pulsing ring */}
      <div className="relative w-16 h-16">
        <div
          className="absolute inset-0 rounded-full animate-ping"
          style={{ background: 'color-mix(in oklab, var(--accent-teal) 22%, transparent)', animationDuration: '1s' }}
        />
        <div
          className="w-full h-full rounded-full flex items-center justify-center text-2xl"
          style={{ background: 'color-mix(in oklab, var(--accent-teal) 12%, transparent)', border: '2px solid var(--accent-teal)' }}
        >
          🚇
        </div>
      </div>

      {/* Step label */}
      <div
        ref={stepRef}
        className="text-sm font-mono transition-all"
        style={{ color: 'var(--accent-teal)', fontFamily: "'JetBrains Mono', monospace" }}
      />

      {/* Progress dots */}
      <div className="flex gap-2">
        {[0, 1, 2].map(i => (
          <div
            key={i}
            className="w-1.5 h-1.5 rounded-full animate-pulse"
            style={{ background: 'var(--accent-teal)', animationDelay: `${i * 200}ms` }}
          />
        ))}
      </div>
    </div>
  );
}
