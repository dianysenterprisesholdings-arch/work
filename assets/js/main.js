/* ==========================================================================
   Emerald City — comportament
   Vanilla, fara dependinte. La trecerea in WordPress, singura schimbare este
   sursa datelor: fetch catre /wp-json/ec/v1/... in loc de fisierele statice.
   ========================================================================== */

(() => {
  'use strict';

  const $  = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  const euro   = n => new Intl.NumberFormat('ro-RO').format(n) + ' €';
  const mp     = n => new Intl.NumberFormat('ro-RO', { maximumFractionDigits: 1 }).format(n) + ' m²';
  const camere = n => n === 1 ? '1 cameră' : n + ' camere';
  // C1..C18 sunt coduri din proiect; comercial se numesc blocuri
  const bloc   = cod => cod.replace(/^C/, '');

  /* ------------------------------------------------------------- reveal */
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      e.target.classList.add('is-in');
      io.unobserve(e.target);
    });
  }, { rootMargin: '0px 0px -10% 0px', threshold: .1 });
  const observa = () => $$('.ec-rv:not(.is-in)').forEach(n => io.observe(n));
  observa();

  /* ----------------------------------------------------------- parallax
     Imaginile din carduri se misca putin mai lent decat pagina. Subtil,
     dar e diferenta dintre "corect" si "scump". */
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!reduced) {
    const figuri = $$('.ec-block figure');
    let tichet = false;
    const muta = () => {
      const vh = innerHeight;
      figuri.forEach(f => {
        const r = f.getBoundingClientRect();
        if (r.bottom < -200 || r.top > vh + 200) return;
        const centru = (r.top + r.height / 2 - vh / 2) / vh;   // -1 .. 1
        const img = f.querySelector('img');
        if (img && !f.matches(':hover')) img.style.setProperty('--py', (centru * -14).toFixed(1) + 'px');
      });
      tichet = false;
    };
    addEventListener('scroll', () => {
      if (tichet) return;
      tichet = true;
      requestAnimationFrame(muta);
    }, { passive: true });
    muta();
  }

  /* ================================================ DISPONIBILITATE ==
     Carduri pe etape, cu bara de progres si contoare calculate — tiparul
     din Lapis, dar numerele nu sunt scrise de mana, ci derivate din date.
     ================================================================== */
  function drawStages(corpuri) {
    const grid = $('#stageGrid');
    if (!grid) return;

    const ETAPE = [
      { cod: 'I',   titlu: 'Etapa I',   sub: 'Blocurile 1–6' },
      { cod: 'II',  titlu: 'Etapa II',  sub: 'Blocurile 7–14' },
      { cod: 'III', titlu: 'Etapa III', sub: 'Blocurile 15–18' }
    ];

    grid.innerHTML = ETAPE.map(et => {
      const s = corpuri.filter(c => c.etapa === et.cod);
      const sum = k => s.reduce((a, c) => a + c[k], 0);
      const total = sum('total'), disp = sum('disponibil');
      const rez = sum('rezervat'), vand = sum('vandut'), soon = sum('in_curand');
      const preturi = s.map(c => c.pret_min).filter(Boolean);
      const vandutPct = total ? Math.round((vand + rez) / total * 100) : 0;

      const stare = soon === total ? 'În curând'
                  : disp === 0     ? 'Epuizat'
                  : vandutPct > 70 ? 'Ultimele unități'
                                   : 'În vânzare';

      const seg = (n, col) => n ? `<i style="width:${n / total * 100}%;background:${col}"></i>` : '';

      return `
        <article class="ec-stage ec-rv">
          <div class="ec-stage__top">
            <div>
              <div class="ec-stage__n">${et.titlu}</div>
              <div style="font-size:.8125rem;color:var(--ec-ink-40)">${et.sub}</div>
            </div>
            <span class="ec-stage__tag">${stare}</span>
          </div>

          <div class="ec-stage__bar">
            ${seg(vand, 'var(--ec-sold)')}
            ${seg(rez,  'var(--ec-reserved)')}
            ${seg(disp, 'var(--ec-available)')}
          </div>

          <div class="ec-stage__rows">
            <div class="ec-stage__row"><span>Total apartamente</span><b>${total}</b></div>
            <div class="ec-stage__row"><span>Disponibile</span><b>${disp || '—'}</b></div>
            <div class="ec-stage__row"><span>Rezervate</span><b>${rez || '—'}</b></div>
            <div class="ec-stage__row"><span>Vândute</span><b>${vand || '—'}</b></div>
          </div>

          <div class="ec-stage__price">
            ${preturi.length ? euro(Math.min(...preturi)) : 'Preț la cerere'}
            <small>${preturi.length ? 'preț de pornire, TVA inclus' : 'în pregătire'}</small>
          </div>

          <a class="ec-btn ec-btn--out" href="#apartamente">Vezi apartamentele</a>
        </article>`;
    }).join('');

    observa();
  }

  /* ========================================================= TIPOLOGII == */
  function drawTypes(units, F) {
    const grid = $('#typeGrid');
    if (!grid) return;

    const tipuri = {};
    units.forEach(u => {
      const t = u[F.tip];
      (tipuri[t] ||= { cod: t, camere: u[F.camere], n: 0, disp: 0, su: [], pret: [] });
      const g = tipuri[t];
      g.n++; g.su.push(u[F.su]);
      if (u[F.status] === 'disponibil') { g.disp++; g.pret.push(u[F.pret]); }
    });

    grid.innerHTML = Object.values(tipuri)
      .sort((a, b) => a.cod.localeCompare(b.cod))
      .map(t => `
        <a class="ec-type ec-rv" href="#apartamente">
          <div class="ec-type__plan">${planSVG(t.camere)}</div>
          <div class="ec-type__code">${t.cod}</div>
          <div class="ec-type__rows">
            <div><span>Camere</span><b>${t.camere}</b></div>
            <div><span>Suprafață</span><b>${mp(Math.min(...t.su))} – ${mp(Math.max(...t.su))}</b></div>
            <div><span>Disponibile</span><b>${t.disp} din ${t.n}</b></div>
          </div>
          <span class="ec-unit__price">${t.pret.length ? 'de la ' + euro(Math.min(...t.pret)) : '—'}</span>
        </a>`).join('');

    observa();
  }

  /* Schita schematica. Se inlocuieste cu SVG-ul extras din planurile
     vectoriale ale biroului de design, cand sunt disponibile. */
  function planSVG(nrCamere) {
    const rooms = nrCamere === 1 ? [[4,4,40,34],[46,4,26,20],[46,26,26,12]]
                : nrCamere === 2 ? [[4,4,42,40],[48,4,28,22],[48,28,28,16]]
                : [[4,4,38,40],[44,4,32,20],[44,26,15,18],[61,26,15,18]];
    return `<svg viewBox="0 0 80 48" aria-hidden="true">
      <rect class="wall" x="0" y="0" width="80" height="48"/>
      ${rooms.map(([x,y,w,h]) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="#fff"/>`).join('')}
    </svg>`;
  }

  /* ========================================================== SELECTOR == */
  function initFinder(units, F) {
    const state = { camere: new Set(), etaj: new Set(), pretMax: 130000 };
    const out = $('#fResults'), count = $('#fCount');

    const match = u =>
      u[F.status] === 'disponibil' &&
      (!state.camere.size || state.camere.has(u[F.camere])) &&
      (!state.etaj.size   || state.etaj.has(u[F.etaj])) &&
      u[F.pret] <= state.pretMax;

    const render = () => {
      const hits = units.filter(match);
      count.textContent = hits.length
        ? `${hits.length} apartamente disponibile corespund criteriilor`
        : 'Niciun apartament nu corespunde. Încearcă să lărgești criteriile.';

      // Sortarea pura pe pret returna sase garsoniere identice la parter.
      // Iau intai cel mai ieftin exemplar din fiecare tipologie+etaj.
      const vazut = new Set(), divers = [], rest = [];
      hits.slice().sort((a, b) => a[F.pret] - b[F.pret]).forEach(u => {
        const k = u[F.tip] + '|' + u[F.etaj];
        if (vazut.has(k)) { rest.push(u); return; }
        vazut.add(k); divers.push(u);
      });

      out.innerHTML = divers.concat(rest).slice(0, 6)
        .sort((a, b) => a[F.pret] - b[F.pret])
        .map(u => `
          <a class="ec-unit" href="#">
            <div class="ec-unit__top">
              <span class="ec-unit__id">${u[F.id]}</span>
              <span class="ec-tag ec-tag--disponibil">Disponibil</span>
            </div>
            <div class="ec-unit__t">${camere(u[F.camere])} · ${mp(u[F.su])}</div>
            <div class="ec-unit__meta">
              <span>Blocul ${bloc(u[F.corp])}</span>
              <span>${u[F.etaj] === 0 ? 'Parter' : 'Etaj ' + u[F.etaj]}</span>
              <span>${u[F.orientare]}</span>
              ${u[F.balcon] > 0 ? `<span>Balcon ${mp(u[F.balcon])}</span>` : ''}
              ${u[F.curte]  > 0 ? `<span>Curte ${mp(u[F.curte])}</span>`   : ''}
            </div>
            <div class="ec-unit__foot">
              <span class="ec-unit__price">${euro(u[F.pret])}</span>
              <span class="ec-unit__ppm">${Math.round(u[F.pret] / u[F.su])} €/m²</span>
            </div>
          </a>`).join('');
    };

    const bindChips = (sel, key) => {
      $$(sel + ' .ec-chip').forEach(btn => {
        btn.addEventListener('click', () => {
          const v = Number(btn.dataset.v);
          state[key].has(v) ? state[key].delete(v) : state[key].add(v);
          btn.classList.toggle('is-on');
          render();
        });
      });
    };
    bindChips('#fCamere', 'camere');
    bindChips('#fEtaj', 'etaj');

    const slider = $('#fPret'), o = $('#oPret');
    slider.addEventListener('input', () => {
      state.pretMax = +slider.value;
      o.textContent = euro(state.pretMax);
      render();
    });

    $('#fReset').addEventListener('click', () => {
      state.camere.clear(); state.etaj.clear(); state.pretMax = 130000;
      $$('.ec-chip').forEach(b => b.classList.remove('is-on'));
      slider.value = 130000; o.textContent = euro(130000);
      render();
    });

    render();
  }

  /* ============================================================== INIT == */
  Promise.all([
    fetch('assets/data/unitati.json').then(r => r.json()),
    fetch('assets/data/corpuri.json').then(r => r.json())
  ]).then(([data, corpuri]) => {
    // datele vin ca tablouri, nu ca obiecte, ca payload-ul sa ramana mic
    const F = {};
    data.campuri.forEach((name, i) => F[name] = i);
    const units = data.unitati;

    drawStages(corpuri);
    drawTypes(units, F);
    initFinder(units, F);
  }).catch(err => {
    console.error('Nu s-au putut încărca datele:', err);
    const c = $('#fCount');
    if (c) c.textContent = 'Datele nu au putut fi încărcate.';
  });

})();
