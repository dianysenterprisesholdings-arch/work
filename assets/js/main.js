/* ==========================================================================
   Emerald City — comportament
   Vanilla, fara dependinte. La trecerea in WordPress, singura schimbare este
   sursa datelor: fetch catre /wp-json/ec/v1/... in loc de fisierele statice.
   ========================================================================== */

(() => {
  'use strict';

  const $  = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const SVGNS = 'http://www.w3.org/2000/svg';

  const el = (name, attrs = {}, parent) => {
    const n = document.createElementNS(SVGNS, name);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  };

  const euro = n => new Intl.NumberFormat('ro-RO').format(n) + ' €';
  const mp   = n => new Intl.NumberFormat('ro-RO', { maximumFractionDigits: 1 }).format(n) + ' m²';
  const camere = n => n === 1 ? '1 cameră' : n + ' camere';
  // C1..C18 sunt coduri din proiect; comercial se numesc blocuri
  const bloc = cod => cod.replace(/^C/, '');

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------------------------------------------------------------- nav */
  const nav = $('#nav');
  const onScroll = () => nav.classList.toggle('is-stuck', window.scrollY > 40);
  addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ------------------------------------------------------------- reveal */
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      e.target.classList.add('is-in');
      io.unobserve(e.target);
    });
  }, { rootMargin: '0px 0px -12% 0px', threshold: .12 });
  $$('.ec-reveal').forEach(n => io.observe(n));

  /* ----------------------------------------------------------- contoare */
  const countIO = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      const node = e.target;
      countIO.unobserve(node);
      const target = parseFloat(node.dataset.count);
      const dec = parseInt(node.dataset.dec || '0', 10);
      if (reduced) { node.textContent = target.toFixed(dec).replace('.', ','); return; }
      const dur = 1400, t0 = performance.now();
      const step = (t) => {
        const p = Math.min((t - t0) / dur, 1);
        const v = target * (1 - Math.pow(1 - p, 3));      // easeOutCubic
        node.textContent = v.toFixed(dec).replace('.', ',');
        if (p < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });
  }, { threshold: .6 });
  $$('[data-count]').forEach(n => countIO.observe(n));

  /* =========================================================== TERENUL ==
     Cotele +-0,00 reale ale fiecarui corp (plansa A01, proiect 266/2023).
     Nu sunt inventate: definesc atat silueta din hero, cat si sectiunea.
     ==================================================================== */

  const COTE = {
    C1: 85.10, C2: 82.10, C3: 91.20, C4: 88.20, C5: 85.20, C6: 84.80,
    C7: 86.90, C8: 88.40, C9: 91.40, C10: 94.40, C11: 103.10, C12: 100.10,
    C13: 97.10, C14: 94.10, C15: 97.00, C16: 100.00, C17: 103.00, C18: 106.00
  };
  const ETAPA = c => (['C1','C2','C3','C4','C5','C6'].includes(c) ? 'I'
                    : ['C15','C16','C17','C18'].includes(c) ? 'III' : 'II');

  // ordonate dupa cota => citirea de la stanga la dreapta este chiar urcarea terenului
  const ORD = Object.keys(COTE).sort((a, b) => COTE[a] - COTE[b]);
  const COTA_MIN = 82.10, COTA_MAX = 106.00, H_CLADIRE = 18;

  /* --- silueta din hero ------------------------------------------------
     Proportii reale: amprenta unui corp are ~46 m lungime si 18 m inaltime,
     deci in sectiune este un volum LAT. Exagerare verticala 3x — conventie
     uzuala la sectiuni de sit, suficienta ca panta sa se citeasca.
     -------------------------------------------------------------------- */
  const EXAG = 4;        // hero
  const EXAG_SEC = 5;    // sectiunea cotata, mai expresiva (declarat pe figura)

  /* Curbe de nivel, nu cladiri: titlul vorbeste despre curbele terenului,
     iar sectiunea literala este explicata mai jos, in sectiunea dedicata.
     Cotele desenate sunt cele reale, din 2 in 2 metri, intre +76 si +108. */
  function drawHero() {
    const svg = $('#heroTerrain');
    if (!svg) return;
    const W = 1200, H = 420;
    const COTE_MIN = 76, COTE_MAX = 108, PAS = 2;
    const n = (COTE_MAX - COTE_MIN) / PAS;

    // relief sintetic, dar coerent: versantul urca spre dreapta-sus,
    // cu doua valuri, asa cum arata pantele din plansa (5%-18%)
    const inaltime = (t, k) =>
      Math.sin(t * Math.PI * 1.15 + .4) * (34 + k * 2.4)
      + Math.sin(t * Math.PI * 2.7 + 1.9) * (11 + k * .8)
      + t * 42;

    for (let k = 0; k <= n; k++) {
      const cota = COTE_MIN + k * PAS;
      const baza = H + 34 - k * (H / (n * .78));
      let d = '';
      for (let i = 0; i <= 60; i++) {
        const t = i / 60;
        const x = -30 + t * (W + 60);
        const y = baza - inaltime(t, k);
        d += (i ? 'L' : 'M') + x.toFixed(1) + ' ' + y.toFixed(1) + ' ';
      }
      const major = cota % 10 === 0;
      const p = el('path', {
        d,
        fill: 'none',
        stroke: major ? 'var(--ec-emerald-200)' : 'var(--ec-emerald-400)',
        'stroke-width': major ? 1.4 : .8,
        'stroke-opacity': (major ? .85 : .5) * (.5 + (k / n) * .5),
        'vector-effect': 'non-scaling-stroke'
      }, svg);

      if (!reduced) {
        const len = 1400;
        p.style.strokeDasharray = len;
        p.style.strokeDashoffset = len;
        p.style.animation = `ecDraw 2.2s var(--ec-ease) ${(.25 + k * .055).toFixed(2)}s forwards`;
      }
    }
  }

  /* --- sectiunea cotata ------------------------------------------------ */
  function drawTerrain() {
    const svg = $('#terrainFig');
    if (!svg) return;
    const W = 1200, H = 310, padB = 46, padL = 40;
    const L_CORP = 46, GAP = 20;
    const stepX = (W - padL) / ORD.length;
    const bw = stepX * (L_CORP / (L_CORP + GAP));
    const mToPx = (stepX / (L_CORP + GAP)) * EXAG_SEC;
    const baza = H - padB;
    const y = c => baza - (c - COTA_MIN) * mToPx;

    // linii de cota din 5 in 5 m
    for (let c = 85; c <= COTA_MAX + H_CLADIRE; c += 5) {
      const yy = y(c);
      if (yy < 4) continue;
      el('line', { x1: padL, y1: yy, x2: W, y2: yy, class: 'grid-l' }, svg);
      const t = el('text', { x: 2, y: yy + 2, class: 'axis' }, svg);
      t.textContent = '+' + c;
    }

    // profilul terenului, ca suprafata continua sub corpuri
    const pts = ORD.map((c, i) => [padL + i * stepX, y(COTE[c])]);
    let d = `M${padL} ${H} `;
    pts.forEach(([x, yy], i) => {
      d += `L${x.toFixed(1)} ${yy.toFixed(1)} L${(x + stepX).toFixed(1)} ${yy.toFixed(1)} `;
    });
    d += `L${W} ${H} Z`;
    el('path', { d, class: 'ground' }, svg);
    // linia de teren, ca treptele sa fie citibile
    el('path', { d, fill: 'none', stroke: 'var(--ec-ink-30)',
                 'stroke-width': .8, 'stroke-opacity': .55 }, svg);

    ORD.forEach((c, i) => {
      const x = padL + i * stepX + (stepX - bw) / 2;
      const yBot = y(COTE[c]);
      const h = H_CLADIRE * mToPx;
      const et = ETAPA(c);
      const g = el('g', { class: 'bld-g' }, svg);

      const cls = 'bld' + (et === 'II' ? ' bld--s2' : et === 'III' ? ' bld--s3' : '');
      el('rect', { x, y: yBot - h, width: bw, height: h, class: cls }, g);

      // cele 4 niveluri de apartamente (P+3E) peste cele 2 demisoluri
      for (let f = 1; f < 6; f++) {
        const yy = yBot - h * (f / 6);
        el('line', { x1: x, y1: yy, x2: x + bw, y2: yy,
                     stroke: 'rgba(237,232,224,.25)', 'stroke-width': .4 }, g);
      }

      const lb = el('text', { x: x + bw / 2, y: H - padB + 15, class: 'lbl' }, g);
      lb.textContent = c;
      const ct = el('text', { x: x + bw / 2, y: H - padB + 26, class: 'cota' }, g);
      ct.textContent = '+' + COTE[c].toFixed(2).replace('.', ',');
    });

    // cota de referinta a demisolurilor, marcata discret
    const t2 = el('text', { x: padL, y: 12, class: 'axis' }, svg);
    t2.textContent = 'Exagerare verticală 5× · înălțime corp 18,00 m · regim 2D+P+3E';
  }

  /* ======================================================== MASTERPLAN == */

  function drawMaster(corpuri) {
    const svg = $('#masterSvg');
    if (!svg) return;
    const byCode = Object.fromEntries(corpuri.map(c => [c.cod, c]));

    // grupez corpurile pe cele trei etape de constructie; sirurile lungi
    // se rup in randuri de maximum 5, ca planul sa ramana lizibil
    const ETAPE = [['I', 6], ['II', 8], ['III', 4]];
    const terase = [];
    const eticheta = [];
    ETAPE.forEach(([et]) => {
      const lista = corpuri.filter(c => c.etapa === et).map(c => c.cod);
      for (let i = 0; i < lista.length; i += 5) {
        terase.push(lista.slice(i, i + 5));
        eticheta.push(i === 0 ? 'ETAPA ' + et : '');
      }
    });

    /* Plan de sit: amprentele reale (adancime 14 m, lungime dedusa din AC),
       asezate pe curbe de nivel. Scara ~1,6 px/m. */
    const W = 760, H = 460, padX = 46, padT = 30;
    const ADANCIME = 14, GAP_M = 10;
    // scara se deduce din sirul cel mai lat, ca planul sa umple cadrul
    const latimeM = r => r.reduce((s2, c) => s2 + byCode[c].amprenta / ADANCIME, 0)
                       + GAP_M * (r.length - 1);
    const PX_M = (W - padX * 2) * .92 / Math.max(...terase.map(latimeM));
    const rowH = (H - padT - 46) / terase.length;

    // curbe de nivel de fundal — arce line, sugereaza versantul
    const contur = (yy, amp) =>
      `M${padX - 26} ${yy + amp} Q${W / 2} ${yy - amp} ${W - padX + 26} ${yy + amp * .6}`;

    terase.forEach((row, ri) => {
      const yC = padT + ri * rowH + rowH / 2;
      const amp = 9;

      if (eticheta[ri]) {
        el('path', { d: contur(yC - rowH * .52, amp * .5), class: 'terrace' }, svg);
        const tl = el('text', { x: 0, y: yC - rowH * .52 + 2, class: 'terrace-lbl' }, svg);
        tl.textContent = eticheta[ri];
      }

      // latimile reale ale corpurilor din acest sir
      const lung = row.map(c => byCode[c].amprenta / ADANCIME * PX_M);
      const total = lung.reduce((a, b) => a + b, 0);
      const gap = GAP_M * PX_M;
      let x = (W - (total + gap * (row.length - 1))) / 2;
      const h = Math.min(ADANCIME * PX_M * 1.25, rowH * .62);

      row.forEach((c, i) => {
        const d = byCode[c];
        const w = lung[i];
        // urmeaza curba: corpurile din centru stau putin mai sus
        const t = row.length > 1 ? (i / (row.length - 1)) * 2 - 1 : 0;
        const yy = yC - (1 - t * t) * amp * .8;

        const g = el('g', { class: 'corp', 'data-corp': c, tabindex: '0',
                            role: 'button', 'aria-label': `Blocul ${bloc(c)}` }, svg);

        const ratio = d.total ? d.disponibil / d.total : 0;
        let fill = '#7FA294', op = .4;
        if (d.in_curand === d.total)      { fill = '#7FA294'; op = .32; }
        else if (ratio > .45)             { fill = '#2E7D5B'; op = .92; }
        else if (ratio > .15)             { fill = '#B8863B'; op = .9;  }
        else                              { fill = '#8C3A33'; op = .85; }

        el('rect', { x: x.toFixed(1), y: (yy - h / 2).toFixed(1),
                     width: w.toFixed(1), height: h.toFixed(1),
                     fill, 'fill-opacity': op, rx: 1 }, g);
        const lbl = el('text', { x: (x + w / 2).toFixed(1), y: (yy + 2).toFixed(1) }, g);
        lbl.textContent = bloc(c);
        x += w + gap;
      });
    });

    // accesul din Strada Ion Nistor, la baza versantului
    el('path', {
      d: `M${padX - 30} ${H - 22} Q${W / 2} ${H - 40} ${W - padX + 30} ${H - 18}`,
      fill: 'none', stroke: 'rgba(255,255,255,.22)', 'stroke-width': 3.5
    }, svg);
    const rd = el('text', { x: padX - 26, y: H - 6, class: 'terrace-lbl' }, svg);
    rd.textContent = 'ACCES · STRADA ION NISTOR';

    // interactiune
    const panel = {
      stage: $('#cpStage'), code: $('#cpCode'), cota: $('#cpCota'),
      bar: $('#cpBar'), rows: $('#cpRows')
    };
    const show = (cod) => {
      const d = byCode[cod];
      if (!d) return;
      $$('.corp', svg).forEach(g => g.classList.toggle('is-active', g.dataset.corp === cod));
      panel.stage.textContent = 'Etapa ' + d.etapa;
      panel.code.textContent = 'Blocul ' + bloc(d.cod);
      panel.cota.textContent = d.total + ' apartamente · parter și 3 etaje';

      panel.bar.innerHTML = '';
      [['disponibil', 'var(--ec-available)'], ['rezervat', 'var(--ec-reserved)'],
       ['vandut', 'var(--ec-sold)'], ['in_curand', 'rgba(127,162,148,.5)']]
        .forEach(([k, col]) => {
          if (!d[k]) return;
          const i = document.createElement('i');
          i.style.width = (d[k] / d.total * 100) + '%';
          i.style.background = col;
          panel.bar.appendChild(i);
        });

      const rows = [
        ['Disponibile', d.disponibil || '—'],
        ['Rezervate', d.rezervat || '—'],
        ['Suprafețe', mp(d.su_min) + ' – ' + mp(d.su_max)],
        ['Preț de la', d.pret_min ? euro(d.pret_min) : '—']
      ];
      if (d.comercial) rows.push(['Spațiu comercial', mp(d.comercial)]);
      panel.rows.innerHTML = rows.map(([l, v]) =>
        `<div class="ec-master__row"><span>${l}</span><b>${v}</b></div>`).join('');
    };

    $$('.corp', svg).forEach(g => {
      const cod = g.dataset.corp;
      g.addEventListener('mouseenter', () => show(cod));
      g.addEventListener('focus', () => show(cod));
      g.addEventListener('click', () => show(cod));
      g.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); show(cod); }
      });
    });
    show('C1');
  }

  /* ========================================================== TIPOLOGII == */

  function drawTypes(units, F) {
    const grid = $('#typeGrid');
    if (!grid) return;
    const tipuri = {};
    units.forEach(u => {
      const t = u[F.tip];
      (tipuri[t] ||= { cod: t, camere: u[F.camere], n: 0, disp: 0, su: [], pret: [] });
      const g = tipuri[t];
      g.n++;
      g.su.push(u[F.su]);
      if (u[F.status] === 'disponibil') { g.disp++; g.pret.push(u[F.pret]); }
    });

    grid.innerHTML = Object.values(tipuri)
      .sort((a, b) => a.cod.localeCompare(b.cod))
      .map(t => `
        <a class="ec-type" href="#apartamente">
          <div class="ec-type__plan">${planSVG(t.camere)}</div>
          <div class="ec-type__code">${t.cod}</div>
          <div class="ec-type__rows">
            <div><span>Camere</span><b>${t.camere}</b></div>
            <div><span>Suprafață</span><b>${mp(Math.min(...t.su))} – ${mp(Math.max(...t.su))}</b></div>
            <div><span>Unități</span><b>${t.n}</b></div>
            <div><span>Disponibile</span><b>${t.disp}</b></div>
          </div>
          <span class="ec-card__price">${t.pret.length ? 'de la ' + euro(Math.min(...t.pret)) : '—'}</span>
        </a>`).join('');
  }

  /* Schita de plan, schematica. Se inlocuieste cu SVG-ul extras din
     planurile vectoriale ale biroului de design. */
  function planSVG(camere) {
    const rooms = camere === 1 ? [[4,4,40,34],[46,4,26,20],[46,26,26,12]]
                : camere === 2 ? [[4,4,42,40],[48,4,28,22],[48,28,28,16]]
                : [[4,4,38,40],[44,4,32,20],[44,26,15,18],[61,26,15,18]];
    return `<svg viewBox="0 0 80 48" aria-hidden="true">
      <rect class="wall" x="0" y="0" width="80" height="48"/>
      ${rooms.map(([x,y,w,h]) =>
        `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="var(--ec-sand)"/>`).join('')}
    </svg>`;
  }

  /* =========================================================== SELECTOR == */

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

      // Sortarea pura pe pret returna 6 garsoniere identice la parter.
      // Aleg cel mai ieftin exemplar din fiecare combinatie tipologie+etaj,
      // apoi completez pana la 6 — utilizatorul vede varietatea reala.
      const vazut = new Set();
      const divers = [];
      const rest = [];
      hits.slice().sort((a, b) => a[F.pret] - b[F.pret]).forEach(u => {
        const k = u[F.tip] + '|' + u[F.etaj];
        if (vazut.has(k)) { rest.push(u); return; }
        vazut.add(k); divers.push(u);
      });
      out.innerHTML = divers.concat(rest)
        .slice(0, 6)
        .sort((a, b) => a[F.pret] - b[F.pret])
        .map(u => `
          <a class="ec-card" href="#">
            <div class="ec-card__top">
              <span class="ec-card__id">${u[F.id]}</span>
              <span class="ec-tag ec-tag--disponibil">Disponibil</span>
            </div>
            <div class="ec-card__t">${camere(u[F.camere])} · ${mp(u[F.su])}</div>
            <div class="ec-card__meta">
              <span>Blocul ${bloc(u[F.corp])}</span>
              <span>${u[F.etaj] === 0 ? 'Parter' : 'Etaj ' + u[F.etaj]}</span>
              <span>${u[F.orientare]}</span>
              ${u[F.balcon] > 0 ? `<span>Balcon ${mp(u[F.balcon])}</span>` : ''}
              ${u[F.curte] > 0 ? `<span>Curte ${mp(u[F.curte])}</span>` : ''}
            </div>
            <div class="ec-card__foot">
              <span class="ec-card__price">${euro(u[F.pret])}</span>
              <span class="ec-card__ppm">${Math.round(u[F.pret] / u[F.su])} €/m²</span>
            </div>
          </a>`).join('');
    };

    const bindChips = (sel, key, cast) => {
      $$(sel + ' .ec-chip').forEach(btn => {
        btn.addEventListener('click', () => {
          const v = cast(btn.dataset.v);
          state[key].has(v) ? state[key].delete(v) : state[key].add(v);
          btn.classList.toggle('is-on');
          render();
        });
      });
    };
    bindChips('#fCamere', 'camere', Number);
    bindChips('#fEtaj', 'etaj', Number);

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

  /* ================================================================ INIT == */

  drawHero();

  Promise.all([
    fetch('assets/data/unitati.json').then(r => r.json()),
    fetch('assets/data/corpuri.json').then(r => r.json())
  ]).then(([data, corpuri]) => {
    // indexul campurilor: datele vin ca tablouri, nu ca obiecte (payload mai mic)
    const F = {};
    data.campuri.forEach((name, i) => F[name] = i);
    const units = data.unitati;

    drawMaster(corpuri);
    drawTypes(units, F);
    initFinder(units, F);
  }).catch(err => {
    console.error('Nu s-au putut încărca datele:', err);
    const c = $('#fCount');
    if (c) c.textContent = 'Datele nu au putut fi încărcate.';
  });

})();
