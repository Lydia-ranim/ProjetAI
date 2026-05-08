/* ═══════════════════════════════════════════════════════════
   LYHLYH — Notifications (toast system)
═══════════════════════════════════════════════════════════ */

const NOTIF_ICONS = {
  success: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="8.5" stroke="#BEEEDB" stroke-width="1.4"/><path d="M6.5 10L9 12.5L13.5 8" stroke="#BEEEDB" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  info:    `<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="8.5" stroke="#C6B7E2" stroke-width="1.4"/><path d="M10 9.5v4M10 7.5v.5" stroke="#C6B7E2" stroke-width="1.6" stroke-linecap="round"/></svg>`,
  error:   `<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="8.5" stroke="#F2C4CE" stroke-width="1.4"/><path d="M7.5 7.5l5 5M12.5 7.5l-5 5" stroke="#F2C4CE" stroke-width="1.6" stroke-linecap="round"/></svg>`,
};

/**
 * Show a toast notification.
 * @param {string} title   Bold heading
 * @param {string} msg     Secondary body text
 * @param {'success'|'info'|'error'} type
 */
function notif(title, msg, type = 'success') {
  const icon = NOTIF_ICONS[type] || NOTIF_ICONS.info;
  const n = document.createElement('div');
  n.className = 'notif';
  n.innerHTML = `
    ${icon}
    <div style="flex:1;min-width:0">
      <div style="font-weight:600;font-size:.86rem;margin-bottom:2px">${title}</div>
      <div style="font-size:.78rem;color:var(--text-s)">${msg}</div>
    </div>
    <span style="cursor:pointer;color:var(--text-t);padding:2px;font-size:.8rem"
          onclick="this.parentElement.remove()">✕</span>`;
  document.getElementById('nc').appendChild(n);
  setTimeout(() => {
    n.style.animation = 'slideR .3s ease reverse';
    setTimeout(() => n.remove(), 300);
  }, 4000);
}
