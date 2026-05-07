/* ═══════════════════════════════════════════════════════════
   LYHLYH — Theme: light/dark toggle, persisted in localStorage
   No layout / structure changes — just flips the `light-mode`
   class on <html> so tokens.css swaps every CSS variable.
═══════════════════════════════════════════════════════════ */

const THEME_KEY = 'lyhlyh-theme';

/**
 * Apply a theme by setting / removing the `light-mode` class on <html>.
 * Called both at page load (via the inline pre-paint script in index.html)
 * and from {@link toggleTheme}.
 *
 * @param {'light'|'dark'} mode
 */
function applyTheme(mode) {
  const root = document.documentElement;
  if (mode === 'light') root.classList.add('light-mode');
  else                  root.classList.remove('light-mode');
}

/** Toggle between light and dark mode and persist the preference. */
function toggleTheme() {
  const isLight  = document.documentElement.classList.contains('light-mode');
  const nextMode = isLight ? 'dark' : 'light';
  applyTheme(nextMode);
  try { localStorage.setItem(THEME_KEY, nextMode); } catch (_) { /* private mode */ }

  /* Map tiles can be CORS-cached; force Leaflet to recompute its size in
     case the page just reflowed (e.g. scrollbar appeared/disappeared). */
  if (typeof dashMap !== 'undefined' && dashMap) dashMap.invalidateSize();
  if (typeof heroMap !== 'undefined' && heroMap) heroMap.invalidateSize();
  if (typeof expMap  !== 'undefined' && expMap)  expMap.invalidateSize();
}
