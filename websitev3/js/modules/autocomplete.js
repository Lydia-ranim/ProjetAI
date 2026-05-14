/* ═══════════════════════════════════════════════════════════
   LYHLYH — Autocomplete: station search & keyboard nav
   Depends on: stations.js (STATIONS filled via loadAllStops)
               map.js (placeMarker), routing.js (setStatus)
═══════════════════════════════════════════════════════════ */

/* Selected station per field */
const acSel   = { origin: null, dest: null };
const acFocus = { origin: -1,   dest: -1 };

function acSearch(which, q) {
  const list = document.getElementById('ac-' + which);
  acSel[which] = null;
  if (!q || q.length < 1) { list.classList.remove('open'); return; }

  const matches = STATIONS
    .filter(s =>
      (s.name.toLowerCase().includes(q.toLowerCase()) ||
       s.short.toLowerCase().includes(q.toLowerCase())) &&
      isStopInService(normalizeModeKey(s.type))
    )
    .slice(0, 8);

  if (!matches.length) { list.classList.remove('open'); return; }

  acFocus[which] = -1;
  list.innerHTML = matches.map(s => `
    <div class="ac-item" data-id="${s.id}" onclick="selectStation('${which}','${s.id}')">
      <div class="ac-icon" style="background:${TYPE_COLOR[s.type]}22;color:${TYPE_COLOR[s.type]};font-size:.85rem">${s.icon}</div>
      <div>
        <div class="ac-name">${s.name}</div>
        <div class="ac-line">${s.line}</div>
      </div>
    </div>`).join('');
  list.classList.add('open');
}

function acKey(e, which) {
  const list  = document.getElementById('ac-' + which);
  const items = list.querySelectorAll('.ac-item');
  if (!list.classList.contains('open') || !items.length) return;

  if      (e.key === 'ArrowDown')  acFocus[which] = Math.min(acFocus[which] + 1, items.length - 1);
  else if (e.key === 'ArrowUp')    acFocus[which] = Math.max(acFocus[which] - 1, 0);
  else if (e.key === 'Enter') {
    if (acFocus[which] >= 0) selectStation(which, items[acFocus[which]].dataset.id);
    return;
  }
  else if (e.key === 'Escape') { list.classList.remove('open'); return; }

  items.forEach((it, i) => it.classList.toggle('focused', i === acFocus[which]));
}

function selectStation(which, id) {
  const s = SMAP[id];
  if (!s) return;
  const input = document.getElementById(which === 'origin' ? 'origin-input' : 'dest-input');
  input.value = s.name;
  acSel[which] = s;
  document.getElementById('ac-' + which).classList.remove('open');
  if (which === 'origin') placeMarker('origin', s.coords, s.name);
  else                    placeMarker('dest',   s.coords, s.name);
  setStatus();
}

document.addEventListener('click', e => {
  if (!e.target.closest('.autocomplete-wrap')) {
    document.querySelectorAll('.autocomplete-list').forEach(l => l.classList.remove('open'));
  }
});
