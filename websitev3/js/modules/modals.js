/* ═══════════════════════════════════════════════════════════
   LYHLYH — Modals
═══════════════════════════════════════════════════════════ */

/** Open a modal by its backdrop id. */
function openModal(id)  { document.getElementById(id).classList.add('open'); }

/** Close a modal by its backdrop id. */
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

/**
 * Close modal when clicking the backdrop (not the modal box itself).
 * Attach to backdrop's onclick: onclick="closeBD(event,'my-modal')"
 */
function closeBD(e, id) { if (e.target === e.currentTarget) closeModal(id); }
