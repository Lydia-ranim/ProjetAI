const trips = [
  {from:'Martyrs',       to:'Zeralda',   time:55, co2:50, cost:85, modes:['Métro','Train']},
  {from:'Agha',          to:'Boumendil', time:22, co2:10, cost:50, modes:['Métro']},
  {from:'Ruisseau',      to:'TP-TH',     time:18, co2:8,  cost:35, modes:['Tram']},
  {from:'Hamma',         to:'Jardin',    time:12, co2:5,  cost:30, modes:['Téléphérique']},
  {from:'Gare Centrale', to:'Harrach',   time:28, co2:20, cost:35, modes:['Train']},
];

const achiev = [
  {icon:'🌿', title:'Voyageur Vert',   desc:'100 trajets profil écologique',  ok:true},
  {icon:'⚡', title:'Rapide',          desc:'50 requêtes profil rapide',       ok:true},
  {icon:'🚇', title:'Maître du Métro', desc:'200 segments métro',             ok:true},
  {icon:'🌍', title:'Héros Carbone',   desc:'50 kg CO₂ économisés',           ok:false},
  {icon:'🔄', title:'Connecteur',      desc:'100 trajets multi-modaux',       ok:false},
  {icon:'🏆', title:'Expert IA',       desc:'Essayé les 3 algorithmes',       ok:true},
];

const modeUse = [
  {m:'Métro',        p:52, c:'var(--mint)'},
  {m:'Tram',         p:20, c:'var(--purple)'},
  {m:'Train',        p:15, c:'var(--pink)'},
  {m:'Téléphérique', p:7,  c:'#FF7043'},
  {m:'Marche',       p:6,  c:'var(--text-s)'},
];

let profTabActive = 'hist';

function buildProfile() {
  const h = document.getElementById('prof-hist');
  if (h) h.innerHTML = trips.map(trip => `
    <div class="card" style="padding:16px;transition:transform var(--tr)"
         onmouseenter="this.style.transform='translateY(-2px)'" onmouseleave="this.style.transform='none'">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
        <div>
          <div style="font-weight:600;font-size:.9rem">${trip.from} → ${trip.to}</div>
          <div style="font-size:.75rem;color:var(--text-t);margin-top:2px">${t('prof.today')}</div>
          <div style="display:flex;gap:5px;margin-top:7px;flex-wrap:wrap">
            ${trip.modes.map(m => `<div class="chip ${m==='Métro'?'chip-m':m==='Tram'?'chip-p':m==='Train'?'chip-k':'chip-c'}" style="font-size:.68rem">${m}</div>`).join('')}
          </div>
        </div>
        <div style="text-align:right">
          <div style="font-weight:600;font-size:.9rem">${trip.time} min</div>
          <div style="font-size:.75rem;color:var(--text-s);margin-top:2px">${trip.cost} DA</div>
          <div style="font-size:.72rem;color:var(--mint);margin-top:1px">${trip.co2}g CO₂</div>
        </div>
      </div>
    </div>`).join('');

  const a = document.getElementById('prof-achiev');
  if (a) a.innerHTML = achiev.map(ac => `
    <div class="card" style="padding:18px;text-align:center;opacity:${ac.ok?1:.4};transition:transform var(--tr)"
         onmouseenter="this.style.transform='translateY(-3px)'" onmouseleave="this.style.transform='none'">
      <div style="font-size:2rem;margin-bottom:9px">${ac.icon}</div>
      <div style="font-weight:600;font-size:.86rem;margin-bottom:4px">${ac.title}</div>
      <div style="font-size:.74rem;color:var(--text-s)">${ac.desc}</div>
      ${ac.ok
        ? `<div class="chip chip-m" style="font-size:.68rem;display:inline-flex;margin-top:10px">${t('prof.completed')}</div>`
        : `<div class="chip" style="font-size:.68rem;display:inline-flex;margin-top:10px;background:var(--bg-3);color:var(--text-t)">🔒</div>`}
    </div>`).join('');

  const mb = document.getElementById('mode-b');
  if (mb) mb.innerHTML = modeUse.map(m => `
    <div>
      <div style="display:flex;justify-content:space-between;font-size:.78rem;margin-bottom:4px">
        <span>${m.m}</span><span style="color:${m.c}">${m.p}%</span>
      </div>
      <div class="progress-wrap">
        <div class="progress-bar" style="width:${m.p}%;background:${m.c}"></div>
      </div>
    </div>`).join('');
}

function profTab(tab, el) {
  profTabActive = tab;
  document.querySelectorAll('#page-profile .tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  const hist   = document.getElementById('prof-hist');
  const achiev = document.getElementById('prof-achiev');
  const stats  = document.getElementById('prof-stats');
  hist.style.display   = tab==='hist'   ? 'flex'  : 'none';
  if (tab==='hist') hist.style.flexDirection = 'column';
  achiev.style.display = tab==='achiev' ? 'grid'  : 'none';
  stats.style.display  = tab==='stats'  ? 'block' : 'none';
  if (tab==='hist') buildProfile();
}
