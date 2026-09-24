#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generator de pagini statice pentru Emerald City.

Scrie, din `date/unitati-demo.csv`:
  apartamente-iasi/index.html            — listare completa, cu filtre si tabel sortabil
  apartamente-iasi/<unit_id>/index.html  — 925 pagini de unitate
  tipologii/index.html              — hub de tipologii
  tipologii/<cod>/index.html        — 5 pagini de tipologie

Acelasi lucru il va face WordPress printr-un custom post type: sursa de
adevar ramane tabelul de unitati, paginile sunt derivate. Aici doar
demonstram ca fluxul functioneaza pe volumul real de 925 de unitati.
"""

import csv, html, json, os, shutil
from collections import defaultdict

RAD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(RAD, "date", "unitati-demo.csv")

TEL = "+40000000000"
TEL_AFIS = "+40 000 000 000"
WA = "https://wa.me/40000000000"
TEL_LINK = "tel:+40000000000"

# ---------------------------------------------------------------- tipologii
# Ponderile pe camera sunt orientative: documentatia nu contine defalcarea
# pe incaperi. Se inlocuiesc cand vine tabelul final de la dezvoltator.
CAMERE_TIP = {
    "1A": [("Hol", .10), ("Living si bucatarie", .66), ("Baie", .15), ("Debara", .09)],
    "2A": [("Hol", .08), ("Living si bucatarie", .45), ("Dormitor", .27), ("Baie", .11), ("Debara", .09)],
    "2B": [("Hol", .08), ("Living si bucatarie", .43), ("Dormitor", .28), ("Baie", .12), ("Debara", .09)],
    "3A": [("Hol", .07), ("Living", .30), ("Bucatarie", .13), ("Dormitor 1", .20),
           ("Dormitor 2", .16), ("Baie", .08), ("Baie 2", .06)],
    "3B": [("Hol", .09), ("Living si bucatarie", .36), ("Dormitor", .20), ("Birou", .15),
           ("Baie", .11), ("Baie 2", .09)],
}
DESC_TIP = {
    "1A": "Garsoniera compacta, cu zona de zi deschisa si bucatarie integrata.",
    "2A": "Doua camere, cu living deschis spre bucatarie si dormitor separat.",
    "2B": "Doua camere, cu dormitor mai generos si spatiu suplimentar de depozitare.",
    "3A": "Trei camere, cu bucatarie inchisa, doua dormitoare si doua bai.",
    "3B": "Trei camere, cu living deschis, dormitor si o a treia camera pentru birou.",
}
GALERIE_TIP = {
    "1A": ["living-02", "bucatarie-01", "baie-01"],
    "2A": ["living-01", "dormitor-01", "hol-01"],
    "2B": ["living-02", "dining-01", "baie-01"],
    "3A": ["living-01", "dining-01", "dormitor-01"],
    "3B": ["dining-01", "bucatarie-01", "hol-01"],
}

STATUS_ET = {"disponibil": "Disponibil", "rezervat": "Rezervat",
             "vandut": "Vandut", "in_curand": "In curand"}
STATUS_SCHEMA = {"disponibil": "InStock", "rezervat": "LimitedAvailability",
                 "vandut": "SoldOut", "in_curand": "PreOrder"}
CATEGORII = {
    1: {"slug": "apartamente-1-camera",  "titlu": "Apartamente 1 cameră",  "h1": "Apartamente 1 cameră în Iași, zona Păcurari",
        "img": "living-02", "lead": "Garsoniere compacte, cu zona de zi deschisă și bucătărie integrată. "
        "Potrivite pentru prima locuință sau pentru investiție — cel mai cerut format pe piața de închirieri din Iași."},
    2: {"slug": "apartamente-2-camere", "titlu": "Apartamente 2 camere", "h1": "Apartamente 2 camere în Iași, zona Păcurari",
        "img": "living-01", "lead": "Living deschis spre bucătărie și dormitor separat. Formatul cel mai echilibrat "
        "între spațiu și preț, potrivit pentru cupluri și familii tinere."},
    3: {"slug": "apartamente-3-camere", "titlu": "Apartamente 3 camere", "h1": "Apartamente 3 camere în Iași, zona Păcurari",
        "img": "dining-01", "lead": "Două dormitoare, două băi și zonă de zi generoasă. Pentru familii care au nevoie "
        "de o cameră în plus, de birou sau de spațiu pentru copii."},
}

ORIENTARE = {"N": "nord", "NE": "nord-est", "E": "est", "SE": "sud-est",
             "S": "sud", "SV": "sud-vest", "V": "vest", "NV": "nord-vest"}


def e(x):
    return html.escape(str(x), quote=True)


def euro(n):
    return f"{n:,}".replace(",", ".") + " €"


def mp(n):
    return f"{n:.1f}".replace(".", ",") + " m²"


def camere_txt(n):
    return "1 cameră" if n == 1 else f"{n} camere"


def bloc(cod):
    return cod.lstrip("C")


def etaj_txt(n):
    return "Parter" if n == 0 else f"Etaj {n}"


# ------------------------------------------------------------------ sablon
def pagina(titlu, descriere, continut, radacina, schema=None, canonic=""):
    """Invelisul comun: topbar, navigatie, continut, subsol, WhatsApp."""
    r = radacina
    ld = f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>' if schema else ""
    return f"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titlu)}</title>
<meta name="description" content="{e(descriere)}">
<link rel="canonical" href="https://emerald-city.ro/{canonic}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Inter+Tight:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{r}assets/css/main.css">
{ld}
</head>
<body data-radacina="{r}">

<div class="ec-topbar">
  <div class="ec-topbar__in">
    <span class="ec-topbar__l"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s7-6.2 7-11a7 7 0 10-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.6"/></svg> Iași, zona Păcurari — <strong>DIRECT DEZVOLTATOR</strong></span>
    <div class="ec-topbar__right">
      <a href="tel:+40000000000"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4.5 4h3l1.5 4-2 1.5a12 12 0 006 6L14.5 13l4 1.5v3a2 2 0 01-2.2 2A16 16 0 012.5 6.2 2 2 0 014.5 4z"/></svg> +40 000 000 000</a>
      <a href="mailto:vanzari@emerald-city.ro"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3.5 6.5l8.5 6 8.5-6"/></svg> vanzari@emerald-city.ro</a>
      <span><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg> L–V 9–18 · S 10–14</span>
    </div>
  </div>
</div>

<header class="ec-nav">
  <div class="ec-nav__in">
    <a class="ec-nav__logo" href="{r}" aria-label="Emerald City — acasă">
      <img src="{r}brand/logo-verde.svg" alt="Emerald City" width="590" height="286">
    </a>
    <nav class="ec-nav__menu">
      <span class="ec-nav__has">
        <a href="{r}despre-dezvoltator/">Despre noi</a>
        <span class="ec-nav__sub">
          <a href="{r}apartamente-iasi-pacurari/">Amplasament</a>
          <a href="{r}stadiu-lucrari/">Jurnal de șantier</a>
          <a href="{r}despre-dezvoltator/">Dezvoltator</a>
          <a href="{r}proiect/">Proiect</a>
          <a href="{r}aparitii-presa/">Apariții în presă</a>
        </span>
      </span>
      <span class="ec-nav__has">
        <a href="{r}apartamente-iasi/">Apartamente</a>
        <span class="ec-nav__sub">
          <a href="{r}apartamente-iasi/">Toate apartamentele</a>
          <a href="{r}apartamente-iasi/apartamente-1-camera/">1 cameră</a>
          <a href="{r}apartamente-iasi/apartamente-2-camere/">2 camere</a>
          <a href="{r}apartamente-iasi/apartamente-3-camere/">3 camere</a>
          <a href="{r}tipologii/">Tipuri de compartimentări</a>
        </span>
      </span>
      <a href="{r}apartamente-iasi/disponibilitate/">Disponibilitate</a>
      <a href="{r}investitie-apartamente-iasi/">Investiție</a>
      <a href="{r}contact/">Contact</a>
    </nav>
    <a class="ec-btn" href="{r}contact/"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg> Programează vizionare</a>
  </div>
</header>

<main>
{continut}
</main>

<footer class="ec-foot">
  <div class="ec-wrap">

    <div class="ec-foot__top">
      <div>
        <img src="{r}brand/logo-alb.svg" alt="Emerald City" width="590" height="286">
        <p class="ec-foot__claim">
          925 de apartamente în nordul Iașului, pe cinci hectare din care
          aproape o treime rămâne verde.
        </p>
      </div>
      <div class="ec-foot__reach">
        <a class="ec-foot__r" href="tel:{TEL}">
          <span>Sună direct</span><b>{TEL_AFIS}</b>
        </a>
        <a class="ec-foot__r" href="{WA}">
          <span>Scrie pe WhatsApp</span><b>Răspundem azi</b>
        </a>
        <a class="ec-foot__r" href="mailto:vanzari@emerald-city.ro">
          <span>Email</span><b>vanzari@emerald-city.ro</b>
        </a>
        <a class="ec-foot__r" href="{r}investitie-apartamente-iasi/">
          <span>Cumperi ca investiție?</span><b>Calculator de randament</b>
        </a>
      </div>
    </div>

    <div class="ec-foot__stats">
      <div><b>925</b><span><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 21V5a1 1 0 011-1h9a1 1 0 011 1v16"/><path d="M15 21V10h4a1 1 0 011 1v10"/><path d="M7 8h2M7 12h2M7 16h2M11 8h1M11 12h1M11 16h1"/><path d="M2 21h20"/></svg> Apartamente</span></div>
      <div><b>18</b><span><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 21V8l5-3 5 3v13"/><path d="M13 21V12h8v9"/><path d="M6 11h1.5M6 15h1.5M10 11h1.5M10 15h1.5M16 16h2"/><path d="M2 21h20"/></svg> Blocuri, parter + 3 etaje</span></div>
      <div><b>30,85%</b><span><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 19c0-8 5-13 14-13 0 9-5 13-14 13z"/><path d="M5 19c3-4 6-6 10-7.5"/></svg> Spațiu verde</span></div>
      <div><b>940</b><span><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 17h14M6 17V9l2-4h8l2 4v8"/><circle cx="8" cy="17" r="2"/><circle cx="16" cy="17" r="2"/></svg> Locuri de parcare</span></div>
    </div>

    <div class="ec-foot__grid">
      <div>
        <h4>Apartamente</h4>
        <ul>
          <li><a href="{r}apartamente-iasi/apartamente-1-camera/">1 cameră</a></li>
          <li><a href="{r}apartamente-iasi/apartamente-2-camere/">2 camere</a></li>
          <li><a href="{r}apartamente-iasi/apartamente-3-camere/">3 camere</a></li>
          <li><a href="{r}apartamente-iasi/disponibilitate/">Disponibilitate și prețuri</a></li>
          <li><a href="{r}compara/">Compară apartamente</a></li>
        </ul>
      </div>
      <div>
        <h4>Tipologii</h4>
        <ul>{"".join(f'<li><a href="{r}tipologii/{c.lower()}/">Tip {c}</a></li>' for c in CAMERE_TIP)}</ul>
      </div>
      <div>
        <h4>Despre noi</h4>
        <ul>
          <li><a href="{r}apartamente-iasi-pacurari/">Amplasament</a></li>
          <li><a href="{r}stadiu-lucrari/">Jurnal de șantier</a></li>
          <li><a href="{r}despre-dezvoltator/">Dezvoltator</a></li>
          <li><a href="{r}proiect/">Proiect</a></li>
          <li><a href="{r}aparitii-presa/">Apariții în presă</a></li>
        </ul>
      </div>
      <div>
        <h4>Util</h4>
        <ul>
          <li><a href="{r}investitie-apartamente-iasi/">Investiție și randament</a></li>
          <li><a href="{r}contact/">Contact</a></li>
          <li><a href="{r}#finisaje">Finisaje</a></li>
        </ul>
      </div>
      <div>
        <h4>Informații legale</h4>
        <ul>
          <li><a href="{r}termeni-si-conditii/">Termeni și condiții</a></li>
          <li><a href="{r}politica-de-confidentialitate/">Politica de confidențialitate</a></li>
          <li><a href="{r}politica-de-cookies/">Politica de cookies</a></li>
          <li><a href="{r}informare-gdpr/">Informare GDPR</a></li>
          <li><a href="https://anpc.ro/ce-este-sal/" rel="nofollow noopener" target="_blank">ANPC — SAL</a></li>
          <li><a href="https://ec.europa.eu/consumers/odr" rel="nofollow noopener" target="_blank">ANPC — SOL</a></li>
        </ul>
      </div>
    </div>

    <div class="ec-foot__bottom">
      <span>© 2026 Emerald City · Tala Sapphire S.R.L. · Str. Ion Nistor, Iași</span>
      <span>Machetă de lucru — date demonstrative</span>
    </div>
  </div>
</footer>

<a class="ec-wa" href="{WA}" aria-label="Scrie-ne pe WhatsApp">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2a10 10 0 00-8.6 15L2 22l5.2-1.4A10 10 0 1012 2zm0 18a8 8 0 01-4.1-1.1l-.3-.2-3 .8.8-3-.2-.3A8 8 0 1112 20zm4.4-6c-.2-.1-1.4-.7-1.6-.8-.2-.1-.4-.1-.5.1l-.7.9c-.1.2-.3.2-.5.1a6.5 6.5 0 01-3.2-2.8c-.1-.2 0-.4.1-.5l.4-.5c.1-.2.1-.3 0-.5l-.7-1.6c-.2-.4-.4-.4-.5-.4h-.5a1 1 0 00-.7.3c-.3.3-.9.9-.9 2.1s.9 2.4 1 2.6c.1.2 1.8 2.8 4.4 3.9 1.6.7 2.2.7 3 .6.5 0 1.4-.6 1.6-1.2.2-.6.2-1.1.1-1.2 0-.1-.2-.2-.4-.3z"/></svg>
  <span>Discută pe WhatsApp</span>
</a>
<script>
// paginile interioare nu incarca main.js; reveal-ul e destul de mic cat sa stea inline
(() => {{
  const n = [...document.querySelectorAll('.ec-rv')];
  if (!n.length) return;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) {{
    n.forEach(x => x.classList.add('is-in')); return;
  }}
  const o = new IntersectionObserver(es => es.forEach(e => {{
    if (e.isIntersecting) {{ e.target.classList.add('is-in'); o.unobserve(e.target); }}
  }}), {{ rootMargin: '0px 0px -8% 0px', threshold: .08 }});
  n.forEach(x => o.observe(x));
}})();

// plan interactiv: hotspot-urile si legenda se evidentiaza reciproc
(() => {{
  document.querySelectorAll('[data-plan]').forEach(p => {{
    const tip = p.querySelector('[data-tip]');
    const spots = [...p.querySelectorAll('.ec-plan__spot')];
    const randuri = [...p.querySelectorAll('.ec-plan__legend li')];
    const arata = (i, on) => {{
      spots.forEach(s => s.classList.toggle('is-on', on && s.dataset.i === i));
      randuri.forEach(r => r.classList.toggle('is-on', on && r.dataset.i === i));
      const s = spots.find(x => x.dataset.i === i);
      if (on && s) {{
        tip.innerHTML = s.getAttribute('aria-label');
        tip.style.left = s.style.left;
        tip.style.top = s.style.top;
        tip.classList.add('is-on');
      }} else tip.classList.remove('is-on');
    }};
    [...spots, ...randuri].forEach(el => {{
      const i = el.dataset.i;
      el.addEventListener('mouseenter', () => arata(i, true));
      el.addEventListener('mouseleave', () => arata(i, false));
      el.addEventListener('focus', () => arata(i, true));
      el.addEventListener('blur', () => arata(i, false));
      el.addEventListener('click', e => {{ e.preventDefault(); arata(i, true); }});
    }});
  }});



// bara lipita pe mobil: pretul si actiunile raman la indemana
(() => {{
  const b = document.querySelector('[data-sticky]');
  if (!b) return;
  const reper = document.querySelector('.ec-pricebar');
  if (!reper) return;
  new IntersectionObserver(es => {{
    b.classList.toggle('is-on', !es[0].isIntersecting);
  }}, {{ rootMargin: '-80px 0px 0px 0px' }}).observe(reper);
}})();

// prefetch la hover: cele 925 de pagini sunt statice, deci navigarea devine instanta
(() => {{
  if (matchMedia('(hover: none)').matches) return;
  const vazute = new Set();
  const cere = u => {{
    if (vazute.has(u) || vazute.size > 40) return;
    vazute.add(u);
    const l = document.createElement('link');
    l.rel = 'prefetch'; l.href = u; document.head.appendChild(l);
  }};
  document.addEventListener('mouseover', ev => {{
    const a = ev.target.closest('a[href]');
    if (!a || a.host !== location.host || a.hash) return;
    cere(a.href);
  }}, {{ passive: true }});
}})();
</script>
<script src="{r}assets/js/unelte.js"></script>
</body>
</html>
"""


SCURT = {'Living si bucatarie': 'Living', 'Living și bucătărie': 'Living', 'Living': 'Living', 'Dormitor 1': 'Dorm. 1', 'Dormitor 2': 'Dorm. 2', 'Dormitor': 'Dormitor', 'Bucatarie': 'Bucătărie', 'Bucătărie': 'Bucătărie', 'Baie': 'Baie', 'Baie 2': 'Baie 2', 'Hol': 'Hol', 'Debara': 'Debara', 'Birou': 'Birou'}


def plan_svg(nr_camere, tip=None, su=None, compact=False):
    """Schema de compartimentare: camere proportionale cu aria, cotate.

    Impartire prin taieturi succesive (slice layout): zona de zi ocupa banda
    din stanga, restul se aseaza pe coloana din dreapta, in ordinea ariei.
    """
    cam = CAMERE_TIP.get(tip or "", None)
    if not cam:
        cam = ([("Living si bucatarie", .66), ("Baie", .17), ("Hol", .17)] if nr_camere == 1
               else [("Living si bucatarie", .45), ("Dormitor", .3), ("Baie", .13), ("Hol", .12)]
               if nr_camere == 2
               else [("Living", .34), ("Dormitor 1", .22), ("Dormitor 2", .18),
                     ("Baie", .13), ("Hol", .13)])
    total = su or 60.0

    W, H = 200.0, 128.0          # cadrul desenului
    GROS = 3.4                    # grosimea peretelui
    principal = cam[0]
    rest = cam[1:]

    # banda principala in stanga, proportionala cu aria zonei de zi
    wp = W * min(max(principal[1] * 1.55, .42), .58)
    incaperi = [(principal[0], principal[1], 0.0, 0.0, wp, H)]

    # restul, stivuite pe coloana din dreapta, proportional cu aria
    rest_pond = sum(p for _, p in rest) or 1
    y = 0.0
    for i, (nume, pond) in enumerate(rest):
        h = H - y if i == len(rest) - 1 else H * (pond / rest_pond)
        incaperi.append((nume, pond, wp, y, W - wp, h))
        y += h

    piese = [f'<rect x="0" y="0" width="{W}" height="{H}" fill="var(--ec-emerald)"/>']
    for nume, pond, x, yy, w, h in incaperi:
        piese.append(f'<rect x="{x + GROS:.1f}" y="{yy + GROS:.1f}" '
                     f'width="{max(w - GROS * 2, 1):.1f}" height="{max(h - GROS * 2, 1):.1f}" '
                     f'fill="#fff"/>')
        cx, cy = x + w / 2, yy + h / 2
        arie = total * pond
        # in cardurile mici nu incape si numele, si aria: pastrez numele, scurtat
        et = SCURT.get(nume, nume) if compact else nume
        if compact:
            if h >= 22:
                piese.append(f'<text class="pn" x="{cx:.1f}" y="{cy + 2.5:.1f}">{et}</text>')
        else:
            mic = h < 34
            piese.append(
                f'<text class="pn" x="{cx:.1f}" y="{cy - (4 if not mic else 1):.1f}">{et}</text>')
            if not mic:
                piese.append(f'<text class="pa" x="{cx:.1f}" y="{cy + 8:.1f}">'
                             f'{arie:.1f}'.replace(".", ",") + ' m²</text>')

    # ferestre pe peretele exterior si usi pe peretii interiori:
    # o schema fara ele arata ca o diagrama, nu ca un plan
    fer = lambda x1, y1, x2, y2: piese.append(
        f'<line class="pf" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')
    # zona de zi: doua ferestre pe latura stanga
    fer(GROS / 2, H * .22, GROS / 2, H * .44)
    fer(GROS / 2, H * .58, GROS / 2, H * .80)
    # camerele din dreapta: cate o fereastra pe latura exterioara
    for _, _, x, yy, w, h in incaperi[1:]:
        if h > 26:
            fer(W - GROS / 2, yy + h * .3, W - GROS / 2, yy + h * .7)
    # usi: o intrerupere alba plus arcul de deschidere, pe peretele comun
    for _, _, x, yy, w, h in incaperi[1:]:
        cy = yy + h / 2
        d = min(11.0, h * .45)
        piese.append(f'<line class="pu" x1="{x:.1f}" y1="{cy - d/2:.1f}" '
                     f'x2="{x:.1f}" y2="{cy + d/2:.1f}"/>')
        piese.append(f'<path class="pua" d="M{x:.1f} {cy - d/2:.1f} '
                     f'a{d:.1f} {d:.1f} 0 0 1 {d:.1f} {d:.1f}"/>')

    # cote generale, jos si in dreapta
    lat = (total ** .5) * 1.35
    piese.append(f'<line class="pc" x1="0" y1="{H + 9}" x2="{W}" y2="{H + 9}"/>')
    piese.append(f'<text class="pd" x="{W/2:.0f}" y="{H + 20}">'
                 + f'{lat:.1f}'.replace(".", ",") + ' m</text>')
    piese.append(f'<line class="pc" x1="{W + 9}" y1="0" x2="{W + 9}" y2="{H}"/>')
    piese.append(f'<text class="pd" x="{W + 20}" y="{H/2:.0f}" '
                 f'transform="rotate(90 {W + 20} {H/2:.0f})">'
                 + f'{total / lat:.1f}'.replace(".", ",") + ' m</text>')

    return (f'<svg viewBox="-4 -4 {W + 34:.0f} {H + 32:.0f}" role="img" '
            f'aria-label="Schemă de compartimentare, tipologia {tip or nr_camere}">'
            + "".join(piese) + '</svg>')

# ----------------------------------------------------- planuri interactive
_PL = os.path.join(RAD, "assets", "data", "planuri.json")
PLANURI = json.load(open(_PL, encoding="utf-8")) if os.path.exists(_PL) else {}


def plan_interactiv(tip, nr_camere, r):
    """Plan cu hotspot-uri pe camere. Cade pe schita schematica daca nu exista."""
    d = PLANURI.get(tip)
    if not d:
        return (f'<div class="ec-planbox">{plan_svg(nr_camere)}'
                f'<p class="ec-plan__note">Schiță orientativă. Planul cotat se predă la semnarea '
                f'antecontractului.</p></div>')

    spots, legenda = "", ""
    for i, c in enumerate(d["camere"], 1):
        et = f'{c["nume"]} &middot; {mp(c["aria"])}'
        spots += (f'<button class="ec-plan__spot" style="left:{c["x"]}%;top:{c["y"]}%" '
                  f'data-i="{i}" aria-label="{e(et)}">{i}</button>')
        legenda += (f'<li data-i="{i}"><i>{i}</i><span>{c["nume"]}</span>'
                    f'<b>{mp(c["aria"])}</b></li>')

    return f"""<div class="ec-plan" data-plan>
  <figure class="ec-plan__fig">
    <img src="{r}{d['img']}" alt="Plan apartament tip {tip}" loading="lazy"
         width="{d['w']}" height="{d['h']}">
    {spots}
    <span class="ec-plan__tip" data-tip></span>
  </figure>
  <ul class="ec-plan__legend">{legenda}</ul>
  <p class="ec-plan__note">
    Treci cu mouse-ul peste numerele de pe plan pentru suprafața fiecărei camere.
    Plan orientativ; cotele definitive se predau la semnarea antecontractului.
  </p>
</div>"""


def formular(u=None, r="../../"):
    """Formularul preia identificatorul unitatii — la Lapis lipseste exact asta."""
    ctx = ""
    if u:
        ctx = (f'<div class="ec-form__unit">Întreb despre apartamentul '
               f'<b>{e(u["unit_id"])}</b> — {camere_txt(u["nr_camere"])}, {mp(u["su_utila"])}, '
               f'blocul {bloc(u["corp"])}, {etaj_txt(u["etaj"]).lower()}</div>'
               f'<input type="hidden" name="unit_id" value="{e(u["unit_id"])}">')
    return f"""<div class="ec-form">
  <h2 class="ec-title" style="font-size:1.2rem">Cere detalii</h2>
  <p class="ec-body" style="margin-bottom:1.25rem">Un consultant te sună în aceeași zi lucrătoare.</p>
  <form method="post" action="#" novalidate>
    {ctx}
    <div class="ec-form__grid">
      <div><label for="nume">Nume</label><input id="nume" name="nume" type="text" autocomplete="name"></div>
      <div><label for="tel">Telefon</label><input id="tel" name="telefon" type="tel" autocomplete="tel"></div>
      <div class="full"><label for="mail">Email</label><input id="mail" name="email" type="email" autocomplete="email"></div>
      <div class="full"><label for="msg">Mesaj</label><textarea id="msg" name="mesaj" rows="3"></textarea></div>
      <div class="full"><button class="ec-btn ec-btn--brass" type="submit">Trimite solicitarea</button></div>
    </div>
    <p class="ec-form__note">Machetă de lucru — formularul nu trimite date.</p>
  </form>
</div>"""


# ------------------------------------------------------------- imagini
_LQ = os.path.join(RAD, "assets", "data", "lqip.json")
LQIP = json.load(open(_LQ, encoding="utf-8")) if os.path.exists(_LQ) else {}


def imagine(nume, alt, r, sizes="100vw", eager=False, w=1600, h=900, cls=""):
    """<picture> cu WebP si rezerva JPEG, plus blur-up din miniatura de 20px."""
    lq = LQIP.get(nume, "")
    stil = f' style="background:#DCE7DE url({lq}) center/cover"' if lq else ""
    incarcare = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    c = f' class="{cls}"' if cls else ""
    return f"""<picture>
  <source type="image/webp" srcset="{r}assets/img/{nume}-800.webp 800w, {r}assets/img/{nume}.webp 1600w" sizes="{sizes}">
  <img{c} src="{r}assets/img/{nume}.jpg"
       srcset="{r}assets/img/{nume}-800.jpg 800w, {r}assets/img/{nume}.jpg 1600w" sizes="{sizes}"
       alt="{e(alt)}" width="{w}" height="{h}" {incarcare}{stil}
       onload="this.style.background='none'">
</picture>"""


# ------------------------------------------------- unelte de conversie
def buton_salvare(uid):
    return (f'<button class="ec-save" data-save="{e(uid)}" type="button" aria-pressed="false">'
            '<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" '
            'stroke-width="1.6"><path d="M4 2h8v12l-4-3-4 3z"/></svg>'
            '<span data-save-t>Salvează</span></button>')


def calc_rata(pret):
    """Anuitate. Valorile implicite urmeaza practica pietei: 15% avans, 6%, 30 ani."""
    return f"""<div class="ec-calc" data-calc-rata data-pret="{pret}">
  <h3>Cât ar fi rata lunară</h3>
  <p class="ec-calc__sub">Simulare orientativă pentru un credit ipotecar. Nu este o ofertă de creditare.</p>
  <div class="ec-calc__f">
    <div>
      <label>Avans <span class="val" data-oav></span></label>
      <input type="range" data-av min="15" max="60" step="5" value="15">
    </div>
    <div>
      <label>Dobândă anuală <span class="val" data-odob></span></label>
      <input type="range" data-dob min="4" max="9" step="0.1" value="6">
    </div>
    <div>
      <label>Perioadă <span class="val" data-oani></span></label>
      <input type="range" data-ani min="5" max="30" step="1" value="30">
    </div>
    <div>
      <label>Sumă finanțată <span class="val" data-ocredit></span></label>
      <p style="font-size:var(--ec-small);color:var(--ec-ink-60);margin-top:.6rem">
        Diferența dintre preț și avans.</p>
    </div>
  </div>
  <div class="ec-calc__out">
    <div class="ec-calc__o"><b class="big" data-orata></b><span>Rată lunară</span></div>
    <div class="ec-calc__o"><b data-ototal></b><span>Cost total</span></div>
    <div class="ec-calc__o">
      <a class="ec-btn ec-btn--out" href="{TEL_LINK}">Discută cu un consultant</a>
    </div>
  </div>
  <p class="ec-calc__note">
    Calculul folosește formula de anuitate și nu include comisioane, asigurări sau taxe notariale.
    Dobânda reală depinde de bancă și de profilul tău.
  </p>
</div>"""


def calc_randament(pret, chirie):
    return f"""<div class="ec-calc" data-calc-randament>
  <h3>Calculator de randament</h3>
  <p class="ec-calc__sub">Estimează randamentul unei achiziții pentru închiriere.</p>
  <div class="ec-calc__f">
    <div>
      <label>Preț de achiziție <span class="val" data-opret></span></label>
      <input type="range" data-pret min="50000" max="130000" step="500" value="{pret}">
    </div>
    <div>
      <label>Chirie lunară estimată <span class="val" data-ochirie></span></label>
      <input type="range" data-chirie min="200" max="700" step="10" value="{chirie}">
    </div>
    <div>
      <label>Perioade neînchiriat <span class="val" data-ogol></span></label>
      <input type="range" data-gol min="0" max="25" step="1" value="8">
    </div>
  </div>
  <div class="ec-calc__out">
    <div class="ec-calc__o"><b class="big" data-obrut></b><span>Randament brut</span></div>
    <div class="ec-calc__o"><b data-onet></b><span>Randament net</span></div>
    <div class="ec-calc__o"><b data-oani2></b><span>Amortizare</span></div>
  </div>
  <p class="ec-calc__note">
    Randamentul net scade din chiria anuală perioadele neînchiriate și aproximativ 8% cheltuieli
    de administrare, impozit și reparații. Chiriile sunt estimări de piață pentru zona Păcurari,
    nu valori garantate.
  </p>
</div>"""


def card_unitate(u, r):
    return f"""<a class="ec-unit" href="{r}apartamente-iasi/{e(u['unit_id'].lower())}/">
  <div class="ec-unit__top">
    <span class="ec-unit__id">{e(u['unit_id'])}</span>
    <span class="ec-tag ec-tag--{u['status']}">{STATUS_ET[u['status']]}</span>
  </div>
  <div class="ec-unit__t">{camere_txt(u['nr_camere'])} · {mp(u['su_utila'])}</div>
  <div class="ec-unit__meta">
    <span>Blocul {bloc(u['corp'])}</span><span>{etaj_txt(u['etaj'])}</span><span>{u['orientare']}</span>
  </div>
  <div class="ec-unit__foot">
    <span class="ec-unit__price">{euro(u['pret_eur'])}</span>
    <span class="ec-unit__ppm">{round(u['pret_eur']/u['su_utila'])} €/m²</span>
  </div>
</a>"""


# =========================================================== pagina unitate
def pagina_unitate(u, similare):
    r = "../../"
    uid = u["unit_id"]
    titlu_h = f"Apartament {camere_txt(u['nr_camere'])}, {mp(u['su_utila'])} — blocul {bloc(u['corp'])}, {etaj_txt(u['etaj']).lower()}"
    disp = u["status"] == "disponibil"

    randuri = ""
    total_ver = 0
    for nume, pond in CAMERE_TIP[u["tip_apartament"]]:
        s = round(u["su_utila"] * pond, 2)
        total_ver += s
        randuri += f"<tr><td>{nume}</td><td>{mp(s)}</td></tr>"
    extra = ""
    if u["su_balcon"] > 0:
        extra = f"<tr><td>Balcon</td><td>{mp(u['su_balcon'])}</td></tr>"
    elif u["su_curte"] > 0:
        extra = f"<tr><td>Curte proprie</td><td>{mp(u['su_curte'])}</td></tr>"

    schema = {
        "@context": "https://schema.org", "@type": "Apartment",
        "@id": f"https://emerald-city.ro/apartamente-iasi/{uid.lower()}/#apartament",
        "name": titlu_h,
        "numberOfRooms": u["nr_camere"],
        "floorSize": {"@type": "QuantitativeValue", "value": u["su_utila"], "unitCode": "MTK"},
        "floorLevel": str(u["etaj"]),
        "url": f"https://emerald-city.ro/apartamente-iasi/{uid.lower()}/",
        "address": {"@type": "PostalAddress", "streetAddress": "Strada Ion Nistor",
                    "addressLocality": "Iași", "addressRegion": "Iași", "addressCountry": "RO"},
        "containedInPlace": {"@id": "https://emerald-city.ro/#ansamblu"},
        "amenityFeature": [
            {"@type": "LocationFeatureSpecification", "name": "Balcon", "value": u["su_balcon"] > 0},
            {"@type": "LocationFeatureSpecification", "name": "Boxă", "value": u["boxa_disponibila"] == "da"},
            {"@type": "LocationFeatureSpecification", "name": "Parcare subterană", "value": u["parcare_subterana"] == "da"},
        ],
        "offers": {"@type": "Offer", "price": str(u["pret_eur"]), "priceCurrency": "EUR",
                   "availability": f"https://schema.org/{STATUS_SCHEMA[u['status']]}",
                   "seller": {"@id": "https://emerald-city.ro/#dezvoltator"}},
    }

    cta = (f'<a class="ec-btn ec-btn--brass" href="#cere-detalii">Cere detalii</a>'
           f'<a class="ec-btn ec-btn--wa" href="{WA}">WhatsApp</a>') if disp else \
          f'<a class="ec-btn" href="{r}apartamente-iasi/{CATEGORII[u["nr_camere"]]["slug"]}/">Vezi apartamente similare</a>'

    continut = f"""<div class="ec-wrap">
  <nav class="ec-crumbs" aria-label="Firimituri">
    <a href="{r}">Acasă</a><span>/</span><a href="{r}apartamente-iasi/">Apartamente</a><span>/</span>
    <a href="{r}tipologii/{u['tip_apartament'].lower()}/">Tip {u['tip_apartament']}</a><span>/</span>{e(uid)}
  </nav>

  <header class="ec-phead">
    <span class="ec-tag ec-tag--{u['status']}">{STATUS_ET[u['status']]}</span>
    <h1 style="margin-top:.75rem">{e(titlu_h)}</h1>
    <div class="ec-phead__meta">
      <span>Cod unitate {e(uid)}</span><span>Etapa {u['etapa']}</span>
      <span>Tipologia {u['tip_apartament']}</span>
      <span>Orientare {ORIENTARE.get(u['orientare'], u['orientare'])}</span>
    </div>
  </header>

  <div class="ec-pricebar">
    <div>
      <div class="ec-pricebar__p">{euro(u['pret_eur'])}</div>
      <div class="ec-pricebar__s">{round(u['pret_eur']/u['su_utila'])} €/m² · TVA {u.get('tva','9')}% inclus · avans 15%</div>
    </div>
    <div class="ec-pricebar__cta">{buton_salvare(uid)}{cta}</div>
  </div>

  <section class="ec-section" style="padding-block:2.5rem">
    <dl class="ec-specs">
      <div class="ec-spec"><dt>Suprafață utilă</dt><dd>{mp(u['su_utila'])}</dd></div>
      <div class="ec-spec"><dt>{'Balcon' if u['su_balcon'] > 0 else 'Curte proprie'}</dt>
        <dd>{mp(u['su_balcon'] if u['su_balcon'] > 0 else u['su_curte'])}</dd></div>
      <div class="ec-spec"><dt>Bloc și etaj</dt><dd>{bloc(u['corp'])} · {etaj_txt(u['etaj'])}</dd></div>
      <div class="ec-spec"><dt>Camere</dt><dd>{u['nr_camere']}</dd></div>
      <div class="ec-spec"><dt>Boxă</dt><dd>{'Disponibilă' if u['boxa_disponibila']=='da' else 'Indisponibilă'}</dd></div>
      <div class="ec-spec"><dt>Parcare</dt><dd>{'Subterană' if u['parcare_subterana']=='da' else 'Supraterană'}</dd></div>
      <div class="ec-spec"><dt>Regim</dt><dd>Parter + 3 etaje</dd></div>
      <div class="ec-spec"><dt>Etapa</dt><dd>{u['etapa']}</dd></div>
    </dl>
  </section>

  <div class="ec-split" style="margin-bottom:var(--ec-gap)">
    {plan_interactiv(u['tip_apartament'], u['nr_camere'], r)}
    <div class="ec-rooms">
      <table>
        <caption class="ec-sr">Suprafețe pe cameră</caption>
        <thead><tr><th>Încăpere</th><th>Suprafață</th></tr></thead>
        <tbody>{randuri}{extra}</tbody>
        <tfoot><tr><td>Total util</td><td>{mp(u['su_utila'])}</td></tr></tfoot>
      </table>
      <p class="ec-form__note" style="padding:1rem 1.25rem">
        Defalcarea pe încăperi este orientativă. Planul definitiv se predă la semnarea antecontractului.
      </p>
    </div>
  </div>

  <div class="ec-split" style="margin-bottom:var(--ec-gap)">
    {calc_rata(u['pret_eur'])}
    <div class="ec-calc" style="display:flex;flex-direction:column;justify-content:center">
      <h3>Îl cumperi ca investiție?</h3>
      <p class="ec-calc__sub">Vezi ce randament ar aduce închiriat, cu chiriile actuale din zona Păcurari.</p>
      <p><a class="ec-btn ec-btn--brass" href="{r}investitie-apartamente-iasi/?pret={u['pret_eur']}&amp;su={u['su_utila']}">
        Calculator de randament
        <svg width="14" height="10" viewBox="0 0 14 10" fill="none" aria-hidden="true"><path d="M9 1l4 4-4 4M13 5H0" stroke="currentColor" stroke-width="1.4"/></svg>
      </a></p>
    </div>
  </div>

  <div class="ec-split" style="margin-bottom:var(--ec-gap)" id="cere-detalii">
    {formular(u, r)}
    <figure style="margin:0;overflow:hidden">
      {imagine(GALERIE_TIP[u['tip_apartament']][0], f"Amenajare orientativă pentru tipologia {u['tip_apartament']}", r, "(max-width: 62rem) 100vw, 50vw")}
    </figure>
  </div>

  <div class="ec-sticky" data-sticky>
    <span class="ec-sticky__p">{euro(u['pret_eur'])}<small>{camere_txt(u['nr_camere'])} · {mp(u['su_utila'])}</small></span>
    <span class="ec-sticky__b">
      {buton_salvare(uid)}
      <a class="ec-btn ec-btn--brass" href="{TEL_LINK}">Sună</a>
    </span>
  </div>

  <section class="ec-section" style="padding-block:2rem 4rem">
    <p class="ec-eyebrow">Alternative</p>
    <h2 class="ec-title" style="margin:1rem 0 1.5rem">Apartamente similare</h2>
    <div class="ec-similar">{''.join(card_unitate(s, r) for s in similare)}</div>
  </section>
</div>"""

    return pagina(
        f"{titlu_h} — Emerald City Iași",
        f"Apartament {camere_txt(u['nr_camere'])} de {mp(u['su_utila'])} în Emerald City, Iași zona Păcurari. "
        f"Blocul {bloc(u['corp'])}, {etaj_txt(u['etaj']).lower()}, {euro(u['pret_eur'])}. Direct de la dezvoltator.",
        continut, r, schema, f"apartamente-iasi/{uid.lower()}/")


# ========================================================== pagina tipologie
def pagina_tipologie(cod, unitati):
    r = "../../"
    nr = unitati[0]["nr_camere"]
    disp = [u for u in unitati if u["status"] == "disponibil"]
    su_min, su_max = min(u["su_utila"] for u in unitati), max(u["su_utila"] for u in unitati)
    pmin = min((u["pret_eur"] for u in disp), default=None)

    randuri = "".join(f"""<tr class="{'is-sold' if u['status'] != 'disponibil' else ''}">
      <td><a href="{r}apartamente-iasi/{u['unit_id'].lower()}/">{e(u['unit_id'])}</a></td>
      <td>{bloc(u['corp'])}</td><td>{etaj_txt(u['etaj'])}</td>
      <td class="num">{mp(u['su_utila'])}</td><td>{u['orientare']}</td>
      <td class="num" data-et="Preț">{euro(u['pret_eur'])}</td>
      <td class="st" data-et="Stare"><span class="ec-tag ec-tag--{u['status']}">{STATUS_ET[u['status']]}</span></td>
    </tr>""" for u in sorted(unitati, key=lambda x: x["pret_eur"])[:60])

    gal = "".join('<figure>' + imagine(g, f"Amenajare orientativă, tipologia {cod}", r,
                                    "(max-width: 46rem) 100vw, 33vw") + '</figure>'
                  for g in GALERIE_TIP[cod])

    schema = {
        "@context": "https://schema.org", "@type": "Apartment",
        "@id": f"https://emerald-city.ro/tipologii/{cod.lower()}/#tipologie",
        "name": f"Apartament {camere_txt(nr)} tip {cod} — Emerald City Iași",
        "numberOfRooms": nr,
        "floorSize": {"@type": "QuantitativeValue", "minValue": su_min, "maxValue": su_max, "unitCode": "MTK"},
        "url": f"https://emerald-city.ro/tipologii/{cod.lower()}/",
        "address": {"@type": "PostalAddress", "streetAddress": "Strada Ion Nistor",
                    "addressLocality": "Iași", "addressRegion": "Iași", "addressCountry": "RO"},
    }

    continut = f"""<div class="ec-wrap">
  <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span><a href="{r}tipologii/">Tipologii</a><span>/</span>Tip {cod}</nav>

  <header class="ec-phead">
    <p class="ec-eyebrow">Tipologia {cod}</p>
    <h1 style="margin-top:1rem">Apartament {camere_txt(nr)}, tip {cod}</h1>
    <p class="ec-body" style="max-width:60ch;font-size:var(--ec-lead)">{DESC_TIP[cod]}</p>
  </header>

  <dl class="ec-specs" style="margin-bottom:var(--ec-gap)">
    <div class="ec-spec"><dt>Suprafață utilă</dt><dd>{mp(su_min)} – {mp(su_max)}</dd></div>
    <div class="ec-spec"><dt>Camere</dt><dd>{nr}</dd></div>
    <div class="ec-spec"><dt>Disponibile</dt><dd>{len(disp)} din {len(unitati)}</dd></div>
    <div class="ec-spec"><dt>Preț de la</dt><dd>{euro(pmin) if pmin else '—'}</dd></div>
  </dl>

  <div class="ec-split" style="margin-bottom:var(--ec-gap)">
    {plan_interactiv(cod, nr, r)}
    {formular(None, r)}
  </div>

  <section class="ec-section" style="padding-block:2rem">
    <h2 class="ec-title" style="margin-bottom:1.5rem">Amenajare</h2>
    <div class="ec-gal">{gal}</div>
    <p class="ec-form__note">Imaginile au caracter orientativ. Amenajarea nu este inclusă în prețul de vânzare.</p>
  </section>

  <section class="ec-section" style="padding-block:2rem 4rem">
    <h2 class="ec-title" style="margin-bottom:1.5rem">Unități disponibile de acest tip</h2>
    <div class="ec-table">
      <table>
        <thead><tr><th>Cod</th><th>Bloc</th><th>Etaj</th><th>Suprafață</th><th>Orientare</th><th>Preț</th><th>Stare</th></tr></thead>
        <tbody>{randuri}</tbody>
      </table>
    </div>
    <p class="ec-more"><a class="ec-btn ec-btn--out" href="{r}apartamente-iasi/?tip={cod}">Vezi toate unitățile tip {cod}</a></p>
  </section>
</div>"""

    return pagina(
        f"Apartament {camere_txt(nr)} tip {cod} în Iași — Emerald City",
        f"Apartament {camere_txt(nr)} tip {cod}, {mp(su_min)}–{mp(su_max)}, în Emerald City, Iași zona Păcurari. "
        f"{len(disp)} unități disponibile, de la {euro(pmin) if pmin else '—'}.",
        continut, r, schema, f"tipologii/{cod.lower()}/")


# ============================================================ pagina listare
def pagina_listare(unitati):
    r = "../../"
    blocuri = sorted({u["corp"] for u in unitati}, key=lambda c: int(c[1:]))
    chip = lambda grp, v, et: f'<button class="ec-chip" data-f="{grp}" data-v="{v}">{et}</button>'

    continut = f"""<div class="ec-wrap">
  <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span><a href="{r}apartamente-iasi/">Apartamente</a><span>/</span>Disponibilitate</nav>

  <header class="ec-phead">
    <p class="ec-eyebrow">Disponibilitate și prețuri</p>
    <h1 style="margin-top:1rem">Toate apartamentele disponibile</h1>
    <p class="ec-body" style="max-width:62ch;font-size:var(--ec-lead)">
      {len(unitati)} de apartamente cu 1, 2 și 3 camere. Filtrează după ce contează pentru tine —
      rezultatele se actualizează instant, fără reîncărcarea paginii.
    </p>
  </header>

  <div class="ec-filters">
    <div class="ec-field"><label id="l1">Camere</label>
      <div class="ec-chips" role="group" aria-labelledby="l1">
        {''.join(chip('camere', n, camere_txt(n)) for n in (1,2,3))}</div></div>

    <div class="ec-field"><label id="l2">Etaj</label>
      <div class="ec-chips" role="group" aria-labelledby="l2">
        {''.join(chip('etaj', n, etaj_txt(n)) for n in (0,1,2,3))}</div></div>

    <div class="ec-field"><label id="l3">Etapa</label>
      <div class="ec-chips" role="group" aria-labelledby="l3">
        {''.join(chip('etapa', et, 'Etapa ' + et) for et in ('I','II','III'))}</div></div>

    <div class="ec-field"><label id="l4">Stare</label>
      <div class="ec-chips" role="group" aria-labelledby="l4">
        {''.join(chip('status', s, STATUS_ET[s]) for s in ('disponibil','rezervat','vandut'))}</div></div>

    <div class="ec-field"><label for="fPret">Preț maxim</label>
      <div class="ec-range"><input type="range" id="fPret" min="50000" max="130000" step="1000" value="130000">
        <output for="fPret" id="oPret">130.000 €</output></div></div>

    <div class="ec-field"><label for="fSu">Suprafață minimă</label>
      <div class="ec-range"><input type="range" id="fSu" min="36" max="81" step="1" value="36">
        <output for="fSu" id="oSu">36 m²</output></div></div>

    <div class="ec-field"><label id="l5">Extra</label>
      <div class="ec-chips" role="group" aria-labelledby="l5">
        {chip('extra','balcon','Cu balcon')}{chip('extra','curte','Cu curte')}
        {chip('extra','boxa','Cu boxă')}{chip('extra','parcare','Parcare subterană')}</div></div>

    <div class="ec-field"><label id="l6">Bloc</label>
      <div class="ec-chips" role="group" aria-labelledby="l6">
        {''.join(chip('corp', c, bloc(c)) for c in blocuri)}</div></div>

    <div class="ec-filters__foot">
      <span class="ec-toolbar__n" id="fCount">—</span>
      <button class="ec-btn ec-btn--out" id="fReset" type="button">Resetează filtrele</button>
    </div>
  </div>

  <div class="ec-toolbar">
    <div class="ec-search" style="flex:1;min-width:16rem">
      <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="7" cy="7" r="5"/><path d="M11 11l4 4"/></svg>
      <input type="search" id="fSearch" placeholder="Caută: „2 camere etaj 3 bloc 12” sau un cod de unitate"
             aria-label="Caută apartamente">
    </div>
    <span class="ec-toolbar__n">Apasă pe capul de tabel pentru sortare.</span>
  </div>

  <div class="ec-table">
    <table id="fTable">
      <caption class="ec-sr">Lista apartamentelor disponibile</caption>
      <thead><tr>
        <th data-s="id">Cod</th><th data-s="corp">Bloc</th><th data-s="etaj">Etaj</th>
        <th data-s="tip">Tip</th><th data-s="camere">Camere</th><th data-s="su">Suprafață</th>
        <th data-s="orientare">Orientare</th><th data-s="pret" data-dir="asc">Preț</th><th>Stare</th>
      </tr></thead>
      <tbody id="fBody"></tbody>
    </table>
  </div>
  <div id="fEmpty"></div>
  <div class="ec-more"><button class="ec-btn ec-btn--out" id="fMore" type="button">Încarcă încă 50</button></div>

  <section class="ec-section" style="padding-block:3rem 4rem">{formular(None, r)}</section>
</div>

<script src="{r}assets/js/listare.js"></script>"""

    return pagina(
        "Disponibilitate și prețuri — apartamente Emerald City Iași",
        f"Toate cele {len(unitati)} de apartamente din Emerald City, Iași zona Păcurari. "
        "Filtrează după camere, etaj, suprafață și preț. Direct de la dezvoltator.",
        continut, r, None, "apartamente-iasi/disponibilitate/")


def pagina_hub_tipologii(grupe):
    r = "../"
    carduri = ""
    for cod in sorted(grupe):
        us = grupe[cod]
        disp = [u for u in us if u["status"] == "disponibil"]
        pmin = min((u["pret_eur"] for u in disp), default=None)
        carduri += f"""<a class="ec-type" href="{r}tipologii/{cod.lower()}/">
          <div class="ec-type__plan">{plan_svg(us[0]['nr_camere'], cod, sum(x['su_utila'] for x in us) / len(us), True)}</div>
          <div class="ec-type__code">{cod}</div>
          <div class="ec-type__rows">
            <div><span>Camere</span><b>{us[0]['nr_camere']}</b></div>
            <div><span>Suprafață</span><b>{mp(min(u['su_utila'] for u in us))} – {mp(max(u['su_utila'] for u in us))}</b></div>
            <div><span>Disponibile</span><b>{len(disp)} din {len(us)}</b></div>
          </div>
          <span class="ec-unit__price">{'de la ' + euro(pmin) if pmin else '—'}</span>
        </a>"""

    continut = f"""<div class="ec-wrap">
  <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Tipologii</nav>
  <header class="ec-phead">
    <p class="ec-eyebrow">Tipologii</p>
    <h1 style="margin-top:1rem">Compartimentări disponibile</h1>
    <p class="ec-body" style="max-width:62ch;font-size:var(--ec-lead)">
      Cinci compartimentări, de la garsonieră la trei camere. Fiecare tipologie are pagină proprie,
      cu plan, amenajare și lista unităților disponibile.
    </p>
  </header>
  <div class="ec-types" style="padding-bottom:4rem">{carduri}</div>
</div>"""
    return pagina("Tipologii de apartamente — Emerald City Iași",
                  "Cinci compartimentări de apartamente în Emerald City, Iași zona Păcurari: "
                  "garsonieră, 2 camere și 3 camere.", continut, r, None, "tipologii/")



# ============================================== hub de siloz /apartamente-iasi/
def _icon(d):
    return ('<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"'
            ' stroke-width="1.5" aria-hidden="true">' + d + '</svg>')

ARGUMENTE = [
    ("Finisaje premium incluse",
     "Nu cumperi la gri. Apartamentul se predă finisat, cu materiale alese de un birou de design.",
     '<path d="M12 3l2.5 6H21l-5 4 2 7-6-4-6 4 2-7-5-4h6.5z"/>'),
    ("Parcare la subsol",
     "258 de locuri subterane din 940 în total. Mașina nu stă între blocuri, iar spațiul dintre clădiri rămâne verde.",
     '<path d="M5 17h14M6 17V9l2-4h8l2 4v8M8 13h8"/><circle cx="8" cy="17" r="2"/><circle cx="16" cy="17" r="2"/>'),
    ("Direct de la dezvoltator",
     "Fără comision de intermediere. Discuți cu cine construiește, nu cu un agent care revinde.",
     '<path d="M3 21h18M5 21V8l7-5 7 5v13M9 21v-6h6v6"/>'),
    ("Aproape o treime verde",
     "15.501 m² de spațiu verde amenajat, parc dendrologic și loc de joacă, pe cinci hectare.",
     '<path d="M12 21v-7M12 14c0-4 3-7 7-7 0 4-3 7-7 7zM12 14c0-4-3-7-7-7 0 4 3 7 7 7z"/>'),
]

DOTARI = ["Finisaje premium incluse în preț", "Tâmplărie cu geam termoizolant",
          "Încălzire în pardoseală în băi", "Balcon la fiecare apartament",
          "Boxă disponibilă la demisol", "Interfon și acces controlat",
          "Lift în fiecare bloc", "Contorizare individuală"]
FACILITATI = ["Parc dendrologic amenajat", "Loc de joacă pentru copii",
              "Spații comerciale la parter", "940 de locuri de parcare",
              "Alei pietonale între blocuri", "Iluminat exterior integrat",
              "Acces din Strada Ion Nistor", "7 km până în centrul Iașului"]

SAGEATA = ('<span class="ec-arrow" style="padding:0"><svg width="22" height="10" viewBox="0 0 22 10"'
           ' fill="none" aria-hidden="true"><path d="M17 1l4 4-4 4M21 5H0" stroke="currentColor"'
           ' stroke-width="1.3"/></svg></span>')


def pagina_hub(unitati, grupe):
    r = "../"
    disp_tot = [u for u in unitati if u["status"] == "disponibil"]
    su_min = min(u["su_utila"] for u in unitati)
    su_max = max(u["su_utila"] for u in unitati)
    p_min = min(u["pret_eur"] for u in disp_tot)

    silo = ""
    for nr in (1, 2, 3):
        c = CATEGORII[nr]
        us = [u for u in unitati if u["nr_camere"] == nr]
        d = [u for u in us if u["status"] == "disponibil"]
        pm = min((x["pret_eur"] for x in d), default=None)
        tipuri = sorted({u["tip_apartament"] for u in us})
        silo += f"""<a class="ec-silo__c ec-rv" href="{r}apartamente-iasi/{c['slug']}/">
          <figure>
            {imagine(c['img'], c['titlu'] + " în Emerald City", r, "(max-width: 52rem) 100vw, 33vw")}
            <span class="ec-silo__badge">{len(d)} disponibile</span>
          </figure>
          <div class="ec-silo__b">
            <h2 class="ec-silo__t">{c['titlu']}</h2>
            <div class="ec-silo__rows">
              <div><span>Suprafață utilă</span><b>{mp(min(u['su_utila'] for u in us))} – {mp(max(u['su_utila'] for u in us))}</b></div>
              <div><span>Compartimentări</span><b>{', '.join(tipuri)}</b></div>
              <div><span>Total unități</span><b>{len(us)}</b></div>
            </div>
            <div class="ec-silo__foot">
              <span class="ec-silo__p">{euro(pm) if pm else '—'}<small>preț de pornire</small></span>
              {SAGEATA}
            </div>
          </div>
        </a>"""

    why = "".join('<div class="ec-why__i ec-rv">' + _icon(ic) + '<h3>' + t + '</h3><p>' + d + '</p></div>'
                  for t, d, ic in ARGUMENTE)

    continut = f"""<div class="ec-wrap">
  <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Apartamente noi în Iași</nav>

  <header class="ec-phead">
    <p class="ec-eyebrow">Apartamente</p>
    <h1 style="margin-top:1rem">Apartamente noi în Iași, zona Păcurari</h1>
    <p class="ec-body" style="max-width:66ch;font-size:var(--ec-lead)">
      Emerald City are {len(unitati)} de apartamente cu 1, 2 și 3 camere, în cinci compartimentări.
      Toate se predau cu finisaje premium incluse, cu balcon și cu boxă disponibilă la demisol.
      Alege mai jos după numărul de camere, sau mergi direct la lista completă cu filtre.
    </p>
    <div class="ec-hstats">
      <div class="ec-hstat"><b>{len(unitati)}</b><span><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 21V5a1 1 0 011-1h9a1 1 0 011 1v16"/><path d="M15 21V10h4a1 1 0 011 1v10"/><path d="M7 8h2M7 12h2M7 16h2M11 8h1M11 12h1M11 16h1"/><path d="M2 21h20"/></svg> Apartamente</span></div>
      <div class="ec-hstat"><b>{len(disp_tot)}</b><span>Disponibile acum</span></div>
      <div class="ec-hstat"><b>{mp(su_min)} – {mp(su_max)}</b><span>Suprafață utilă</span></div>
      <div class="ec-hstat"><b>{euro(p_min)}</b><span>Preț de pornire</span></div>
    </div>
  </header>

  <section class="ec-section" style="padding-block:1rem 3rem">
    <h2 class="ec-title" style="margin-bottom:1.5rem">Alege după numărul de camere</h2>
    <div class="ec-silo">{silo}</div>
  </section>

  <section class="ec-section" style="padding-block:1rem 3rem">
    <h2 class="ec-title" style="margin-bottom:1.5rem">De ce un apartament nou aici</h2>
    <div class="ec-why">{why}</div>
  </section>

  <section class="ec-section" style="padding-block:1rem 3rem">
    <h2 class="ec-title" style="margin-bottom:1.5rem">Dotări și facilități</h2>
    <div class="ec-lists">
      <div class="ec-list"><h3>Dotări apartament</h3><ul>{''.join('<li>' + x + '</li>' for x in DOTARI)}</ul></div>
      <div class="ec-list"><h3>Facilități ansamblu</h3><ul>{''.join('<li>' + x + '</li>' for x in FACILITATI)}</ul></div>
    </div>
  </section>

  <section class="ec-section" style="padding-block:1rem 3rem">
    <div class="ec-strip">
      <div>
        <h2>Vezi toate cele {len(unitati)} de apartamente</h2>
        <p>Filtrează după camere, etaj, bloc, suprafață și buget. Rezultatele se actualizează instant.</p>
      </div>
      <div class="ec-strip__cta">
        <a class="ec-btn ec-btn--white" href="{r}apartamente-iasi/disponibilitate/">Disponibilitate și prețuri</a>
        <a class="ec-btn ec-btn--wa" href="{WA}">WhatsApp</a>
      </div>
    </div>
  </section>

  <section class="ec-section" style="padding-block:1rem 4rem">
    <div class="ec-prose">
      <h2>Despre apartamentele noi din Emerald City</h2>
      <p>
        Emerald City este un ansamblu rezidențial din Iași, zona Păcurari, cu {len(unitati)} de
        apartamente distribuite în 18 blocuri de tip parter plus trei etaje. Regimul scund și
        distanțele generoase dintre clădiri înseamnă lumină naturală în fiecare apartament și mai
        puțină aglomerare decât într-un bloc-turn.
      </p>
      <h3>Ce tipuri de apartamente sunt disponibile</h3>
      <p>
        Ansamblul are cinci compartimentări: 1A pentru o cameră, 2A și 2B pentru două camere,
        3A și 3B pentru trei camere. Suprafețele utile pornesc de la {mp(su_min)} și ajung la
        {mp(su_max)}. Fiecare apartament are balcon, iar cele de la parter au curte proprie.
      </p>
      <h3>Cum se cumpără</h3>
      <p>
        Vânzarea se face direct de la dezvoltator, Tala Sapphire S.R.L., fără comision de
        intermediere. Prețurile afișate includ TVA, iar rezervarea se face cu un avans de 15% la
        semnarea antecontractului, diferența fiind achitată la predare.
      </p>
      <h3>Unde se află</h3>
      <p>
        În zona Păcurari, la ieșirea de nord-vest a Iașului, cu acces din Strada Ion Nistor.
        Aproximativ 7 km pană in centrul orașului, 5 km pană in Copou și 6 km pană la
        Universitatea Alexandru Ioan Cuza.
      </p>
    </div>
  </section>
</div>"""

    return pagina(
        "Apartamente noi in Iasi, zona Pacurari \u2014 1, 2, 3 camere | Emerald City",
        "Apartamente noi de vânzare în Iași, zona Păcurari: " + str(len(unitati)) +
        " de unități cu 1, 2 sau 3 camere, cu finisaje premium incluse. Direct de la dezvoltator.",
        continut, r, None, "apartamente-iasi/")


# ==================================================== pagina de categorie
def pagina_categorie(nr, unitati, grupe):
    r = "../../"
    c = CATEGORII[nr]
    us = [u for u in unitati if u["nr_camere"] == nr]
    disp = [u for u in us if u["status"] == "disponibil"]
    su_min, su_max = min(u["su_utila"] for u in us), max(u["su_utila"] for u in us)
    pmin = min((u["pret_eur"] for u in disp), default=None)
    tipuri = sorted({u["tip_apartament"] for u in us})

    carduri = ""
    for cod in tipuri:
        tu = grupe[cod]
        td = [u for u in tu if u["status"] == "disponibil"]
        tp = min((u["pret_eur"] for u in td), default=None)
        carduri += f"""<a class="ec-type" href="{r}tipologii/{cod.lower()}/">
          <div class="ec-type__plan">{plan_svg(nr, cod, sum(u['su_utila'] for u in tu) / len(tu), True)}</div>
          <div class="ec-type__code">{cod}</div>
          <div class="ec-type__rows">
            <div><span>Suprafață</span><b>{mp(min(u['su_utila'] for u in tu))} – {mp(max(u['su_utila'] for u in tu))}</b></div>
            <div><span>Disponibile</span><b>{len(td)} din {len(tu)}</b></div>
          </div>
          <span class="ec-unit__price">{'de la ' + euro(tp) if tp else '—'}</span>
        </a>"""

    randuri = "".join(f"""<tr class="{'is-sold' if u['status'] != 'disponibil' else ''}">
      <td data-et="Cod"><a href="{r}apartamente-iasi/{u['unit_id'].lower()}/">{e(u['unit_id'])}</a></td>
      <td data-et="Bloc">{bloc(u['corp'])}</td><td data-et="Etaj">{etaj_txt(u['etaj'])}</td><td data-et="Tip">{u['tip_apartament']}</td>
      <td class="num" data-et="Suprafață">{mp(u['su_utila'])}</td><td data-et="Orientare">{u['orientare']}</td>
      <td class="num" data-et="Preț">{euro(u['pret_eur'])}</td>
      <td class="st" data-et="Stare"><span class="ec-tag ec-tag--{u['status']}">{STATUS_ET[u['status']]}</span></td>
    </tr>""" for u in sorted(disp, key=lambda x: x["pret_eur"])[:40])

    continut = f"""<div class="ec-wrap">
  <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>
    <a href="{r}apartamente-iasi/">Apartamente</a><span>/</span>{c['titlu']}</nav>

  <header class="ec-phead">
    <p class="ec-eyebrow">{c['titlu']}</p>
    <h1 style="margin-top:1rem">{c['h1']}</h1>
    <p class="ec-body" style="max-width:66ch;font-size:var(--ec-lead)">{c['lead']}</p>
    <div class="ec-hstats">
      <div class="ec-hstat"><b>{len(disp)}</b><span>Disponibile acum</span></div>
      <div class="ec-hstat"><b>{mp(su_min)} – {mp(su_max)}</b><span>Suprafață utilă</span></div>
      <div class="ec-hstat"><b>{len(tipuri)}</b><span>Compartimentări</span></div>
      <div class="ec-hstat"><b>{euro(pmin) if pmin else '—'}</b><span>Preț de pornire</span></div>
    </div>
  </header>

  <section class="ec-section" style="padding-block:1rem 3rem">
    <h2 class="ec-title" style="margin-bottom:1.5rem">Compartimentări disponibile</h2>
    <div class="ec-types">{carduri}</div>
  </section>

  <section class="ec-section" style="padding-block:1rem 3rem">
    <h2 class="ec-title" style="margin-bottom:1.5rem">Unități disponibile</h2>
    <div class="ec-table">
      <table>
        <caption class="ec-sr">{c['titlu']} disponibile în Emerald City</caption>
        <thead><tr><th>Cod</th><th>Bloc</th><th>Etaj</th><th>Tip</th><th>Suprafață</th>
          <th>Orientare</th><th>Preț</th><th>Stare</th></tr></thead>
        <tbody>{randuri}</tbody>
      </table>
    </div>
    <p class="ec-more"><a class="ec-btn ec-btn--out" href="{r}apartamente-iasi/disponibilitate/?camere={nr}">Vezi toate cele {len(disp)} de unități disponibile</a></p>
  </section>

  <section class="ec-section" style="padding-block:1rem 3rem">
    <div class="ec-split">{formular(None, r)}
      <figure style="margin:0;overflow:hidden">
        {imagine(c['img'], c['titlu'] + " — amenajare orientativă", r, "(max-width: 62rem) 100vw, 50vw")}
      </figure>
    </div>
  </section>

  <section class="ec-section" style="padding-block:1rem 4rem">
    <div class="ec-prose">
      <h2>{c['h1']}</h2>
      <p>
        În Emerald City există {len(us)} de {c['titlu'].lower()}, dintre care {len(disp)} sunt
        disponibile în acest moment. Suprafețele utile pornesc de la {mp(su_min)} și ajung la
        {mp(su_max)}, în {len(tipuri)} compartimentări: {', '.join(tipuri)}.
      </p>
      <p>
        Toate se predau cu finisaje premium incluse în preț, au balcon, iar cele de la parter au
        curte proprie. Boxa de la demisol și locul de parcare subteran se pot achiziționa separat.
      </p>
    </div>
  </section>
</div>"""

    return pagina(
        c["h1"] + " - Emerald City",
        c["titlu"] + " de vânzare în Iași, zona Păcurari: " + str(len(disp)) +
        " unități disponibile. Direct de la dezvoltator, fără comision.",
        continut, r, None, "apartamente-iasi/" + c["slug"] + "/")



# ======================================================= investitie ==
def chirie_estimata(su):
    """Estimare de piata pentru zona Pacurari, ~6,2 EUR/mp util."""
    return int(round(su * 6.2 / 10) * 10)


def pagina_investitie(unitati):
    r = "../"
    disp = [u for u in unitati if u["status"] == "disponibil"]
    gars = [u for u in disp if u["nr_camere"] == 1]
    ref = min(gars, key=lambda u: u["pret_eur"]) if gars else min(disp, key=lambda u: u["pret_eur"])
    ch_ref = chirie_estimata(ref["su_utila"])

    # cele mai bune randamente estimate
    scor = sorted(disp, key=lambda u: -(chirie_estimata(u["su_utila"]) * 12 / u["pret_eur"]))[:12]
    randuri = ""
    for u in scor:
        ch = chirie_estimata(u["su_utila"])
        y = ch * 12 / u["pret_eur"] * 100
        randuri += f"""<tr>
          <td><a href="{r}apartamente-iasi/{u['unit_id'].lower()}/">{e(u['unit_id'])}</a></td>
          <td>{camere_txt(u['nr_camere'])}</td>
          <td class="num">{mp(u['su_utila'])}</td>
          <td class="num">{euro(u['pret_eur'])}</td>
          <td class="num">{euro(ch)}</td>
          <td class="num"><b>{y:.2f}</b>%</td>
        </tr>"""

    continut = f"""<div class="ec-wrap">
  <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Investiție</nav>

  <header class="ec-phead">
    <p class="ec-eyebrow">Investiție</p>
    <h1 style="margin-top:1rem">Investiție în apartamente noi în Iași</h1>
    <p class="ec-body" style="max-width:66ch;font-size:var(--ec-lead)">
      Emerald City are {len(gars)} de garsoniere disponibile — formatul cel mai cerut pe piața de
      închirieri din Iași, unde cererea vine constant dinspre studenți și tineri angajați.
      Calculează mai jos ce randament ar aduce o achiziție.
    </p>
  </header>

  <section class="ec-section" style="padding-block:0 3rem">
    {calc_randament(ref['pret_eur'], ch_ref)}
  </section>

  <section class="ec-section" style="padding-block:0 3rem">
    <h2 class="ec-title" style="margin-bottom:1.5rem">Cele mai bune randamente estimate</h2>
    <div class="ec-table">
      <table>
        <caption class="ec-sr">Apartamente ordonate după randamentul brut estimat</caption>
        <thead><tr><th>Cod</th><th>Tip</th><th>Suprafață</th><th>Preț</th>
          <th>Chirie estimată</th><th>Randament brut</th></tr></thead>
        <tbody>{randuri}</tbody>
      </table>
    </div>
    <p class="ec-calc__note">
      Chiriile sunt estimări de piață pentru zona Păcurari, calculate la aproximativ 6,2 €/m² util.
      Nu sunt valori garantate și nu constituie consultanță de investiții.
    </p>
  </section>

  <section class="ec-section" style="padding-block:0 3rem">
    <h2 class="ec-title" style="margin-bottom:1.5rem">De ce Iași și de ce zona Păcurari</h2>
    <div class="ec-why">
      <div class="ec-why__i"><h3>Cerere constantă de chirii</h3>
        <p>Iașul are unul dintre cele mai mari centre universitare din țară. Cererea de garsoniere
           și apartamente de două camere nu depinde de un singur angajator.</p></div>
      <div class="ec-why__i"><h3>Aproape de Copou</h3>
        <p>Circa 5 km până în Copou și 6 km până la Universitatea „Alexandru Ioan Cuza”,
           zona cu cea mai mare concentrare de studenți.</p></div>
      <div class="ec-why__i"><h3>Locuință nouă, costuri mici</h3>
        <p>Clădire nouă înseamnă cheltuieli de întreținere mai mici și mai puține reparații
           neprevăzute decât într-un bloc vechi.</p></div>
      <div class="ec-why__i"><h3>Direct de la dezvoltator</h3>
        <p>Fără comision de intermediere la achiziție — un cost pe care îl recuperezi
           din primele luni de chirie.</p></div>
    </div>
  </section>

  <section class="ec-section" style="padding-block:0 4rem">
    <div class="ec-split">
      {formular(None, r)}
      <div class="ec-prose">
        <h2>Ce trebuie știut înainte</h2>
        <h3>Randament brut sau net</h3>
        <p>
          Randamentul brut împarte chiria anuală la prețul de achiziție. Cel net scade
          perioadele neînchiriate, impozitul, cheltuielile de administrare și reparațiile.
          Diferența dintre cele două este de obicei de un punct procentual sau mai mult.
        </p>
        <h3>Costuri care nu apar în calculator</h3>
        <p>
          Taxele notariale, intabularea, mobilarea inițială și eventualul comision de
          administrare nu sunt incluse. Pentru o garsonieră, mobilarea completă pornește
          în general de la câteva mii de euro.
        </p>
        <h3>Nu este consultanță financiară</h3>
        <p>
          Cifrele de pe această pagină sunt estimări bazate pe prețuri de listare și pe chirii
          observate în zonă. Decizia de investiție rămâne a ta; pentru o evaluare completă
          discută cu un consultant financiar.
        </p>
      </div>
    </div>
  </section>
</div>"""

    return pagina(
        "Investiție în apartamente noi în Iași — randament și calculator | Emerald City",
        "Calculator de randament pentru apartamente noi în Iași, zona Păcurari. "
        f"{len(gars)} de garsoniere disponibile, cu estimări de chirie și amortizare.",
        continut, r, None, "investitie-apartamente-iasi/")


# ======================================================= comparator ==
def pagina_comparator():
    r = "../"
    continut = f"""<div class="ec-wrap">
  <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Compară apartamente</nav>
  <header class="ec-phead">
    <p class="ec-eyebrow">Comparator</p>
    <h1 style="margin-top:1rem">Compară apartamentele salvate</h1>
    <p class="ec-body" style="max-width:62ch;font-size:var(--ec-lead)">
      Adaugă apartamente cu butonul „Salvează” de pe paginile de unitate, apoi trimite linkul
      acestei pagini cui vrei. Lista se păstrează și în adresă, deci funcționează și pe alt dispozitiv.
    </p>
  </header>
  <div id="cmpOut"></div>
  <p style="margin:2rem 0 4rem"><a class="ec-btn ec-btn--out" href="{r}apartamente-iasi/disponibilitate/">Caută alte apartamente</a></p>
</div>
<script src="{r}assets/js/compara.js"></script>"""
    return pagina("Compară apartamente — Emerald City Iași",
                  "Compară până la șase apartamente din Emerald City, Iași zona Păcurari.",
                  continut, r, None, "compara/")


# ========================================================== contact ==
def pagina_contact():
    r = "../"
    continut = f"""<div class="ec-wrap">
  <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Contact</nav>
  <header class="ec-phead">
    <p class="ec-eyebrow">Contact</p>
    <h1 style="margin-top:1rem">Vorbește cu echipa de vânzări</h1>
    <p class="ec-body" style="max-width:62ch;font-size:var(--ec-lead)">
      Răspundem în aceeași zi lucrătoare. Pentru o vizionare la fața locului, programează-te
      telefonic sau pe WhatsApp.
    </p>
  </header>

  <div class="ec-split" style="margin-bottom:var(--ec-gap)">
    {formular(None, r)}
    <div class="ec-panel">
      <h2 class="ec-title" style="font-size:1.1rem;margin-bottom:1.25rem">Date de contact</h2>
      <div class="ec-dist">
        <div><span>Telefon</span><b><a href="{TEL_LINK}">{TEL_AFIS}</a></b></div>
        <div><span>Email</span><b><a href="mailto:vanzari@emerald-city.ro">vanzari@emerald-city.ro</a></b></div>
        <div><span>WhatsApp</span><b><a href="{WA}">Scrie-ne</a></b></div>
        <div><span>Adresă</span><b>Str. Ion Nistor, Iași</b></div>
        <div style="border:0"><span>Dezvoltator</span><b>Tala Sapphire S.R.L.</b></div>
      </div>
      <p class="ec-calc__note">Program: luni–vineri 9–18, sâmbătă 10–14.</p>
    </div>
  </div>

  <div class="ec-media" style="min-height:22rem;margin-bottom:4rem">
    <p>Hartă interactivă<br>— de implementat —</p>
  </div>
</div>"""
    return pagina("Contact — Emerald City Iași",
                  "Contact Emerald City, ansamblu rezidențial în Iași, zona Păcurari. "
                  "Telefon, email și programare vizionare.",
                  continut, r, None, "contact/")



# ========================================================= zona Pacurari ==
POI = [
    ("Centrul Iașului", "7 km", "~15 min cu mașina"),
    ("Copou", "5 km", "~12 min"),
    ("Universitatea „Alexandru Ioan Cuza”", "6 km", "~14 min"),
    ("Palas Mall", "8 km", "~18 min"),
    ("Spitalul Sf. Spiridon", "7 km", "~16 min"),
    ("Aeroportul Iași", "11 km", "~22 min"),
    ("Grădina Botanică", "4 km", "~10 min"),
    ("Ieșire spre Botoșani (DN28)", "2 km", "~4 min"),
]


def pagina_zona():
    r = "../"
    randuri = "".join(f"<tr><td>{a}</td><td class='num'>{b}</td><td>{c}</td></tr>"
                      for a, b, c in POI)
    continut = f"""<div class="ec-wrap">
  <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Zona Păcurari</nav>

  <header class="ec-phead">
    <p class="ec-eyebrow">Amplasament</p>
    <h1 style="margin-top:1rem">Apartamente în Iași, zona Păcurari</h1>
    <p class="ec-body" style="max-width:66ch;font-size:var(--ec-lead)">
      Păcurari este una dintre cele mai căutate zone rezidențiale din Iași: aproape de Copou
      și de centrul universitar, dar suficient de la margine cât să mai existe teren pentru
      ansambluri cu spațiu între clădiri.
    </p>
  </header>

  <section class="ec-section" style="padding-block:0 3rem">
    <div class="ec-split">
      <div class="ec-panel">
        <h2 class="ec-title" style="font-size:1.1rem;margin-bottom:1.25rem">Distanțe și timpi</h2>
        <div class="ec-table" style="background:transparent">
          <table>
            <caption class="ec-sr">Distanțe de la Emerald City</caption>
            <thead><tr><th>Destinație</th><th>Distanță</th><th>Timp estimat</th></tr></thead>
            <tbody>{randuri}</tbody>
          </table>
        </div>
        <p class="ec-calc__note">Distanțe orientative, măsurate pe traseu rutier. De confirmat.</p>
      </div>
      <div class="ec-media"><p>Hartă interactivă<br>puncte de interes<br>— de implementat —</p></div>
    </div>
  </section>

  <section class="ec-section" style="padding-block:0 4rem">
    <div class="ec-prose">
      <h2>Ce înseamnă să locuiești în Păcurari</h2>
      <p>
        Zona s-a dezvoltat în jurul axei Păcurari, una dintre principalele artere de ieșire
        din Iași spre nord-vest. Are transport public constant spre centru, magazine de
        proximitate și acces rapid la Copou, unde se află cea mai mare parte a centrului
        universitar ieșean.
      </p>
      <h3>Pentru cine este potrivită</h3>
      <p>
        Pentru familii tinere care vor spațiu verde fără să iasă din oraș, pentru cei care
        lucrează în zona de nord-vest și pentru investitori: cererea de chirii este susținută
        de apropierea de universități.
      </p>
      <h3>Cum ajungi</h3>
      <p>
        Accesul în Emerald City se face din Strada Ion Nistor. Din centrul Iașului sunt
        aproximativ 7 km pe ruta Păcurari, iar ieșirea spre Botoșani, pe DN28, este la
        aproximativ 2 km.
      </p>
      <h3>Ce se construiește în zonă</h3>
      <p>
        Emerald City este unul dintre cele mai mari ansambluri din zonă, cu 925 de apartamente
        în 18 blocuri de tip parter plus trei etaje, pe un teren de cinci hectare din care
        aproape o treime rămâne spațiu verde amenajat.
      </p>
    </div>
  </section>

  <section class="ec-section" style="padding-block:0 4rem">
    <div class="ec-strip">
      <div><h2>Vezi apartamentele disponibile</h2>
        <p>925 de apartamente cu 1, 2 și 3 camere, cu filtre după buget, etaj și suprafață.</p></div>
      <div class="ec-strip__cta">
        <a class="ec-btn ec-btn--white" href="{r}apartamente-iasi/">Apartamente</a>
      </div>
    </div>
  </section>
</div>"""
    return pagina("Apartamente în Iași, zona Păcurari — ghid de zonă | Emerald City",
                  "Ghid al zonei Păcurari din Iași: distanțe, transport, cui i se potrivește "
                  "și ce se construiește. Emerald City, 925 de apartamente noi.",
                  continut, r, None, "apartamente-iasi-pacurari/")


# ========================================================= stadiu lucrari ==
JURNAL = [
    ("Septembrie 2026", "Etapa I — structură la nivelul etajului 2",
     "Turnarea planșeului peste etajul 1 s-a încheiat la blocurile 1–4. La blocurile 5 și 6 "
     "se lucrează la cofraje. Săpătura pentru demisolurile blocurilor 7–8 a început."),
    ("August 2026", "Etapa I — fundații finalizate",
     "Fundațiile pentru blocurile 1–6 sunt turnate și recepționate. A început ridicarea "
     "structurii la blocurile 1 și 2."),
    ("Iulie 2026", "Organizare de șantier și terasamente",
     "Platforma de organizare a fost amenajată, drumurile de acces provizorii sunt "
     "funcționale, iar terasamentele pentru prima etapă sunt finalizate."),
]


def pagina_stadiu():
    r = "../"
    intrari = "".join(f"""<article class="ec-timeline__i">
      <div class="ec-timeline__d">{d}</div>
      <div>
        <div class="ec-timeline__t">{t}</div>
        <p style="color:var(--ec-ink-60);font-size:.875rem">{c}</p>
        <div class="ec-media" style="min-height:11rem;margin-top:1rem"><p>Fotografii de șantier<br>— de furnizat —</p></div>
      </div>
    </article>""" for d, t, c in JURNAL)

    continut = f"""<div class="ec-wrap">
  <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Stadiul lucrărilor</nav>
  <header class="ec-phead">
    <p class="ec-eyebrow">Șantier</p>
    <h1 style="margin-top:1rem">Stadiul lucrărilor</h1>
    <p class="ec-body" style="max-width:62ch;font-size:var(--ec-lead)">
      Publicăm lunar stadiul real al construcției, cu fotografii datate. Poți vedea exact
      unde s-a ajuns, fără să te bazezi pe promisiuni.
    </p>
  </header>
  <div class="ec-panel" style="margin-bottom:4rem">{intrari}</div>
</div>"""
    return pagina("Stadiul lucrărilor — Emerald City Iași",
                  "Jurnal de șantier Emerald City, Iași zona Păcurari. Actualizat lunar, "
                  "cu fotografii datate din teren.",
                  continut, r, None, "stadiu-lucrari/")


# ====================================================== despre dezvoltator ==
def pagina_dezvoltator():
    r = "../"
    continut = f"""<div class="ec-wrap">
  <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Despre dezvoltator</nav>
  <header class="ec-phead">
    <p class="ec-eyebrow">Dezvoltator</p>
    <h1 style="margin-top:1rem">Tala Sapphire S.R.L.</h1>
    <p class="ec-body" style="max-width:62ch;font-size:var(--ec-lead)">
      Emerald City este dezvoltat de Tala Sapphire S.R.L. Vânzarea se face direct,
      fără comision de intermediere.
    </p>
  </header>

  <section class="ec-section" style="padding-block:0 3rem">
    <dl class="ec-specs">
      <div class="ec-spec"><dt>Beneficiar</dt><dd>Tala Sapphire S.R.L.</dd></div>
      <div class="ec-spec"><dt>Proiect</dt><dd>266/2023</dd></div>
      <div class="ec-spec"><dt>Fază</dt><dd>D.T.A.C.</dd></div>
      <div class="ec-spec"><dt>Amplasament</dt><dd>Str. Ion Nistor, Iași</dd></div>
    </dl>
  </section>

  <section class="ec-section" style="padding-block:0 4rem">
    <div class="ec-split">
      <div class="ec-prose">
        <h2>Proiectul și avizele</h2>
        <p>
          Proiectul de autorizare a fost întocmit de S.C. C.A.D. S.R.L. din Iași, cu
          arh. Ovidiu M. Murgu ca șef de proiect. Documentația a fost elaborată în baza
          certificatului de urbanism emis de primăria locală.
        </p>
        <h3>Indicatori urbanistici</h3>
        <p>
          Suprafață teren 50.235 m², POT 30%, CUT 1,80. Spațiu verde amenajat 15.501,80 m²,
          adică 30,85% din suprafața terenului. Regim de înălțime parter plus trei etaje,
          cu înălțimea maximă la atic de 18,00 m.
        </p>
        <h3>Transparență</h3>
        <p>
          Publicăm lunar stadiul lucrărilor, cu fotografii datate din teren, și afișăm
          deschis prețurile și disponibilitatea fiecărui apartament.
          Documentele de autorizare pot fi consultate la cerere.
        </p>
      </div>
      {formular(None, r)}
    </div>
  </section>
</div>"""
    return pagina("Despre dezvoltator — Tala Sapphire | Emerald City Iași",
                  "Tala Sapphire S.R.L., dezvoltatorul ansamblului Emerald City din Iași, "
                  "zona Păcurari. Proiect, avize și indicatori urbanistici.",
                  continut, r, None, "despre-dezvoltator/")



# ============================================================== proiect ==
def pagina_proiect():
    r = "../"
    continut = f"""<div class="ec-wrap">
  <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Proiect</nav>
  <header class="ec-phead">
    <p class="ec-eyebrow">Proiect</p>
    <h1 style="margin-top:1rem">Cum este gândit ansamblul</h1>
    <p class="ec-body" style="max-width:66ch;font-size:var(--ec-lead)">
      Optsprezece blocuri joase în loc de câteva turnuri. Decizia asta schimbă tot restul:
      cât de multă lumină intră, cât spațiu rămâne între clădiri și cât de aglomerat se simte
      cartierul în care locuiești.
    </p>
    <div class="ec-hstats">
      <div class="ec-hstat"><b>925</b><span><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 21V5a1 1 0 011-1h9a1 1 0 011 1v16"/><path d="M15 21V10h4a1 1 0 011 1v10"/><path d="M7 8h2M7 12h2M7 16h2M11 8h1M11 12h1M11 16h1"/><path d="M2 21h20"/></svg> Apartamente</span></div>
      <div class="ec-hstat"><b>18</b><span><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 21V8l5-3 5 3v13"/><path d="M13 21V12h8v9"/><path d="M6 11h1.5M6 15h1.5M10 11h1.5M10 15h1.5M16 16h2"/><path d="M2 21h20"/></svg> Blocuri</span></div>
      <div class="ec-hstat"><b>5,02 ha</b><span>Suprafață teren</span></div>
      <div class="ec-hstat"><b>3</b><span>Etape de construcție</span></div>
    </div>
  </header>

  <section class="ec-section" style="padding-block:0 3rem">
    <h2 class="ec-title" style="margin-bottom:1.5rem">Etapele</h2>
    <div class="ec-table">
      <table>
        <caption class="ec-sr">Etapele de construcție</caption>
        <thead><tr><th>Etapă</th><th>Blocuri</th><th>Apartamente</th><th>Observații</th></tr></thead>
        <tbody>
          <tr><td>Etapa I</td><td>1–6</td><td class="num">322</td>
              <td>Include spațiul comercial de la parterul blocului 6</td></tr>
          <tr><td>Etapa II</td><td>7–14</td><td class="num">423</td>
              <td>Cea mai mare etapă, cu acces direct la parcul central</td></tr>
          <tr><td>Etapa III</td><td>15–18</td><td class="num">180</td>
              <td>Blocurile cu cea mai deschisă perspectivă spre oraș</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section class="ec-section" style="padding-block:0 3rem">
    <h2 class="ec-title" style="margin-bottom:1.5rem">Indicatori</h2>
    <dl class="ec-specs">
      <div class="ec-spec"><dt>Suprafață teren</dt><dd>50.235 m²</dd></div>
      <div class="ec-spec"><dt>POT</dt><dd>30%</dd></div>
      <div class="ec-spec"><dt>CUT</dt><dd>1,80</dd></div>
      <div class="ec-spec"><dt>Regim de înălțime</dt><dd>Parter + 3 etaje</dd></div>
      <div class="ec-spec"><dt>Înălțime maximă</dt><dd>18,00 m</dd></div>
      <div class="ec-spec"><dt>Spațiu verde</dt><dd>15.501 m² · 30,85%</dd></div>
      <div class="ec-spec"><dt>Parcare</dt><dd>940 locuri · 258 subterane</dd></div>
      <div class="ec-spec"><dt>Spații comerciale</dt><dd>848 m²</dd></div>
    </dl>
  </section>

  <section class="ec-section" style="padding-block:0 4rem">
    <div class="ec-prose">
      <h2>De ce blocuri joase</h2>
      <p>
        Un ansamblu cu aceeași suprafață construită se poate face din patru turnuri sau din
        optsprezece blocuri joase. A doua variantă costă mai mult teren, dar înseamnă scări cu
        mai puțini vecini, lifturi mai puțin aglomerate, lumină pe mai multe laturi și distanțe
        reale între ferestre.
      </p>
      <h3>Ce înseamnă pentru apartamentul tău</h3>
      <p>
        Toate apartamentele stau pe parter plus trei etaje. Nu există etaj 8 cu vedere spre
        acoperișul vecinului și nici curte interioară în care se aude tot. Cele două demisoluri
        preiau parcarea și depozitarea, ca mașinile să nu ocupe spațiul dintre clădiri.
      </p>
      <h3>Documentație</h3>
      <p>
        Proiectul numărul 266/2023 a fost întocmit de S.C. C.A.D. S.R.L., cu arh. Ovidiu M. Murgu
        ca șef de proiect. Documentele de autorizare pot fi consultate la cerere, la biroul de vânzări.
      </p>
    </div>
  </section>
</div>"""
    return pagina("Proiectul Emerald City — 925 de apartamente în 18 blocuri | Iași",
                  "Cum este gândit ansamblul Emerald City din Iași: 18 blocuri joase, "
                  "925 de apartamente, 5 hectare, indicatori urbanistici și etape.",
                  continut, r, None, "proiect/")


# ================================================================ presa ==
def pagina_presa():
    r = "../"
    continut = f"""<div class="ec-wrap">
  <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Apariții în presă</nav>
  <header class="ec-phead">
    <p class="ec-eyebrow">Presă</p>
    <h1 style="margin-top:1rem">Apariții în presă</h1>
    <p class="ec-body" style="max-width:62ch;font-size:var(--ec-lead)">
      Materiale despre Emerald City apărute în publicații locale și naționale, plus datele
      de care are nevoie un jurnalist ca să scrie corect despre proiect.
    </p>
  </header>

  <section class="ec-section" style="padding-block:0 3rem">
    <div class="ec-empty" style="text-align:left">
      <p><b>Secțiune în pregătire.</b></p>
      <p style="margin-top:.5rem">
        Aici vor apărea articolele despre proiect, pe măsură ce sunt publicate.
        Fiecare intrare va avea publicația, data și link către articolul original.
      </p>
    </div>
  </section>

  <section class="ec-section" style="padding-block:0 4rem">
    <div class="ec-split">
      <div class="ec-panel">
        <h2 class="ec-title" style="font-size:1.1rem;margin-bottom:1.25rem">Date pentru presă</h2>
        <div class="ec-dist">
          <div><span>Denumire</span><b>Emerald City</b></div>
          <div><span>Dezvoltator</span><b>Tala Sapphire S.R.L.</b></div>
          <div><span>Amplasament</span><b>Str. Ion Nistor, Iași</b></div>
          <div><span><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 21V5a1 1 0 011-1h9a1 1 0 011 1v16"/><path d="M15 21V10h4a1 1 0 011 1v10"/><path d="M7 8h2M7 12h2M7 16h2M11 8h1M11 12h1M11 16h1"/><path d="M2 21h20"/></svg> Apartamente</span><b>925, în 18 blocuri</b></div>
          <div><span>Suprafață teren</span><b>50.235 m²</b></div>
          <div><span><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 19c0-8 5-13 14-13 0 9-5 13-14 13z"/><path d="M5 19c3-4 6-6 10-7.5"/></svg> Spațiu verde</span><b>15.501 m² · 30,85%</b></div>
          <div><span>Regim</span><b>Parter + 3 etaje</b></div>
          <div style="border:0"><span>Etape</span><b>3 · 322 / 423 / 180 apartamente</b></div>
        </div>
        <p class="ec-calc__note">
          Pentru solicitări de presă, interviuri sau imagini de înaltă rezoluție,
          scrie la <a href="mailto:presa@emerald-city.ro">presa@emerald-city.ro</a>.
        </p>
      </div>
      {formular(None, r)}
    </div>
  </section>
</div>"""
    return pagina("Apariții în presă — Emerald City Iași",
                  "Materiale de presă despre Emerald City, ansamblu rezidențial în Iași, "
                  "zona Păcurari. Date de proiect și contact pentru jurnaliști.",
                  continut, r, None, "aparitii-presa/")



# ========================================================= pagini legale ==
LEGALE = {
    "termeni-si-conditii": ("Termeni și condiții",
        "Condițiile de utilizare a site-ului emerald-city.ro și regulile aplicabile "
        "solicitărilor transmise prin formularele de contact."),
    "politica-de-confidentialitate": ("Politica de confidențialitate",
        "Cum sunt colectate, folosite și păstrate datele cu caracter personal transmise "
        "prin acest site."),
    "politica-de-cookies": ("Politica de cookies",
        "Ce module cookie folosește site-ul, în ce scop și cum îți poți retrage acordul."),
    "informare-gdpr": ("Informare GDPR",
        "Drepturile pe care le ai asupra datelor tale personale conform Regulamentului "
        "(UE) 2016/679 și cum le poți exercita."),
}


def pagina_legala(slug):
    r = "../"
    titlu, descriere = LEGALE[slug]
    continut = f"""<div class="ec-wrap">
  <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>{titlu}</nav>
  <header class="ec-phead">
    <p class="ec-eyebrow">Informații legale</p>
    <h1 style="margin-top:1rem">{titlu}</h1>
    <p class="ec-body" style="max-width:62ch;font-size:var(--ec-lead)">{descriere}</p>
  </header>

  <div class="ec-prose" style="margin-bottom:2rem">
    <h2>Document în pregătire</h2>
    <p>
      Textul acestui document se redactează împreună cu consilierul juridic al
      dezvoltatorului și va fi publicat înainte de lansarea site-ului. Până atunci,
      pentru orice întrebare privind datele tale sau condițiile de utilizare, ne poți
      scrie la <a href="mailto:vanzari@emerald-city.ro">vanzari@emerald-city.ro</a>.
    </p>
    <h3>Operator de date</h3>
    <p>Tala Sapphire S.R.L., Str. Ion Nistor, Iași.</p>
    <h3>Soluționarea reclamațiilor</h3>
    <p>
      Pentru soluționarea alternativă a litigiilor poți folosi platforma
      <a href="https://anpc.ro/ce-este-sal/" rel="nofollow noopener" target="_blank">ANPC SAL</a>
      sau platforma europeană
      <a href="https://ec.europa.eu/consumers/odr" rel="nofollow noopener" target="_blank">SOL</a>.
    </p>
  </div>

  <div style="margin-bottom:4rem">{formular(None, r)}</div>
</div>"""
    return pagina(f"{titlu} — Emerald City Iași", descriere, continut, r, None, slug + "/")


# ==================================================================== rulare
def main():
    NUM = {"etaj": int, "nr_camere": int, "su_utila": float, "su_balcon": float,
           "su_curte": float, "pret_eur": int, "pret_mp_eur": float, "cota_teren": float}
    unitati = []
    for row in csv.DictReader(open(CSV, encoding="utf-8")):
        unitati.append({k: NUM[k](v) if k in NUM else v for k, v in row.items()})

    for d in ("apartamente-iasi", "tipologii", "investitie-apartamente-iasi", "compara", "contact",
              "apartamente-iasi-pacurari", "stadiu-lucrari", "despre-dezvoltator",
              "proiect", "aparitii-presa", *LEGALE):
        p = os.path.join(RAD, d)
        if os.path.isdir(p):
            shutil.rmtree(p)
        os.makedirs(p)

    # datele pe care le citeste pagina de listare
    camp = ["unit_id", "corp", "etapa", "etaj", "tip_apartament", "nr_camere", "su_utila",
            "su_balcon", "su_curte", "orientare", "pret_eur", "status",
            "boxa_disponibila", "parcare_subterana"]
    payload = {"campuri": ["id","corp","etapa","etaj","tip","camere","su","balcon","curte",
                           "orientare","pret","status","boxa","parcare"],
               "unitati": [[u[c] if c not in ("su_utila","su_balcon","su_curte")
                            else round(u[c], 1) for c in camp] for u in unitati]}
    with open(os.path.join(RAD, "assets", "data", "unitati.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"), ensure_ascii=False)

    grupe = defaultdict(list)
    for u in unitati:
        grupe[u["tip_apartament"]].append(u)

    # hub de siloz
    with open(os.path.join(RAD, "apartamente-iasi", "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina_hub(unitati, grupe))

    # lista filtrabila, intr-un subdirector propriu
    d = os.path.join(RAD, "apartamente-iasi", "disponibilitate")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina_listare(unitati))

    # cele trei pagini de categorie
    for nr in (1, 2, 3):
        d = os.path.join(RAD, "apartamente-iasi", CATEGORII[nr]["slug"])
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(pagina_categorie(nr, unitati, grupe))

    with open(os.path.join(RAD, "tipologii", "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina_hub_tipologii(grupe))

    # pagini de sine statatoare
    for nume, continut in (("investitie-apartamente-iasi", pagina_investitie(unitati)),
                           ("compara", pagina_comparator()),
                           ("contact", pagina_contact()),
                           ("apartamente-iasi-pacurari", pagina_zona()),
                           ("stadiu-lucrari", pagina_stadiu()),
                           ("despre-dezvoltator", pagina_dezvoltator()),
                           ("proiect", pagina_proiect()),
                           ("aparitii-presa", pagina_presa())):
        d = os.path.join(RAD, nume)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(continut)

    for slug in LEGALE:
        d = os.path.join(RAD, slug)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(pagina_legala(slug))

    # tipologii
    for cod, us in grupe.items():
        d = os.path.join(RAD, "tipologii", cod.lower())
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(pagina_tipologie(cod, us))

    # unitati
    for u in unitati:
        # similare: acelasi tip, alt bloc sau alt etaj, disponibile
        sim = [s for s in grupe[u["tip_apartament"]]
               if s["unit_id"] != u["unit_id"] and s["status"] == "disponibil"]
        sim.sort(key=lambda s: (abs(s["pret_eur"] - u["pret_eur"]), s["unit_id"]))
        d = os.path.join(RAD, "apartamente-iasi", u["unit_id"].lower())
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(pagina_unitate(u, sim[:3]))

    n_unit = len(unitati)
    dim = sum(os.path.getsize(os.path.join(dp, f))
              for d in ("apartamente-iasi", "tipologii")
              for dp, _, fs in os.walk(os.path.join(RAD, d)) for f in fs)
    print("  apartamente-iasi/              hub + 3 categorii + disponibilitate")
    print(f"  apartamente-iasi/<cod>/            {n_unit} pagini de unitate")
    print(f"  tipologii/                    1 + {len(grupe)} pagini")
    print(f"\n  total {n_unit + len(grupe) + 2} pagini, {dim/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()
