/* ═══════════════════════════════════════════════════════════
   LYHLYH — Data: Stations, network lines, type colours
═══════════════════════════════════════════════════════════ */

const STATIONS = [
  {id:'M_MARTYRS',  name:'Place des Martyrs',         short:'Martyrs',        coords:[36.7894,3.0624], type:'metro', line:'Métro L1',       icon:'🚇'},
  {id:'M_TAFOURAH', name:'Tafourah - Grande Poste',   short:'Tafourah',       coords:[36.7768,3.0591], type:'metro', line:'Métro L1',       icon:'🚇'},
  {id:'M_BOUMENDIL',name:'Boumendil',                  short:'Boumendil',      coords:[36.7692,3.0541], type:'metro', line:'Métro L1',       icon:'🚇'},
  {id:'M_PREMIER',  name:'Premier Mai',               short:'Premier Mai',    coords:[36.7628,3.0488], type:'metro', line:'Métro L1',       icon:'🚇'},
  {id:'M_EL_BADR',  name:'Haï El Badr',               short:'El Badr',        coords:[36.7440,3.0880], type:'metro', line:'Métro L1',       icon:'🚇'},
  {id:'M_HARRACH',  name:'El Harrach (Métro)',         short:'Harrach M.',     coords:[36.7180,3.1025], type:'metro', line:'Métro L1',       icon:'🚇'},
  {id:'M_AIN',      name:'Aïn Naâdja',                 short:'Aïn Naâdja',     coords:[36.7068,3.0392], type:'metro', line:'Métro L1',       icon:'🚇'},
  {id:'M_BACH',     name:'Bachdjarah',                 short:'Bachdjarah',     coords:[36.7348,3.0958], type:'metro', line:'Métro L1',       icon:'🚇'},
  {id:'T_RUISSEAU', name:'Ruisseau (Tram)',            short:'Ruisseau',       coords:[36.7414,3.0631], type:'tram',  line:'Tramway T1',     icon:'🚊'},
  {id:'T_FUSILLES', name:'Les Fusillés (Tram)',        short:'Fusillés',       coords:[36.7505,3.0547], type:'tram',  line:'Tramway T1',     icon:'🚊'},
  {id:'T_TPTH',     name:'TP-TH (Tram)',               short:'TP-TH',          coords:[36.7580,3.0450], type:'tram',  line:'Tramway T1',     icon:'🚊'},
  {id:'TR_ALGER',   name:"Gare Centrale d'Alger",    short:'Gare Centrale',  coords:[36.7661,3.0664], type:'train', line:'Train banlieue', icon:'🚆'},
  {id:'TR_AGHA',    name:'Agha (Train)',               short:'Agha',           coords:[36.7430,3.0890], type:'train', line:'Train banlieue', icon:'🚆'},
  {id:'TR_HARRACH', name:'El Harrach (Train)',         short:'Harrach T.',     coords:[36.7180,3.1025], type:'train', line:'Train banlieue', icon:'🚆'},
  {id:'TR_ZERALDA', name:'Zeralda (Train)',            short:'Zeralda',        coords:[36.6980,2.8580], type:'train', line:'Train banlieue', icon:'🚆'},
  {id:'TR_THENIA',  name:'Thénia (Train)',             short:'Thénia',         coords:[36.7220,3.5500], type:'train', line:'Train banlieue', icon:'🚆'},
  {id:'C_HAMMA',    name:'Hamma (Téléphérique)',      short:'Hamma',          coords:[36.7682,3.0780], type:'cable', line:'Téléphérique',   icon:'🚡'},
  {id:'C_JARDIN',   name:"Jardin d'Essai (Téléph.)", short:"Jardin d'Essai", coords:[36.7745,3.0820], type:'cable', line:'Téléphérique',   icon:'🚡'},
];

/* Lookup map: id → station object */
const SMAP = {};
STATIONS.forEach(s => { SMAP[s.id] = s; });

/* Ordered line arrays (used for path finding + network drawing) */
const METRO_L1   = ['M_AIN','M_BACH','M_HARRACH','M_EL_BADR','M_PREMIER','M_BOUMENDIL','M_TAFOURAH','M_MARTYRS'];
const TRAM_T1    = ['T_RUISSEAU','T_FUSILLES','T_TPTH'];
const TRAIN_WEST = ['TR_ZERALDA','TR_ALGER','TR_AGHA','TR_HARRACH'];

/* Transport type → colour mapping */
const TYPE_COLOR = {
  metro: '#BEEEDB',
  tram:  '#C6B7E2',
  train: '#F2C4CE',
  cable: '#FF7043',
  walk:  'rgba(140,170,200,.5)',
};
