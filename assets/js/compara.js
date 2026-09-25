/* ==========================================================================
   Emerald City — comparator
   Citeste id-urile din adresa (sau din lista salvata local) si construieste
   tabelul. Adresa e sursa principala, ca lista sa poata fi trimisa altcuiva.
   ========================================================================== */

(() => {
  'use strict';

  const $ = (s, r = document) => r.querySelector(s);
  const EN = document.documentElement.lang === 'en';
  const A = document.body.dataset.assets || '../';
  const CAT = EN ? 'apartments-iasi' : 'apartamente-iasi';
  const euro = n => EN ? '€' + new Intl.NumberFormat('en-GB').format(n) : new Intl.NumberFormat('ro-RO').format(n) + ' €';
  const mp   = n => new Intl.NumberFormat('ro-RO', { maximumFractionDigits: 1 }).format(n) + ' m²';
  const bloc = c => c.replace(/^C/, '');
  const etaj = n => n === 0 ? 'Parter' : 'Etaj ' + n;
  const ST = EN ? { disponibil: 'Available', rezervat: 'Reserved', vandut: 'Sold', in_curand: 'Coming soon' }
               : { disponibil: 'Disponibil', rezervat: 'Rezervat', vandut: 'Vândut', in_curand: 'În curând' };

  const out = $('#cmpOut');

  const din_adresa = new URLSearchParams(location.search).get('u');
  let ids = din_adresa ? din_adresa.split(',').filter(Boolean) : [];
  if (!ids.length) {
    try { ids = JSON.parse(localStorage.getItem('ec-lista') || '[]'); } catch { ids = []; }
  }

  if (!ids.length) {
    out.innerHTML = `<div class="ec-empty">
      <p>${EN ? 'No apartment has been saved yet.' : 'Nu ai salvat încă niciun apartament.'}</p>
      <p style="margin-top:.5rem">Folosește butonul <b>Salvează</b> de pe paginile de unitate,
         apoi revino aici.</p>
      <div class="ec-empty__s"><a class="ec-btn ec-btn--brass" href="../apartamente-iasi/disponibilitate/">Vezi apartamentele</a></div>
    </div>`;
    return;
  }

  fetch(A + 'assets/data/unitati.json').then(r => r.json()).then(d => {
    const F = {};
    d.campuri.forEach((n, i) => F[n] = i);
    const gasite = ids
      .map(id => d.unitati.find(u => u[F.id].toLowerCase() === id.toLowerCase()))
      .filter(Boolean);

    if (!gasite.length) { out.innerHTML = `<div class="ec-empty"><p>${EN ? 'The apartments in the link were not found.' : 'Apartamentele din link nu au fost găsite.'}</p></div>`; return; }

    // marchez cea mai buna valoare pe randurile unde "mai mult/mai putin" inseamna ceva
    const min = k => Math.min(...gasite.map(u => u[F[k]]));
    const max = k => Math.max(...gasite.map(u => u[F[k]]));
    const ppm = u => Math.round(u[F.pret] / u[F.su]);
    const ppmMin = Math.min(...gasite.map(ppm));

    const cap = gasite.map(u =>
      `<th><a href="../${CAT}/${u[F.id].toLowerCase()}/">${u[F.id]}</a></th>`).join('');

    const rand = (eticheta, fn) =>
      `<tr><th>${eticheta}</th>${gasite.map(u => `<td>${fn(u)}</td>`).join('')}</tr>`;

    out.innerHTML = `<div class="ec-cmp">
      <table>
        <thead><tr><th>Apartament</th>${cap}</tr></thead>
        <tbody>
          ${rand(EN ? 'Price' : 'Preț', u => `<span class="${u[F.pret] === min('pret') ? 'best' : ''}">${euro(u[F.pret])}</span>`)}
          ${rand(EN ? 'Price per m²' : 'Preț pe m²', u => `<span class="${ppm(u) === ppmMin ? 'best' : ''}">${EN ? '€' + ppm(u) + '/m²' : ppm(u) + ' €/m²'}</span>`)}
          ${rand(EN ? 'Usable area' : 'Suprafață utilă', u => `<span class="${u[F.su] === max('su') ? 'best' : ''}">${mp(u[F.su])}</span>`)}
          ${rand('Camere', u => u[F.camere])}
          ${rand('Tipologie', u => u[F.tip])}
          ${rand('Bloc', u => 'Blocul ' + bloc(u[F.corp]))}
          ${rand('Etaj', u => etaj(u[F.etaj]))}
          ${rand('Orientare', u => u[F.orientare])}
          ${rand('Balcon', u => u[F.balcon] > 0 ? mp(u[F.balcon]) : '—')}
          ${rand('Curte', u => u[F.curte] > 0 ? mp(u[F.curte]) : '—')}
          ${rand(EN ? 'Storage room' : 'Boxă', u => u[F.boxa] === 'da' ? (EN ? 'Available' : 'Disponibilă') : '—')}
          ${rand(EN ? 'Underground parking' : 'Parcare subterană', u => u[F.parcare] === 'da' ? (EN ? 'Yes' : 'Da') : (EN ? 'Surface' : 'Supraterană'))}
          ${rand('Etapa', u => u[F.etapa])}
          ${rand('Stare', u => `<span class="ec-tag ec-tag--${u[F.status]}">${ST[u[F.status]]}</span>`)}
          ${rand('', u => `<a class="ec-btn ec-btn--out" href="../${CAT}/${u[F.id].toLowerCase()}/">${EN ? 'View' : 'Vezi'}</a>`)}
        </tbody>
      </table>
    </div>
    <p class="ec-calc__note">Valorile marcate cu verde sunt cele mai bune din comparație.</p>`;
  }).catch(() => {
    out.innerHTML = `<div class="ec-empty"><p>${EN ? 'The data could not be loaded.' : 'Datele nu au putut fi încărcate.'}</p></div>`;
  });

})();
