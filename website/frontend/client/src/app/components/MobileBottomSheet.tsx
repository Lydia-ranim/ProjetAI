import { Drawer } from 'vaul';
import { PanelBottom, X } from 'lucide-react';
import ControlPanel from './ControlPanel';

export default function MobileBottomSheet() {
  return (
    <div className="mobile-only">
      <Drawer.Root>
        <Drawer.Trigger asChild>
          <button
            type="button"
            className="fixed left-1/2 bottom-12 z-[1200] -translate-x-1/2 rounded-full px-7 py-3.5 flex items-center gap-2.5"
            style={{
              background: 'linear-gradient(135deg, var(--accent-teal) 0%, var(--accent-blue) 100%)',
              border: 'none',
              boxShadow: '0 4px 20px color-mix(in oklab, var(--accent-blue) 28%, transparent), 0 0 0 0 color-mix(in oklab, var(--accent-blue) 20%, transparent)',
              color: '#0A1628',
            }}
            aria-label="Open route panel"
          >
            <PanelBottom className="w-5 h-5" style={{ color: '#0A1628' }} />
            <span className="text-sm font-bold tracking-wide">Route Panel</span>
          </button>
        </Drawer.Trigger>
        <Drawer.Portal>
          <Drawer.Overlay className="fixed inset-0 z-[1200]" style={{ background: 'rgba(0,0,0,0.55)' }} />
          <Drawer.Content
            className="fixed left-0 right-0 bottom-0 z-[1201] rounded-t-[22px] overflow-hidden"
            style={{
              background: 'color-mix(in oklab, var(--bg-panel) 92%, transparent)',
              borderTop: '1px solid var(--border-color)',
              backdropFilter: 'blur(22px)',
              WebkitBackdropFilter: 'blur(22px)',
              maxHeight: '84vh',
            }}
          >
            <div className="px-4 pt-3 pb-2 flex items-center gap-3">
              <div className="mx-auto h-1.5 w-12 rounded-full" style={{ background: 'color-mix(in oklab, var(--text-muted) 35%, transparent)' }} />
              <Drawer.Close asChild>
                <button
                  type="button"
                  className="ml-auto rounded-xl p-2"
                  style={{
                    border: '1px solid var(--border-color)',
                    background: 'color-mix(in oklab, var(--bg-elevated) 85%, transparent)',
                    color: 'var(--text-secondary)',
                  }}
                  aria-label="Close route panel"
                >
                  <X className="w-4 h-4" />
                </button>
              </Drawer.Close>
            </div>
            <div style={{ height: 'calc(84vh - 52px)', overflow: 'auto' }}>
              <ControlPanel />
            </div>
          </Drawer.Content>
        </Drawer.Portal>
      </Drawer.Root>
    </div>
  );
}
