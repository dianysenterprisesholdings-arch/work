#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generator de pagini statice pentru Emerald City.

Scrie, din `date/unitati-demo.csv`:
  apartamente/index.html            — listare completa, cu filtre si tabel sortabil
  apartamente/<unit_id>/index.html  — 925 pagini de unitate
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
<body>

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
      <a href="{r}apartamente/">Apartamente</a>
      <a href="{r}tipologii/">Tipologii</a>
      <a href="{r}#finisaje">Finisaje</a>
      <a href="{r}#amplasament">Amplasament</a>
    </nav>
    <a class="ec-btn" href="{r}apartamente/">Vezi apartamentele</a>
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
          <li><a href="{r}apartamente/?camere=1">1 cameră</a></li>
          <li><a href="{r}apartamente/?camere=2">2 camere</a></li>
          <li><a href="{r}apartamente/?camere=3">3 camere</a></li>
          <li><a href="{r}apartamente/">Toate unitățile</a></li>
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


def card_unitate(u, r):
    return f"""<a class="ec-unit" href="{r}apartamente/{e(u['unit_id'].lower())}/">
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
        "@id": f"https://emerald-city.ro/apartamente/{uid.lower()}/#apartament",
        "name": titlu_h,
        "numberOfRooms": u["nr_camere"],
        "floorSize": {"@type": "QuantitativeValue", "value": u["su_utila"], "unitCode": "MTK"},
        "floorLevel": str(u["etaj"]),
        "url": f"https://emerald-city.ro/apartamente/{uid.lower()}/",
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
          f'<a class="ec-btn" href="{r}apartamente/?camere={u["nr_camere"]}">Vezi apartamente similare</a>'

    continut = f"""<div class="ec-wrap">
  <nav class="ec-crumbs" aria-label="Firimituri">
    <a href="{r}">Acasă</a><span>/</span><a href="{r}apartamente/">Apartamente</a><span>/</span>
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
    <div class="ec-pricebar__cta">{cta}</div>
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
    <div class="ec-planbox">{plan_svg(u['nr_camere'])}</div>
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

  <div class="ec-split" style="margin-bottom:var(--ec-gap)" id="cere-detalii">
    {formular(u, r)}
    <figure style="margin:0;overflow:hidden">
      <img src="{r}assets/img/{GALERIE_TIP[u['tip_apartament']][0]}.jpg"
           srcset="{r}assets/img/{GALERIE_TIP[u['tip_apartament']][0]}-800.jpg 800w, {r}assets/img/{GALERIE_TIP[u['tip_apartament']][0]}.jpg 1600w"
           sizes="(max-width: 62rem) 100vw, 50vw"
           alt="Amenajare orientativă pentru tipologia {u['tip_apartament']}" loading="lazy" width="1600" height="900">
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
        continut, r, schema, f"apartamente/{uid.lower()}/")


# ========================================================== pagina tipologie
def pagina_tipologie(cod, unitati):
    r = "../../"
    nr = unitati[0]["nr_camere"]
    disp = [u for u in unitati if u["status"] == "disponibil"]
    su_min, su_max = min(u["su_utila"] for u in unitati), max(u["su_utila"] for u in unitati)
    pmin = min((u["pret_eur"] for u in disp), default=None)

    randuri = "".join(f"""<tr class="{'is-sold' if u['status'] != 'disponibil' else ''}">
      <td><a href="{r}apartamente/{u['unit_id'].lower()}/">{e(u['unit_id'])}</a></td>
      <td>{bloc(u['corp'])}</td><td>{etaj_txt(u['etaj'])}</td>
      <td class="num">{mp(u['su_utila'])}</td><td>{u['orientare']}</td>
      <td class="num">{euro(u['pret_eur'])}</td>
      <td class="st"><span class="ec-tag ec-tag--{u['status']}">{STATUS_ET[u['status']]}</span></td>
    </tr>""" for u in sorted(unitati, key=lambda x: x["pret_eur"])[:60])

    gal = "".join(f"""<figure><img src="{r}assets/img/{g}.jpg"
        srcset="{r}assets/img/{g}-800.jpg 800w, {r}assets/img/{g}.jpg 1600w"
        sizes="(max-width: 46rem) 100vw, 33vw"
        alt="Amenajare orientativă, tipologia {cod}" loading="lazy" width="1600" height="900"></figure>"""
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
    <div class="ec-planbox">{plan_svg(nr)}</div>
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
    <p class="ec-more"><a class="ec-btn ec-btn--out" href="{r}apartamente/?tip={cod}">Vezi toate unitățile tip {cod}</a></p>
  </section>
</div>"""

    return pagina(
        f"Apartament {camere_txt(nr)} tip {cod} în Iași — Emerald City",
        f"Apartament {camere_txt(nr)} tip {cod}, {mp(su_min)}–{mp(su_max)}, în Emerald City, Iași zona Păcurari. "
        f"{len(disp)} unități disponibile, de la {euro(pmin) if pmin else '—'}.",
        continut, r, schema, f"tipologii/{cod.lower()}/")


# ============================================================ pagina listare
def pagina_listare(unitati):
    r = "../"
    blocuri = sorted({u["corp"] for u in unitati}, key=lambda c: int(c[1:]))
    chip = lambda grp, v, et: f'<button class="ec-chip" data-f="{grp}" data-v="{v}">{et}</button>'

    continut = f"""<div class="ec-wrap">
  <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Apartamente</nav>

  <header class="ec-phead">
    <p class="ec-eyebrow">Disponibilitate</p>
    <h1 style="margin-top:1rem">Apartamente noi în Iași, zona Păcurari</h1>
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
        "Apartamente noi în Iași, zona Păcurari — disponibilitate și prețuri",
        f"Toate cele {len(unitati)} de apartamente din Emerald City, Iași zona Păcurari. "
        "Filtrează după camere, etaj, suprafață și preț. Direct de la dezvoltator.",
        continut, r, None, "apartamente/")


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


# ==================================================================== rulare
def main():
    NUM = {"etaj": int, "nr_camere": int, "su_utila": float, "su_balcon": float,
           "su_curte": float, "pret_eur": int, "pret_mp_eur": float, "cota_teren": float}
    unitati = []
    for row in csv.DictReader(open(CSV, encoding="utf-8")):
        unitati.append({k: NUM[k](v) if k in NUM else v for k, v in row.items()})

    for d in ("apartamente", "tipologii"):
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

    # listare + hub
    with open(os.path.join(RAD, "apartamente", "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina_listare(unitati))
    with open(os.path.join(RAD, "tipologii", "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina_hub_tipologii(grupe))

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
        d = os.path.join(RAD, "apartamente", u["unit_id"].lower())
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(pagina_unitate(u, sim[:3]))

    n_unit = len(unitati)
    dim = sum(os.path.getsize(os.path.join(dp, f))
              for d in ("apartamente", "tipologii")
              for dp, _, fs in os.walk(os.path.join(RAD, d)) for f in fs)
    print(f"  apartamente/index.html        1 pagina de listare")
    print(f"  apartamente/<cod>/            {n_unit} pagini de unitate")
    print(f"  tipologii/                    1 + {len(grupe)} pagini")
    print(f"\n  total {n_unit + len(grupe) + 2} pagini, {dim/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()
