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

  const euro   = n => new Intl.NumberFormat('ro-RO').format(n) + ' €';
  const mp     = n => new Intl.NumberFormat('ro-RO', { maximumFractionDigits: 1 }).format(n) + ' m²';
  const bloc   = c => c.replace(/^C/, '');
  const etajTxt = n => n === 0 ? 'Parter' : 'Etaj ' + n;
  const ST = { disponibil: 'Disponibil', rezervat: 'Rezervat', vandut: 'Vândut', in_curand: 'În curând' };

  const PAS = 50;                       // randuri adaugate la fiecare "incarca"

  const stare = {
    camere: new Set(), etaj: new Set(), etapa: new Set(),
    status: new Set(), corp: new Set(), extra: new Set(),
    pretMin: 0, pretMax: 130000, suMin: 36, text: '',
    sort: 'pret', dir: 'asc', limita: PAS
  };

  let U = [], F = {};

  /* ---------------------------------------------------------- filtrare */
  const trece = u => {
    if (stare.camere.size && !stare.camere.has(String(u[F.camere]))) return false;
    if (stare.etaj.size   && !stare.etaj.has(String(u[F.etaj])))     return false;
    if (stare.etapa.size  && !stare.etapa.has(u[F.etapa]))           return false;
    if (stare.status.size && !stare.status.has(u[F.status]))         return false;
    if (stare.corp.size   && !stare.corp.has(bloc(u[F.corp])))       return false;
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
        u[F.id], 'bloc ' + bloc(u[F.corp]), u[F.tip], u[F.orientare],
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

  function rand(u) {
    const vandut = u[F.status] !== 'disponibil';
    return `<tr class="${vandut ? 'is-sold' : ''}">
      <td data-et="Cod"><a href="../${u[F.id].toLowerCase()}/">${u[F.id]}</a></td>
      <td data-et="Bloc">${bloc(u[F.corp])}</td>
      <td data-et="Etaj">${etajTxt(u[F.etaj])}</td>
      <td data-et="Tip">${u[F.tip]}</td>
      <td class="num" data-et="Camere">${u[F.camere]}</td>
      <td class="num" data-et="Suprafață">${mp(u[F.su])}</td>
      <td data-et="Orientare">${u[F.orientare]}</td>
      <td class="num" data-et="Preț">${euro(u[F.pret])}</td>
      <td class="st" data-et="Stare"><span class="ec-tag ec-tag--${u[F.status]}">${ST[u[F.status]]}</span></td>
    </tr>`;
  }

  function deseneaza() {
    const k = F[CHEI[stare.sort]];
    const semn = stare.dir === 'asc' ? 1 : -1;
    const gasite = U.filter(trece).sort((a, b) => {
      const x = a[k], y = b[k];
      return (typeof x === 'number' ? x - y : String(x).localeCompare(String(y))) * semn;
    });

    $('#fCount').textContent = gasite.length === 1
      ? '1 apartament corespunde criteriilor'
      : gasite.length
        ? `${gasite.length} apartamente corespund criteriilor`
        : 'Niciun apartament nu corespunde criteriilor.';

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
        const etichete = { camere: 'numărul de camere', etaj: 'etajul', etapa: 'etapa',
                           status: 'starea', corp: 'blocul', extra: 'dotările',
                           pretMax: 'bugetul', suMin: 'suprafața minimă' };
        for (const k of Object.keys(etichete)) {
          const activ = stare[k] instanceof Set ? stare[k].size
                      : (k === 'pretMax' ? (stare.pretMax !== 130000 || stare.pretMin !== 0)
                                         : stare.suMin !== 36);
          if (!activ) continue;
          const n = fara(k);
          if (n > 0) sug.push(`<button class="ec-btn ec-btn--out" data-relax="${k}">Renunță la ${etichete[k]} · ${n} rezultate</button>`);
        }
        gol.innerHTML = `<div class="ec-empty">
          <p>Niciun apartament nu corespunde tuturor criteriilor.</p>
          <p style="margin-top:.4rem">Relaxează unul dintre ele:</p>
          <div class="ec-empty__s">${sug.join('') || '<button class="ec-btn ec-btn--brass" data-relax="tot">Resetează filtrele</button>'}</div>
        </div>`;
      }
    }

    const vizibile = gasite.slice(0, stare.limita);
    $('#fBody').innerHTML = vizibile.map(rand).join('');

    const more = $('#fMore');
    more.style.display = gasite.length > vizibile.length ? '' : 'none';
    more.textContent = `Încarcă încă ${Math.min(PAS, gasite.length - vizibile.length)}`;

    scrieURL();
  }

  /* ------------------------------------------------- starea in adresa */
  function scrieURL() {
    const p = new URLSearchParams();
    ['camere','etaj','etapa','status','corp','extra'].forEach(g => {
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
    ['camere','etaj','etapa','status','corp','extra'].forEach(g => {
      const v = p.get(g);
      if (v) v.split(',').forEach(x => stare[g].add(x));
    });
    // link-uri scurte din subsol si din paginile de tipologie
    const tip = p.get('tip');
    if (tip) { stare.tipFiltru = tip; }
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
      ['camere','etaj','etapa','status','corp','extra'].forEach(g => stare[g].clear());
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

    $$('#fTable thead th[data-s]').forEach(th => {
      th.addEventListener('click', () => {
        const s = th.dataset.s;
        if (stare.sort === s) stare.dir = stare.dir === 'asc' ? 'desc' : 'asc';
        else { stare.sort = s; stare.dir = 'asc'; }
        $$('#fTable thead th').forEach(x => x.removeAttribute('data-dir'));
        th.dataset.dir = stare.dir;
        deseneaza();
      });
    });
  }

  /* ---------------------------------------------------------------- init */
  fetch('../../assets/data/unitati.json')
    .then(r => r.json())
    .then(d => {
      d.campuri.forEach((n, i) => F[n] = i);
      U = d.unitati;
      // filtrul pe tipologie vine din adresa, nu are buton propriu
      const p = new URLSearchParams(location.search).get('tip');
      if (p) U = U.filter(u => u[F.tip] === p);
      citesteURL();
      leaga();
      deseneaza();
    })
    .catch(err => {
      console.error('Nu s-au putut încărca datele:', err);
      $('#fCount').textContent = 'Datele nu au putut fi încărcate.';
    });

})();
