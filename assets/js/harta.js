/* ==========================================================================
   Emerald City — hartă interactivă
   Leaflet + tile-uri OpenStreetMap. Biblioteca se încarcă abia când harta
   intră în ecran, ca să nu coste nimic pe restul paginii.
   Coordonatele vin din assets/data/distante.json, calculate cu OSRM/Nominatim.
   ========================================================================== */

(() => {
  'use strict';

  const gazda = document.getElementById('ecHarta');
  if (!gazda) return;

  const CSS = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css';
  const JS  = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js';

  const incarca = () => new Promise((rezolva, respinge) => {
    if (window.L) return rezolva();
    const l = document.createElement('link');
    l.rel = 'stylesheet'; l.href = CSS; document.head.appendChild(l);
    const s = document.createElement('script');
    s.src = JS; s.onload = rezolva; s.onerror = respinge;
    document.head.appendChild(s);
  });

  const pin = (text, principal) => window.L.divIcon({
    className: 'ec-pin' + (principal ? ' ec-pin--main' : ''),
    html: `<span>${text}</span>`,
    iconSize: principal ? [46, 46] : [30, 30],
    iconAnchor: principal ? [23, 23] : [15, 15],
  });

  async function porneste() {
    let date;
    try {
      const r = await fetch(gazda.dataset.sursa || 'assets/data/distante.json');
      date = await r.json();
      await incarca();
    } catch {
      gazda.innerHTML = '<p class="ec-harta__err">Harta nu a putut fi încărcată.</p>';
      return;
    }

    const L = window.L;
    const panza = gazda.querySelector('[data-panza]');
    const harta = L.map(panza, { scrollWheelZoom: false, zoomControl: true })
                   .setView([date.lat, date.lon], 13);

    // tile-uri OpenStreetMap: libere, fara cheie. CARTO cere acum API key.
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(harta);

    const acasa = L.marker([date.lat, date.lon], { icon: pin('EC', true), zIndexOffset: 1000 })
      .addTo(harta)
      .bindPopup('<b>Emerald City</b><br>Iași, zona Păcurari');

    const marcaje = date.puncte.map((p, i) => {
      const m = L.marker([p.lat, p.lon], { icon: pin(p.min) }).addTo(harta);
      const kmTxt = String(p.km).replace('.', ',');
      m.bindPopup(`<b>${p.nume}</b><br>${kmTxt} km · ${p.min} min cu mașina`);
      m.on('click', () => selecteaza(i));
      return m;
    });

    // incadrez tot, dar nu prea departe
    harta.fitBounds(L.featureGroup([acasa, ...marcaje]).getBounds().pad(0.18));

    // lista laterala, sincronizata cu harta
    const lista = gazda.querySelector('[data-lista]');
    lista.innerHTML = date.puncte.map((p, i) =>
      `<button class="ec-harta__i" data-i="${i}" type="button">
        <span class="ec-harta__min">${p.min}<small>min</small></span>
        <span class="ec-harta__t"><b>${p.nume}</b><i>${String(p.km).replace('.', ',')} km</i></span>
      </button>`).join('');

    let curent = -1;
    function selecteaza(i) {
      curent = i;
      [...lista.children].forEach((b, k) => b.classList.toggle('is-on', k === i));
      const p = date.puncte[i];
      harta.flyTo([p.lat, p.lon], 15, { duration: .7 });
      marcaje[i].openPopup();
    }
    lista.addEventListener('click', ev => {
      const b = ev.target.closest('[data-i]');
      if (b) selecteaza(+b.dataset.i);
    });
    lista.addEventListener('mouseover', ev => {
      const b = ev.target.closest('[data-i]');
      if (b && +b.dataset.i !== curent) marcaje[+b.dataset.i].openPopup();
    });

    gazda.querySelector('[data-reset]')?.addEventListener('click', () => {
      [...lista.children].forEach(b => b.classList.remove('is-on'));
      harta.flyTo([date.lat, date.lon], 13, { duration: .7 });
      acasa.openPopup();
    });

    gazda.classList.add('is-gata');
  }

  // pornesc doar cand harta se apropie de ecran
  new IntersectionObserver((es, obs) => {
    if (!es[0].isIntersecting) return;
    obs.disconnect();
    porneste();
  }, { rootMargin: '300px' }).observe(gazda);

})();
