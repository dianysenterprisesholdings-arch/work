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
    <span>Apartamente cu 1, 2 și 3 camere în Iași, zona Păcurari — <strong>DIRECT DEZVOLTATOR</strong></span>
    <div class="ec-topbar__right">
      <a href="tel:{TEL}">{TEL_AFIS}</a>
      <a href="mailto:vanzari@emerald-city.ro">vanzari@emerald-city.ro</a>
    </div>
  </div>
</div>

<header class="ec-nav">
  <div class="ec-nav__in">
    <a class="ec-nav__logo" href="{r}" aria-label="Emerald City — acasă">
      <img src="{r}brand/logo-verde.svg" alt="Emerald City" width="590" height="286">
    </a>
    <nav class="ec-nav__menu">
      <a href="{r}#despre">Despre</a>
      <a href="{r}apartamente-iasi/">Apartamente</a>
      <a href="{r}apartamente-iasi/disponibilitate/">Disponibilitate</a>
      <a href="{r}tipologii/">Tipologii</a>
      <a href="{r}#finisaje">Finisaje</a>
      <a href="{r}#amplasament">Amplasament</a>
      <a href="{r}contact/">Contact</a>
    </nav>
    <a class="ec-btn" href="{r}apartamente-iasi/">Vezi apartamentele</a>
  </div>
</header>

<main>
{continut}
</main>

<footer class="ec-foot">
  <div class="ec-wrap">
    <div class="ec-foot__grid">
      <div>
        <img src="{r}brand/logo-alb.svg" alt="Emerald City" width="590" height="286">
        <p style="margin-top:1.25rem;max-width:34ch">
          Ansamblu rezidențial în Iași, zona Păcurari.<br>
          Str. Ion Nistor.<br>
          Dezvoltator: Tala Sapphire S.R.L.
        </p>
      </div>
      <div>
        <h4>Apartamente</h4>
        <ul>
          <li><a href="{r}apartamente-iasi/apartamente-1-camera/">1 cameră</a></li>
          <li><a href="{r}apartamente-iasi/apartamente-2-camere/">2 camere</a></li>
          <li><a href="{r}apartamente-iasi/apartamente-3-camere/">3 camere</a></li>
          <li><a href="{r}apartamente-iasi/disponibilitate/">Disponibilitate</a></li>
          <li><a href="{r}investitie-apartamente-iasi/">Investiție</a></li>
        </ul>
      </div>
      <div>
        <h4>Tipologii</h4>
        <ul>{"".join(f'<li><a href="{r}tipologii/{c.lower()}/">Tip {c}</a></li>' for c in CAMERE_TIP)}</ul>
      </div>
      <div>
        <h4>Contact</h4>
        <ul>
          <li><a href="tel:{TEL}">{TEL_AFIS}</a></li>
          <li><a href="mailto:vanzari@emerald-city.ro">vanzari@emerald-city.ro</a></li>
        </ul>
      </div>
    </div>
    <div class="ec-foot__bottom">
      <span>© 2026 Emerald City · Tala Sapphire S.R.L.</span>
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


def plan_svg(nr):
    rooms = ([[4,4,40,34],[46,4,26,20],[46,26,26,12]] if nr == 1 else
             [[4,4,42,40],[48,4,28,22],[48,28,28,16]] if nr == 2 else
             [[4,4,38,40],[44,4,32,20],[44,26,15,18],[61,26,15,18]])
    inner = "".join(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#fff"/>'
                    for x, y, w, h in rooms)
    return (f'<svg viewBox="0 0 80 48" role="img" aria-label="Schiță orientativă de plan">'
            f'<rect class="wall" x="0" y="0" width="80" height="48"/>{inner}</svg>')


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
      <td class="num">{euro(u['pret_eur'])}</td>
      <td class="st"><span class="ec-tag ec-tag--{u['status']}">{STATUS_ET[u['status']]}</span></td>
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
          <div class="ec-type__plan">{plan_svg(us[0]['nr_camere'])}</div>
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
      <div class="ec-hstat"><b>{len(unitati)}</b><span>Apartamente</span></div>
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
          <div class="ec-type__plan">{plan_svg(nr)}</div>
          <div class="ec-type__code">{cod}</div>
          <div class="ec-type__rows">
            <div><span>Suprafață</span><b>{mp(min(u['su_utila'] for u in tu))} – {mp(max(u['su_utila'] for u in tu))}</b></div>
            <div><span>Disponibile</span><b>{len(td)} din {len(tu)}</b></div>
          </div>
          <span class="ec-unit__price">{'de la ' + euro(tp) if tp else '—'}</span>
        </a>"""

    randuri = "".join(f"""<tr class="{'is-sold' if u['status'] != 'disponibil' else ''}">
      <td><a href="{r}apartamente-iasi/{u['unit_id'].lower()}/">{e(u['unit_id'])}</a></td>
      <td>{bloc(u['corp'])}</td><td>{etaj_txt(u['etaj'])}</td><td>{u['tip_apartament']}</td>
      <td class="num">{mp(u['su_utila'])}</td><td>{u['orientare']}</td>
      <td class="num">{euro(u['pret_eur'])}</td>
      <td class="st"><span class="ec-tag ec-tag--{u['status']}">{STATUS_ET[u['status']]}</span></td>
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


# ==================================================================== rulare
def main():
    NUM = {"etaj": int, "nr_camere": int, "su_utila": float, "su_balcon": float,
           "su_curte": float, "pret_eur": int, "pret_mp_eur": float, "cota_teren": float}
    unitati = []
    for row in csv.DictReader(open(CSV, encoding="utf-8")):
        unitati.append({k: NUM[k](v) if k in NUM else v for k, v in row.items()})

    for d in ("apartamente-iasi", "tipologii", "investitie-apartamente-iasi", "compara", "contact"):
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
                           ("contact", pagina_contact())):
        d = os.path.join(RAD, nume)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(continut)

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
