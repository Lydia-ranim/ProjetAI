const explorerData = [
  {from:'Place des Martyrs', to:'Zeralda',      o:'M_MARTYRS',  d:'TR_ZERALDA',  time:55, cost:85, co2:50, tf:2, modes:['Métro','Train']},
  {from:'Agha',              to:'Boumendil',    o:'TR_AGHA',    d:'M_BOUMENDIL', time:22, cost:50, co2:10, tf:0, modes:['Métro']},
  {from:'Ruisseau',          to:'TP-TH',        o:'T_RUISSEAU', d:'T_TPTH',      time:18, cost:35, co2:8,  tf:0, modes:['Tram']},
  {from:'Hamma',             to:'Jardin',       o:'C_HAMMA',    d:'C_JARDIN',    time:12, cost:30, co2:5,  tf:0, modes:['Téléphérique']},
  {from:'Gare Centrale',     to:'El Harrach',   o:'TR_ALGER',   d:'TR_HARRACH',  time:28, cost:35, co2:20, tf:1, modes:['Train']},
  {from:'Tafourah',          to:'Bachdjarah',   o:'M_TAFOURAH', d:'M_BACH',      time:14, cost:50, co2:7,  tf:0, modes:['Métro']},
  {from:'Martyrs',           to:'Ruisseau',     o:'M_MARTYRS',  d:'T_RUISSEAU',  time:20, cost:60, co2:11, tf:1, modes:['Métro','Tram']},
  {from:'Zeralda',           to:'El Harrach',   o:'TR_ZERALDA', d:'TR_HARRACH',  time:38, cost:35, co2:28, tf:0, modes:['Train']},
];

let expFiltered  = [...explorerData];
let expMapInited = false;

function initExplorer() {
  renderExpCards(expFiltered);
  if (!expMapInited) {
    expMapInited = true;
    setTimeout(() => {
      expMap = L.map('explorer-map', {
        center:ALG_CENTER, zoom:11,
        maxBounds:ALG_BOUNDS,
        zoomControl:false, scrollWheelZoom:false,
        dragging:false, attributionControl:false,
      });
      L.tileLayer(TILE_URL, TILE_OPT).addTo(expMap);
      drawNetwork(expMap);
      expMap.invalidateSize();
    }, 100);
  }
}

function renderExpCards(data) {
  const g = document.getElementById('exp-grid');
  if (!g) return;
  g.innerHTML = data.map(r => `
    <div class="card" style="cursor:pointer;transition:transform var(--tr),border-color var(--tr),box-shadow var(--tr)"
         onclick="quickRoute('${r.o}','${r.d}')"
         onmouseenter="this.style.transform='translateY(-4px)';this.style.borderColor='rgba(198,183,226,.3)';this.style.boxShadow='0 8px 24px rgba(0,0,0,.3)'"
         onmouseleave="this.style.transform='none';this.style.borderColor='var(--border)';this.style.boxShadow='none'">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
        <div>
          <div style="font-weight:600;font-size:.9rem">${r.from}</div>
          <div style="font-size:.76rem;color:var(--text-t);margin:2px 0">→ ${r.to}</div>
        </div>
        <div class="chip chip-m" style="font-size:.7rem">${r.time} min</div>
      </div>
      <div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:10px">
        ${r.modes.map(m => `<div class="chip ${m==='Métro'?'chip-m':m==='Tram'?'chip-p':m==='Train'?'chip-k':'chip-c'}" style="font-size:.7rem">${m}</div>`).join('')}
      </div>
      <div class="divider" style="margin:8px 0"></div>
      <div style="display:flex;justify-content:space-between;font-size:.75rem;color:var(--text-s)">
        <span>${r.cost} DA</span><span>${r.co2}g CO₂</span><span>${r.tf} ${t('res.transfers')}</span>
      </div>
    </div>`).join('');
}

function filterExp(q) {
  expFiltered = explorerData.filter(r =>
    r.from.toLowerCase().includes(q.toLowerCase()) ||
    r.to.toLowerCase().includes(q.toLowerCase())   ||
    r.modes.some(m => m.toLowerCase().includes(q.toLowerCase()))
  );
  renderExpCards(expFiltered);
}

function sortExp(by) {
  const k = {time:'time', cost:'cost', co2:'co2', tf:'tf'}[by];
  renderExpCards([...expFiltered].sort((a,b) => a[k]-b[k]));
}
