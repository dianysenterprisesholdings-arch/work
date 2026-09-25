/* ==========================================================================
   Emerald City — hartă interactivă
   Leaflet + OpenStreetMap. Biblioteca se încarcă abia când harta intră în
   ecran, ca să nu coste nimic pe restul paginii.

   Funcții: filtre pe categorii, izocrone (5 și 10 minute), traseu real
   desenat la click, comutare hartă/satelit, marker clasic pentru ansamblu.
   Coordonatele vin din assets/data/distante.json.
   ========================================================================== */

(() => {
  'use strict';
  const EN = document.documentElement.lang === 'en';

  const gazda = document.getElementById('ecHarta');
  if (!gazda) return;

  const CSS = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css';
  const JS  = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js';

  const CATEGORII = {
    cumparaturi: EN ? 'Shopping' : 'Cumpărături',
    educatie:    EN ? 'Education' : 'Educație',
    verde:       EN ? 'Green spaces' : 'Spații verzi',
    transport:   'Transport',
    oras:        EN ? 'City' : 'Oraș',
  };

  // Izocrone aproximative: in oras se circula cu ~28 km/h in medie,
  // deci 5 minute inseamna aproximativ 2,3 km pe traseu, adica ~1,7 km in
  // linie dreapta. Cercurile sunt orientative si asa sunt si etichetate.
  const IZO = [
    { min: 5,  raza: 1700 },
    { min: 10, raza: 3400 },
  ];

  const incarca = () => new Promise((rezolva, respinge) => {
    if (window.L) return rezolva();
    const l = document.createElement('link');
    l.rel = 'stylesheet'; l.href = CSS; document.head.appendChild(l);
    const s = document.createElement('script');
    s.src = JS; s.onload = rezolva; s.onerror = respinge;
    document.head.appendChild(s);
  });

  const pinNumar = min => window.L.divIcon({
    className: 'ec-pin', html: `<span>${min}</span>`,
    iconSize: [30, 30], iconAnchor: [15, 15],
  });

  // marker clasic de harta: varful atinge exact punctul, deci ancora e jos
  const pinMarca = () => window.L.divIcon({
    className: 'ec-pinmap',
    html: `<svg width="40" height="52" viewBox="0 0 40 52" fill="none" aria-hidden="true">
      <path d="M20 51C20 51 37 31.5 37 19A17 17 0 103 19c0 12.5 17 32 17 32z"
            fill="var(--ec-emerald)" stroke="#fff" stroke-width="2.5"/>
      <circle cx="20" cy="19" r="6.5" fill="#fff"/>
    </svg>`,
    iconSize: [40, 52], iconAnchor: [20, 52], popupAnchor: [0, -46],
  });

  async function porneste() {
    let date;
    try {
      const r = await fetch(gazda.dataset.sursa || (document.body.dataset.assets || '') + 'assets/data/distante.json');
      date = await r.json();
      await incarca();
    } catch {
      gazda.innerHTML = `<p class="ec-harta__err">${EN ? 'The map could not be loaded.' : 'Harta nu a putut fi încărcată.'}</p>`;
      return;
    }

    const L = window.L;
    const panza = gazda.querySelector('[data-panza]');
    const harta = L.map(panza, { scrollWheelZoom: false, zoomControl: true })
                   .setView([date.lat, date.lon], 13);

    /* --- straturi de fundal ------------------------------------------- */
    const strat = {
      harta: L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }),
      satelit: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: '&copy; Esri, Maxar, Earthstar Geographics',
        maxZoom: 19,
      }),
    };
    let fundal = 'harta';
    strat.harta.addTo(harta);

    /* --- izocrone ------------------------------------------------------ */
    const izocrone = L.layerGroup(
      IZO.map(z => L.circle([date.lat, date.lon], {
        radius: z.raza, className: 'ec-izo',
        interactive: false, fillOpacity: .06, weight: 1,
      }).bindTooltip(EN ? `${z.min} minutes by car` : `${z.min} minute cu mașina`, { permanent: false, direction: 'top' }))
    );

    /* --- reperul principal si punctele ---------------------------------- */
    const acasa = L.marker([date.lat, date.lon], { icon: pinMarca(), zIndexOffset: 1000 })
      .addTo(harta).bindPopup(EN ? '<b>Emerald City</b><br>Apartments in Iași, Păcurari area' : '<b>Emerald City</b><br>Apartamente Iași, zona Păcurari');

    const marcaje = date.puncte.map((p, i) => {
      const m = L.marker([p.lat, p.lon], { icon: pinNumar(p.min) });
      m.bindPopup(`<b>${p.nume}</b><br>${EN ? p.km : String(p.km).replace('.', ',')} km · ${p.min} min ${EN ? 'by car' : 'cu mașina'}`);
      m.on('click', () => selecteaza(i));
      m._cat = p.cat || 'oras';
      m.addTo(harta);
      return m;
    });

    /* --- traseu desenat ------------------------------------------------- */
    let traseu = null;
    async function deseneazaTraseu(p) {
      if (traseu) { harta.removeLayer(traseu); traseu = null; }
      try {
        const u = `https://router.project-osrm.org/route/v1/driving/`
                + `${date.lon},${date.lat};${p.lon},${p.lat}?overview=full&geometries=geojson`;
        const r = await fetch(u);
        const d = await r.json();
        if (d.code !== 'Ok' || !d.routes.length) return;
        const pct = d.routes[0].geometry.coordinates.map(c => [c[1], c[0]]);
        traseu = L.polyline(pct, { className: 'ec-traseu', weight: 4 }).addTo(harta);
        harta.fitBounds(traseu.getBounds().pad(0.2));
      } catch { /* fara traseu, raman doar pinii */ }
    }

    /* --- lista laterala --------------------------------------------------*/
    const lista = gazda.querySelector('[data-lista]');
    const randuri = () => date.puncte.map((p, i) =>
      `<button class="ec-harta__i" data-i="${i}" data-cat="${p.cat || 'oras'}" type="button">
        <span class="ec-harta__min">${p.min}<small>min</small></span>
        <span class="ec-harta__t"><b>${p.nume}</b><i>${String(p.km).replace('.', ',')} km</i></span>
      </button>`).join('');
    lista.innerHTML = randuri();

    let curent = -1;
    function selecteaza(i) {
      curent = i;
      [...lista.children].forEach((b, k) => b.classList.toggle('is-on', k === i));
      const p = date.puncte[i];
      marcaje[i].openPopup();
      deseneazaTraseu(p);
    }
    lista.addEventListener('click', ev => {
      const b = ev.target.closest('[data-i]');
      if (b) selecteaza(+b.dataset.i);
    });

    /* --- controale ------------------------------------------------------ */
    const bara = gazda.querySelector('[data-controale]');
    bara.innerHTML =
      Object.entries(CATEGORII).map(([k, et]) =>
        `<button class="ec-chip is-on" data-filtru="${k}" type="button">${et}</button>`).join('')
      + `<button class="ec-chip" data-izo type="button">Timpi de mers</button>`
      + `<button class="ec-chip" data-satelit type="button">Satelit</button>`;

    const active = new Set(Object.keys(CATEGORII));
    const aplicaFiltre = () => {
      marcaje.forEach(m => {
        const vizibil = active.has(m._cat);
        if (vizibil && !harta.hasLayer(m)) m.addTo(harta);
        if (!vizibil && harta.hasLayer(m)) harta.removeLayer(m);
      });
      [...lista.children].forEach(b => {
        b.style.display = active.has(b.dataset.cat) ? '' : 'none';
      });
    };

    bara.addEventListener('click', ev => {
      const b = ev.target.closest('button');
      if (!b) return;
      if (b.dataset.filtru) {
        const k = b.dataset.filtru;
        active.has(k) ? active.delete(k) : active.add(k);
        b.classList.toggle('is-on');
        aplicaFiltre();
      } else if (b.hasAttribute('data-izo')) {
        b.classList.toggle('is-on');
        harta.hasLayer(izocrone) ? harta.removeLayer(izocrone) : izocrone.addTo(harta);
      } else if (b.hasAttribute('data-satelit')) {
        b.classList.toggle('is-on');
        harta.removeLayer(strat[fundal]);
        fundal = fundal === 'harta' ? 'satelit' : 'harta';
        strat[fundal].addTo(harta);
        gazda.classList.toggle('is-satelit', fundal === 'satelit');
      }
    });

    gazda.querySelector('[data-reset]')?.addEventListener('click', () => {
      [...lista.children].forEach(b => b.classList.remove('is-on'));
      if (traseu) { harta.removeLayer(traseu); traseu = null; }
      harta.flyTo([date.lat, date.lon], 13, { duration: .7 });
      acasa.openPopup();
    });

    harta.fitBounds(L.featureGroup([acasa, ...marcaje]).getBounds().pad(0.18));
    gazda.classList.add('is-gata');
  }

  new IntersectionObserver((es, obs) => {
    if (!es[0].isIntersecting) return;
    obs.disconnect();
    porneste();
  }, { rootMargin: '300px' }).observe(gazda);

})();
