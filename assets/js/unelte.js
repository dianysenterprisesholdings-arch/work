/* ==========================================================================
   Emerald City — unelte de conversie
   Calculator de rata, calculator de randament, lista scurta partajabila.
   Se incarca pe paginile de unitate, de categorie si pe cea de investitie.
   ========================================================================== */

(() => {
  'use strict';

  const $  = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const euro = n => new Intl.NumberFormat('ro-RO', { maximumFractionDigits: 0 }).format(n) + ' €';
  const pct  = n => n.toFixed(2).replace('.', ',') + '%';

  /* ====================================================== rata lunara ==
     Anuitate clasica. Valorile implicite urmeaza practica pietei din RO:
     avans 15%, dobanda ~6%, 30 de ani. Sunt orientative, nu o oferta.
     ==================================================================== */
  function rata(P, dob, ani) {
    const i = dob / 100 / 12, n = ani * 12;
    if (i === 0) return P / n;
    return P * i / (1 - Math.pow(1 + i, -n));
  }

  function initRata(box) {
    const pret = +box.dataset.pret;
    const av = $('[data-av]', box), db = $('[data-dob]', box), an = $('[data-ani]', box);
    const oAv = $('[data-oav]', box), oDb = $('[data-odob]', box), oAn = $('[data-oani]', box);
    const oRata = $('[data-orata]', box), oCredit = $('[data-ocredit]', box), oTot = $('[data-ototal]', box);

    const calc = () => {
      const avans = pret * (+av.value) / 100;
      const credit = pret - avans;
      const r = rata(credit, +db.value, +an.value);
      oAv.textContent = av.value + '% · ' + euro(avans);
      oDb.textContent = (+db.value).toFixed(1).replace('.', ',') + '%';
      oAn.textContent = an.value + ' ani';
      oRata.textContent = euro(r);
      oCredit.textContent = euro(credit);
      oTot.textContent = euro(r * an.value * 12 + avans);
    };
    [av, db, an].forEach(x => x.addEventListener('input', calc));
    calc();
  }

  /* ================================================== randament ==
     Randament brut si net, plus anii pana la amortizarea investitiei.
     Chiria implicita e estimata din suprafata; se poate schimba.
     ============================================================== */
  function initRandament(box) {
    const pr = $('[data-pret]', box), ch = $('[data-chirie]', box), gl = $('[data-gol]', box);
    const oPr = $('[data-opret]', box), oCh = $('[data-ochirie]', box), oGl = $('[data-ogol]', box);
    const oBr = $('[data-obrut]', box), oNet = $('[data-onet]', box), oAni = $('[data-oani2]', box);

    const calc = () => {
      const pret = +pr.value, chirie = +ch.value, gol = +gl.value;
      const anBrut = chirie * 12;
      const anNet = anBrut * (1 - gol / 100) * 0.92;   // ~8% cheltuieli si administrare
      oPr.textContent = euro(pret);
      oCh.textContent = euro(chirie) + '/lună';
      oGl.textContent = gol + '%';
      oBr.textContent = pct(anBrut / pret * 100);
      oNet.textContent = pct(anNet / pret * 100);
      oAni.textContent = (pret / anNet).toFixed(1).replace('.', ',') + ' ani';
    };
    // valori venite din pagina unei unitati sau dintr-un scenariu (?pret=&su=)
    try {
      const q = new URLSearchParams(location.search);
      if (q.get('pret')) pr.value = Math.min(Math.max(+q.get('pret'), +pr.min), +pr.max);
      if (q.get('su')) ch.value = Math.min(Math.max(Math.round(+q.get('su') * 6.2 / 10) * 10, +ch.min), +ch.max);
    } catch (e) {}
    [pr, ch, gl].forEach(x => x.addEventListener('input', calc));
    calc();
  }

  /* ============================================ lista scurta ==
     Pana la 6 apartamente, tinute in localStorage si codificate in
     adresa, ca lista sa poata fi trimisa altcuiva.
     ========================================================== */
  const CHEIE = 'ec-lista';
  const MAX = 6;

  const citeste = () => {
    try { return JSON.parse(localStorage.getItem(CHEIE) || '[]'); }
    catch { return []; }
  };
  const scrie = l => {
    try { localStorage.setItem(CHEIE, JSON.stringify(l)); } catch {}
  };

  function initLista(radacina) {
    let lista = citeste();

    const bara = document.createElement('div');
    bara.className = 'ec-fav';
    bara.innerHTML = `<span class="ec-fav__n"></span>
      <span class="ec-fav__b">
        <a class="ec-btn ec-btn--white" data-cmp>Compară</a>
        <button class="ec-btn ec-btn--brass" data-share type="button">Trimite lista</button>
      </span>`;
    document.body.appendChild(bara);

    const nr = $('.ec-fav__n', bara), cmp = $('[data-cmp]', bara), share = $('[data-share]', bara);

    const sincronizeaza = () => {
      bara.classList.toggle('is-on', lista.length > 0);
      nr.textContent = lista.length === 1 ? '1 apartament salvat' : `${lista.length} apartamente salvate`;
      cmp.href = radacina + 'compara/?u=' + lista.join(',');
      $$('[data-save]').forEach(b => {
        const on = lista.includes(b.dataset.save);
        b.classList.toggle('is-on', on);
        b.setAttribute('aria-pressed', on);
        const t = $('[data-save-t]', b);
        if (t) t.textContent = on ? 'Salvat' : 'Salvează';
      });
    };

    document.addEventListener('click', ev => {
      const b = ev.target.closest('[data-save]');
      if (!b) return;
      ev.preventDefault();
      const id = b.dataset.save;
      if (lista.includes(id)) lista = lista.filter(x => x !== id);
      else if (lista.length >= MAX) { alert(`Poți compara maximum ${MAX} apartamente.`); return; }
      else lista.push(id);
      scrie(lista);
      sincronizeaza();
    });

    share.addEventListener('click', async () => {
      const url = location.origin + radacina.replace(/^\.\//, '/') + 'compara/?u=' + lista.join(',');
      try {
        if (navigator.share) await navigator.share({ title: 'Apartamente Emerald City', url });
        else { await navigator.clipboard.writeText(url); share.textContent = 'Link copiat'; setTimeout(() => share.textContent = 'Trimite lista', 2000); }
      } catch {}
    });

    sincronizeaza();
  }

  /* ============================================================ init */
  $$('[data-calc-rata]').forEach(initRata);
  $$('[data-calc-randament]').forEach(initRandament);

  const rad = document.body.dataset.radacina || './';
  if (document.querySelector('[data-save]')) initLista(rad);

})();
