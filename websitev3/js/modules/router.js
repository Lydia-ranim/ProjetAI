let currentPage = 'landing';

function goTo(p) {
  document.querySelectorAll('.page').forEach(x => x.classList.remove('active'));
  const el = document.getElementById('page-' + p);
  if (!el) { document.getElementById('page-404').classList.add('active'); return; }
  el.classList.add('active');
  currentPage = p;
  window.scrollTo({ top: 0, behavior: 'smooth' });
  closeMob();
  syncNav();
  if (p === 'dashboard') {
    if (!dashMapInited) initDashMap();
    else if (dashMap) setTimeout(() => dashMap.invalidateSize(), 250);
  }
  if (p === 'landing') {
    if (!heroMapInited) initHeroMap();
    else if (heroMap) setTimeout(() => heroMap.invalidateSize(), 250);
  }
  if (p === 'explorer') initExplorer();
  if (p === 'profile') buildProfile();
}

window.addEventListener('resize', () => {
  if (dashMap) dashMap.invalidateSize();
  if (heroMap) heroMap.invalidateSize();
  if (expMap) expMap.invalidateSize();
});

function syncNav() {
  document.querySelectorAll('.nav-link[data-page]').forEach(l => {
    l.classList.toggle('active', l.dataset.page === currentPage);
  });
}

function toggleMobile() { document.getElementById('mob-menu').classList.toggle('open'); }
function closeMob() { document.getElementById('mob-menu').classList.remove('open'); }

function getNavHeight() {
  const raw = getComputedStyle(document.documentElement).getPropertyValue('--nav-h').trim();
  return parseInt(raw, 10) || 62;
}

function smoothScrollTo(el) {
  if (!el) return;
  const top = el.getBoundingClientRect().top + window.scrollY - getNavHeight();
  window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
}

function scrollF() { smoothScrollTo(document.getElementById('features-s')); }
