/* ═══════════════════════════════════════════════════════════
   LYHLYH — Router: page navigation & nav sync
   Depends on: map.js (initDashMap, initHeroMap, initExplorer)
               profile.js (buildProfile)
═══════════════════════════════════════════════════════════ */

let currentPage = 'landing';

/**
 * Navigate to a named page.
 * @param {string} p  Page key: 'landing'|'dashboard'|'auth'|'explorer'|'profile'|'settings'
 */
function goTo(p) {
  document.querySelectorAll('.page').forEach(x => x.classList.remove('active'));
  const el = document.getElementById('page-' + p);
  if (!el) { document.getElementById('page-404').classList.add('active'); return; }
  el.classList.add('active');
  currentPage = p;
  window.scrollTo({ top: 0, behavior: 'smooth' });
  closeMob();
  syncNav();
  if (p === 'dashboard' && !dashMapInited) initDashMap();
  if (p === 'landing'   && !heroMapInited) initHeroMap();
  if (p === 'explorer')  initExplorer();
  if (p === 'profile')   buildProfile();
}

/** Highlight the active nav link to match current page. */
function syncNav() {
  const pageMap = {
    accueil:'landing', itinéraire:'dashboard',
    explorer:'explorer', profil:'profile', paramètres:'settings',
  };
  document.querySelectorAll('.nav-link').forEach(l => {
    l.classList.toggle('active', pageMap[l.textContent.trim().toLowerCase()] === currentPage);
  });
}

/** Toggle the mobile menu open/closed. */
function toggleMobile() { document.getElementById('mob-menu').classList.toggle('open'); }

/** Close the mobile menu. */
function closeMob() { document.getElementById('mob-menu').classList.remove('open'); }

/** Smooth-scroll to the features section on the landing page. */
function scrollF() { document.getElementById('features-s')?.scrollIntoView({ behavior: 'smooth' }); }
