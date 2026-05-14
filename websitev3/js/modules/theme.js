const THEME_KEY = 'lyhlyh-theme';

function applyTheme(mode) {
  const root = document.documentElement;
  if (mode === 'light') root.classList.add('light-mode');
  else                  root.classList.remove('light-mode');
}

function toggleTheme() {
  const isLight  = document.documentElement.classList.contains('light-mode');
  const nextMode = isLight ? 'dark' : 'light';
  applyTheme(nextMode);
  try { localStorage.setItem(THEME_KEY, nextMode); } catch (_) {}
  if (typeof dashMap !== 'undefined' && dashMap) dashMap.invalidateSize();
  if (typeof heroMap !== 'undefined' && heroMap) heroMap.invalidateSize();
  if (typeof expMap  !== 'undefined' && expMap)  expMap.invalidateSize();
}
