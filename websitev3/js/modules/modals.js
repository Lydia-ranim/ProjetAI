function openModal(id)  { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }
function closeBD(e, id) { if (e.target === e.currentTarget) closeModal(id); }
