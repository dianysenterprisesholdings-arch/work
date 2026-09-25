/* ==========================================================================
   Emerald City — vizualizare pe ecran complet pentru imagini

   Se leaga singur la imaginile din galerii si din blocurile editoriale, cu
   conditia sa nu fie deja intr-o legatura. Grupurile se formeaza pe
   containerul comun, deci navigarea inainte-inapoi ramane in aceeasi galerie.

   Comenzi: sageti, Escape, clic in afara, glisare pe telefon.
   ========================================================================== */

(() => {
  'use strict';

  const SELECTOARE = '.ec-pgal, .ec-cams, .ec-gal, .ec-tipuri, .ec-split, .ec-blocks, [data-galerie]';
  const redus = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // adunam imaginile pe grupuri, sarind peste cele care sunt deja legaturi
  const grupuri = [];
  document.querySelectorAll(SELECTOARE).forEach(cont => {
    const imgs = [...cont.querySelectorAll('img')].filter(im => !im.closest('a'));
    if (imgs.length) grupuri.push(imgs);
  });
  if (!grupuri.length) return;

  let strat = null, poz = 0, grup = null;

  const construieste = () => {
    strat = document.createElement('div');
    strat.className = 'ec-lb';
    strat.setAttribute('role', 'dialog');
    strat.setAttribute('aria-modal', 'true');
    strat.setAttribute('aria-label', 'Imagine pe ecran complet');
    strat.innerHTML =
      '<button class="ec-lb__x" type="button" aria-label="' + (document.documentElement.lang === 'en' ? 'Close' : 'Închide') + '">' +
        '<i class="fa-solid fa-xmark" aria-hidden="true"></i></button>' +
      '<button class="ec-lb__n ec-lb__n--prev" type="button" aria-label="' + (document.documentElement.lang === 'en' ? 'Previous image' : 'Imaginea anterioară') + '">' +
        '<i class="fa-solid fa-chevron-left" aria-hidden="true"></i></button>' +
      '<button class="ec-lb__n ec-lb__n--next" type="button" aria-label="' + (document.documentElement.lang === 'en' ? 'Next image' : 'Imaginea următoare') + '">' +
        '<i class="fa-solid fa-chevron-right" aria-hidden="true"></i></button>' +
      '<figure class="ec-lb__f"><img alt=""><figcaption></figcaption></figure>';
    document.body.appendChild(strat);

    strat.querySelector('.ec-lb__x').addEventListener('click', inchide);
    strat.querySelector('.ec-lb__n--prev').addEventListener('click', e => { e.stopPropagation(); muta(-1); });
    strat.querySelector('.ec-lb__n--next').addEventListener('click', e => { e.stopPropagation(); muta(1); });
    strat.addEventListener('click', ev => { if (ev.target === strat || ev.target.tagName === 'FIGURE') inchide(); });

    // glisare pe telefon
    let x0 = null;
    strat.addEventListener('touchstart', e => { x0 = e.touches[0].clientX; }, { passive: true });
    strat.addEventListener('touchend', e => {
      if (x0 === null) return;
      const d = e.changedTouches[0].clientX - x0;
      if (Math.abs(d) > 45) muta(d < 0 ? 1 : -1);
      x0 = null;
    }, { passive: true });
  };

  const eticheta = im => {
    const fc = im.closest('figure')?.querySelector('figcaption');
    if (!fc) return im.getAttribute('alt') || '';
    // legenda are titlu si subtitlu in elemente separate; fara separator
    // textele s-ar lipi unul de altul
    const parti = [...fc.children].map(x => x.textContent.trim()).filter(Boolean);
    const t = parti.length ? parti.join(' · ') : fc.textContent;
    return t.replace(/\s+/g, ' ').trim();
  };

  const arata = () => {
    const im = grup[poz];
    const mare = strat.querySelector('img');
    // sursa mare: varianta fara sufixul de latime, daca exista
    mare.src = (im.currentSrc || im.src).replace(/-800(\.\w+)$/, '$1');
    mare.alt = im.getAttribute('alt') || '';
    const cap = strat.querySelector('figcaption');
    const t = eticheta(im);
    cap.textContent = grup.length > 1 ? `${t}${t ? ' · ' : ''}${poz + 1} / ${grup.length}` : t;
    strat.querySelectorAll('.ec-lb__n').forEach(b => {
      b.style.display = grup.length > 1 ? '' : 'none';
    });
  };

  const muta = d => { poz = (poz + d + grup.length) % grup.length; arata(); };

  function inchide() {
    strat.classList.remove('is-on');
    document.documentElement.style.overflow = '';
    document.removeEventListener('keydown', tasta);
  }

  function tasta(ev) {
    if (ev.key === 'Escape') inchide();
    else if (ev.key === 'ArrowRight') muta(1);
    else if (ev.key === 'ArrowLeft') muta(-1);
  }

  const deschide = (g, i) => {
    if (!strat) construieste();
    grup = g; poz = i;
    arata();
    strat.classList.add('is-on');
    if (redus) strat.style.transition = 'none';
    document.documentElement.style.overflow = 'hidden';
    document.addEventListener('keydown', tasta);
    strat.querySelector('.ec-lb__x').focus();
  };

  grupuri.forEach(g => g.forEach((im, i) => {
    im.classList.add('ec-zoom');
    im.addEventListener('click', ev => { ev.preventDefault(); deschide(g, i); });
    im.setAttribute('tabindex', '0');
    im.setAttribute('role', 'button');
    im.addEventListener('keydown', ev => {
      if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); deschide(g, i); }
    });
  }));
})();
