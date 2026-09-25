/* ==========================================================================
   Emerald City — indicator de parcurgere

   O linie subtire in capul paginii, care arata cat a fost parcurs. Se
   actualizeaza pe cadru, nu la fiecare eveniment de derulare.
   ========================================================================== */

(() => {
  'use strict';

  const bara = document.querySelector('[data-prog]');
  if (!bara) return;

  let inAsteptare = false;

  const deseneaza = () => {
    inAsteptare = false;
    const h = document.documentElement.scrollHeight - innerHeight;
    // pe paginile scurte indicatorul nu are ce arata
    if (h < 400) { bara.style.width = '0'; return; }
    bara.style.width = Math.min(scrollY / h, 1) * 100 + '%';
  };

  addEventListener('scroll', () => {
    if (!inAsteptare) { inAsteptare = true; requestAnimationFrame(deseneaza); }
  }, { passive: true });
  addEventListener('resize', deseneaza, { passive: true });
  deseneaza();
})();
