/**
 * Hook: useKeyboardShortcuts
 * Global keyboard shortcuts for the application
 */

import { useEffect } from 'react';
import { useTransitStore } from '../store/transit-store';

export function useKeyboardShortcuts() {
  const {
    reset, toggleDarkMode, applyPreset, setShowShortcuts,
  } = useTransitStore();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const ctrl = e.ctrlKey || e.metaKey;

      // Ctrl shortcuts
      if (ctrl) {
        switch (e.key.toLowerCase()) {
          case 'r': e.preventDefault(); reset(); break;
          case 'd': e.preventDefault(); toggleDarkMode(); break;
          case '1': e.preventDefault(); applyPreset('fastest'); break;
          case '2': e.preventDefault(); applyPreset('cheapest'); break;
          case '3': e.preventDefault(); applyPreset('greenest'); break;
          case '4': e.preventDefault(); applyPreset('balanced'); break;
          case 'f': e.preventDefault(); document.getElementById('search-from')?.focus(); break;
        }
      }

      // Non-ctrl shortcuts
      if (!ctrl) {
        if (e.key === 'Escape') {
          setShowShortcuts(false);
        }
        if (e.key === '?' && e.shiftKey) {
          e.preventDefault();
          setShowShortcuts(true);
        }
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [reset, toggleDarkMode, applyPreset, setShowShortcuts]);
}
