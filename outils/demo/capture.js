// Outil de capture d'écran pour le guide (docs/images/captures/).
//
// 1. Lancer la démo : ./outils/demo/lancer_demo.sh   (active la route /api/demo-capture)
// 2. Ouvrir http://localhost:3001 dans Chrome, fenêtre réglée à 1440 × 900.
// 3. Ouvrir la console (F12), coller ce fichier, puis par exemple :
//        await __cap('05_etudiants_liste')                 // capture de l'écran visible
//        __mark([__byText('Ajouter un étudiant')]); await __cap('05_etudiants_liste')  // avec cadre rouge
// Les images sont écrites dans docs/images/captures/<nom>.jpg (1,5 × la résolution de l'écran).
// Après capture : relancer outils/doc-word/construire.sh pour régénérer le Word.
(async () => {
  if (!window.html2canvas) {
    const code = await fetch('/api/demo-capture').then((r) => r.text());
    const s = document.createElement('script');
    s.textContent = code;
    document.head.appendChild(s);
  }
  if (!document.getElementById('__capstyle')) {
    const st = document.createElement('style');
    st.id = '__capstyle';
    // z-index sur les puces MUI : sans cela, html2canvas efface leur texte.
    st.textContent = '.MuiChip-root{position:relative!important;z-index:1!important} nextjs-portal{display:none!important}';
    document.head.appendChild(st);
  }
  window.__S = (ms) => new Promise((r) => setTimeout(r, ms));
  window.__byText = (txt, sel = 'button,a,[role=tab],[role=button],li') =>
    [...document.querySelectorAll(sel)].find((e) => e.textContent.trim().startsWith(txt));
  // Encadre en rouge (et numérote s'il y en a plusieurs) les éléments à mettre en évidence.
  window.__mark = (els) => {
    document.querySelectorAll('.__capbox').forEach((e) => e.remove());
    (els || []).forEach((e, i) => {
      if (!e) return;
      const r = e.getBoundingClientRect();
      const d = document.createElement('div');
      d.className = '__capbox';
      d.style.cssText = `position:fixed;z-index:99999;pointer-events:none;border:3px solid #E53935;border-radius:8px;left:${r.left - 5}px;top:${r.top - 5}px;width:${r.width + 4}px;height:${r.height + 4}px`;
      if (els.length > 1) {
        const b = document.createElement('div');
        b.textContent = i + 1;
        b.style.cssText = 'position:absolute;top:-13px;left:-13px;width:24px;height:24px;border-radius:12px;background:#E53935;color:#fff;font:bold 14px/24px Arial;text-align:center';
        d.appendChild(b);
      }
      document.body.appendChild(d);
    });
  };
  window.__cap = async (nom) => {
    await __S(500);
    const canvas = await html2canvas(document.body, {
      scale: 1.5, useCORS: true, backgroundColor: '#ffffff', logging: false,
      windowWidth: document.documentElement.clientWidth, windowHeight: window.innerHeight,
      width: window.innerWidth, height: window.innerHeight, x: window.scrollX, y: window.scrollY,
    });
    const image = canvas.toDataURL('image/jpeg', 0.88);
    const r = await fetch('/api/demo-capture', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nom, image }),
    });
    window.__mark([]);
    return r.status;
  };
  return 'outil de capture prêt';
})();
