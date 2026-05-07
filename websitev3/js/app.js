/* ═══════════════════════════════════════════════════════════
   LYHLYH — app.js  (Entry point)
   Script load order in index.html must be:
     1. js/data/stations.js
     2. js/modules/notifications.js
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
  /* Sync nav highlight for the initial landing page */
  syncNav();

  /* Kick off the hero map slightly deferred so the DOM is painted first */
  setTimeout(initHeroMap, 200);
})();

/**
 * Custom number-input stepper (replaces the native spinner arrows).
 * Honors the input's step / min / max attributes; falls back to step=1.
 * Fires a `change` event so any existing onchange handlers still run.
 *
 * @param {string} id    Input element id.
 * @param {number} dir   +1 to increment, -1 to decrement.
 */
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
  /* Round to the precision implied by `step` (avoids 0.30000000004). */
  const decimals = ((input.step || '').split('.')[1] || '').length;
  input.value = decimals ? next.toFixed(decimals) : String(next);
  input.dispatchEvent(new Event('change', { bubbles: true }));
}
