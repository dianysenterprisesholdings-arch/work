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
    pretMax: 130000, suMin: 36,
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
    if (u[F.su]   < stare.suMin)   return false;
    for (const x of stare.extra) {
      if (x === 'balcon'  && !(u[F.balcon] > 0))    return false;
      if (x === 'curte'   && !(u[F.curte]  > 0))    return false;
      if (x === 'boxa'    && u[F.boxa]    !== 'da') return false;
      if (x === 'parcare' && u[F.parcare] !== 'da') return false;
    }
    return true;
  };

  const CHEI = { id: 'id', corp: 'corp', etaj: 'etaj', tip: 'tip',
                 camere: 'camere', su: 'su', orientare: 'orientare', pret: 'pret' };

  function rand(u) {
    const vandut = u[F.status] !== 'disponibil';
    return `<tr class="${vandut ? 'is-sold' : ''}">
      <td><a href="../apartamente/${u[F.id].toLowerCase()}/">${u[F.id]}</a></td>
      <td>${bloc(u[F.corp])}</td>
      <td>${etajTxt(u[F.etaj])}</td>
      <td>${u[F.tip]}</td>
      <td class="num">${u[F.camere]}</td>
      <td class="num">${mp(u[F.su])}</td>
      <td>${u[F.orientare]}</td>
      <td class="num">${euro(u[F.pret])}</td>
      <td class="st"><span class="ec-tag ec-tag--${u[F.status]}">${ST[u[F.status]]}</span></td>
    </tr>`;
  }

  function deseneaza() {
    const k = F[CHEI[stare.sort]];
    const semn = stare.dir === 'asc' ? 1 : -1;
    const gasite = U.filter(trece).sort((a, b) => {
      const x = a[k], y = b[k];
      return (typeof x === 'number' ? x - y : String(x).localeCompare(String(y))) * semn;
    });

    $('#fCount').textContent = gasite.length
      ? `${gasite.length} apartamente corespund criteriilor`
      : 'Niciun apartament nu corespunde. Încearcă să lărgești criteriile.';

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
      stare.pretMax = 130000; stare.suMin = 36; stare.limita = PAS;
      $$('.ec-chip').forEach(b => b.classList.remove('is-on'));
      $('#fPret').value = 130000; $('#oPret').textContent = euro(130000);
      $('#fSu').value = 36; $('#oSu').textContent = '36 m²';
      deseneaza();
    });

    $('#fMore').addEventListener('click', () => { stare.limita += PAS; deseneaza(); });

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
  fetch('../assets/data/unitati.json')
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
