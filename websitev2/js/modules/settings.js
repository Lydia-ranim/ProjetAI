/* ═══════════════════════════════════════════════════════════
   LYHLYH — Settings page
   Depends on: notifications.js (notif)
═══════════════════════════════════════════════════════════ */

/**
 * Select a profile preset card in the settings page.
 * Highlights the card and syncs the weight sliders.
 * @param {HTMLElement} el  The clicked card element
 * @param {'fastest'|'cheapest'|'greenest'|'balanced'} p
 */
function selProf(el, p) {
  /* Reset all sibling cards */
  document.querySelectorAll('#page-settings .card .card').forEach(c => {
    c.style.borderColor = 'var(--border)';
    c.style.background  = 'var(--bg-2)';
  });
  /* Highlight selected card */
  el.style.borderColor = 'var(--purple)';
  el.style.background  = 'var(--purple-08)';

  /* Sync sliders */
  const pp = {
    fastest:  {w1:80, w2:10, w3:10},
    cheapest: {w1:10, w2:80, w3:10},
    greenest: {w1:10, w2:10, w3:80},
    balanced: {w1:33, w2:33, w3:34},
  };
  const v = pp[p];
  if (!v) return;
  document.getElementById('sw1').textContent = (v.w1/100).toFixed(2);
  document.getElementById('sw2').textContent = (v.w2/100).toFixed(2);
  document.getElementById('sw3').textContent = (v.w3/100).toFixed(2);
  const ranges = document.querySelectorAll('#page-settings input[type=range]');
  if (ranges[0]) ranges[0].value = v.w1;
  if (ranges[1]) ranges[1].value = v.w2;
  if (ranges[2]) ranges[2].value = v.w3;
}
