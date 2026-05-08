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
