/* ═══════════════════════════════════════════════════════════
   LYHLYH — app.js  (Entry point)
   Script load order in index.html must be:
     1. js/data/stations.js
     2. js/api.js
     3. js/transit-store.js
     4. js/modules/notifications.js
     3. js/modules/modals.js
     4. js/modules/auth.js
     5. js/modules/map.js
     6. js/modules/autocomplete.js
     7. js/modules/routing.js
     8. js/modules/results.js
     9. js/modules/explorer.js
    10. js/modules/profile.js
    11. js/modules/settings.js
    12. js/modules/router.js
    13. js/app.js          ← this file (runs last)
═══════════════════════════════════════════════════════════ */

/* ── Initialise on DOM ready ── */
(function init() {
  syncNav();

  setTimeout(initHeroMap, 200);

  loadAllStops()
    .then(n => {
      if (typeof refreshDashStationMarkers === 'function') refreshDashStationMarkers();
      if (typeof refreshHeroMapAfterStops === 'function') refreshHeroMapAfterStops();
      if (!n) console.warn('LYHLYH: aucun arrêt chargé — vérifiez GET /api/stops');
    })
    .catch(err => console.error('LYHLYH: échec chargement des arrêts', err));
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
