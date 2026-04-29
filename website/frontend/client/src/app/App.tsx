import { useEffect } from 'react';
import { Toaster } from 'sonner';
import { useTransitStore } from './store/transit-store';
import MapView from './components/MapView';
import ControlPanel from './components/ControlPanel';
import RouteDetails from './components/RouteDetails';
import ChartPanel from './components/ChartPanel';
import LoadingOverlay from './components/LoadingOverlay';
import InfoPanel from './components/InfoPanel';
import MobileBottomSheet from './components/MobileBottomSheet';
import KeyboardShortcuts from './components/KeyboardShortcuts';
import RouteActions from './components/RouteActions';
import ErrorBoundary from './components/ErrorBoundary';
import ShortcutsPanel from './components/ShortcutsPanel';
import RouteTimeline from './components/RouteTimeline';
import AIExplanation from './components/AIExplanation';
import EnhancedHeader from './components/EnhancedHeader';
import StartNavigationButton from './components/StartNavigationButton';

const RIGHT_TABS: { id: 'details' | 'timeline' | 'ai' | 'analytics'; label: string }[] = [
  { id: 'details',   label: 'Details'     },
  { id: 'timeline',  label: 'Timeline'    },
  { id: 'ai',        label: 'AI Insights' },
  { id: 'analytics', label: 'Analytics'   },
];

export default function App() {
  const { isLoading, isDarkMode, activeRightTab, setActiveTab } = useTransitStore();

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDarkMode);
    document.documentElement.classList.toggle('light', !isDarkMode);
  }, [isDarkMode]);

  return (
    <ErrorBoundary>
      <div
        className="app-layout"
        style={{ fontFamily: "'DM Sans', sans-serif" }}
      >
        <Toaster
          position="top-right"
          richColors
          toastOptions={{
            style: {
              background: 'var(--bg-panel)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-primary)',
              fontFamily: "'DM Sans', sans-serif",
            },
          }}
        />
        <KeyboardShortcuts />
        <EnhancedHeader />
        <div className="app-main">

          <aside className="control-panel">
            <ControlPanel />
          </aside>

          <main className="map-container">
            <MapView />
            <InfoPanel />
            {isLoading && <LoadingOverlay />}
            <StartNavigationButton />
          </main>

          <aside className="right-panel hidden xl:flex flex-col">
            <div className="tab-bar">
              {RIGHT_TABS.map(t => (
                <button
                  key={t.id}
                  className={`tab-btn ${activeRightTab === t.id ? 'active' : ''}`}
                  onClick={() => setActiveTab(t.id)}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div
              className="flex-1 overflow-y-auto"
              style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(190, 238, 219, 0.15) transparent' }}
            >
              {activeRightTab === 'details'   && <RouteDetails />}
              {activeRightTab === 'timeline'  && <RouteTimeline />}
              {activeRightTab === 'ai'        && <AIExplanation />}
              {activeRightTab === 'analytics' && <ChartPanel />}
            </div>

            <RouteActions />
          </aside>
        </div>

        <MobileBottomSheet />
        <ShortcutsPanel />
      </div>
    </ErrorBoundary>
  );
}