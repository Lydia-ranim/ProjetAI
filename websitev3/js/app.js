(function init() {
  syncNav();
  setTimeout(initHeroMap, 200);

  loadAllStops()
    .then(n => {
      if (typeof refreshDashStationMarkers === 'function') refreshDashStationMarkers();
      if (typeof refreshHeroMapAfterStops === 'function') refreshHeroMapAfterStops();
      if (!n) console.warn('LYHLYH: no stops — check GET /api/stops');
    })
    .catch(err => console.error('LYHLYH: stops load failed', err));
})();

function numStep(id, dir) {
  const input = document.getElementById(id);
  if (!input) return;
  const step = parseFloat(input.step) || 1;
  const cur  = parseFloat(input.value);
  let next   = (isNaN(cur) ? 0 : cur) + dir * step;
  const min  = parseFloat(input.min);
  const max  = parseFloat(input.max);
  if (!isNaN(min)) next = Math.max(next, min);
  if (!isNaN(max)) next = Math.min(next, max);
  const decimals = ((input.step || '').split('.')[1] || '').length;
  input.value = decimals ? next.toFixed(decimals) : String(next);
  input.dispatchEvent(new Event('change', { bubbles: true }));
}
