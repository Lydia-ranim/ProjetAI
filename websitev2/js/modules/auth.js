/* ═══════════════════════════════════════════════════════════
   LYHLYH — Auth: login, signup, password strength
   Depends on: notifications.js (notif), router.js (goTo)
═══════════════════════════════════════════════════════════ */

/**
 * Switch between Login and Signup tabs on the auth page.
 * @param {'login'|'signup'} mode
 * @param {HTMLElement} el   The clicked tab element
 */
function authTab(mode, el) {
  document.querySelectorAll('#auth-tabs .tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  const isLogin = mode === 'login';
  document.getElementById('login-f').style.display  = isLogin ? '' : 'none';
  document.getElementById('signup-f').style.display = isLogin ? 'none' : '';
  document.getElementById('auth-title').textContent  = isLogin ? 'Bon retour' : 'Créer un compte';
  document.getElementById('auth-sub').textContent    = isLogin ? 'Connectez-vous à LYHLYH' : 'Rejoignez la communauté LYHLYH';
}

/** Handle login form submission (mock). */
function doLogin() {
  const email = document.getElementById('le').value;
  const pass  = document.getElementById('lp').value;
  if (!email || !pass) { notif('Champs manquants', 'Veuillez remplir tous les champs', 'error'); return; }
  notif('Connecté !', 'Bienvenue, Ahmed 👋', 'success');
  setTimeout(() => goTo('dashboard'), 800);
}

/** Handle signup form submission (mock). */
function doSignup() {
  notif('Compte créé !', 'Bienvenue chez LYHLYH 🌿', 'success');
  setTimeout(() => goTo('dashboard'), 800);
}

/**
 * Live password strength indicator.
 * @param {string} v  Current password value
 */
function pwStr(v) {
  const bar   = document.getElementById('pw-b');
  const label = document.getElementById('pw-l');
  let score = 0;
  if (v.length >= 6)              score++;
  if (v.length >= 10)             score++;
  if (/[A-Z]/.test(v))           score++;
  if (/[0-9!@#$%]/.test(v))     score++;
  const cfg = [
    [0, 'Très faible', '#670627'],
    [1, 'Faible',      '#670627'],
    [2, 'Correct',     'var(--pink)'],
    [3, 'Bien',        'var(--purple)'],
    [4, 'Fort',        'var(--mint)'],
  ];
  const [, lbl, clr] = cfg[Math.min(score, 4)];
  bar.style.width      = (score * 25) + '%';
  bar.style.background = clr;
  label.textContent    = lbl;
  label.style.color    = clr;
}
