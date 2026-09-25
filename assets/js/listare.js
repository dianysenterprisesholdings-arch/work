/* ==========================================================================
   Emerald City — pagina de listare
   Filtrare si sortare pe cele 925 de unitati, integral in client. Datele vin
   o singura data ca JSON compact (~66 KB, ~12 KB gzip); dupa aceea nu mai
   exista nicio cerere. Randarea e paginata, ca sa nu punem 925 de randuri in
   DOM deodata.
   ========================================================================== */

(() => {
  'use strict';

  const $  = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  const EN = document.documentElement.lang === 'en';
  const A = document.body.dataset.assets || '../../';
  const euro   = n => EN ? '€' + new Intl.NumberFormat('en-GB').format(n) : new Intl.NumberFormat('ro-RO').format(n) + ' €';
  const mp     = n => new Intl.NumberFormat(EN ? 'en-GB' : 'ro-RO', { maximumFractionDigits: 1 }).format(n) + ' m²';
  const bloc   = c => c.replace(/^C/, '');
  const etajTxt = n => EN ? (n === 0 ? 'Ground floor' : 'Floor ' + n) : (n === 0 ? 'Parter' : 'Etaj ' + n);
  const ST = EN ? { disponibil: 'Available', rezervat: 'Reserved', vandut: 'Sold', in_curand: 'Coming soon' }
               : { disponibil: 'Disponibil', rezervat: 'Rezervat', vandut: 'Vândut', in_curand: 'În curând' };

  const PAS = 50;                       // randuri adaugate la fiecare "incarca"

  const stare = {
    camere: new Set(), etaj: new Set(), etapa: new Set(),
    status: new Set(), corp: new Set(), extra: new Set(), orientare: new Set(), tip: new Set(),
    pretMin: 0, pretMax: 130000, suMin: 36, text: '',
    sort: 'pret', dir: 'asc', limita: PAS, vedere: 'tabel'
  };

  let U = [], F = {};

  /* ---------------------------------------------------------- filtrare */
  const trece = u => {
    if (stare.camere.size && !stare.camere.has(String(u[F.camere]))) return false;
    if (stare.etaj.size   && !stare.etaj.has(String(u[F.etaj])))     return false;
    if (stare.etapa.size  && !stare.etapa.has(u[F.etapa]))           return false;
    if (stare.status.size && !stare.status.has(u[F.status]))         return false;
    if (stare.corp.size   && !stare.corp.has(bloc(u[F.corp])))       return false;
    if (stare.orientare.size && !stare.orientare.has(u[F.orientare])) return false;
    if (stare.tip.size && !stare.tip.has(u[F.tip])) return false;
    if (u[F.pret] > stare.pretMax) return false;
    if (u[F.pret] < stare.pretMin) return false;
    if (u[F.su]   < stare.suMin)   return false;
    for (const x of stare.extra) {
      if (x === 'balcon'  && !(u[F.balcon] > 0))    return false;
      if (x === 'curte'   && !(u[F.curte]  > 0))    return false;
      if (x === 'boxa'    && u[F.boxa]    !== 'da') return false;
      if (x === 'parcare' && u[F.parcare] !== 'da') return false;
    }
    if (stare.text) {
      // fiecare cuvant din cautare trebuie sa se regaseasca undeva pe rand
      const hay = [
        u[F.id], (EN ? 'building ' : 'bloc ') + bloc(u[F.corp]), u[F.tip], u[F.orientare],
        u[F.camere] + ' camere', u[F.camere] === 1 ? '1 camera' : '',
        etajTxt(u[F.etaj]), 'etaj ' + u[F.etaj], 'etapa ' + u[F.etapa],
        ST[u[F.status]]
      ].join(' ').toLowerCase()
       .normalize('NFD').replace(/[̀-ͯ]/g, '');
      if (!stare.text.every(t => hay.includes(t))) return false;
    }
    return true;
  };

  const CHEI = { id: 'id', corp: 'corp', etaj: 'etaj', tip: 'tip',
                 camere: 'camere', su: 'su', orientare: 'orientare', pret: 'pret' };
  const ppm = u => u[F.pret] / u[F.su];

  function rand(u) {
    const vandut = u[F.status] !== 'disponibil';
    return `<tr class="${vandut ? 'is-sold' : ''}">
      <td data-et="Cod"><a href="../${u[F.id].toLowerCase()}/">${u[F.id]}</a></td>
      <td data-et="Bloc">${bloc(u[F.corp])}</td>
      <td data-et="Etaj">${etajTxt(u[F.etaj])}</td>
      <td data-et="Tip">${u[F.tip]}</td>
      <td class="num" data-et="${EN ? 'Area' : 'Suprafață'}">${mp(u[F.su])}</td>
      <td data-et="Orientare">${u[F.orientare]}</td>
      <td class="num" data-et="${EN ? 'Price' : 'Preț'}"><b>${euro(u[F.pret])}</b></td>
      <td class="num" data-et="${EN ? 'Price/m²' : 'Preț/m²'}">${EN ? '€' + Math.round(ppm(u)) + '/m²' : Math.round(ppm(u)) + ' €/m²'}</td>
      <td class="st" data-et="Stare"><span class="ec-tag ec-tag--${u[F.status]}">${ST[u[F.status]]}</span></td>
    </tr>`;
  }

  function card(u) {
    const cam = EN ? (u[F.camere] === 1 ? '1 room' : u[F.camere] + ' rooms') : (u[F.camere] === 1 ? '1 cameră' : u[F.camere] + ' camere');
    return `<article class="ec-unit ${u[F.status] !== 'disponibil' ? 'is-sold' : ''}">
      <a class="ec-unit__link" href="../${u[F.id].toLowerCase()}/" aria-label="${EN ? 'Apartment' : 'Apartamentul'} ${u[F.id]}"></a>
      <div class="ec-unit__top">
        <span class="ec-unit__id">${u[F.id]}</span>
        <span class="ec-tag ec-tag--${u[F.status]}">${ST[u[F.status]]}</span>
      </div>
      <div class="ec-unit__t">${cam} · ${mp(u[F.su])}</div>
      <div class="ec-unit__meta">
        <span>${EN ? 'Building' : 'Blocul'} ${bloc(u[F.corp])}</span><span>${etajTxt(u[F.etaj])}</span>
        <span>Tip ${u[F.tip]}</span><span>${u[F.orientare]}</span>
      </div>
      <div class="ec-unit__foot">
        <span class="ec-unit__price">${euro(u[F.pret])}</span>
        <span class="ec-unit__ppm">${EN ? '€' + Math.round(ppm(u)) + '/m²' : Math.round(ppm(u)) + ' €/m²'}</span>
      </div>
    </article>`;
  }

  function scrieActive() {
    const el = $('#fActive');
    if (!el) return;
    const n = ['camere','etaj','etapa','status','corp','extra','orientare','tip']
      .reduce((a, g) => a + stare[g].size, 0)
      + (stare.pretMax !== 130000 || stare.pretMin !== 0 ? 1 : 0)
      + (stare.suMin !== 36 ? 1 : 0);
    el.textContent = EN ? (n ? (n === 1 ? '1 active filter' : n + ' active filters') : 'No active filter')
                        : (n ? (n === 1 ? '1 criteriu activ' : n + ' criterii active') : 'Niciun criteriu activ');
    el.classList.toggle('is-on', n > 0);
  }

  function deseneaza() {
    scrieActive();
    const semn = stare.dir === 'asc' ? 1 : -1;
    const val = stare.sort === 'ppm' ? ppm : (u => u[F[CHEI[stare.sort]]]);
    const gasite = U.filter(trece).sort((a, b) => {
      const x = val(a), y = val(b);
      return (typeof x === 'number' ? x - y : String(x).localeCompare(String(y))) * semn;
    });

    $('#fCount').textContent = gasite.length === 1
      ? (EN ? '1 apartment matches the criteria' : '1 apartament corespunde criteriilor')
      : gasite.length
        ? (EN ? `${gasite.length} apartments match the criteria` : `${gasite.length} apartamente corespund criteriilor`)
        : (EN ? 'No apartment matches the criteria.' : 'Niciun apartament nu corespunde criteriilor.');

    const gol = $('#fEmpty');
    if (gol) {
      if (gasite.length) gol.innerHTML = '';
      else {
        // arat ce s-ar intampla daca relaxez fiecare filtru pe rand
        const sug = [];
        const fara = cheie => {
          const copie = { ...stare, [cheie]: cheie === 'pretMax' ? 130000
                        : cheie === 'suMin' ? 36 : new Set() };
          const salvat = stare[cheie];
          stare[cheie] = copie[cheie];
          const n = U.filter(trece).length;
          stare[cheie] = salvat;
          return n;
        };
        const etichete = EN ? { camere: 'number of rooms', etaj: 'floor', etapa: 'phase', status: 'status', corp: 'building', extra: 'features',
                                orientare: 'orientation', tip: 'layout', pretMax: 'budget', suMin: 'minimum area' }
                          : { camere: 'numărul de camere', etaj: 'etajul', etapa: 'etapa',
                           status: 'starea', corp: 'blocul', extra: 'dotările',
                           orientare: 'orientarea', tip: 'compartimentarea',
                           pretMax: 'bugetul', suMin: 'suprafața minimă' };
        for (const k of Object.keys(etichete)) {
          const activ = stare[k] instanceof Set ? stare[k].size
                      : (k === 'pretMax' ? (stare.pretMax !== 130000 || stare.pretMin !== 0)
                                         : stare.suMin !== 36);
          if (!activ) continue;
          const n = fara(k);
          if (n > 0) sug.push(`<button class="ec-btn ec-btn--out" data-relax="${k}">${EN ? 'Drop' : 'Renunță la'} ${etichete[k]} · ${n} ${EN ? 'results' : 'rezultate'}</button>`);
        }
        gol.innerHTML = `<div class="ec-empty">
          <p>${EN ? 'No apartment matches all the criteria.' : 'Niciun apartament nu corespunde tuturor criteriilor.'}</p>
          <p style="margin-top:.4rem">Relaxează unul dintre ele:</p>
          <div class="ec-empty__s">${sug.join('') || `<button class="ec-btn ec-btn--brass" data-relax="tot">${EN ? 'Reset filters' : 'Resetează filtrele'}</button>`}</div>
        </div>`;
      }
    }

    const vizibile = gasite.slice(0, stare.limita);
    const carduri = $('#fCards');
    if (stare.vedere === 'carduri' && carduri) {
      carduri.innerHTML = vizibile.map(card).join('');
      $('#fBody').innerHTML = '';
    } else {
      $('#fBody').innerHTML = vizibile.map(rand).join('');
      if (carduri) carduri.innerHTML = '';
    }

    const more = $('#fMore');
    more.style.display = gasite.length > vizibile.length ? '' : 'none';
    const rest = Math.min(PAS, gasite.length - vizibile.length);
    more.textContent = EN ? `${rest} more ${rest === 1 ? 'apartment' : 'apartments'}` : `Încă ${rest} ${rest === 1 ? 'apartament' : 'apartamente'}`;

    scrieURL();
  }

  /* ------------------------------------------------- starea in adresa */
  function scrieURL() {
    const p = new URLSearchParams();
    ['camere','etaj','etapa','status','corp','extra','orientare','tip'].forEach(g => {
      if (stare[g].size) p.set(g, [...stare[g]].join(','));
    });
    if (stare.pretMin !== 0) p.set('pret-min', stare.pretMin);
    if (stare.pretMax !== 130000) p.set('pret-max', stare.pretMax);
    if (stare.suMin !== 36) p.set('su-min', stare.suMin);
    const q = p.toString();
    history.replaceState(null, '', q ? '?' + q : location.pathname);
  }

  function citesteURL() {
    const p = new URLSearchParams(location.search);
    ['camere','etaj','etapa','status','corp','extra','orientare','tip'].forEach(g => {
      const v = p.get(g);
      if (v) v.split(',').forEach(x => stare[g].add(x));
    });
    if (p.get('pret-min')) stare.pretMin = +p.get('pret-min');
    if (p.get('pret-max')) stare.pretMax = +p.get('pret-max');
    if (p.get('su-min'))   stare.suMin   = +p.get('su-min');

    // marchez vizual butoanele care vin din adresa
    $$('.ec-chip[data-f]').forEach(b => {
      if (stare[b.dataset.f]?.has(b.dataset.v)) b.classList.add('is-on');
    });
    const sl = $('#fPret'), so = $('#fSu');
    sl.value = stare.pretMax; $('#oPret').textContent = euro(stare.pretMax);
    so.value = stare.suMin;   $('#oSu').textContent   = stare.suMin + ' m²';
  }

  /* ------------------------------------------------------------ legaturi */
  function leaga() {
    $$('.ec-chip[data-f]').forEach(btn => {
      btn.addEventListener('click', () => {
        const g = btn.dataset.f, v = btn.dataset.v;
        stare[g].has(v) ? stare[g].delete(v) : stare[g].add(v);
        btn.classList.toggle('is-on');
        stare.limita = PAS;
        deseneaza();
      });
    });

    $('#fPret').addEventListener('input', e => {
      stare.pretMax = +e.target.value;
      $('#oPret').textContent = euro(stare.pretMax);
      stare.limita = PAS; deseneaza();
    });
    $('#fSu').addEventListener('input', e => {
      stare.suMin = +e.target.value;
      $('#oSu').textContent = stare.suMin + ' m²';
      stare.limita = PAS; deseneaza();
    });

    $('#fReset').addEventListener('click', () => {
      ['camere','etaj','etapa','status','corp','extra','orientare','tip'].forEach(g => stare[g].clear());
      stare.pretMin = 0; stare.pretMax = 130000; stare.suMin = 36; stare.limita = PAS;
      $$('.ec-chip').forEach(b => b.classList.remove('is-on'));
      $('#fPret').value = 130000; $('#oPret').textContent = euro(130000);
      $('#fSu').value = 36; $('#oSu').textContent = '36 m²';
      deseneaza();
    });

    $('#fMore').addEventListener('click', () => { stare.limita += PAS; deseneaza(); });

    const cauta = $('#fSearch');
    if (cauta) {
      let t;
      cauta.addEventListener('input', () => {
        clearTimeout(t);
        t = setTimeout(() => {
          const v = cauta.value.trim().toLowerCase()
            .normalize('NFD').replace(/[̀-ͯ]/g, '');
          stare.text = v ? v.split(/\s+/) : '';
          stare.limita = PAS;
          deseneaza();
        }, 120);
      });
    }

    document.addEventListener('click', ev => {
      const b = ev.target.closest('[data-relax]');
      if (!b) return;
      const k = b.dataset.relax;
      if (k === 'tot') { $('#fReset').click(); return; }
      if (stare[k] instanceof Set) stare[k].clear();
      else if (k === 'pretMax') { stare.pretMax = 130000; stare.pretMin = 0; }
      else if (k === 'suMin') stare.suMin = 36;
      $$('.ec-chip[data-f="' + k + '"]').forEach(x => x.classList.remove('is-on'));
      $('#fPret').value = stare.pretMax; $('#oPret').textContent = euro(stare.pretMax);
      $('#fSu').value = stare.suMin; $('#oSu').textContent = stare.suMin + ' m²';
      stare.limita = PAS;
      deseneaza();
    });

    const sel = $('#fSort');
    if (sel) {
      sel.addEventListener('change', () => {
        const [s, d] = sel.value.split(':');
        stare.sort = s; stare.dir = d;
        $$('#fTable thead th').forEach(x => x.removeAttribute('data-dir'));
        const th = $(`#fTable thead th[data-s="${s}"]`);
        if (th) th.dataset.dir = d;
        deseneaza();
      });
    }
    $$('.ec-lst__view button').forEach(b => {
      b.addEventListener('click', () => {
        stare.vedere = b.dataset.view;
        $$('.ec-lst__view button').forEach(x => {
          const on = x === b;
          x.classList.toggle('is-on', on);
          x.setAttribute('aria-pressed', String(on));
        });
        $$('[data-view-pane]').forEach(pn => { pn.hidden = pn.dataset.viewPane !== stare.vedere; });
        try { localStorage.setItem('ec-vedere', stare.vedere); } catch (e) {}
        deseneaza();
      });
    });
    try {
      const v = localStorage.getItem('ec-vedere');
      // pe telefon tabelul e greu de citit: implicit carduri, pana cand vizitatorul alege altfel
      if (v === 'carduri' || (!v && matchMedia('(max-width: 46rem)').matches)) $('.ec-lst__view button[data-view="carduri"]')?.click();
    } catch (e) {}

    $$('#fTable thead th[data-s]').forEach(th => {
      th.addEventListener('click', () => {
        const s = th.dataset.s;
        if (stare.sort === s) stare.dir = stare.dir === 'asc' ? 'desc' : 'asc';
        else { stare.sort = s; stare.dir = 'asc'; }
        $$('#fTable thead th').forEach(x => x.removeAttribute('data-dir'));
        th.dataset.dir = stare.dir;
        if (sel) sel.value = `${stare.sort}:${stare.dir}`;
        deseneaza();
      });
    });
  }

  /* ---------------------------------------------------------------- init */
  fetch(A + 'assets/data/unitati.json')
    .then(r => r.json())
    .then(d => {
      d.campuri.forEach((n, i) => F[n] = i);
      U = d.unitati;
      citesteURL();
      leaga();
      deseneaza();
    })
    .catch(err => {
      console.error('Nu s-au putut încărca datele:', err);
      $('#fCount').textContent = EN ? 'The data could not be loaded.' : 'Datele nu au putut fi încărcate.';
    });

})();
