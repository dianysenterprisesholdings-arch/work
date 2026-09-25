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
  const mp   = n => new Intl.NumberFormat(EN ? 'en-GB' : 'ro-RO', { maximumFractionDigits: 1 }).format(n) + ' m²';
  const bloc = c => c.replace(/^C/, '');
  const etaj = n => EN ? (n === 0 ? 'Ground floor' : 'Floor ' + n) : (n === 0 ? 'Parter' : 'Etaj ' + n);
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

    // punctele forte: ce are fiecare unitate in plus fata de celelalte din comparatie
    const forte = u => {
      const b = [];
      const singur = k => gasite.filter(x => x[F[k]] > 0).length === 1 && u[F[k]] > 0;
      if (gasite.length > 1 && u[F.pret] === min('pret')) b.push(EN ? 'lowest price' : 'cel mai mic preț');
      if (gasite.length > 1 && ppm(u) === ppmMin) b.push(EN ? 'best price per m²' : 'cel mai bun preț/m²');
      if (gasite.length > 1 && u[F.su] === max('su')) b.push(EN ? 'largest area' : 'cea mai mare suprafață');
      if (singur('curte')) b.push(EN ? 'the only one with a garden' : 'singurul cu curte');
      else if (u[F.curte] > 0 && u[F.curte] === max('curte') && gasite.filter(x => x[F.curte] > 0).length > 1) b.push(EN ? 'largest garden' : 'cea mai mare curte');
      if (u[F.balcon] > 0 && u[F.balcon] === max('balcon') && gasite.length > 1) b.push(EN ? 'largest balcony' : 'cel mai mare balcon');
      if (u[F.etaj] === max('etaj') && gasite.length > 1 && u[F.etaj] > 0) b.push(EN ? 'highest floor' : 'etajul cel mai înalt');
      if (u[F.etaj] === 0 && gasite.filter(x => x[F.etaj] === 0).length === 1) b.push(EN ? 'ground floor, direct access' : 'parter, acces direct');
      if (u[F.boxa] === 'da' && gasite.filter(x => x[F.boxa] === 'da').length === 1) b.push(EN ? 'the only one with a storage room' : 'singurul cu boxă');
      if (u[F.parcare] === 'da' && gasite.filter(x => x[F.parcare] === 'da').length === 1) b.push(EN ? 'the only one with underground parking' : 'singurul cu parcare subterană');
      return b.map(x => `<span class="ec-cmp__badge">${x}</span>`).join('');
    };

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
          ${rand(EN ? 'Highlights' : 'Puncte forte', u => forte(u) || '<span class="ec-cmp__none">—</span>')}
          ${rand(EN ? 'Rooms' : 'Camere', u => u[F.camere])}
          ${rand(EN ? 'Layout' : 'Compartimentare', u => u[F.tip])}
          ${rand(EN ? 'Building' : 'Bloc', u => (EN ? 'Building ' : 'Blocul ') + bloc(u[F.corp]))}
          ${rand(EN ? 'Floor' : 'Etaj', u => etaj(u[F.etaj]))}
          ${rand(EN ? 'Orientation' : 'Orientare', u => EN ? String(u[F.orientare]).replace(/V/g, 'W') : u[F.orientare])}
          ${rand(EN ? 'Balcony' : 'Balcon', u => u[F.balcon] > 0 ? mp(u[F.balcon]) : '—')}
          ${rand(EN ? 'Garden' : 'Curte', u => u[F.curte] > 0 ? mp(u[F.curte]) : '—')}
          ${rand(EN ? 'Storage room' : 'Boxă', u => u[F.boxa] === 'da' ? (EN ? 'Available' : 'Disponibilă') : '—')}
          ${rand(EN ? 'Underground parking' : 'Parcare subterană', u => u[F.parcare] === 'da' ? (EN ? 'Yes' : 'Da') : (EN ? 'Surface' : 'Supraterană'))}
          ${rand(EN ? 'Phase' : 'Etapa', u => u[F.etapa])}
          ${rand(EN ? 'Status' : 'Stare', u => `<span class="ec-tag ec-tag--${u[F.status]}">${ST[u[F.status]]}</span>`)}
          ${rand('', u => `<a class="ec-btn ec-btn--out" href="../${CAT}/${u[F.id].toLowerCase()}/">${EN ? 'View' : 'Vezi'}</a>`)}
        </tbody>
      </table>
    </div>
    <p class="ec-calc__note">Valorile marcate cu verde sunt cele mai bune din comparație.</p>`;
  }).catch(() => {
    out.innerHTML = `<div class="ec-empty"><p>${EN ? 'The data could not be loaded.' : 'Datele nu au putut fi încărcate.'}</p></div>`;
  });

})();
