/* ==========================================================================
   Emerald City — meniu pe ecrane mici

   Butonul si panoul se construiesc din navigatia existenta, ca sa nu tinem
   doua liste de legaturi in paralel. Submeniurile (megamenu) devin grupuri
   care se deschid si se inchid la atingere.
   ========================================================================== */

(() => {
  'use strict';

  const antet = document.querySelector('.ec-nav__in');
  const meniu = document.querySelector('.ec-nav__menu');
  if (!antet || !meniu || document.querySelector('.ec-burger')) return;

  /* ---- butonul ---------------------------------------------------------- */
  const buton = document.createElement('button');
  buton.className = 'ec-burger';
  buton.type = 'button';
  const EN = document.documentElement.lang === 'en';
  buton.setAttribute('aria-label', EN ? 'Open menu' : 'Deschide meniul');
  buton.setAttribute('aria-expanded', 'false');
  buton.innerHTML = '<span></span><span></span><span></span>';
  antet.appendChild(buton);

  /* ---- panoul ----------------------------------------------------------- */
  const panou = document.createElement('div');
  panou.className = 'ec-mob';
  panou.setAttribute('aria-hidden', 'true');

  const grupuri = [];
  [...meniu.children].forEach(el => {
    if (el.classList.contains('ec-nav__has')) {
      // legatura principala plus elementele din megamenu
      const cap = el.querySelector(':scope > a');
      const sub = [...el.querySelectorAll('.ec-mega__i')].map(a => ({
        href: a.getAttribute('href'),
        titlu: a.querySelector('b')?.textContent.trim() || a.textContent.trim(),
        desc: a.querySelector('em')?.textContent.trim() || '',
      }));
      grupuri.push({ href: cap.getAttribute('href'), titlu: cap.textContent.trim(), sub });
    } else if (el.tagName === 'A') {
      grupuri.push({ href: el.getAttribute('href'), titlu: el.textContent.trim(), sub: [] });
    }
  });

  const radacina = document.body.dataset.radacina || '';
  panou.innerHTML =
    '<nav class="ec-mob__n">' +
    grupuri.map((g, i) => g.sub.length
      ? `<div class="ec-mob__g">
           <button class="ec-mob__t" type="button" aria-expanded="false" data-g="${i}">
             <span>${g.titlu}</span>
             <i class="fa-solid fa-chevron-down" aria-hidden="true"></i>
           </button>
           <div class="ec-mob__s" data-s="${i}">
             <a class="ec-mob__l ec-mob__l--tot" href="${g.href}">${EN ? 'All' : 'Toate'} — ${g.titlu}</a>
             ${g.sub.map(x => `<a class="ec-mob__l" href="${x.href}">
                 <b>${x.titlu}</b>${x.desc ? `<em>${x.desc}</em>` : ''}</a>`).join('')}
           </div>
         </div>`
      : `<a class="ec-mob__t ec-mob__t--simplu" href="${g.href}">${g.titlu}</a>`).join('') +
    '</nav>' +
    `<div class="ec-mob__f">
       <a class="ec-btn" href="${radacina}${EN ? 'book-a-viewing' : 'programare-vizionare'}/">
         <i class="fa-solid fa-calendar-check" aria-hidden="true"></i> ${EN ? 'Book a viewing' : 'Programare vizionare'}</a>
       <a class="ec-mob__tel" href="tel:+40757707080">
         <i class="fa-solid fa-phone" aria-hidden="true"></i> 0757 70 70 80</a>
       ${(document.querySelector('.ec-lang') || { outerHTML: '' }).outerHTML.replace('class="ec-lang"', 'class="ec-lang ec-lang--mob"')}
     </div>`;
  document.body.appendChild(panou);

  /* ---- deschidere si inchidere ------------------------------------------ */
  let deschis = false;
  const comuta = v => {
    deschis = v;
    panou.classList.toggle('is-on', v);
    buton.classList.toggle('is-on', v);
    buton.setAttribute('aria-expanded', String(v));
    buton.setAttribute('aria-label', EN ? (v ? 'Close menu' : 'Open menu') : (v ? 'Închide meniul' : 'Deschide meniul'));
    panou.setAttribute('aria-hidden', String(!v));
    document.body.classList.toggle('are-meniu', v);
    document.documentElement.style.overflow = v ? 'hidden' : '';
  };

  buton.addEventListener('click', () => comuta(!deschis));
  panou.addEventListener('click', ev => {
    const t = ev.target.closest('.ec-mob__t[data-g]');
    if (t) {
      const sub = panou.querySelector(`[data-s="${t.dataset.g}"]`);
      const on = t.getAttribute('aria-expanded') === 'true';
      t.setAttribute('aria-expanded', String(!on));
      sub.classList.toggle('is-on', !on);
      return;
    }
    if (ev.target.closest('a')) comuta(false);
  });
  addEventListener('keydown', ev => { if (ev.key === 'Escape' && deschis) comuta(false); });
  // la trecerea pe ecran lat panoul nu mai are ce cauta deschis
  matchMedia('(min-width: 64rem)').addEventListener('change', e => { if (e.matches) comuta(false); });
})();
