/* ==========================================================================
   Emerald City — bara de acțiune lipită

   Apare după ce vizitatorul a parcurs o parte din pagină, ca să nu acopere
   antetul de la prima vedere. Pe telefon stă jos, pe toată lățimea; pe
   ecrane late se așază în dreapta, deasupra subsolului.

   Se ascunde singură când subsolul intră în ecran, ca să nu dubleze
   informațiile de contact de acolo.
   ========================================================================== */

(() => {
  'use strict';

  const TEL = '+40757707080';
  const WA = 'https://wa.me/40757707080';
  const PRAG = 0.22;              // cât din pagină trebuie parcurs

  // pe paginile de unitate exista deja o bara proprie, cu pretul
  if (document.querySelector('[data-sticky]')) return;

  const radacina = document.body.dataset.radacina || '';
  const EN = document.documentElement.lang === 'en';

  const bara = document.createElement('div');
  bara.className = 'ec-abar';
  bara.innerHTML =
    `<a class="ec-abar__a" href="tel:${TEL}">
       <i class="fa-solid fa-phone" aria-hidden="true"></i>
       <span><b data-scurt="${EN ? 'Call' : 'Sună'}">0757 70 70 80</b><em>${EN ? 'Mon–Fri 9–18' : 'Luni–vineri 9–18'}</em></span>
     </a>
     <a class="ec-abar__a ec-abar__a--wa" href="${WA}" target="_blank" rel="noopener">
       <i class="fa-brands fa-whatsapp" aria-hidden="true"></i>
       <span><b>WhatsApp</b><em>${EN ? 'We reply today' : 'Răspundem azi'}</em></span>
     </a>
     <a class="ec-abar__a ec-abar__a--pr" href="${radacina}${EN ? 'book-a-viewing' : 'programare-vizionare'}/">
       <i class="fa-solid fa-calendar-check" aria-hidden="true"></i>
       <span><b data-scurt="${EN ? 'Viewing' : 'Vizionare'}">${EN ? 'Book a viewing' : 'Programare vizionare'}</b><em>${EN ? '40 minutes, on site' : '40 de minute, la fața locului'}</em></span>
     </a>`;
  document.body.appendChild(bara);

  // pe ecrane inguste eticheta lunga nu incape, deci se schimba cu una scurta
  const mqScurt = matchMedia('(max-width: 46rem)');
  const etichete = [...bara.querySelectorAll('b[data-scurt]')].map(el => ({
    el, lung: el.textContent, scurt: el.dataset.scurt,
  }));
  const potrivesteEtichete = () => etichete.forEach(x => {
    x.el.textContent = mqScurt.matches ? x.scurt : x.lung;
  });
  potrivesteEtichete();
  mqScurt.addEventListener('change', potrivesteEtichete);

  let vizibila = false;
  const arata = v => {
    if (v === vizibila) return;
    vizibila = v;
    bara.classList.toggle('is-on', v);
    document.body.classList.toggle('are-abar', v);
  };

  // subsolul: cand intra in ecran, bara se retrage
  let laSubsol = false;
  const subsol = document.querySelector('.ec-foot');
  if (subsol) {
    new IntersectionObserver(es => {
      laSubsol = es[0].isIntersecting;
      if (laSubsol) arata(false);
    }, { rootMargin: '0px 0px -40% 0px' }).observe(subsol);
  }

  let inAsteptare = false;
  const verifica = () => {
    inAsteptare = false;
    const h = document.documentElement.scrollHeight - innerHeight;
    arata(!laSubsol && h > 400 && scrollY / h > PRAG);
  };
  addEventListener('scroll', () => {
    if (!inAsteptare) { inAsteptare = true; requestAnimationFrame(verifica); }
  }, { passive: true });
  verifica();
})();
