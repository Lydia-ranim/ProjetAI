function authTab(mode, el) {
  document.querySelectorAll('#auth-tabs .tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  const isLogin = mode === 'login';
  document.getElementById('login-f').style.display  = isLogin ? '' : 'none';
  document.getElementById('signup-f').style.display = isLogin ? 'none' : '';
  document.getElementById('auth-title').textContent  = isLogin ? t('auth.title') : t('cta.btn1');
  document.getElementById('auth-sub').textContent    = isLogin ? t('auth.sub') : t('cta.desc');
}

function doLogin() {
  const email = document.getElementById('le').value;
  const pass  = document.getElementById('lp').value;
  if (!email || !pass) {
    notif(t('notif.missing-fields-title'), t('notif.missing-fields-msg'), 'error');
    return;
  }
  notif(t('notif.login-title'), t('notif.login-msg'), 'success');
  setTimeout(() => goTo('dashboard'), 800);
}

function doSignup() {
  notif(t('notif.signup-title'), t('notif.signup-msg'), 'success');
  setTimeout(() => goTo('dashboard'), 800);
}

function pwStr(v) {
  const bar   = document.getElementById('pw-b');
  const label = document.getElementById('pw-l');
  let score = 0;
  if (v.length >= 6)           score++;
  if (v.length >= 10)          score++;
  if (/[A-Z]/.test(v))        score++;
  if (/[0-9!@#$%]/.test(v))  score++;
  const cfg = [
    [0, t('auth.pw-weak'), '#670627'],
    [1, t('auth.pw-weak'), '#670627'],
    [2, t('auth.pw-med'),  'var(--pink)'],
    [3, t('auth.pw-good'), 'var(--purple)'],
    [4, t('auth.pw-str'),  'var(--mint)'],
  ];
  const [, lbl, clr] = cfg[Math.min(score, 4)];
  bar.style.width      = (score * 25) + '%';
  bar.style.background = clr;
  label.textContent    = lbl;
  label.style.color    = clr;
}
