import { useState } from 'react';
import { Search, RotateCcw, Settings, ChevronDown, ChevronUp, MapPin } from 'lucide-react';
import { useTransitStore } from '../store/transit-store';
import AutocompleteSearch from './AutocompleteSearch';
import TransportToggle from './TransportToggle';
import WeightSliders from './WeightSliders';
import AdvancedFilters from './AdvancedFilters';
import RouteCard from './RouteCard';
import PredictiveSuggestions from './PredictiveSuggestions';
import StatsDashboard from './StatsDashboard';

export default function ControlPanel() {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const {
    startStop, endStop, routes, isLoading,
    findRoutes, reset, error,
  } = useTransitStore();

  const canSearch = !!(startStop && endStop);

  return (
    <div
      className="h-full flex flex-col"
      style={{ background: 'transparent' }}
    >
      <div
        className="flex-1 overflow-y-auto p-4 space-y-4"
        style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(190, 238, 219, 0.18) transparent' }}
      >
        <div className="space-y-1">
          <div className="section-label">
            <MapPin className="w-3 h-3" style={{ color: 'var(--accent-teal)', flexShrink: 0 }} />
            Route Selection
          </div>
          <AutocompleteSearch />
        </div>

        <div className="flex gap-2">
          <button
            onClick={findRoutes}
            disabled={!canSearch || isLoading}
            className="btn-primary flex-1"
          >
            {isLoading ? (
              <>
                <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin inline-block" />
                Searching…
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                Show Routes
              </>
            )}
          </button>
          <button
            onClick={reset}
            className="btn-icon"
            aria-label="Reset"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>

        {error && (
          <div
            className="px-3 py-2.5 rounded-xl text-xs flex items-start gap-2"
            style={{
              background: 'color-mix(in oklab, var(--accent-coral) 10%, transparent)',
              color: 'var(--accent-coral)',
              border: '1px solid color-mix(in oklab, var(--accent-coral) 35%, transparent)',
            }}
          >
            <span className="flex-shrink-0 mt-0.5">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        <div>
          <div className="section-label">Transport Modes</div>
          <TransportToggle />
        </div>

        <div>
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-xs w-full transition-all rounded-lg px-2 py-1.5 hover:bg-white/4"
            style={{ color: showAdvanced ? 'var(--accent-teal)' : 'var(--text-muted)' }}
          >
            <Settings className="w-3.5 h-3.5" />
            <span className="font-semibold tracking-wide" style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Advanced Constraints (CSP)
            </span>
            {showAdvanced
              ? <ChevronUp className="w-3.5 h-3.5 ml-auto" />
              : <ChevronDown className="w-3.5 h-3.5 ml-auto" />
            }
          </button>
          {showAdvanced && (
            <div className="mt-2 animate-scale-in">
              <AdvancedFilters />
            </div>
          )}
        </div>

        <div>
          <div className="section-label">Weight Distribution</div>
          <WeightSliders />
        </div>

        {routes.length > 0 && (
          <div className="space-y-3">
            <div className="section-label">Routes Found ({routes.length})</div>
            <div className="space-y-2">
              {routes.map((route, i) => (
                <RouteCard key={route.id} route={route} index={i} />
              ))}
            </div>
            <PredictiveSuggestions />
          </div>
        )}

        {routes.length > 0 && <StatsDashboard />}

        {!startStop && !endStop && routes.length === 0 && (
          <div className="text-center py-10 space-y-3">
            <div className="text-4xl animate-float">🗺️</div>
            <div>
              <p className="text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
                Plan your journey
              </p>
              <p className="text-xs leading-relaxed" style={{ color: 'var(--text-muted)', maxWidth: 200, margin: '0 auto' }}>
                Search for stops or click twice on the map to set start and end points
              </p>
            </div>
            <div
              className="mx-auto px-3 py-1.5 rounded-full text-xs"
              style={{
                background: 'color-mix(in oklab, var(--accent-teal) 10%, transparent)',
                color: 'var(--accent-teal)',
                border: '1px solid color-mix(in oklab, var(--accent-teal) 28%, transparent)',
                width: 'fit-content',
              }}
            >
              ↓ Click on the map to begin
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
