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

import csv, html, json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limbi import hreflang, comutator
from collections import defaultdict

RAD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(RAD, "date", "unitati-demo.csv")

TEL = "+40757707080"
TEL_AFIS = "0757 70 70 80"
WA = "https://wa.me/40757707080"
TEL_LINK = "tel:+40757707080"

# ---------------------------------------------------------------- tipologii
# Ponderile pe camera sunt orientative: documentatia nu contine defalcarea
# pe incaperi. Se inlocuiesc cand vine tabelul final de la dezvoltator.
CAMERE_TIP = {
    "1A": [("Hol", .10), ("Living și bucătărie", .66), ("Baie", .15), ("Debara", .09)],
    "2A": [("Hol", .08), ("Living și bucătărie", .45), ("Dormitor", .27), ("Baie", .11), ("Debara", .09)],
    "2B": [("Hol", .08), ("Living și bucătărie", .43), ("Dormitor", .28), ("Baie", .12), ("Debara", .09)],
    "3A": [("Hol", .07), ("Living", .30), ("Bucătărie", .13), ("Dormitor 1", .20),
           ("Dormitor 2", .16), ("Baie", .08), ("Baie 2", .06)],
    "3B": [("Hol", .09), ("Living și bucătărie", .36), ("Dormitor", .20), ("Birou", .15),
           ("Baie", .11), ("Baie 2", .09)],
}
DESC_TIP = {
    "1A": "Garsonieră compactă, cu zona de zi deschisă și bucătărie integrată.",
    "2A": "Două camere, cu living deschis spre bucătărie și dormitor separat.",
    "2B": "Două camere, cu dormitor mai generos și spațiu suplimentar de depozitare.",
    "3A": "Trei camere, cu bucătărie închisă, două dormitoare și două grupuri sanitare.",
    "3B": "Trei camere, cu living deschis, dormitor și o a treia cameră pentru birou.",
}
GALERIE_TIP = {
    "1A": ["living-02", "bucatarie-01", "baie-01"],
    "2A": ["living-01", "dormitor-01", "hol-01"],
    "2B": ["living-02", "dining-01", "baie-01"],
    "3A": ["living-01", "dining-01", "dormitor-01"],
    "3B": ["dining-01", "bucatarie-01", "hol-01"],
}

STATUS_ET = {"disponibil": "Disponibil", "rezervat": "Rezervat",
             "vandut": "Vândut", "in_curand": "În curând"}
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



# Eticheta fiecarui segment de adresa, pentru firimiturile din date
# structurate. Ce nu e aici se deduce din slug.
ETICHETE_CALE = {
    "apartamente-iasi": "Apartamente noi în Iași",
    "disponibilitate": "Disponibilitate și prețuri",
    "apartamente-1-camera": "Apartamente 1 cameră",
    "apartamente-2-camere": "Apartamente 2 camere",
    "apartamente-3-camere": "Apartamente 3 camere",
    "apartamente-iasi-pacurari": "Zona Păcurari",
    "investitie-apartamente-iasi": "Investiție și randament",
    "despre-emerald-city": "Despre noi",
    "despre-dezvoltator": "Dezvoltator",
    "stadiu-lucrari": "Stadiul lucrărilor",
    "aparitii-presa": "Apariții în presă",
    "finisaje": "Finisaje",
    "proiect": "Proiect",
    "contact": "Contact",
    "programare-vizionare": "Programare vizionare",
    "noutati": "Noutăți",
    "termeni-si-conditii": "Termeni și condiții",
    "politica-de-confidentialitate": "Politica de confidențialitate",
    "politica-de-cookies": "Politica de cookies",
    "informare-gdpr": "Informare GDPR",
    "compara": "Comparator",
}


def firimituri(canonic):
    """BreadcrumbList din adresa canonica, ca sa apara in rezultatele cautarii."""
    parti = [x for x in canonic.strip("/").split("/") if x]
    elemente = [{"@type": "ListItem", "position": 1, "name": "Acasă",
                 "item": "https://emerald-city.ro/"}]
    cale = ""
    for i, seg in enumerate(parti, 2):
        cale += seg + "/"
        if seg.startswith("tip-"):
            nume = "Tip " + seg[4:].upper()
        elif seg[:1] == "c" and "-" in seg and seg[1:2].isdigit():
            nume = seg.upper()
        elif seg in globals().get("ARTICOLE_BLOG_SLUG", {}):
            nume = ARTICOLE_BLOG_SLUG[seg]["titlu"]
        else:
            nume = ETICHETE_CALE.get(seg, seg.replace("-", " ").capitalize())
        elemente.append({"@type": "ListItem", "position": i, "name": nume,
                         "item": f"https://emerald-city.ro/{cale}"})
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": elemente}

# ------------------------------------------------------------------ sablon
ORGANIZATIE = {
    "@context": "https://schema.org",
    "@graph": [
        {"@type": "Organization", "@id": "https://emerald-city.ro/#org",
         "name": "Emerald City", "legalName": "Tala Sapphire S.R.L.",
         "url": "https://emerald-city.ro/", "logo": "https://emerald-city.ro/brand/logo-verde.svg",
         "parentOrganization": {"@type": "Organization", "name": "Green Stone Group",
                                "url": "https://greenstone-group.ro/"},
         "address": {"@type": "PostalAddress", "streetAddress": "Str. Dealul Zorilor 9",
                     "addressLocality": "Iași", "addressRegion": "Iași", "postalCode": "700000",
                     "addressCountry": "RO"},
         "contactPoint": [{"@type": "ContactPoint", "contactType": "sales", "telephone": "+40757707080",
                           "email": "vanzari@emerald-city.ro", "availableLanguage": ["ro", "en"],
                           "areaServed": "RO"}],
         "sameAs": ["https://www.facebook.com/", "https://www.instagram.com/",
                    "https://www.tiktok.com/", "https://www.youtube.com/"]},
        {"@type": "WebSite", "@id": "https://emerald-city.ro/#site", "url": "https://emerald-city.ro/",
         "name": "Emerald City", "inLanguage": ["ro", "en"],
         "publisher": {"@id": "https://emerald-city.ro/#org"}},
    ]}


def pagina(titlu, descriere, continut, radacina, schema=None, canonic="",
           imagine_og="hero-living", robots=""):
    """Invelisul comun: topbar, navigatie, continut, subsol, WhatsApp."""
    r = radacina
    ld = f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>' if schema else ""
    ld += ('<script type="application/ld+json">'
           + json.dumps(firimituri(canonic), ensure_ascii=False) + "</script>")
    ld += '<script type="application/ld+json">' + json.dumps(ORGANIZATIE, ensure_ascii=False) + "</script>"
    meta_robots = f'\n<meta name="robots" content="{robots}">' if robots else ""
    adresa = f"https://emerald-city.ro/{canonic}"
    og = f"""<meta property="og:type" content="website">
<meta property="og:site_name" content="Emerald City">
<meta property="og:locale" content="ro_RO">
<meta property="og:title" content="{e(titlu)}">
<meta property="og:description" content="{e(descriere)}">
<meta property="og:url" content="{adresa}">
<meta property="og:image" content="https://emerald-city.ro/assets/img/{imagine_og}.jpg">
<meta property="og:image:width" content="1600">
<meta property="og:image:height" content="900">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(titlu)}">
<meta name="twitter:description" content="{e(descriere)}">
<meta name="twitter:image" content="https://emerald-city.ro/assets/img/{imagine_og}.jpg">"""
    return f"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titlu)}</title>
<meta name="description" content="{e(descriere)}">
<link rel="canonical" href="https://emerald-city.ro/{canonic}">{meta_robots}
{hreflang(canonic)}
{og}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Inter+Tight:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css" integrity="sha512-Evv84Mr4kqVGRNSgIGL/F/aIDqQb7xQ2vcrdIwxfjThSH8CSR7PBEakCr51Ck+w+/U6swU2Im1vVX0SVk9ABhg==" crossorigin="anonymous" referrerpolicy="no-referrer">
<link rel="stylesheet" href="{r}assets/css/main.css">
{ld}
</head>
<body data-radacina="{r}">

<div class="ec-prog" data-prog aria-hidden="true"></div>

<div class="ec-topbar">
  <div class="ec-topbar__in">
    <span class="ec-topbar__l"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s7-6.2 7-11a7 7 0 10-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.6"/></svg> Apartamente Iași, zona Păcurari — <strong>DIRECT DEZVOLTATOR</strong></span>
    <div class="ec-topbar__right">
      <a href="tel:+40757707080"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4.5 4h3l1.5 4-2 1.5a12 12 0 006 6L14.5 13l4 1.5v3a2 2 0 01-2.2 2A16 16 0 012.5 6.2 2 2 0 014.5 4z"/></svg> 0757 70 70 80</a>
      <a href="mailto:vanzari@emerald-city.ro"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3.5 6.5l8.5 6 8.5-6"/></svg> vanzari@emerald-city.ro</a>
      <span class="ec-topbar__soc">
        <a href="https://www.facebook.com/" target="_blank" rel="noopener" aria-label="Facebook"><i class="fa-brands fa-facebook-f" aria-hidden="true"></i></a>
        <a href="https://www.instagram.com/" target="_blank" rel="noopener" aria-label="Instagram"><i class="fa-brands fa-instagram" aria-hidden="true"></i></a>
        <a href="https://www.tiktok.com/" target="_blank" rel="noopener" aria-label="TikTok"><i class="fa-brands fa-tiktok" aria-hidden="true"></i></a>
        <a href="https://www.youtube.com/" target="_blank" rel="noopener" aria-label="YouTube"><i class="fa-brands fa-youtube" aria-hidden="true"></i></a>
      </span>
      {comutator(canonic)}
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
        <a href="{r}despre-emerald-city/">Despre noi</a>
        <div class="ec-mega">
          <div class="ec-mega__col">
            <span class="ec-mega__h">Proiectul</span>
            <a class="ec-mega__i" href="{r}proiect/"><span class="ec-mega__ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 21V7l9-4 9 4v14"/><path d="M3 12h18M12 3v18"/></svg></span><span class="ec-mega__tx"><b>Proiect</b><em>18 blocuri P+3E, indicatori urbanistici</em></span></a>
            <a class="ec-mega__i" href="{r}apartamente-iasi-pacurari/"><span class="ec-mega__ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s7-6.2 7-11a7 7 0 10-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.6"/></svg></span><span class="ec-mega__tx"><b>Amplasament</b><em>Iași, zona Păcurari — distanțe și acces</em></span></a>
            <a class="ec-mega__i" href="{r}stadiu-lucrari/"><span class="ec-mega__ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 14v-2a8 8 0 0116 0v2"/><rect x="2" y="14" width="4" height="6" rx="1"/><rect x="18" y="14" width="4" height="6" rx="1"/></svg></span><span class="ec-mega__tx"><b>Jurnal de șantier</b><em>Stadiul lucrărilor, actualizat lunar</em></span></a>
          </div>
          <div class="ec-mega__col">
            <span class="ec-mega__h">Compania</span>
            <a class="ec-mega__i" href="{r}despre-emerald-city/"><span class="ec-mega__ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5h.01"/></svg></span><span class="ec-mega__tx"><b>Despre noi</b><em>Finisaje, garanții, documente și proces</em></span></a>
            <a class="ec-mega__i" href="{r}despre-dezvoltator/"><span class="ec-mega__ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 21h18M5 21V7l7-4 7 4v14"/><path d="M9 21v-5h6v5"/></svg></span><span class="ec-mega__tx"><b>Dezvoltator</b><em>Tala Sapphire S.R.L., avize și echipă</em></span></a>
            <a class="ec-mega__i" href="{r}aparitii-presa/"><span class="ec-mega__ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 5h13v14a2 2 0 002-2V8h1v9a3 3 0 01-3 3H4z"/><path d="M7 9h7M7 12h7M7 15h4"/></svg></span><span class="ec-mega__tx"><b>Apariții în presă</b><em>Materiale și date pentru jurnaliști</em></span></a>
            <a class="ec-mega__i" href="{r}finisaje/"><span class="ec-mega__ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg></span><span class="ec-mega__tx"><b>Finisaje</b><em>Dotări incluse la cheie</em></span></a>
          </div>
          <a class="ec-mega__card" href="{r}stadiu-lucrari/">
            <img src="{r}assets/img/hol-01-800.jpg" alt="Hol de intrare finisat, Emerald City Iași" width="800" height="450" loading="lazy">
            <span class="ec-mega__cardb"><b>Stadiul lucrărilor</b>
              <em>Publicăm lunar progresul real, cu fotografii datate din teren</em></span>
          </a>
        </div>
      </span>
      <span class="ec-nav__has">
        <a href="{r}apartamente-iasi/">Apartamente</a>
        <div class="ec-mega">
          <div class="ec-mega__col">
            <span class="ec-mega__h">După numărul de camere</span>
            <a class="ec-mega__i" href="{r}apartamente-iasi/apartamente-1-camera/"><span class="ec-mega__ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 21V7l9-4 9 4v14"/><path d="M3 12h18M12 3v18"/></svg></span><span class="ec-mega__tx"><b>Apartament 1 cameră</b><em>109 libere · 37–39 m² · de la 53.500 €</em></span></a>
            <a class="ec-mega__i" href="{r}apartamente-iasi/apartamente-2-camere/"><span class="ec-mega__ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 21V7l9-4 9 4v14"/><path d="M3 12h18M12 3v18"/></svg></span><span class="ec-mega__tx"><b>Apartamente 2 camere</b><em>285 libere · 51–61 m² · de la 74.000 €</em></span></a>
            <a class="ec-mega__i" href="{r}apartamente-iasi/apartamente-3-camere/"><span class="ec-mega__ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 21V7l9-4 9 4v14"/><path d="M3 12h18M12 3v18"/></svg></span><span class="ec-mega__tx"><b>Apartamente 3 camere</b><em>123 libere · 69–81 m² · de la 101.500 €</em></span></a>
          </div>
          <div class="ec-mega__col">
            <span class="ec-mega__h">Compartimentări</span>
            <div class="ec-mega__tipuri"><a class="ec-mega__t" href="{r}apartamente-iasi/{CATEGORII[1]["slug"]}/tip-1a/"><b>1A</b><span>37–39 m²</span><i>109 libere</i></a><a class="ec-mega__t" href="{r}apartamente-iasi/{CATEGORII[2]["slug"]}/tip-2a/"><b>2A</b><span>51–54 m²</span><i>163 libere</i></a><a class="ec-mega__t" href="{r}apartamente-iasi/{CATEGORII[2]["slug"]}/tip-2b/"><b>2B</b><span>57–61 m²</span><i>122 libere</i></a><a class="ec-mega__t" href="{r}apartamente-iasi/{CATEGORII[3]["slug"]}/tip-3a/"><b>3A</b><span>69–74 m²</span><i>70 libere</i></a><a class="ec-mega__t" href="{r}apartamente-iasi/{CATEGORII[3]["slug"]}/tip-3b/"><b>3B</b><span>76–81 m²</span><i>53 libere</i></a></div>
            <a class="ec-mega__i" href="{r}apartamente-iasi/disponibilitate/"><span class="ec-mega__ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/></svg></span><span class="ec-mega__tx"><b>Disponibilitate și prețuri</b><em>Toate cele 925, cu filtre</em></span></a>
            <a class="ec-mega__i" href="{r}investitie-apartamente-iasi/"><span class="ec-mega__ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 12h2M12 12h2M16 12h.01M8 16h2M12 16h2M16 16h.01"/></svg></span><span class="ec-mega__tx"><b>Investiție și randament</b><em>Calculator de chirie și amortizare</em></span></a>
          </div>
          <a class="ec-mega__card" href="{r}apartamente-iasi/">
            <img src="{r}assets/img/living-01-800.jpg" alt="Living cu bucătărie deschisă, Emerald City Iași" width="800" height="450" loading="lazy">
            <span class="ec-mega__cardb"><b>517 apartamente disponibile</b>
              <em>Preț și disponibilitate actualizate din tabelul de vânzări</em></span>
          </a>
        </div>
      </span>
      <a href="{r}apartamente-iasi/disponibilitate/">Disponibilitate</a>
      <a href="{r}investitie-apartamente-iasi/">Investiție</a>
      <a href="{r}noutati/">Noutăți</a>
      <a href="{r}contact/">Contact</a>
    </nav>
    <a class="ec-btn" href="{r}programare-vizionare/"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg> Programare vizionare</a>
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
          <span><i class="fa-solid fa-phone" aria-hidden="true"></i> Sună direct</span><b>{TEL_AFIS}</b>
        </a>
        <a class="ec-foot__r" href="{WA}">
          <span><i class="fa-brands fa-whatsapp" aria-hidden="true"></i> Contact WhatsApp</span><b>Răspundem azi</b>
        </a>
        <a class="ec-foot__r" href="mailto:vanzari@emerald-city.ro">
          <span><i class="fa-solid fa-envelope" aria-hidden="true"></i> Email</span><b>vanzari@emerald-city.ro</b>
        </a>
        <a class="ec-foot__r" href="{r}investitie-apartamente-iasi/">
          <span><i class="fa-solid fa-chart-line" aria-hidden="true"></i> Cumperi ca investiție?</span><b>Calculator de randament</b>
        </a>
      </div>
    </div>

    <div class="ec-foot__stats"><div><div class="ec-statbox"><span class="ec-statbox__i"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="4" width="8" height="16" rx="1"/><rect x="12" y="9" width="8" height="11" rx="1"/><path d="M6.5 8h3M6.5 12h3M6.5 16h3M15 13h2M15 17h2"/></svg></span><span class="ec-statbox__v"><b>925</b><em>Apartamente</em></span></div></div><div><div class="ec-statbox"><span class="ec-statbox__i"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 19V8l5-3 5 3v11"/><path d="M13 19v-8h8v8"/><path d="M6 11h1.5M6 15h1.5M10 11h1.5M10 15h1.5M16 15h2"/></svg></span><span class="ec-statbox__v"><b>18</b><em>Blocuri 2D+P+3E</em></span></div></div><div><div class="ec-statbox"><span class="ec-statbox__i"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 18c0-7.5 5-12 14-12 0 8.5-5 12-14 12z"/><path d="M5 18c2.5-3.5 5.5-5.5 9.5-7"/></svg></span><span class="ec-statbox__v"><b>30,85%</b><em>Spațiu verde</em></span></div></div><div><div class="ec-statbox"><span class="ec-statbox__i"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 16h14M6 16V9l2-4h8l2 4v7"/><circle cx="8" cy="16.5" r="1.8"/><circle cx="16" cy="16.5" r="1.8"/></svg></span><span class="ec-statbox__v"><b>940</b><em>Locuri de parcare</em></span></div></div></div>

    <div class="ec-foot__grid">
      <div>
        <h4>Apartamente</h4>
        <ul>
          <li><a href="{r}apartamente-iasi/apartamente-1-camera/">Apartament 1 cameră</a></li>
          <li><a href="{r}apartamente-iasi/apartamente-2-camere/">Apartamente 2 camere</a></li>
          <li><a href="{r}apartamente-iasi/apartamente-3-camere/">Apartamente 3 camere</a></li>
          <li><a href="{r}apartamente-iasi/disponibilitate/">Disponibilitate și prețuri</a></li>
          <li><a href="{r}compara/">Comparator de apartamente</a></li>
        </ul>
      </div>
      <div>
        <h4>Tipologii</h4>
        <ul>{"".join(f'<li><a href="{r}{slug_tip(c)}">Apartament Tip {c}</a></li>' for c in CAMERE_TIP)}</ul>
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
          <li><a href="{r}noutati/">Noutăți</a></li>
          <li><a href="{r}contact/">Contact</a></li>
          <li><a href="{r}finisaje/">Finisaje</a></li>
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
      <span>Designed by Dianys Holding</span>
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
    const zone = [...p.querySelectorAll('.ec-plan__room, .ec-plan__halo')];
    const randuri = [...p.querySelectorAll('.ec-plan__legend li')];
    const arata = (i, on) => {{
      spots.forEach(s => s.classList.toggle('is-on', on && s.dataset.i === i));
      zone.forEach(z => z.classList.toggle('is-on', on && z.dataset.i === i));
      randuri.forEach(r => r.classList.toggle('is-on', on && r.dataset.i === i));
      if (!tip) return;
      const s = spots.find(x => x.dataset.i === i);
      if (on && s) {{
        tip.innerHTML = s.getAttribute('aria-label');
        tip.style.left = s.style.left;
        tip.style.top = s.style.top;
        tip.classList.add('is-on');
      }} else tip.classList.remove('is-on');
    }};
    [...spots, ...randuri, ...p.querySelectorAll('.ec-plan__room')].forEach(el => {{
      const i = el.dataset.i;
      el.addEventListener('mouseenter', () => arata(i, true));
      el.addEventListener('mouseleave', () => arata(i, false));
      el.addEventListener('focus', () => arata(i, true));
      el.addEventListener('blur', () => arata(i, false));
      el.addEventListener('click', e => {{ e.preventDefault(); arata(i, true); }});
    }});
  }});
}})();

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
<script src="{r}assets/js/galerie.js"></script>
<script src="{r}assets/js/bara.js"></script>
<script src="{r}assets/js/progres.js"></script>
<script src="{r}assets/js/meniu.js"></script>
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
        cam = ([("Living și bucătărie", .66), ("Baie", .17), ("Hol", .17)] if nr_camere == 1
               else [("Living și bucătărie", .45), ("Dormitor", .3), ("Baie", .13), ("Hol", .12)]
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
    # latimea aproximativa a unui text, in unitatile desenului, la corpul
    # folosit in schita mare (7,5px) — ca sa nu scriem nume peste pereti
    lat_text = lambda t, corp=7.5: len(t) * 0.58 * corp
    for nr_cam, (nume, pond, x, yy, w, h) in enumerate(incaperi, 1):
        piese.append(f'<rect class="ec-plan__room" data-i="{nr_cam}" '
                     f'x="{x + GROS:.1f}" y="{yy + GROS:.1f}" '
                     f'width="{max(w - GROS * 2, 1):.1f}" height="{max(h - GROS * 2, 1):.1f}" '
                     f'fill="#fff"/>')
        cx, cy = x + w / 2, yy + h / 2
        arie = total * pond
        if compact:
            # in cardurile mici pastrez numele, scurtat, doar unde incape
            et = SCURT.get(nume, nume)
            if h >= 22:
                piese.append(f'<text class="pn" x="{cx:.1f}" y="{cy + 2.5:.1f}">{et}</text>')
            continue

        # schita mare: fiecare camera are un numar (reluat in legenda), iar
        # numele si aria apar in camera numai daca incap fara sa atinga peretii
        if h >= 11 and w >= 14:
            bx, by = x + GROS + 6.5, yy + GROS + 6.5
            piese.append(f'<circle class="pb" cx="{bx:.1f}" cy="{by:.1f}" r="4.6"/>')
            piese.append(f'<text class="pbt" x="{bx:.1f}" y="{by + 2.1:.1f}">{nr_cam}</text>')
        util = w - GROS * 2 - 6
        aria_txt = f"{arie:.1f}".replace(".", ",")   # virgula doar in numar
        if h >= 34 and lat_text(nume) <= util:
            piese.append(f'<text class="pn" x="{cx:.1f}" y="{cy - 3:.1f}">{nume}</text>')
            piese.append(f'<text class="pa" x="{cx:.1f}" y="{cy + 8:.1f}">{aria_txt} m²</text>')
        elif h >= 44 and " " in nume:
            # pe doua randuri, rupt la spatiul din mijloc
            cuv = nume.split(" ")
            k = max(range(1, len(cuv)), key=lambda i: -abs(len(" ".join(cuv[:i])) - len(" ".join(cuv[i:]))))
            r1, r2 = " ".join(cuv[:k]), " ".join(cuv[k:])
            if max(lat_text(r1), lat_text(r2)) <= util:
                piese.append(f'<text class="pn" x="{cx:.1f}" y="{cy - 7:.1f}">{r1}</text>')
                piese.append(f'<text class="pn" x="{cx:.1f}" y="{cy + 2:.1f}">{r2}</text>')
                piese.append(f'<text class="pa" x="{cx:.1f}" y="{cy + 13:.1f}">{aria_txt} m²</text>')

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

    return (f'<svg viewBox="-16 -16 {W + 58:.0f} {H + 56:.0f}" role="img" '
            f'aria-label="Schemă de compartimentare, tipologia {tip or nr_camere}">'
            + "".join(piese) + '</svg>')

# ----------------------------------------------------- planuri interactive
_PL = os.path.join(RAD, "assets", "data", "planuri.json")
PLANURI = json.load(open(_PL, encoding="utf-8")) if os.path.exists(_PL) else {}


def plan_interactiv(tip, nr_camere, r, su=None):
    """Plan cu hotspot-uri pe camere. Cade pe schita schematica daca nu exista."""
    d = PLANURI.get(tip)
    if not d:
        # schita se deseneaza cu compartimentarea si suprafata reale, nu generice
        cam = CAMERE_TIP.get(tip or "", [])
        total = su or 60.0
        legenda = "".join(
            f'<li data-i="{i}"><i>{i}</i><span>{nume}</span>'
            f'<b>{mp(round(total * pond, 2))}</b></li>'
            for i, (nume, pond) in enumerate(cam, 1))
        return (f'<div class="ec-planbox" data-plan>{plan_svg(nr_camere, tip, su)}'
                + (f'<ul class="ec-plan__legend">{legenda}</ul>' if legenda else "")
                + '</div>')

    spots, legenda = "", ""
    for i, c in enumerate(d["camere"], 1):
        et = f'{c["nume"]} &middot; {mp(c["aria"])}'
        spots += (f'<span class="ec-plan__halo" data-i="{i}" '
                  f'style="left:{c["x"]}%;top:{c["y"]}%"></span>'
                  f'<button class="ec-plan__spot" style="left:{c["x"]}%;top:{c["y"]}%" '
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
    Suprafața fiecărei camere apare la trecerea cursorului peste numere.
    Cotele definitive se predau la semnarea antecontractului.
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
  <h2 class="ec-form__t">Aveți întrebări? Trimiteți-ne un mesaj</h2>
  <p class="ec-form__i">
    Un consultant analizează solicitarea și revine cu un răspuns în aceeași zi
    lucrătoare. Pentru o vizionare, menționați în mesaj intervalul orar care
    vă convine, iar programarea se confirmă telefonic.
  </p>
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


# ---------------------------------------------------- showroom si program
# Un singur bloc de invitatie, folosit identic pe toate paginile.
SHOWROOM = {
    "adresa": "Str. Dealul Zorilor 9, zona Păcurari, Iași",
    "tel": "0757 70 70 80",
    "tel_link": "+40757707080",
    "mail": "vanzari@emerald-city.ro",
    "program": "Luni–vineri 9–18 · Sâmbătă 10–14",
}


def showroom(r, nr="", sub=None):
    """Sectiunea de final: showroom, date de contact si formular."""
    cap = (f'<span class="ec-shead__n">{nr} — Showroom</span>' if nr
           else '<p class="ec-eyebrow">Showroom</p>')
    sub = sub or ("Vizionarea apartamentului-model se face cu programare. O întâlnire "
                  "durează aproximativ 40 de minute și include prezentarea planurilor "
                  "și a disponibilității.")
    return f"""<section class="ec-section" id="showroom">
    <div class="ec-shead">
      <div>{cap}
        <h2>Vă așteptăm <em>în showroom</em></h2></div>
      <p class="ec-shead__p">{e(sub)}</p>
    </div>
    <div class="ec-split" style="margin-top:2.5rem">
      <div class="ec-panel ec-panel--harta">
        <div class="ec-showmap">
          <iframe src="https://www.google.com/maps?q=Strada+Dealul+Zorilor+9,+Ia%C8%99i&amp;z=16&amp;output=embed"
                  title="Harta biroului de vânzări — Str. Dealul Zorilor 9, Iași"
                  loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
          <a class="ec-showmap__fallback" href="https://www.google.com/maps/search/?api=1&amp;query=Strada+Dealul+Zorilor+9+Ia%C8%99i"
             target="_blank" rel="noopener"><i class="fa-solid fa-map-location-dot" aria-hidden="true"></i> Deschideți harta în Google Maps</a>
          <a class="ec-showmap__go" href="https://www.google.com/maps/search/?api=1&amp;query=Strada+Dealul+Zorilor+9+Ia%C8%99i"
             target="_blank" rel="noopener"><i class="fa-solid fa-diamond-turn-right" aria-hidden="true"></i> Indicații rutiere</a>
        </div>
        <div class="ec-acces ec-acces--2">
          <div><span class="ec-acces__i"><i class="fa-solid fa-location-dot" aria-hidden="true"></i></span>
            <div><b>Adresă</b><span>{e(SHOWROOM["adresa"])}</span></div></div>
          <div><span class="ec-acces__i"><i class="fa-solid fa-phone" aria-hidden="true"></i></span>
            <div><b>Telefon</b><span><a href="tel:{SHOWROOM["tel_link"]}">{e(SHOWROOM["tel"])}</a></span></div></div>
          <div><span class="ec-acces__i"><i class="fa-solid fa-clock" aria-hidden="true"></i></span>
            <div><b>Program</b><span>{e(SHOWROOM["program"])}</span></div></div>
          <div><span class="ec-acces__i"><i class="fa-solid fa-envelope" aria-hidden="true"></i></span>
            <div><b>E-mail</b><span><a href="mailto:{SHOWROOM["mail"]}">{e(SHOWROOM["mail"])}</a></span></div></div>
        </div>
        <div class="ec-cta__btns" style="margin-top:2rem">
          <a class="ec-btn" href="tel:{SHOWROOM["tel_link"]}"><i class="fa-solid fa-phone" aria-hidden="true"></i> Contact telefonic</a>
          <a class="ec-btn ec-btn--out" href="https://wa.me/40757707080"><i class="fa-brands fa-whatsapp" aria-hidden="true"></i> Contact WhatsApp</a>
        </div>
      </div>
      {formular(None, r)}
    </div>
  </section>"""


# ------------------------------------------------- alerta si captare de lead
def alerta(titlu, text, context="", pict="bell"):
    """Banda de inscriere la notificari de disponibilitate."""
    ctx = (f'<input type="hidden" name="context" value="{e(context)}">' if context else "")
    return f"""<section class="ec-alerta ec-rv">
    <div class="ec-alerta__b">
      <span class="ec-alerta__ic"><i class="fa-solid fa-{pict}" aria-hidden="true"></i></span>
      <div>
        <h2>{e(titlu)}</h2>
        <p>{e(text)}</p>
      </div>
    </div>
    <form class="ec-alerta__f" method="post" action="#" novalidate>
      {ctx}
      <label class="ec-sr" for="al-{abs(hash(titlu)) % 9999}">Adresă de e-mail</label>
      <input id="al-{abs(hash(titlu)) % 9999}" name="email" type="email"
             placeholder="adresa@exemplu.ro" autocomplete="email">
      <button class="ec-btn ec-btn--brass" type="submit">
        <i class="fa-solid fa-paper-plane" aria-hidden="true"></i> Anunță-mă</button>
      <span class="ec-alerta__n">Machetă de lucru — formularul nu trimite date.</span>
    </form>
  </section>"""



def cta_dublu(r, context=""):
    """Doua indemnuri, unul langa altul: vizionare si informatii."""
    return f"""<section class="ec-duo ec-rv">
    <div class="ec-duo__c">
      <span class="ec-duo__ic"><i class="fa-solid fa-calendar-check" aria-hidden="true"></i></span>
      <h2>Programați o vizionare</h2>
      <p>
        Apartamentul-model, planurile pe masă și lista de disponibilitate, într-o
        întâlnire de aproximativ 40 de minute. Programarea se confirmă telefonic,
        în aceeași zi lucrătoare.
      </p>
      <div class="ec-duo__a">
        <a class="ec-btn ec-btn--white" href="{r}programare-vizionare/">
          <i class="fa-solid fa-calendar-check" aria-hidden="true"></i> Programare vizionare</a>
        <a class="ec-btn ec-btn--outlight" href="tel:{SHOWROOM["tel_link"]}">
          <i class="fa-solid fa-phone" aria-hidden="true"></i> {e(SHOWROOM["tel"])}</a>
      </div>
    </div>
    <div class="ec-duo__c">
      <span class="ec-duo__ic"><i class="fa-solid fa-circle-question" aria-hidden="true"></i></span>
      <h2>Aveți nevoie de informații suplimentare?</h2>
      <p>
        Un consultant transmite lista completă de disponibilitate, planurile detaliate
        ale fiecărei compartimentări și condițiile de plată, pe e-mail sau pe WhatsApp.
      </p>
      <div class="ec-duo__a">
        <a class="ec-btn ec-btn--white" href="mailto:{SHOWROOM["mail"]}">
          <i class="fa-solid fa-envelope" aria-hidden="true"></i> Cerere pe e-mail</a>
        <a class="ec-btn ec-btn--outlight" href="https://wa.me/40757707080" target="_blank" rel="noopener">
          <i class="fa-brands fa-whatsapp" aria-hidden="true"></i> Contact WhatsApp</a>
      </div>
    </div>
  </section>"""

def cta_preturi(r, imagine_fundal="dining-01"):
    """Banda de captare: lista completa de preturi, pe e-mail."""
    return f"""<section class="ec-ctab ec-rv">
    {imagine(imagine_fundal, "", r, "100vw")}
    <div class="ec-ctab__veil"></div>
    <div class="ec-wrap ec-ctab__in">
      <div class="ec-ctab__t">
        <p class="ec-eyebrow" style="color:var(--ec-brass)">Lista de prețuri</p>
        <h2>Toate prețurile, <em>într-un singur document</em></h2>
        <p>
          Lista completă de disponibilitate, cu suprafețe, etaje, orientări și prețuri,
          actualizată la zi. Se transmite pe e-mail în aceeași zi lucrătoare.
        </p>
        <ul class="ec-ctab__l">
          <li><i class="fa-solid fa-check" aria-hidden="true"></i> Toate apartamentele disponibile</li>
          <li><i class="fa-solid fa-check" aria-hidden="true"></i> Prețuri cu TVA inclus</li>
          <li><i class="fa-solid fa-check" aria-hidden="true"></i> Condiții de plată și etape</li>
        </ul>
      </div>
      <form class="ec-ctab__f" method="post" action="#" novalidate>
        <h3>Primește lista</h3>
        <div><label for="cp-nume">Nume</label>
          <input id="cp-nume" name="nume" type="text" autocomplete="name"></div>
        <div><label for="cp-mail">E-mail</label>
          <input id="cp-mail" name="email" type="email" autocomplete="email"></div>
        <div><label for="cp-tel">Telefon</label>
          <input id="cp-tel" name="telefon" type="tel" autocomplete="tel"></div>
        <button class="ec-btn ec-btn--brass" type="submit">
          <i class="fa-solid fa-file-arrow-down" aria-hidden="true"></i> Trimite lista</button>
        <p class="ec-form__note">Machetă de lucru — formularul nu trimite date.</p>
      </form>
    </div>
  </section>"""

# ------------------------------------------------- suprafete si finisaje
FINISAJE_SCURT = [
    ("fire-flame-simple", "Încălzire în pardoseală", "în toate camerele"),
    ("gauge-high",        "Centrală în condensație", "economie până la 35% la gaz"),
    ("border-all",        "Tâmplărie PVC, 7 camere", "geam tripan, sticlă Low-E"),
    ("grip-lines",        "Parchet laminat 10 mm", "clasă de trafic intens"),
    ("bath",              "Grup sanitar echipat", "gresie, faianță, obiecte sanitare"),
    ("video",             "Videointerfon", "acces controlat în bloc și parcare"),
]


def panou_suprafete(r, su, ext, eticheta_ext, total):
    """Suprafata utila, cea totala si finisajele incluse — langa plan."""
    fin = "".join(
        f'<li><span class="ec-dot__i">{ic(p)}</span>'
        f'<span><b>{e(t)}</b><em>{e(d)}</em></span></li>'
        for p, t, d in FINISAJE_SCURT)
    ext_html = (f'<div class="ec-supraf__c"><span>{e(eticheta_ext)}</span><b>{e(ext)}</b></div>'
                if ext else "")
    return f"""<div class="ec-supraf">
        <div class="ec-supraf__cifre">
          <div class="ec-supraf__c"><span>Suprafață utilă</span><b>{e(su)}</b></div>
          {ext_html}
          <div class="ec-supraf__c ec-supraf__c--total"><span>Suprafață totală</span><b>{e(total)}</b></div>
        </div>
        <div class="ec-supraf__h">Finisaje incluse în preț</div>
        <ul class="ec-supraf__l">{fin}</ul>
        <a class="ec-supraf__go" href="{r}finisaje/">{ic("arrow-right")} Lista completă a dotărilor</a>
      </div>"""

# ------------------------------------------------------------- imagini
_LQ = os.path.join(RAD, "assets", "data", "lqip.json")
LQIP = json.load(open(_LQ, encoding="utf-8")) if os.path.exists(_LQ) else {}


ALT_IMPLICIT = {
    "hero-living": "Living finisat într-un apartament Emerald City, Iași",
    "living-01": "Living cu bucătărie deschisă, apartament Emerald City Iași",
    "living-02": "Zonă de zi cu măslin și perete de marmură, Emerald City Iași",
    "dining-01": "Zonă de dining cu vedere spre grădină, Emerald City Iași",
    "dormitor-01": "Dormitor finisat, apartament Emerald City Iași",
    "dormitor-02": "Dormitor cu dressing, apartament Emerald City Iași",
    "hol-01": "Hol de intrare finisat, apartament Emerald City Iași",
    "baie-01": "Baie finisată cu marmură și alamă, Emerald City Iași",
    "bucatarie-01": "Bucătărie cu blat din marmură, Emerald City Iași",
    "gs-ansamblu": "Ansamblu rezidențial dezvoltat de Green Stone Group",
}


def imagine(nume, alt, r, sizes="100vw", eager=False, w=1600, h=900, cls=""):
    """<picture> cu WebP si rezerva JPEG, plus blur-up din miniatura de 20px."""
    alt = alt or ALT_IMPLICIT.get(nume, "")
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
  <p class="ec-calc__sub">Estimare orientativă pentru o achiziție destinată închirierii.</p>
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
# Cum se citeste lumina, dupa orientarea ferestrelor.
LUMINA = {
    "N":  "lumină constantă, difuză, fără soare direct — potrivită pentru birou",
    "NE": "soare dimineața devreme, răcoare în a doua parte a zilei",
    "E":  "soare de dimineață, până spre prânz",
    "SE": "soare de dimineață și până după-amiaza",
    "S":  "soare pe cea mai mare parte a zilei",
    "SV": "soare de la prânz până seara",
    "V":  "soare de după-amiază, apusuri din living",
    "NV": "lumină caldă spre seară, răcoare dimineața",
}
ETAJ_TEXT = {
    0: "Este la parter, deci se intră direct, fără scări și fără lift.",
    1: "Primul etaj rămâne aproape de sol, dar deasupra nivelului aleilor.",
    2: "Etajul al doilea are priveliște deschisă peste spațiile verzi dintre blocuri.",
    3: "Ultimul etaj nu are apartament deasupra, deci nu se aud pași de la vecini.",
}

# Dotarile care conteaza in pagina unei unitati, pe scurt.
INCLUSE_UNIT = [
    ("fire-flame-simple", "Încălzire în pardoseală"),
    ("gauge-high", "Centrală în condensație"),
    ("border-all", "Tâmplărie PVC, 7 camere"),
    ("grip-lines", "Parchet laminat 10 mm"),
    ("bath", "Grup sanitar echipat"),
    ("bolt", "Instalație electrică completă"),
    ("paint-roller", "Pereți gletuiți și vopsiți"),
    ("door-closed", "Uși interioare montate"),
    ("video", "Videointerfon"),
    ("elevator", "Lift în bloc"),
]


def poveste_unitate(u):
    """Doua-trei fraze despre cum se traieste in apartamentul acesta."""
    fraze = []
    lum = LUMINA.get(u["orientare"])
    if lum:
        fraze.append(f"Ferestrele sunt orientate spre "
                     f"{ORIENTARE.get(u['orientare'], u['orientare'])}: {lum}.")
    if u["etaj"] == 0 and u["su_curte"] > 0:
        fraze.append("Este la parter, cu ieșire directă în curte, fără scări și fără lift.")
    else:
        fraze.append(ETAJ_TEXT.get(u["etaj"], ""))
    if u["su_curte"] > 0:
        fraze.append(f"Curtea de {mp(u['su_curte'])} este în folosință exclusivă, cu "
                     "pardoseală exterioară executată și priză proprie.")
    elif u["su_balcon"] > 0:
        fraze.append(f"Balconul de {mp(u['su_balcon'])} se deschide din zona de zi.")
    if u["boxa_disponibila"] == "da":
        fraze.append("La demisol este disponibilă o boxă de depozitare, care se "
                     "contractează separat.")
    return " ".join(x for x in fraze if x)


def pagina_unitate(u, similare):
    r = "../../"
    uid = u["unit_id"]
    tip = u["tip_apartament"]
    titlu_h = (f"Apartament {camere_txt(u['nr_camere'])}, {mp(u['su_utila'])} — "
               f"blocul {bloc(u['corp'])}, {etaj_txt(u['etaj']).lower()}")
    disp = u["status"] == "disponibil"
    ppm = round(u["pret_eur"] / u["su_utila"])
    imagini = GALERIE_TIP.get(tip, ["living-01"])

    # ---- suprafete pe camera ---------------------------------------------
    randuri = ""
    for nume, pond in CAMERE_TIP[tip]:
        randuri += f"<tr><td>{nume}</td><td>{mp(round(u['su_utila'] * pond, 2))}</td></tr>"
    if u["su_balcon"] > 0:
        randuri += f"<tr><td>Balcon</td><td>{mp(u['su_balcon'])}</td></tr>"
    if u["su_curte"] > 0:
        randuri += f"<tr><td>Curte proprie</td><td>{mp(u['su_curte'])}</td></tr>"

    # ---- cifrele din antet ------------------------------------------------
    figuri = "".join(
        f'<div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic(pic)}</span>'
        f'<span><b>{e(val)}</b><em>{e(et)}</em></span></div>'
        for val, et, pic in [
            (mp(u["su_utila"]), "Suprafață utilă", "ruler-combined"),
            (mp(u["su_curte"]) if u["su_curte"] > 0 else mp(u["su_balcon"]),
             "Curte proprie" if u["su_curte"] > 0 else "Balcon", "sun"),
            (etaj_txt(u["etaj"]), f"Blocul {bloc(u['corp'])}", "building"),
            (f"{ppm} €/m²", "Preț pe metru pătrat", "calculator"),
        ])

    NUME_CAMERA = {"living-01": "Living", "living-02": "Living", "dining-01": "Dining",
                   "bucatarie-01": "Bucătărie", "dormitor-01": "Dormitor",
                   "dormitor-02": "Dormitor", "baie-01": "Grup sanitar", "hol-01": "Hol",
                   "hero-living": "Living"}
    et_gal = f"Apartament {camere_txt(u['nr_camere'])} tip {tip}"
    galerie = "".join(
        f'<figure class="ec-pgal__i ec-rv">'
        f'{imagine(x, f"{NUME_CAMERA.get(x, chr(73) + chr(110) + chr(116) + chr(101) + chr(114) + chr(105) + chr(111) + chr(114))} — {et_gal}, Emerald City Iași", r, "(min-width: 70rem) 33vw, 100vw")}'
        f'<figcaption class="ec-pgal__c"><b>{e(NUME_CAMERA.get(x, "Interior"))}</b>'
        f'<span>{e(et_gal)}</span></figcaption></figure>'
        for x in imagini[:3])

    incluse = "".join(
        f'<div class="ec-fac__i ec-rv"><i>{ic(p)}</i><span>{e(t)}</span></div>'
        for p, t in INCLUSE_UNIT)

    puncte = sorted(DISTANTE.get("puncte", []), key=lambda x: x["km"])[:6]
    distante = "".join(
        f'<li><span class="ec-dot__i">{ic("location-dot")}</span>'
        f'<span>{e(p["nume"])}</span><b>{str(p["km"]).replace(".", ",")} km</b></li>'
        for p in puncte)
    cartier = "".join(
        f'<li><span class="ec-dot__i">{ic(p)}</span><span>{e(t)}</span></li>'
        for p, t in [("tree", "Parc și spații verzi amenajate"),
                     ("child-reaching", "Loc de joacă pentru copii"),
                     ("bicycle", "Piste de biciclete în incintă"),
                     ("square-parking", "940 de locuri de parcare"),
                     ("shop", "Spații comerciale la parter"),
                     ("dumbbell", "Zone de fitness")])

    cta = (f'<a class="ec-btn ec-btn--brass" href="#cere-detalii">{ic("envelope")} Cere detalii</a>'
           f'<a class="ec-btn ec-btn--wa" href="{WA}">{ic("whatsapp", brand=True)} WhatsApp</a>') if disp else           (f'<a class="ec-btn" href="{r}apartamente-iasi/{CATEGORII[u["nr_camere"]]["slug"]}/">'
           f'{ic("table-list")} Apartamente similare</a>')

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
            {"@type": "LocationFeatureSpecification", "name": "Curte proprie", "value": u["su_curte"] > 0},
            {"@type": "LocationFeatureSpecification", "name": "Boxă", "value": u["boxa_disponibila"] == "da"},
            {"@type": "LocationFeatureSpecification", "name": "Parcare subterană", "value": u["parcare_subterana"] == "da"},
        ],
        "offers": {"@type": "Offer", "price": str(u["pret_eur"]), "priceCurrency": "EUR",
                   "availability": f"https://schema.org/{STATUS_SCHEMA[u['status']]}",
                   "seller": {"@id": "https://emerald-city.ro/#dezvoltator"}},
    }

    continut = f"""<section class="ec-phero ec-phero--unit">
  {imagine(imagini[0], "", r, "100vw", eager=True)}
  <div class="ec-phero__veil"></div>
  <div class="ec-wrap ec-phero__in">
    <nav class="ec-crumbs" aria-label="Firimituri">
      <a href="{r}">Acasă</a><span>/</span><a href="{r}apartamente-iasi/">Apartamente</a><span>/</span>
      <a href="{r}apartamente-iasi/{CATEGORII[u['nr_camere']]['slug']}/">{e(CATEGORII[u['nr_camere']]['titlu'])}</a>
      <span>/</span>{e(uid)}
    </nav>
    <span class="ec-tag ec-tag--{u['status']}">{STATUS_ET[u['status']]}</span>
    <h1>{e(titlu_h)}</h1>
    <p class="ec-phero__sub">{e(poveste_unitate(u))}</p>
    <div class="ec-uchips">
      <span>{ic("hashtag")} {e(uid)}</span>
      <span>{ic("layer-group")} Etapa {u['etapa']}</span>
      <span>{ic("compass-drafting")} Tip {tip}</span>
      <span>{ic("compass")} {e(ORIENTARE.get(u['orientare'], u['orientare']).capitalize())}</span>
    </div>
  </div>
</section>

<div class="ec-figs-wrap">
  <div class="ec-wrap"><div class="ec-figs">{figuri}</div></div>
</div>

<div class="ec-wrap">
  <div class="ec-pricebar" style="margin-top:var(--ec-gap)">
    <div>
      <div class="ec-pricebar__p">{euro(u['pret_eur'])}</div>
      <div class="ec-pricebar__s">{ppm} €/m² · TVA inclus · avans 15% la antecontract</div>
    </div>
    <div class="ec-pricebar__cta">{buton_salvare(uid)}{cta}</div>
  </div>

  <section class="ec-section" id="plan">
    <div class="ec-shead">
      <div><span class="ec-shead__n">01 — Compartimentare</span>
        <h2>Planul <em>apartamentului</em></h2></div>
      <p class="ec-shead__p">
        Planul compartimentării, cu suprafețele pe cameră. Cotele exacte se confirmă
        în anexa contractului.
      </p>
    </div>
    <div class="ec-split" style="margin-top:2.5rem">
      {plan_interactiv(tip, u['nr_camere'], r, u['su_utila'])}
      {panou_suprafete(r, mp(u['su_utila']),
                       mp(u['su_curte']) if u['su_curte'] > 0 else (mp(u['su_balcon']) if u['su_balcon'] > 0 else ""),
                       "Curte proprie" if u['su_curte'] > 0 else "Balcon",
                       mp(u['su_utila'] + (u['su_curte'] if u['su_curte'] > 0 else u['su_balcon'])))}
    </div>
  </section>

  <section class="ec-section" id="galerie" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">02 — Galerie</span>
        <h2>Apartamentul-model, <em>în imagini</em></h2></div>
      <p class="ec-shead__p">
        Randări din apartamentul-model de tip {tip}, cu finisajele incluse în preț.
      </p>
    </div>
    <div class="ec-pgal ec-pgal--3" style="margin-top:2.5rem">{galerie}</div>
  </section>

  <section class="ec-section" id="detalii" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">03 — Detalii</span>
        <h2>Fișa <em>unității</em></h2></div>
      <p class="ec-shead__p">Datele din tabelul de vânzări, pentru această unitate.</p>
    </div>
    <dl class="ec-specs" style="margin-top:2.5rem">
      <div class="ec-spec"><dt>Cod unitate</dt><dd>{e(uid)}</dd></div>
      <div class="ec-spec"><dt>Bloc și etaj</dt><dd>{bloc(u['corp'])} · {etaj_txt(u['etaj'])}</dd></div>
      <div class="ec-spec"><dt>Compartimentare</dt><dd>Tip {tip}</dd></div>
      <div class="ec-spec"><dt>Camere</dt><dd>{u['nr_camere']}</dd></div>
      <div class="ec-spec"><dt>Suprafață utilă</dt><dd>{mp(u['su_utila'])}</dd></div>
      <div class="ec-spec"><dt>{'Curte proprie' if u['su_curte'] > 0 else 'Balcon'}</dt>
        <dd>{mp(u['su_curte'] if u['su_curte'] > 0 else u['su_balcon'])}</dd></div>
      <div class="ec-spec"><dt>Orientare</dt><dd>{e(ORIENTARE.get(u['orientare'], u['orientare']).capitalize())}</dd></div>
      <div class="ec-spec"><dt>Preț pe metru pătrat</dt><dd>{ppm} €/m²</dd></div>
      <div class="ec-spec"><dt>Boxă de depozitare</dt><dd>{'Disponibilă' if u['boxa_disponibila'] == 'da' else 'Indisponibilă'}</dd></div>
      <div class="ec-spec"><dt>Parcare</dt><dd>{'Subterană' if u['parcare_subterana'] == 'da' else 'La suprafață'}</dd></div>
      <div class="ec-spec"><dt>Regim de înălțime</dt><dd>2D+P+3E</dd></div>
      <div class="ec-spec"><dt>Etapa</dt><dd>{u['etapa']}</dd></div>
    </dl>
  </section>

</div>

<section class="ec-band" id="cartier">
  <div class="ec-wrap">
    <div class="ec-section">
      <div class="ec-shead">
        <div><span class="ec-shead__n" style="color:var(--ec-brass)">04 — Cartierul</span>
          <h2>Ce urmează <em>dincolo de ușă</em></h2></div>
        <p class="ec-shead__p">
          Ansamblul are 5 hectare, din care 30,85% spațiu verde amenajat, în Iași,
          zona Păcurari.
        </p>
      </div>
      <div class="ec-dotari" style="margin-top:2.5rem">
        <div class="ec-dot ec-rv">
          <div class="ec-dot__h"><span class="ec-dot__c">{ic("route")}</span>
            <span class="ec-dot__tx"><b>Distanțe</b><em>Pe traseu rutier</em></span></div>
          <ul class="ec-dot__l ec-dot__l--val">{distante}</ul>
        </div>
        <div class="ec-dot ec-rv">
          <div class="ec-dot__h"><span class="ec-dot__c">{ic("tree-city")}</span>
            <span class="ec-dot__tx"><b>În incintă</b><em>Folosință comună</em></span></div>
          <ul class="ec-dot__l">{cartier}</ul>
        </div>
      </div>
      <div class="ec-center" style="margin-top:2rem">
        <a class="ec-btn ec-btn--white" href="{r}apartamente-iasi-pacurari/">{ic("map-location-dot")} Harta zonei</a>
        <a class="ec-btn ec-btn--outlight" href="{r}proiect/">{ic("compass-drafting")} Datele proiectului</a>
      </div>
    </div>
  </div>
</section>

<div class="ec-wrap">
  <section class="ec-section" id="costuri">
    <div class="ec-shead">
      <div><span class="ec-shead__n">05 — Costuri</span>
        <h2>Cât ar însemna <em>lunar</em></h2></div>
      <p class="ec-shead__p">
        Simulare orientativă de rată, pornind de la prețul acestei unități.
        Oferta finală se stabilește cu banca.
      </p>
    </div>
    <div class="ec-split" style="margin-top:2.5rem">
      {calc_rata(u['pret_eur'])}
      <div class="ec-calc" style="display:flex;flex-direction:column;justify-content:center">
        <h3 class="ec-title" style="font-size:1.1rem">Achiziție în scop investițional</h3>
        <p class="ec-calc__sub">
          Estimare de randament și de amortizare, pornind de la prețul acestei unități
          și de la chiriile practicate în zona Păcurari.
        </p>
        <p><a class="ec-btn ec-btn--brass" href="{r}investitie-apartamente-iasi/?pret={u['pret_eur']}&amp;su={u['su_utila']}">
          {ic("chart-line")} Calculator de randament</a></p>
      </div>
    </div>
  </section>

  <section class="ec-section" id="cere-detalii" style="padding-block:0 var(--ec-section)">
    {cta_dublu(r, uid)}
  </section>

  {showroom(r, "06")}

  <section class="ec-section" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">07 — Alternative</span>
        <h2>Apartamente <em>similare</em></h2></div>
      <p class="ec-shead__p">
        Aceeași compartimentare, la alt etaj sau în alt bloc, cu prețuri apropiate.
      </p>
    </div>
    <div class="ec-similar" style="margin-top:2.5rem">{''.join(card_unitate(x, r) for x in similare)}</div>
  </section>
</div>

<div class="ec-sticky" data-sticky>
  <span class="ec-sticky__p">{euro(u['pret_eur'])}<small>{camere_txt(u['nr_camere'])} · {mp(u['su_utila'])}</small></span>
  <span class="ec-sticky__b">
    {buton_salvare(uid)}
    <a class="ec-btn ec-btn--brass" href="{TEL_LINK}">{ic("phone")} Sună</a>
    <a class="ec-btn ec-btn--wa" href="{WA}">{ic("whatsapp", brand=True)} WhatsApp</a>
  </span>
</div>"""

    # codul unitatii intra in titlu si in descriere: fara el, apartamentele
    # cu aceleasi caracteristici ar avea metadate identice
    return pagina(f"{uid} — apartament {camere_txt(u['nr_camere'])} {mp(u['su_utila'])}, "
                  f"blocul {bloc(u['corp'])} | Emerald City",
                  f"Apartamentul {uid}: {camere_txt(u['nr_camere'])}, {mp(u['su_utila'])}, "
                  f"blocul {bloc(u['corp'])}, {etaj_txt(u['etaj']).lower()}, orientare "
                  f"{ORIENTARE.get(u['orientare'], u['orientare'])}. {euro(u['pret_eur'])}, "
                  "predare la cheie, în Iași, zona Păcurari.",
                  continut, r, schema, f"apartamente-iasi/{uid.lower()}/",
                  imagini[0])


# ========================================================== pagina tipologie
# Ce recomanda fiecare compartimentare, pe scurt.
AVANTAJE_TIP = {
 "1A": [("maximize", "Zonă de zi deschisă",
         "Bucătăria integrată în living folosește eficient suprafața și lasă senzația "
         "de spațiu mai amplu decât o compartimentare închisă."),
        ("box-archive", "Spațiu de depozitare",
         "Debaraua separată preia lucrurile de sezon, fără să ocupe din zona de zi."),
        ("chart-line", "Cea mai cerută la închiriere",
         "Formatul cu cel mai scurt timp de ocupare pe piața de închirieri din Iași."),
        ("tag", "Prag de intrare redus",
         "Cel mai mic preț de achiziție din ansamblu, cu aceleași finisaje incluse.")],
 "2A": [("door-open", "Dormitor separat",
         "Zona de noapte este despărțită complet de zona de zi, fără uși de trecere."),
        ("maximize", "Living deschis spre bucătărie",
         "O singură zonă continuă pentru gătit, masă și relaxare."),
        ("scale-balanced", "Raport echilibrat",
         "Cel mai bun raport între suprafață utilă și preț din tot ansamblul."),
        ("chart-line", "Cerere constantă",
         "Compartimentarea cu cea mai stabilă cerere pe piața din Iași.")],
 "2B": [("expand", "Dormitor mai generos",
         "Câțiva metri pătrați în plus față de 2A, suficienți pentru un pat dublu și "
         "un dulap pe toată lățimea peretelui."),
        ("box-archive", "Depozitare suplimentară",
         "Spațiu de depozitare peste cel standard, util pentru familii."),
        ("maximize", "Zonă de zi amplă",
         "Living deschis spre bucătărie, cu loc pentru masă de patru persoane."),
        ("ruler-combined", "Cea mai mare suprafață de 2 camere",
         "Până la 61 m² utili, la un preț pe metru pătrat comparabil.")],
 "3A": [("bath", "Două grupuri sanitare",
         "Al doilea grup sanitar elimină punctul de blocaj de dimineață."),
        ("utensils", "Bucătărie închisă",
         "Zonă de gătit separată, fără mirosuri și zgomot în living."),
        ("bed", "Două dormitoare",
         "Configurația clasică pentru o familie cu unul sau doi copii."),
        ("ruler-combined", "Suprafețe generoase",
         "Între 69 și 74 m² utili, cu balcon pe măsură.")],
 "3B": [("briefcase", "Cameră pentru birou",
         "A treia cameră poate fi folosită ca birou, fără să reducă spațiul de locuit."),
        ("bath", "Două grupuri sanitare",
         "Ambele complet finisate și echipate, incluse în preț."),
        ("maximize", "Living deschis",
         "Zona de zi continuă, cu bucătăria integrată, pentru o senzație de amplitudine."),
        ("ruler-combined", "Cele mai mari suprafețe",
         "Până la 81 m² utili, cele mai spațioase apartamente din ansamblu.")],
}


def slug_tip(cod):
    """Adresa unei compartimentari, in silozul categoriei ei."""
    return f"apartamente-iasi/{CATEGORII[int(cod[0])]['slug']}/tip-{cod.lower()}/"


def pagina_tip(cod, unitati_tip, grupe):
    r = "../../../"
    nr = int(cod[0])
    c = CATEGORII[nr]
    us = unitati_tip
    disp = [u for u in us if u["status"] == "disponibil"]
    su_min, su_max = min(u["su_utila"] for u in us), max(u["su_utila"] for u in us)
    pmin = min((u["pret_eur"] for u in disp), default=None)
    ppm = [u["pret_eur"] / u["su_utila"] for u in disp]
    su_med = sum(u["su_utila"] for u in us) / len(us)
    lista = f"{r}apartamente-iasi/disponibilitate/?tip={cod}&amp;status=disponibil"
    imagini = GALERIE_TIP.get(cod, ["living-01"])
    NUME_CAMERA = {"living-01": "Living", "living-02": "Living", "dining-01": "Dining",
                   "bucatarie-01": "Bucătărie", "dormitor-01": "Dormitor",
                   "dormitor-02": "Dormitor", "baie-01": "Grup sanitar", "hol-01": "Hol",
                   "hero-living": "Living"}

    figuri = "".join(
        f'<div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic(pic)}</span>'
        f'<span><b{attr}>{e(val)}</b><em>{e(et)}</em></span></div>'
        for val, et, pic, attr in [
            (str(len(disp)), "Disponibile acum", "key", f' data-num="{len(disp)}"'),
            (f"{su_min:.0f}–{su_max:.0f} m²", "Suprafață utilă", "ruler-combined", ""),
            (euro(pmin) if pmin else "—", "Preț de pornire", "tag", ""),
            (f"{min(ppm):.0f} €/m²" if ppm else "—", "De la", "calculator", ""),
        ])

    # suprafata exterioara: curtea la parter, balconul in rest
    balc = [u["su_balcon"] for u in us if u["su_balcon"] > 0]
    curti_t = [u["su_curte"] for u in us if u["su_curte"] > 0]
    if balc:
        ext_min, ext_max, eticheta_ext = min(balc), max(balc), "Balcon"
    elif curti_t:
        ext_min, ext_max, eticheta_ext = min(curti_t), max(curti_t), "Curte proprie"
    else:
        ext_min = ext_max = 0
        eticheta_ext = ""

    et_gal = f"Apartament {camere_txt(nr)} tip {cod}"
    galerie = "".join(
        f'<figure class="ec-pgal__i ec-rv">'
        f'{imagine(x, f"{NUME_CAMERA.get(x, chr(73) + chr(110) + chr(116) + chr(101) + chr(114) + chr(105) + chr(111) + chr(114))} — {et_gal}, Emerald City Iași", r, "(min-width: 70rem) 33vw, 100vw")}'
        f'<figcaption class="ec-pgal__c"><b>{e(NUME_CAMERA.get(x, "Interior"))}</b>'
        f'<span>{e(et_gal)}</span></figcaption></figure>'
        for x in imagini[:3])

    et_lista = []
    for etj in sorted({u["etaj"] for u in us}):
        n = [u for u in disp if u["etaj"] == etj]
        if n:
            et_lista.append((etaj_txt(etj), len(n), f"{lista}&amp;etaj={etj}",
                             "house-chimney" if etj == 0 else "building"))
    DOT = [("Curte proprie", "curte", "seedling", lambda x: x["su_curte"] > 0),
           ("Balcon", "balcon", "sun", lambda x: x["su_balcon"] > 0),
           ("Boxă de depozitare", "boxa", "box-archive", lambda x: x["boxa_disponibila"] == "da"),
           ("Parcare subterană", "parcare", "square-parking", lambda x: x["parcare_subterana"] == "da")]
    dot_lista = [(et, len([u for u in disp if t(u)]), f"{lista}&amp;extra={k}", p)
                 for et, k, p, t in DOT if [u for u in disp if t(u)]]

    def panou_filtru(titlu, pictograma, eticheta, randuri):
        li = "".join(
            f'<li><a href="{x[2]}"><span class="ec-dot__i">{ic(x[3])}</span>'
            f'<span>{e(x[0])}</span><b>{x[1]}</b></a></li>' for x in randuri)
        return (f'<div class="ec-dot ec-rv">'
                f'<div class="ec-dot__h"><span class="ec-dot__c">{ic(pictograma)}</span>'
                f'<span class="ec-dot__tx"><b>{e(titlu)}</b><em>{e(eticheta)}</em></span></div>'
                f'<ul class="ec-dot__l ec-dot__l--link">{li}</ul></div>')

    randuri = "".join(f"""<tr class="{'is-sold' if u['status'] != 'disponibil' else ''}">
      <td data-et="Cod"><a href="{r}apartamente-iasi/{u['unit_id'].lower()}/">{e(u['unit_id'])}</a></td>
      <td data-et="Bloc">{bloc(u['corp'])}</td><td data-et="Etaj">{etaj_txt(u['etaj'])}</td>
      <td class="num" data-et="Suprafață">{mp(u['su_utila'])}</td>
      <td data-et="Orientare">{u['orientare']}</td>
      <td class="num" data-et="Preț">{euro(u['pret_eur'])}</td>
      <td class="num" data-et="Preț/m²">{round(u['pret_eur'] / u['su_utila'])} €/m²</td>
      <td class="st" data-et="Stare"><span class="ec-tag ec-tag--{u['status']}">{STATUS_ET[u['status']]}</span></td>
    </tr>""" for u in sorted(us, key=lambda x: (x["status"] != "disponibil", x["pret_eur"]))[:40])

    avantaje = "".join(
        f'<div class="ec-why__i ec-rv">{ic(pic)}<h3>{e(t)}</h3><p>{e(d)}</p></div>'
        for pic, t, d in AVANTAJE_TIP[cod])

    surori = sorted(x for x in grupe if int(x[0]) == nr and x != cod)
    alte = ""
    for x in surori:
        gx = grupe[x]
        dx = [u for u in gx if u["status"] == "disponibil"]
        px = min((u["pret_eur"] for u in dx), default=None)
        imx = GALERIE_TIP.get(x, ["living-01"])[0]
        alte += f"""<article class="ec-tipc ec-rv">
          <figure class="ec-tipc__f">
            {imagine(imx, f"Apartament tip {x} la Emerald City", r, "(min-width: 62rem) 52vw, 100vw")}
            <span class="ec-tipc__badge">{len(dx)} disponibile</span>
          </figure>
          <div class="ec-tipc__b">
            <span class="ec-tipc__k">Compartimentare</span>
            <h3>Tip {x}</h3>
            <p>{e(DESC_TIP.get(x, ''))}</p>
            <div class="ec-tipc__row">
              <figure class="ec-tipc__p">{plan_svg(nr, x, sum(u['su_utila'] for u in gx) / len(gx), compact=True)}</figure>
              <dl>
                <div><dt>Suprafață utilă</dt><dd>{min(u['su_utila'] for u in gx):.0f}–{max(u['su_utila'] for u in gx):.0f} m²</dd></div>
                <div><dt>Disponibile</dt><dd>{len(dx)} din {len(gx)}</dd></div>
                <div><dt>Preț de pornire</dt><dd>{euro(px) if px else '—'}</dd></div>
              </dl>
            </div>
            <div class="ec-tipc__cta">
              <a class="ec-btn" href="{r}{slug_tip(x)}">{ic("compass-drafting")} Vezi compartimentarea {x}</a>
            </div>
          </div>
        </article>"""

    faq = "".join(f"<details><summary>{e(q)}</summary>"
                  f'<div class="ec-faq__a">{e(a)}</div></details>'
                  for q, a in FAQ_CAT[nr])

    sectiune_alte = ""
    if alte:
        sectiune_alte = (
            '<section class="ec-section" id="alte">'
            '<div class="ec-shead"><div><span class="ec-shead__n">06 — Alternative</span>'
            f'<h2>Cealaltă compartimentare <em>de {camere_txt(nr)}</em></h2></div>'
            '<p class="ec-shead__p">Aceeași categorie, alt plan. Diferă suprafețele '
            'și organizarea camerelor.</p></div>'
            f'<div class="ec-tipuri" style="margin-top:2.5rem">{alte}</div></section>')
    pad_intrebari = "0" if alte else "var(--ec-section)"
    nr_intrebari = "07" if alte else "06"
    nr_showroom = "08" if alte else "07"

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "CollectionPage",
             "name": f"Apartamente {camere_txt(nr)} tip {cod} — Emerald City Iași",
             "url": f"https://emerald-city.ro/{slug_tip(cod)}"},
            {"@type": "FAQPage",
             "mainEntity": [{"@type": "Question", "name": q,
                             "acceptedAnswer": {"@type": "Answer", "text": a}}
                            for q, a in FAQ_CAT[nr]]},
        ]}

    continut = f"""<section class="ec-phero">
  {imagine(imagini[0], "", r, "100vw", eager=True)}
  <div class="ec-phero__veil"></div>
  <div class="ec-wrap ec-phero__in">
    <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>
      <a href="{r}apartamente-iasi/">Apartamente</a><span>/</span>
      <a href="{r}apartamente-iasi/{c['slug']}/">{e(c['titlu'])}</a><span>/</span>Tip {cod}</nav>
    <p class="ec-eyebrow">Compartimentarea {cod}</p>
    <h1>Apartament {camere_txt(nr)} tip {cod}, în Iași</h1>
    <p class="ec-phero__sub">{e(DESC_TIP.get(cod, ''))} Între {su_min:.0f} și {su_max:.0f} m²
      suprafață utilă, cu {len(disp)} unități disponibile în acest moment.</p>
    <div class="ec-phero__cta">
      <a class="ec-btn ec-btn--white" href="#unitati">{ic("table-list")} Cele {len(disp)} unități disponibile</a>
      <a class="ec-btn ec-btn--outlight" href="#plan">{ic("compass-drafting")} Planul compartimentării</a>
    </div>
  </div>
</section>

<div class="ec-figs-wrap">
  <div class="ec-wrap"><div class="ec-figs">{figuri}</div></div>
</div>

<div class="ec-wrap">
  <section class="ec-section" id="plan">
    <div class="ec-shead">
      <div><span class="ec-shead__n">01 — Planul</span>
        <h2>Compartimentare apartament <em>{camere_txt(nr)} tip {cod}</em></h2></div>
      <p class="ec-shead__p">
        Planul compartimentării, cu suprafețele pe cameră. Cotele exacte diferă
        de la o unitate la alta și se confirmă în anexa contractului.
      </p>
    </div>
    <div class="ec-split" style="margin-top:2.5rem">
      {plan_interactiv(cod, nr, r, su_med)}
      {panou_suprafete(r, f"{su_min:.0f}–{su_max:.0f} m²",
                       f"{ext_min:.0f}–{ext_max:.0f} m²" if ext_max else "", eticheta_ext,
                       f"{su_min + ext_min:.0f}–{su_max + ext_max:.0f} m²")}
    </div>
  </section>

  <section class="ec-section" id="galerie" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">02 — Galerie</span>
        <h2>Apartamentul-model, <em>în imagini</em></h2></div>
      <p class="ec-shead__p">
        Randări din apartamentul-model de tip {cod}, cu finisajele incluse în preț.
      </p>
    </div>
    <div class="ec-pgal ec-pgal--3" style="margin-top:2.5rem">{galerie}</div>
  </section>

  <section class="ec-section" id="selectie" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">03 — Selecție rapidă</span>
        <h2>Selecție <em>după etaj și dotări</em></h2></div>
      <p class="ec-shead__p">
        Fiecare rând deschide lista filtrată pe compartimentarea {cod}.
      </p>
    </div>
    <div class="ec-dotari" style="margin-top:2.5rem">
      {panou_filtru("După etaj", "building", "Nivelul apartamentului", et_lista)}
      {panou_filtru("După dotări", "list-check", "Curte, boxă, parcare", dot_lista)}
    </div>
  </section>

  <section class="ec-section" id="unitati" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">04 — Unități</span>
        <h2>Apartamentele <em>de tip {cod}</em></h2></div>
      <p class="ec-shead__p">
        {len(us)} unități în ansamblu, ordonate după preț. Lista completă, cu filtre,
        este în secțiunea de disponibilitate.
      </p>
    </div>
    <div class="ec-table" style="margin-top:2.5rem">
      <table>
        <caption class="ec-sr">Apartamente de tip {cod}</caption>
        <thead><tr><th scope="col">Cod</th><th scope="col">Bloc</th><th scope="col">Etaj</th>
          <th scope="col">Suprafață</th><th scope="col">Orientare</th>
          <th scope="col">Preț</th><th scope="col">Preț/m²</th><th scope="col">Stare</th></tr></thead>
        <tbody>{randuri}</tbody>
      </table>
    </div>
    <div class="ec-center" style="margin-top:2rem">
      <a class="ec-btn" href="{lista}">{ic("table-list")} Lista completă, cu filtre</a>
    </div>
  </section>
</div>

<section class="ec-band" id="avantaje">
  <div class="ec-wrap">
    <div class="ec-section">
      <div class="ec-shead">
        <div><span class="ec-shead__n" style="color:var(--ec-brass)">05 — Avantaje</span>
          <h2>Ce recomandă <em>compartimentarea {cod}</em></h2></div>
        <p class="ec-shead__p">Patru criterii pentru care acest plan este cel potrivit.</p>
      </div>
      <div class="ec-why" style="margin-top:2.5rem">{avantaje}</div>
    </div>
  </div>
</section>

<div class="ec-wrap">
  {sectiune_alte}

  <section class="ec-section" id="intrebari" style="padding-block:{pad_intrebari} var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">{nr_intrebari} — Întrebări</span>
        <h2>Despre <em>{e(c['titlu'].lower())}</em></h2></div>
      <p class="ec-shead__p">
        {len(FAQ_CAT[nr])} întrebări despre suprafețe, compartimentări, dotări și condiții.
      </p>
    </div>
    <div class="ec-faq" style="margin-top:2.5rem">{faq}</div>
  </section>

  <section class="ec-section" style="padding-block:0 var(--ec-section)">
    {cta_dublu(r, cod)}
  </section>

  {showroom(r, nr_showroom)}
</div>

<script>
(() => {{
  const nr = [...document.querySelectorAll('.ec-fig b[data-num]')];
  if (!nr.length || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const o = new IntersectionObserver(es => es.forEach(x => {{
    if (!x.isIntersecting) return;
    const el = x.target, tinta = parseFloat(el.dataset.num), t0 = performance.now();
    const pas = t => {{
      const p = Math.min((t - t0) / 1100, 1);
      el.textContent = Math.round(tinta * (1 - Math.pow(1 - p, 3))).toLocaleString('ro-RO');
      if (p < 1) requestAnimationFrame(pas);
    }};
    requestAnimationFrame(pas);
    o.unobserve(el);
  }}), {{ threshold: .4 }});
  nr.forEach(x => o.observe(x));
}})();
</script>"""

    return pagina(f"Apartament {camere_txt(nr)} tip {cod}, Iași Păcurari | Emerald City",
                  f"{DESC_TIP.get(cod, '')} {su_min:.0f}–{su_max:.0f} m², {len(disp)} unități "
                  f"disponibile, de la {euro(pmin) if pmin else '—'}. Iași, zona Păcurari.",
                  continut, r, schema, slug_tip(cod))


# ============================================================ pagina listare
FAQ_LISTA = [
    ("Cât de des se actualizează lista de disponibilitate?",
     "Lista se generează din tabelul de vânzări al dezvoltatorului și se actualizează la fiecare "
     "modificare de stare: rezervare, semnare de antecontract sau eliberare a unei unități."),
    ("Ce înseamnă stările Disponibil, Rezervat și Vândut?",
     "Disponibil: unitatea poate fi rezervată. Rezervat: este blocată pe numele unui cumpărător, "
     "până la semnarea antecontractului. Vândut: antecontractul sau contractul a fost semnat."),
    ("Prețurile din listă sunt finale?",
     "Prețurile afișate includ TVA și toate finisajele. Devin ferme la rezervare sau la semnarea "
     "antecontractului; până atunci pot fi actualizate odată cu lista."),
    ("Ce reprezintă prețul pe metru pătrat?",
     "Prețul unității împărțit la suprafața utilă. Balconul, curtea, boxa și locul de parcare nu "
     "intră în suprafața utilă, de aceea unitățile cu curte au un preț pe metru pătrat aparent mai mare."),
    ("Cum se filtrează după etapă sau după compartimentare?",
     "Butoanele Etapa I–III și Tip 1A–3B se combină cu celelalte filtre. Fiecare selecție se "
     "reflectă în adresa paginii, care poate fi trimisă mai departe sau salvată."),
    ("Se poate primi lista completă pe e-mail?",
     "Da. Lista de disponibilitate, cu suprafețe, etaje, orientări și prețuri, se transmite pe e-mail "
     "în aceeași zi lucrătoare, la cerere."),
]


def pagina_listare(unitati):
    r = "../../"
    faq = "".join(f"<details><summary>{e(q)}</summary>"
                  f'<div class="ec-faq__a">{e(a)}</div></details>' for q, a in FAQ_LISTA)
    blocuri = sorted({u["corp"] for u in unitati}, key=lambda c: int(c[1:]))
    tipuri = sorted({u["tip_apartament"] for u in unitati})
    orientari = ["N", "NE", "E", "SE", "S", "SV", "V", "NV"]
    disp = [u for u in unitati if u["status"] == "disponibil"]
    su_min, su_max = min(u["su_utila"] for u in unitati), max(u["su_utila"] for u in unitati)
    p_min = min(u["pret_eur"] for u in disp)
    chip = lambda grp, v, et: f'<button class="ec-chip" data-f="{grp}" data-v="{v}" type="button">{et}</button>'

    figuri = "".join(
        f'<div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic(pic)}</span>'
        f'<span><b{attr}>{e(val)}</b><em>{e(et)}</em></span></div>'
        for val, et, pic, attr in [
            (str(len(unitati)), "Apartamente în ansamblu", "building", f' data-num="{len(unitati)}"'),
            (str(len(disp)), "Disponibile acum", "key", f' data-num="{len(disp)}"'),
            (euro(p_min), "Preț de pornire", "tag", ""),
            (f"{su_min:.0f}–{su_max:.0f} m²", "Suprafață utilă", "ruler-combined", ""),
        ])

    def grup(eticheta, id_, continut, mod="seg", pict="", span=""):
        ic_html = f'<i class="fa-solid fa-{pict}" aria-hidden="true"></i>' if pict else ""
        return (f'<div class="ec-fld{(" ec-fld--" + span) if span else ""}"><label id="{id_}">{ic_html}{eticheta}</label>'
                f'<div class="ec-chips ec-chips--{mod}" role="group" aria-labelledby="{id_}">{continut}</div></div>')

    def glisor(eticheta, id_, out_id, pict, atribute, val):
        return (f'<div class="ec-fld"><label for="{id_}"><i class="fa-solid fa-{pict}" aria-hidden="true"></i>{eticheta}</label>'
                f'<div class="ec-range ec-range--v2"><input type="range" id="{id_}" {atribute}>'
                f'<output for="{id_}" id="{out_id}">{val}</output></div></div>')

    continut = f"""<section class="ec-phero">
  {imagine("living-02", "", r, "100vw", eager=True)}
  <div class="ec-phero__veil"></div>
  <div class="ec-wrap ec-phero__in">
    <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>
      <a href="{r}apartamente-iasi/">Apartamente</a><span>/</span>Disponibilitate</nav>
    <p class="ec-eyebrow">Disponibilitate și prețuri</p>
    <h1>Toate apartamentele, cu prețuri afișate</h1>
    <p class="ec-phero__sub">
      {len(unitati)} de apartamente cu 1, 2 și 3 camere, actualizate din tabelul de vânzări.
      Filtrele se aplică instant, fără reîncărcarea paginii, iar fiecare unitate are
      pagina ei, cu plan și preț.
    </p>
    <div class="ec-phero__cta">
      <a class="ec-btn ec-btn--white" href="#lista">{ic("sliders")} Filtrare și listă</a>
      <a class="ec-btn ec-btn--outlight" href="{r}apartamente-iasi/#buget">{ic("tag")} Selecție după buget</a>
    </div>
  </div>
</section>

<div class="ec-figs-wrap">
  <div class="ec-wrap"><div class="ec-figs">{figuri}</div></div>
</div>

<div class="ec-wrap" id="lista">
  <section class="ec-section" style="padding-block:var(--ec-section) 0">
    <div class="ec-shead">
      <div><span class="ec-shead__n">01 — Filtre</span>
        <h2>Selecție <em>după criterii</em></h2></div>
      <p class="ec-shead__p">
        Camere, etaj, etapă, compartimentare, buget, dotări, orientare și bloc.
        Criteriile active se pot elimina individual.
      </p>
    </div>

    <div class="ec-filters ec-filters--v2" style="margin-top:2.5rem">
      <div class="ec-filters__h">
        <span class="ec-filters__t">{ic("sliders")} Filtre</span>
        <span class="ec-filters__act" id="fActive" aria-live="polite"></span>
        <button class="ec-filters__reset" id="fReset" type="button">{ic("rotate-left")} Resetare</button>
      </div>
      <div class="ec-filters__row ec-filters__row--3">
        {grup("Camere", "l1", ''.join(chip('camere', n, camere_txt(n)) for n in (1, 2, 3)), pict="door-open")}
        {grup("Etaj", "l2", ''.join(chip('etaj', n, etaj_txt(n)) for n in (0, 1, 2, 3)), pict="stairs")}
        {grup("Etapa de construcție", "l3", ''.join(chip('etapa', et, 'Etapa ' + et) for et in ('I', 'II', 'III')), pict="helmet-safety")}
      </div>
      <div class="ec-filters__row ec-filters__row--3">
        {grup("Stare", "l4", ''.join(chip('status', st, STATUS_ET[st]) for st in ('disponibil', 'rezervat', 'vandut')), pict="circle-check")}
        {grup("Compartimentare", "l7", ''.join(chip('tip', t, 'Tip ' + t) for t in tipuri), pict="vector-square")}
        {grup("Orientare", "l8", ''.join(chip('orientare', o, o) for o in orientari), pict="compass")}
      </div>
      <div class="ec-filters__row ec-filters__row--3">
        {glisor("Preț maxim", "fPret", "oPret", "tag", 'min="50000" max="130000" step="1000" value="130000"', "130.000 €")}
        {glisor("Suprafață utilă minimă", "fSu", "oSu", "ruler-combined", 'min="36" max="81" step="1" value="36"', "36 m²")}
        {grup("Dotări", "l5", chip('extra', 'balcon', 'Balcon') + chip('extra', 'curte', 'Curte')
                             + chip('extra', 'boxa', 'Boxă') + chip('extra', 'parcare', 'Parcare'), pict="star")}
      </div>
      <div class="ec-filters__row">
        {grup("Bloc", "l6", ''.join(chip('corp', c, bloc(c)) for c in blocuri), mod="bloc", pict="building")}
      </div>
    </div>
  </section>

  <section class="ec-section" style="padding-block:var(--ec-section) 0">
    <div class="ec-shead">
      <div><span class="ec-shead__n">02 — Rezultate</span>
        <h2>Lista <em>apartamentelor</em></h2></div>
      <p class="ec-shead__p">
        Fiecare rând deschide pagina unității, cu planul, galeria și simularea de rată.
      </p>
    </div>

    <div class="ec-lst" style="margin-top:2.5rem">
      <div class="ec-lst__bar">
        <span class="ec-lst__n" id="fCount">—</span>
        <div class="ec-search">
          {ic("magnifying-glass")}
          <input type="search" id="fSearch" placeholder="Cod, bloc, etaj sau „2 camere etaj 3”"
                 aria-label="Căutare în listă">
        </div>
        <label class="ec-lst__sort">
          <span>Sortare</span>
          <select id="fSort">
            <option value="pret:asc">Preț crescător</option>
            <option value="pret:desc">Preț descrescător</option>
            <option value="ppm:asc">Preț/m² crescător</option>
            <option value="su:desc">Suprafață descrescătoare</option>
            <option value="su:asc">Suprafață crescătoare</option>
            <option value="etaj:asc">Etaj crescător</option>
            <option value="corp:asc">Bloc</option>
          </select>
        </label>
        <div class="ec-lst__view" role="group" aria-label="Mod de afișare">
          <button type="button" class="is-on" data-view="tabel" aria-pressed="true">{ic("table-list")} Tabel</button>
          <button type="button" data-view="carduri" aria-pressed="false">{ic("grip")} Carduri</button>
        </div>
      </div>

      <div class="ec-table ec-lst__tabel" data-view-pane="tabel">
        <table id="fTable">
          <caption class="ec-sr">Lista apartamentelor</caption>
          <thead><tr>
            <th data-s="id">Cod</th><th data-s="corp">Bloc</th><th data-s="etaj">Etaj</th>
            <th data-s="tip">Tip</th><th data-s="su">Suprafață</th>
            <th data-s="orientare">Orientare</th><th data-s="pret" data-dir="asc">Preț</th>
            <th data-s="ppm">Preț/m²</th><th>Stare</th>
          </tr></thead>
          <tbody id="fBody"></tbody>
        </table>
      </div>
      <div class="ec-cards ec-lst__carduri" id="fCards" data-view-pane="carduri" hidden></div>
      <div id="fEmpty"></div>
      <div class="ec-more"><button class="ec-btn ec-btn--out" id="fMore" type="button">Încă 50 de apartamente</button></div>
    </div>
  </section>

  <section class="ec-section" style="padding-block:var(--ec-section) 0">
    {cta_dublu(r, "disponibilitate")}
  </section>

  <section class="ec-section" id="intrebari" style="padding-block:var(--ec-section) 0">
    <div class="ec-shead">
      <div><span class="ec-shead__n">03 — Întrebări</span>
        <h2>Despre <em>listă și prețuri</em></h2></div>
      <p class="ec-shead__p">{len(FAQ_LISTA)} întrebări despre actualizare, stări și modul de citire a listei.</p>
    </div>
    <div class="ec-faq" style="margin-top:2.5rem">{faq}</div>
  </section>

  {showroom(r, "04")}
</div>

<script>
(() => {{
  const nr = [...document.querySelectorAll('.ec-fig b[data-num]')];
  if (!nr.length || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const o = new IntersectionObserver(es => es.forEach(x => {{
    if (!x.isIntersecting) return;
    const el = x.target, tinta = parseFloat(el.dataset.num), t0 = performance.now();
    const pas = t => {{
      const pr = Math.min((t - t0) / 1100, 1);
      el.textContent = Math.round(tinta * (1 - Math.pow(1 - pr, 3))).toLocaleString('ro-RO');
      if (pr < 1) requestAnimationFrame(pas);
    }};
    requestAnimationFrame(pas);
    o.unobserve(el);
  }}), {{ threshold: .4 }});
  nr.forEach(x => o.observe(x));
}})();
</script>
<script src="{r}assets/js/listare.js"></script>"""

    schema = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "name": "Disponibilitate și prețuri — Emerald City",
         "url": "https://emerald-city.ro/apartamente-iasi/disponibilitate/"},
        {"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in FAQ_LISTA]}]}
    return pagina(
        "Disponibilitate și prețuri — apartamente Iași | Emerald City",
        f"Toate cele {len(unitati)} de apartamente din Emerald City, Iași zona Păcurari, cu "
        "prețuri afișate. Filtre după camere, etaj, buget, dotări și bloc.",
        continut, r, schema, "apartamente-iasi/disponibilitate/")


# ============================================== hub de siloz /apartamente-iasi/
def _icon(d):
    return ('<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"'
            ' stroke-width="1.5" aria-hidden="true">' + d + '</svg>')

ARGUMENTE = [
    ("Finisaje premium incluse",
     "Apartamentul nu se predă la gri, ci finisat, cu materiale alese de un birou de design.",
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

# Fiecare dotare are pictograma ei, ca randul sa se citeasca dintr-o privire.
DOTARI = [
    ("list-check",         "Finisaje premium incluse în preț"),
    ("border-all",         "Tâmplărie PVC cu 7 camere, geam tripan"),
    ("fire-flame-simple",  "Încălzire în pardoseală în toate camerele"),
    ("sun",                "Balcon la fiecare apartament"),
    ("box-archive",        "Boxă de depozitare la demisol"),
    ("video",              "Videointerfon și acces controlat"),
    ("elevator",           "Lift în fiecare bloc"),
    ("gauge",              "Contorizare individuală a consumurilor"),
]
FACILITATI = [
    ("tree",            "Parc dendrologic amenajat"),
    ("child-reaching",  "Loc de joacă pentru copii"),
    ("shop",            "Spații comerciale la parter"),
    ("square-parking",  "940 de locuri de parcare, 258 subterane"),
    ("person-walking",  "Alei pietonale între blocuri"),
    ("lightbulb",       "Iluminat exterior integrat"),
    ("road",            "Acces din Strada Ion Nistor"),
    ("city",            "4,8 km până în centrul Iașului"),
]


DOTARI_LOCUINTA = [
    ("fire-flame-simple", "Încălzire în pardoseală în toate camerele"),
    ("gauge-high",        "Centrală proprie în condensație"),
    ("border-all",        "Tâmplărie PVC cu 7 camere și geam tripan"),
    ("grip-lines",        "Parchet laminat de 10 mm, trafic intens"),
    ("bath",              "Grup sanitar complet finisat și echipat"),
    ("bolt",              "Instalație electrică cu aparataj montat"),
    ("door-closed",       "Uși interioare montate, ușă metalică la intrare"),
    ("video",             "Videointerfon"),
    ("sun",               "Balcon la fiecare apartament"),
    ("seedling",          "Curte proprie la parter, între 13 și 51 m²"),
]
DOTARI_CARTIER = [
    ("bicycle",         "Piste de biciclete"),
    ("dumbbell",        "Zone de fitness"),
    ("child-reaching",  "Locuri de joacă"),
    ("tree",            "Parc și spații verzi pe 15.501,80 m²"),
    ("square-parking",  "940 de locuri de parcare, 258 subterane"),
    ("charging-station","Preechipare pentru stații de încărcare auto"),
    ("solar-panel",     "Panouri fotovoltaice"),
    ("elevator",        "Lifturi în fiecare bloc"),
    ("recycle",         "Colectare îngropată a deșeurilor"),
    ("shop",            "Spații comerciale la parter"),
]


def panou_dotari(titlu, pictograma, elemente, eticheta=""):
    """Un panou cu antet si randuri cu pictograma proprie."""
    randuri = "".join(
        f'<li><span class="ec-dot__i">{ic(p)}</span><span>{e(t)}</span></li>'
        for p, t in elemente)
    return (f'<div class="ec-dot ec-rv">'
            f'<div class="ec-dot__h"><span class="ec-dot__c">{ic(pictograma)}</span>'
            f'<span class="ec-dot__tx"><b>{e(titlu)}</b>'
            f'<em>{e(eticheta or f"{len(elemente)} elemente")}</em></span></div>'
            f'<ul class="ec-dot__l">{randuri}</ul></div>')

SAGEATA = ('<span class="ec-arrow" style="padding:0"><svg width="22" height="10" viewBox="0 0 22 10"'
           ' fill="none" aria-hidden="true"><path d="M17 1l4 4-4 4M21 5H0" stroke="currentColor"'
           ' stroke-width="1.3"/></svg></span>')


# Pragurile de buget. Numarul de apartamente din fiecare se calculeaza din
# tabelul de vanzari, deci nu ramane nicio cifra scrisa de mana.
BUGETE = [
 (0,      60000,  "Sub 60.000 €",     "Garsoniere și 2 camere la etajele inferioare"),
 (60000,  80000,  "60.000 – 80.000 €", "Cele mai multe apartamente de 2 camere"),
 (80000,  110000, "80.000 – 110.000 €", "2 camere generoase și 3 camere"),
 (110000, 10**9,  "Peste 110.000 €",  "3 camere cu două grupuri sanitare și curte"),
]


FAQ_HUB = [
 ("Câte apartamente sunt disponibile acum?",
  "Numărul afișat pe această pagină se actualizează din tabelul de vânzări. Lista completă, "
  "cu filtre după camere, buget, etaj și bloc, este la secțiunea de disponibilitate."),
 ("Ce suprafețe au apartamentele?",
  "Între 37 și 81 m² suprafață utilă. Fiecare apartament are balcon, iar cele de la parter "
  "au curte proprie, între 13 și 51 m²."),
 ("Prețurile afișate includ TVA?",
  "Da. Prețurile de pe site includ TVA și toate finisajele. Nu există costuri suplimentare "
  "pentru execuția lor."),
 ("Ce înseamnă preț de pornire?",
  "Cel mai mic preț dintre apartamentele disponibile din categoria respectivă, la data "
  "actualizării. Prețul fiecărei unități este afișat individual în listă."),
 ("Se poate cumpăra cu credit ipotecar?",
  "Da. Apartamentele se pot achiziționa cu credit ipotecar standard, iar cele care se "
  "încadrează în plafon pot fi cumpărate și prin Noua Casă."),
 ("Ce avans se cere?",
  "15% din preț la semnarea antecontractului la notar, iar diferența la predare. Etapele "
  "de plată se stabilesc în contract."),
 ("Există comision de intermediere?",
  "Nu. Vânzarea se face direct de la dezvoltator, fără comision de agenție."),
 ("Pot rezerva un apartament?",
  "Da. Apartamentul se blochează pe numele cumpărătorului, iar prețul se menține pe perioada "
  "rezervării. Termenul se stabilește la biroul de vânzări."),
 ("Ce apartamente se predau primele?",
  "Cele din Etapa I, blocurile 1–6. Termenul fiecărei etape se înscrie în antecontract."),
 ("Pot vedea un apartament înainte de a cumpăra?",
  "Da. La biroul de vânzări se poate vizita apartamentul-model și se pot consulta planurile "
  "fiecărei compartimentări."),
]


def pagina_hub(unitati, grupe):
    r = "../"
    disp = [u for u in unitati if u["status"] == "disponibil"]
    su_min = min(u["su_utila"] for u in unitati)
    su_max = max(u["su_utila"] for u in unitati)
    p_min = min(u["pret_eur"] for u in disp)
    lista = f"{r}apartamente-iasi/disponibilitate/"

    # ---- cifrele din antet ------------------------------------------------
    figuri = "".join(
        f'<div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic(pic)}</span>'
        f'<span><b{attr}>{e(val)}</b><em>{e(et)}</em></span></div>'
        for val, et, pic, attr in [
            (str(len(unitati)), "Apartamente în ansamblu", "building",
             f' data-num="{len(unitati)}"'),
            (str(len(disp)), "Disponibile acum", "key", f' data-num="{len(disp)}"'),
            (euro(p_min), "Preț de pornire", "tag", ""),
            (f"{su_min:.0f}–{su_max:.0f} m²", "Suprafață utilă", "ruler-combined", ""),
        ])

    # ---- 01: dupa numarul de camere --------------------------------------
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

    # ---- 02: dupa buget ---------------------------------------------------
    bug_max = max(len([u for u in disp if a <= u["pret_eur"] < b]) for a, b, _, _ in BUGETE)
    bugete = ""
    for a, b, eticheta, descriere in BUGETE:
        n = [u for u in disp if a <= u["pret_eur"] < b]
        if not n:
            continue
        q = []
        if a:
            q.append(f"pret-min={a}")
        if b < 10**8:
            # pragul de sus e inclusiv in lista, exclusiv in gruparea de aici
            q.append(f"pret-max={b - 1}")
        q.append("status=disponibil")
        bugete += (f'<a class="ec-buget ec-rv" href="{lista}?{"&amp;".join(q)}">'
                   f'<span class="ec-buget__e">{e(eticheta)}</span>'
                   f'<span class="ec-buget__n">{len(n)}<small>apartamente</small></span>'
                   f'<span class="ec-buget__bar"><i style="width:{len(n)*100//bug_max}%"></i></span>'
                   f'<span class="ec-buget__d">{e(descriere)}</span>'
                   f'<span class="ec-buget__go">{ic("arrow-right")} Vezi lista</span></a>')

    # ---- 03: compartimentari ---------------------------------------------
    tipuri = ""
    for cod in sorted(grupe):
        us = grupe[cod]
        d = [u for u in us if u["status"] == "disponibil"]
        pm = min((x["pret_eur"] for x in d), default=None)
        tipuri += f"""<a class="ec-type ec-rv" href="{r}{slug_tip(cod)}">
          <div class="ec-type__plan">{plan_svg(us[0]['nr_camere'], cod, us[0]['su_utila'], compact=True)}</div>
          <div class="ec-type__code">{cod}</div>
          <div class="ec-type__rows">
            <div><span>Camere</span><b>{us[0]['nr_camere']}</b></div>
            <div><span>Suprafață</span><b>{min(u['su_utila'] for u in us):.0f}–{max(u['su_utila'] for u in us):.0f} m²</b></div>
            <div><span>Disponibile</span><b>{len(d)}</b></div>
          </div>
          <div class="ec-unit__price">{euro(pm) if pm else '—'}</div>
        </a>"""

    # ---- 04: etape --------------------------------------------------------
    etape = ""
    for cod in ("I", "II", "III"):
        us = [u for u in unitati if u["etapa"] == cod]
        if not us:
            continue
        d = [u for u in us if u["status"] == "disponibil"]
        blocuri = sorted({bloc(u["corp"]) for u in us}, key=int)
        pm = min((x["pret_eur"] for x in d), default=None)
        ocupat = round((len(us) - len(d)) * 100 / len(us))
        if d:
            stare = f'<b>{len(d)}</b> din {len(us)} încă disponibile'
            eticheta, clasa = f"{ocupat}% contractate", ""
        else:
            stare = f"{len(us)} apartamente, în curând în vânzare"
            eticheta, clasa, ocupat = "Nu a intrat în vânzare", " is-asteptare", 0
        etape += f"""<article class="ec-etp{clasa} ec-rv">
          <div class="ec-etp__top">
            <div><span class="ec-etp__k">Blocurile {blocuri[0]}–{blocuri[-1]}</span>
              <h3>Etapa {cod}</h3></div>
            <span class="ec-etp__p">{euro(pm) if pm else '—'}<small>de la</small></span>
          </div>
          <p class="ec-etp__s">{stare}</p>
          <div class="ec-etp__bar"><i data-w="{ocupat}"></i></div>
          <div class="ec-etp__f"><span>{eticheta}</span>
            {f'<a href="{lista}?etapa={cod}&amp;status=disponibil">{ic("arrow-right")} Vezi lista</a>' if d else ''}</div>
        </article>"""

    # ---- 05: cu curte proprie --------------------------------------------
    curti = [u for u in unitati if u["su_curte"] > 0]
    curti_d = [u for u in curti if u["status"] == "disponibil"]
    curte_min = min(u["su_curte"] for u in curti)
    curte_max = max(u["su_curte"] for u in curti)
    curte_pret = min((u["pret_eur"] for u in curti_d), default=None)

    # ---- 06: cel mai bun raport pret/suprafata ---------------------------
    alese = sorted(disp, key=lambda u: u["pret_eur"] / u["su_utila"])[:6]
    recomandate = "".join(card_unitate(u, r) for u in alese)

    why = "".join('<div class="ec-why__i ec-rv">' + _icon(pic) + "<h3>" + t + "</h3><p>" + d + "</p></div>"
                  for t, d, pic in ARGUMENTE)

    faq = "".join(f"<details><summary>{e(q)}</summary>"
                  f'<div class="ec-faq__a">{e(a)}</div></details>'
                  for q, a in FAQ_HUB)

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "CollectionPage",
             "name": "Apartamente noi în Iași, zona Păcurari",
             "url": "https://emerald-city.ro/apartamente-iasi/"},
            {"@type": "FAQPage",
             "mainEntity": [{"@type": "Question", "name": q,
                             "acceptedAnswer": {"@type": "Answer", "text": a}}
                            for q, a in FAQ_HUB]},
        ]}

    continut = f"""<section class="ec-phero">
  {imagine("hero-living", "", r, "100vw", eager=True)}
  <div class="ec-phero__veil"></div>
  <div class="ec-wrap ec-phero__in">
    <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Apartamente noi în Iași</nav>
    <p class="ec-eyebrow">Apartamente</p>
    <h1>Apartamente noi în Iași, zona Păcurari</h1>
    <p class="ec-phero__sub">
      {len(disp)} apartamente disponibile acum, cu 1, 2 și 3 camere, între {su_min:.0f} și
      {su_max:.0f} m². Toate se predau complet finisate, cu prețuri afișate și vânzare
      directă de la dezvoltator.
    </p>
    <div class="ec-phero__cta">
      <a class="ec-btn ec-btn--white" href="{lista}">{ic("table-list")} Lista apartamentelor</a>
      <a class="ec-btn ec-btn--outlight" href="#buget">{ic("tag")} Selecție după buget</a>
    </div>
  </div>
</section>

<div class="ec-figs-wrap">
  <div class="ec-wrap"><div class="ec-figs">{figuri}</div></div>
</div>

<div class="ec-wrap">
  <section class="ec-section" id="camere">
    <div class="ec-shead">
      <div><span class="ec-shead__n">01 — După camere</span>
        <h2>Apartamente <em>după numărul de camere</em></h2></div>
      <p class="ec-shead__p">
        Trei categorii, cu disponibilitatea și prețul de pornire actualizate din tabelul
        de vânzări.
      </p>
    </div>
    <div class="ec-silo" style="margin-top:2.5rem">{silo}</div>
  </section>

  <section class="ec-section" id="buget" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">02 — După buget</span>
        <h2>Apartamente <em>după buget</em></h2></div>
      <p class="ec-shead__p">
        Patru praguri de preț, cu numărul de apartamente din fiecare. Fiecare prag
        deschide lista filtrată corespunzător.
      </p>
    </div>
    <div class="ec-bugete" style="margin-top:2.5rem">{bugete}</div>
  </section>

  <section class="ec-section" id="compartimentari" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">03 — Compartimentări</span>
        <h2>{len(grupe)} planuri <em>de apartament</em></h2></div>
      <p class="ec-shead__p">
        De la garsonieră la 3 camere cu două grupuri sanitare. Fiecare cu planul,
        suprafețele și disponibilitatea proprie.
      </p>
    </div>
    <div class="ec-types" style="margin-top:2.5rem">{tipuri}</div>
  </section>

  <section class="ec-section" id="etape" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">04 — Etape</span>
        <h2>Cât a mai <em>rămas din fiecare etapă</em></h2></div>
      <p class="ec-shead__p">
        Ansamblul se construiește în trei etape. Procentul contractat se actualizează
        din tabelul de vânzări.
      </p>
    </div>
    <div class="ec-etps" style="margin-top:2.5rem">{etape}</div>
  </section>
</div>

<section class="ec-band" id="curte">
  <div class="ec-wrap">
    <div class="ec-section">
      <div class="ec-shead">
        <div><span class="ec-shead__n" style="color:var(--ec-brass)">05 — Curte proprie</span>
          <h2>{len(curti)} apartamente <em>cu curte la parter</em></h2></div>
        <p class="ec-shead__p">
          Între {curte_min:.0f} și {curte_max:.0f} m² de curte, în folosință exclusivă.
          Configurație rar întâlnită într-un ansamblu de această dimensiune.
        </p>
      </div>
      <div class="ec-figs" style="margin-top:2.5rem">
        <div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic("seedling")}</span>
          <span><b>{len(curti)}</b><em>În ansamblu</em></span></div>
        <div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic("key")}</span>
          <span><b>{len(curti_d)}</b><em>Disponibile acum</em></span></div>
        <div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic("ruler-combined")}</span>
          <span><b>{curte_min:.0f}–{curte_max:.0f} m²</b><em>Suprafață curte</em></span></div>
        <div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic("tag")}</span>
          <span><b>{euro(curte_pret) if curte_pret else '—'}</b><em>Preț de pornire</em></span></div>
      </div>
      <div class="ec-center" style="margin-top:2rem">
        <a class="ec-btn ec-btn--white" href="{lista}?extra=curte&amp;status=disponibil">{ic("table-list")} Apartamentele cu curte</a>
      </div>
    </div>
  </div>
</section>

<div class="ec-wrap">
  <section class="ec-section" id="recomandate">
    <div class="ec-shead">
      <div><span class="ec-shead__n">06 — Cel mai bun raport</span>
        <h2>Cele mai bune <em>prețuri pe metru pătrat</em></h2></div>
      <p class="ec-shead__p">
        Șase apartamente disponibile, selectate automat după cel mai mic preț pe metru pătrat
        din ansamblu.
      </p>
    </div>
    <div class="ec-cards" style="margin-top:2.5rem">{recomandate}</div>
    <div class="ec-center" style="margin-top:2rem">
      <a class="ec-btn" href="{lista}">{ic("table-list")} Toate cele {len(disp)} apartamente disponibile</a>
      <a class="ec-btn ec-btn--out" href="{r}compara/">{ic("code-compare")} Comparator de apartamente</a>
    </div>
  </section>

  <section class="ec-section" id="avantaje" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">07 — Avantaje</span>
        <h2>De ce <em>un apartament nou aici</em></h2></div>
      <p class="ec-shead__p">Patru argumente verificabile, nu promisiuni.</p>
    </div>
    <div class="ec-why" style="margin-top:2.5rem">{why}</div>
  </section>

  <section class="ec-section" id="dotari" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">08 — Dotări</span>
        <h2>Dotări <em>și facilități</em></h2></div>
      <p class="ec-shead__p">
        Dotările incluse în fiecare locuință și facilitățile de folosință comună.
      </p>
    </div>
    <div class="ec-dotari" style="margin-top:2.5rem">
      {panou_dotari("Dotări apartament", "house-chimney", DOTARI, "Incluse în preț")}
      {panou_dotari("Facilități ansamblu", "tree-city", FACILITATI, "Folosință comună")}
    </div>
    <div class="ec-center" style="margin-top:2rem">
      <a class="ec-btn ec-btn--out" href="{r}finisaje/">{ic("list-check")} Lista completă a dotărilor în preț</a>
    </div>
  </section>

  <section class="ec-section" id="intrebari" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">09 — Întrebări</span>
        <h2>Despre apartamente <em>și achiziție</em></h2></div>
      <p class="ec-shead__p">
        {len(FAQ_HUB)} întrebări despre suprafețe, prețuri și modul de cumpărare.
      </p>
    </div>
    <div class="ec-faq" style="margin-top:2.5rem">{faq}</div>
  </section>

  {showroom(r, "10")}
</div>

{cta_preturi(r, "living-01")}

<script>
/* barele de etapa cresc la intrarea in ecran */
(() => {{
  const b = [...document.querySelectorAll('.ec-etp__bar i[data-w]')];
  if (!b.length) return;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) {{
    b.forEach(x => {{ x.style.width = x.dataset.w + '%'; }});
    return;
  }}
  const o = new IntersectionObserver(es => es.forEach(x => {{
    if (!x.isIntersecting) return;
    x.target.style.width = x.target.dataset.w + '%';
    o.unobserve(x.target);
  }}), {{ threshold: .3 }});
  b.forEach(x => o.observe(x));
}})();

(() => {{
  const nr = [...document.querySelectorAll('.ec-fig b[data-num]')];
  if (!nr.length) return;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const urca = el => {{
    const tinta = parseFloat(el.dataset.num);
    const t0 = performance.now(), dur = 1100;
    const pas = t => {{
      const p = Math.min((t - t0) / dur, 1);
      el.textContent = Math.round(tinta * (1 - Math.pow(1 - p, 3))).toLocaleString('ro-RO');
      if (p < 1) requestAnimationFrame(pas);
    }};
    requestAnimationFrame(pas);
  }};
  const o = new IntersectionObserver(es => es.forEach(x => {{
    if (x.isIntersecting) {{ urca(x.target); o.unobserve(x.target); }}
  }}), {{ threshold: .4 }});
  nr.forEach(x => o.observe(x));
}})();
</script>"""

    return pagina("Apartamente noi în Iași, zona Păcurari | Emerald City",
                  f"{len(disp)} apartamente noi în Iași, zona Păcurari: 1, 2 și 3 camere, "
                  f"{su_min:.0f}–{su_max:.0f} m², de la {euro(p_min)}. Predare la cheie, direct "
                  "de la dezvoltator.",
                  continut, r, schema, "apartamente-iasi/")


# ==================================================== pagina de categorie
# Argumentele si intrebarile difera de la o categorie la alta: cine cumpara
# o garsoniera nu are aceleasi criterii cu cine cauta trei camere.
ARGUMENTE_CAT = {
 1: [("chart-line", "Cea mai cerută la închiriere",
      "Garsonierele au cel mai scurt timp de ocupare pe piața de închirieri din Iași, "
      "susținută de apropierea de centrul universitar."),
     ("tag", "Prag de intrare redus",
      "Cel mai mic preț de achiziție din ansamblu, cu aceleași finisaje și aceleași "
      "dotări comune ca la celelalte compartimentări."),
     ("maximize", "Zonă de zi deschisă",
      "Bucătăria integrată în living folosește eficient suprafața și lasă senzația de "
      "spațiu mai amplu decât o compartimentare închisă."),
     ("key", "Prima locuință",
      "Se încadrează în plafonul programului Noua Casă și poate fi achiziționată și "
      "prin credit ipotecar standard.")],
 2: [("people-roof", "Formatul cel mai echilibrat",
      "Living deschis spre bucătărie și dormitor separat — raportul cel mai bun între "
      "suprafață utilă și preț din tot ansamblul."),
     ("chart-line", "Cerere constantă",
      "Compartimentarea cu cea mai stabilă cerere, atât la vânzare cât și la închiriere, "
      "pe piața rezidențială din Iași."),
     ("seedling", "Curte proprie la parter",
      "Apartamentele de la parter au curte în folosință exclusivă, o configurație rar "
      "întâlnită la această suprafață."),
     ("layer-group", "Două compartimentări",
      "Tipurile 2A și 2B diferă prin dimensiunea dormitorului și prin spațiul de "
      "depozitare, la aceeași zonă de zi.")],
 3: [("people-roof", "Spațiu pentru o familie",
      "Două dormitoare, două grupuri sanitare și zonă de zi generoasă — configurația "
      "care acoperă nevoile unei familii pe termen lung."),
     ("bath", "Două grupuri sanitare",
      "Un al doilea grup sanitar elimină punctul de blocaj de dimineață, cel mai frecvent "
      "reproș adus apartamentelor de trei camere mai vechi."),
     ("briefcase", "Cameră pentru birou",
      "Tipul 3B include o a treia cameră care poate fi folosită ca birou, fără să reducă "
      "spațiul de locuit."),
     ("ruler-combined", "Cele mai mari suprafețe",
      "Cele mai generoase apartamente din ansamblu, cu balcoane pe măsură și curte la "
      "parter.")],
}

FAQ_CAT = {
 1: [("Ce suprafață are o garsonieră?",
      "Între 37 și 39 m² suprafață utilă, cu balcon. Cele de la parter au și curte proprie."),
     ("Sunt potrivite pentru investiție?",
      "Da. Garsonierele au cel mai scurt timp de ocupare pe piața de închirieri din Iași, "
      "iar pagina de investiție include un calculator de randament și de amortizare."),
     ("Se încadrează în programul Noua Casă?",
      "Prețurile de pornire se situează sub plafonul programului. Încadrarea exactă se "
      "verifică la data achiziției, împreună cu banca."),
     ("Ce compartimentare au?",
      "Tipul 1A: zonă de zi deschisă, cu bucătăria integrată în living, grup sanitar și "
      "spațiu de depozitare."),
     ("Există garsoniere cu curte proprie?",
      "Da, cele de la parter. Curtea este în folosință exclusivă, cu pardoseală exterioară "
      "executată și priză proprie."),
     ("Se poate cumpăra prin credit ipotecar?",
      "Da, cu credit ipotecar standard sau, în limita plafonului, prin programul Noua Casă. "
      "Avansul minim la antecontract este de 15%."),
     ("Ce cheltuieli de întreținere are o garsonieră?",
      "Consumurile sunt contorizate individual, iar încălzirea în pardoseală cu centrală în "
      "condensație menține costurile reduse. Cheltuielile comune se stabilesc prin asociația "
      "de proprietari."),
     ("Ce chirie se poate obține?",
      "Estimarea depinde de etaj, de dotările contractate și de momentul închirierii. Pagina "
      "de investiție include un calculator care pornește de la prețul fiecărei unități și "
      "de la chiriile practicate în zonă.")],
 2: [("Ce diferență este între tipurile 2A și 2B?",
      "2B are dormitorul mai generos și spațiu suplimentar de depozitare, la aceeași "
      "configurație a zonei de zi. Suprafețele diferă cu câțiva metri pătrați."),
     ("Ce suprafață are un apartament de 2 camere?",
      "Între 51 și 61 m² suprafață utilă, în funcție de compartimentare. Toate au balcon."),
     ("Care sunt cele cu curte proprie?",
      "Cele de la parter. Curțile au între 13 și 51 m² și sunt în folosință exclusivă."),
     ("Este potrivit pentru o familie cu un copil?",
      "Da. Dormitorul separat și zona de zi deschisă acoperă nevoile unei familii tinere, "
      "iar ansamblul are loc de joacă și spații verzi amenajate."),
     ("Ce înseamnă boxă de depozitare?",
      "Un spațiu propriu în al doilea demisol, pentru bagaje, biciclete și lucrurile de "
      "sezon. Se contractează separat, în limita disponibilității din bloc."),
     ("Care este avansul la antecontract?",
      "15% din preț, la semnarea antecontractului la notar. Diferența se achită la predare "
      "sau conform graficului agreat."),
     ("Când se predau apartamentele de 2 camere?",
      "În funcție de etapa în care se află blocul. Termenul de predare se înscrie în "
      "antecontract, pentru fiecare unitate."),
     ("Are loc de parcare inclus?",
      "Locul de parcare se contractează separat, subteran sau la suprafață. Ansamblul are "
      "940 de locuri, dintre care 258 subterane.")],
 3: [("Ce suprafață are un apartament de 3 camere?",
      "Între 69 și 81 m² suprafață utilă, în funcție de compartimentare. Toate au balcon."),
     ("Ce diferență este între tipurile 3A și 3B?",
      "3A are bucătărie închisă și două dormitoare. 3B are living deschis, un dormitor și "
      "o a treia cameră care poate fi folosită ca birou. Ambele au două grupuri sanitare."),
     ("Au două grupuri sanitare?",
      "Da, ambele compartimentări de trei camere includ două grupuri sanitare complet "
      "finisate și echipate."),
     ("Există apartamente de 3 camere cu curte?",
      "Da, cele de la parter. Curțile au între 13 și 51 m², în folosință exclusivă."),
     ("Câte locuri de parcare pot contracta?",
      "Numărul de locuri care pot fi contractate pentru un apartament se stabilește la "
      "biroul de vânzări, în funcție de disponibilitatea din blocul respectiv."),
     ("Se pot uni sau modifica camerele?",
      "Modificările nestructurale se analizează la biroul de vânzări, în funcție de faza de "
      "execuție a blocului. Pereții de rezistență nu se modifică."),
     ("Ce orientare au apartamentele de 3 camere?",
      "Diferă de la o unitate la alta; orientarea fiecărui apartament este afișată în lista "
      "de disponibilitate și în pagina lui."),
     ("Ce suprafață are balconul?",
      "Balcoanele apartamentelor de trei camere sunt cele mai generoase din ansamblu. "
      "Suprafața exactă este afișată în pagina fiecărei unități.")],
}


def pagina_categorie(nr, unitati, grupe):
    r = "../../"
    c = CATEGORII[nr]
    us = [u for u in unitati if u["nr_camere"] == nr]
    disp = [u for u in us if u["status"] == "disponibil"]
    su_min, su_max = min(u["su_utila"] for u in us), max(u["su_utila"] for u in us)
    pmin = min((u["pret_eur"] for u in disp), default=None)
    ppm = [u["pret_eur"] / u["su_utila"] for u in disp]
    tipuri = sorted({u["tip_apartament"] for u in us})
    lista = f"{r}apartamente-iasi/disponibilitate/?camere={nr}&amp;status=disponibil"

    figuri = "".join(
        f'<div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic(pic)}</span>'
        f'<span><b{attr}>{e(val)}</b><em>{e(et)}</em></span></div>'
        for val, et, pic, attr in [
            (str(len(disp)), "Disponibile acum", "key", f' data-num="{len(disp)}"'),
            (f"{su_min:.0f}–{su_max:.0f} m²", "Suprafață utilă", "ruler-combined", ""),
            (euro(pmin) if pmin else "—", "Preț de pornire", "tag", ""),
            (f"{min(ppm):.0f} €/m²" if ppm else "—", "De la", "calculator", ""),
        ])

    # ---- compartimentarile categoriei -------------------------------------
    carduri = ""
    NUME_CAMERA = {"living-01": "Living", "living-02": "Living", "dining-01": "Dining",
                   "bucatarie-01": "Bucătărie", "dormitor-01": "Dormitor",
                   "dormitor-02": "Dormitor", "baie-01": "Grup sanitar", "hol-01": "Hol",
                   "hero-living": "Living"}
    for k, cod in enumerate(tipuri):
        tu = grupe[cod]
        td = [u for u in tu if u["status"] == "disponibil"]
        tp = min((u["pret_eur"] for u in td), default=None)
        img = GALERIE_TIP.get(cod, ["living-01"])[0]
        carduri += f"""<article class="ec-tipc ec-rv{' is-invers' if k % 2 else ''}">
          <figure class="ec-tipc__f">
            {imagine(img, f"Apartament tip {cod} la Emerald City", r, "(min-width: 62rem) 52vw, 100vw")}
            <span class="ec-tipc__badge">{len(td)} disponibile</span>
          </figure>
          <div class="ec-tipc__b">
            <span class="ec-tipc__k">Compartimentare</span>
            <h3>Tip {cod}</h3>
            <p>{e(DESC_TIP.get(cod, ''))}</p>
            <div class="ec-tipc__row">
              <figure class="ec-tipc__p">{plan_svg(nr, cod, sum(u['su_utila'] for u in tu) / len(tu), compact=True)}</figure>
              <dl>
                <div><dt>Suprafață utilă</dt><dd>{min(u['su_utila'] for u in tu):.0f}–{max(u['su_utila'] for u in tu):.0f} m²</dd></div>
                <div><dt>Disponibile</dt><dd>{len(td)} din {len(tu)}</dd></div>
                <div><dt>Preț de pornire</dt><dd>{euro(tp) if tp else '—'}</dd></div>
              </dl>
            </div>
            <div class="ec-tipc__cta">
              <a class="ec-btn" href="{r}{slug_tip(cod)}">{ic("compass-drafting")} Planul complet</a>
              <a class="ec-btn ec-btn--out" href="{lista}&amp;tip={cod}">{ic("table-list")} Unitățile de tip {cod}</a>
            </div>
          </div>
        </article>"""

    # ---- galeria categoriei -----------------------------------------------
    imagini, vazute = [], set()
    for cod in tipuri:
        for x in GALERIE_TIP.get(cod, []):
            if x not in vazute:
                vazute.add(x); imagini.append(x)
    imagini = imagini[:3] if len(imagini) >= 3 else imagini
    et_gal = f"{c['titlu']} în Iași, zona Păcurari"
    galerie = "".join(
        f'<figure class="ec-pgal__i ec-rv">'
        f'{imagine(x, f"{NUME_CAMERA.get(x, chr(73) + chr(110) + chr(116) + chr(101) + chr(114) + chr(105) + chr(111) + chr(114))} — {et_gal}, Emerald City", r, "(min-width: 70rem) 33vw, 100vw")}'
        f'<figcaption class="ec-pgal__c"><b>{e(NUME_CAMERA.get(x, "Interior"))}</b>'
        f'<span>{e(c["titlu"])}</span></figcaption></figure>'
        for x in imagini)

    # ---- selectie rapida: etaj si orientare -------------------------------
    et_lista = []
    for etj in sorted({u["etaj"] for u in us}):
        n = [u for u in disp if u["etaj"] == etj]
        if n:
            et_lista.append((etaj_txt(etj), len(n),
                             f"{lista}&amp;etaj={etj}",
                             "house-chimney" if etj == 0 else "building"))
    DOTARI_FILTRU = [
        ("Curte proprie",       "curte",   "seedling",       lambda x: x["su_curte"] > 0),
        ("Balcon",              "balcon",  "sun",            lambda x: x["su_balcon"] > 0),
        ("Boxă de depozitare",  "boxa",    "box-archive",    lambda x: x["boxa_disponibila"] == "da"),
        ("Parcare subterană",   "parcare", "square-parking", lambda x: x["parcare_subterana"] == "da"),
    ]
    dot_lista = []
    for eticheta, cheie, pict, testeaza in DOTARI_FILTRU:
        n = [u for u in disp if testeaza(u)]
        if n:
            dot_lista.append((eticheta, len(n), f"{lista}&amp;extra={cheie}", pict))

    def panou_filtru(titlu, pictograma, eticheta, randuri):
        li = "".join(
            f'<li><a href="{x[2]}"><span class="ec-dot__i">{ic(x[3])}</span>'
            f'<span>{e(x[0])}</span><b>{x[1]}</b></a></li>' for x in randuri)
        return (f'<div class="ec-dot ec-rv">'
                f'<div class="ec-dot__h"><span class="ec-dot__c">{ic(pictograma)}</span>'
                f'<span class="ec-dot__tx"><b>{e(titlu)}</b><em>{e(eticheta)}</em></span></div>'
                f'<ul class="ec-dot__l ec-dot__l--link">{li}</ul></div>')

    # ---- tabelul complet ---------------------------------------------------
    randuri = "".join(f"""<tr class="{'is-sold' if u['status'] != 'disponibil' else ''}">
      <td data-et="Cod"><a href="{r}apartamente-iasi/{u['unit_id'].lower()}/">{e(u['unit_id'])}</a></td>
      <td data-et="Bloc">{bloc(u['corp'])}</td><td data-et="Etaj">{etaj_txt(u['etaj'])}</td>
      <td data-et="Tip">{u['tip_apartament']}</td>
      <td class="num" data-et="Suprafață">{mp(u['su_utila'])}</td>
      <td data-et="Orientare">{u['orientare']}</td>
      <td class="num" data-et="Preț">{euro(u['pret_eur'])}</td>
      <td class="num" data-et="Preț/m²">{round(u['pret_eur'] / u['su_utila'])} €/m²</td>
      <td class="st" data-et="Stare"><span class="ec-tag ec-tag--{u['status']}">{STATUS_ET[u['status']]}</span></td>
    </tr>""" for u in sorted(us, key=lambda x: (x["status"] != "disponibil", x["pret_eur"]))[:40])

    argumente = "".join(
        f'<div class="ec-why__i ec-rv">{ic(pic)}<h3>{e(t)}</h3><p>{e(d)}</p></div>'
        for pic, t, d in ARGUMENTE_CAT[nr])

    faq = "".join(f"<details><summary>{e(q)}</summary>"
                  f'<div class="ec-faq__a">{e(a)}</div></details>'
                  for q, a in FAQ_CAT[nr])

    curti = [u for u in disp if u["su_curte"] > 0]
    spot_curte = ""
    if curti:
        cmin = min(u["su_curte"] for u in curti)
        cmax = max(u["su_curte"] for u in curti)
        cpret = min(u["pret_eur"] for u in curti)
        spot_curte = f"""<section class="ec-section" id="curte" style="padding-block:0 var(--ec-section)">
    <div class="ec-spot">
      <div class="ec-spot__b">
        <p class="ec-eyebrow" style="color:var(--ec-brass)">05 — Curte proprie</p>
        <h2>{len(curti)} apartamente cu curte, la parter</h2>
        <p>
          Curte în folosință exclusivă, între {cmin:.0f} și {cmax:.0f} m², cu pardoseală
          exterioară executată și priză proprie. Configurație rar întâlnită la această
          suprafață.
        </p>
        <ul class="ec-spot__list">
          <li>Acces direct din living, fără scări</li>
          <li>Pardoseală exterioară antiderapantă, montată</li>
          <li>Balustradă și priză exterioară incluse</li>
          <li>Preț de pornire {euro(cpret)}</li>
        </ul>
        <div class="ec-spot__cta">
          <a class="ec-btn ec-btn--white" href="{lista}&amp;extra=curte">{ic("table-list")} Cele {len(curti)} apartamente</a>
        </div>
      </div>
      <figure>{imagine("dining-01", "Apartament cu curte proprie la parter", r, "(min-width: 60rem) 48vw, 100vw")}</figure>
    </div>
  </section>"""

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "CollectionPage", "name": c["h1"],
             "url": f"https://emerald-city.ro/apartamente-iasi/{c['slug']}/"},
            {"@type": "FAQPage",
             "mainEntity": [{"@type": "Question", "name": q,
                             "acceptedAnswer": {"@type": "Answer", "text": a}}
                            for q, a in FAQ_CAT[nr]]},
        ]}

    continut = f"""<section class="ec-phero">
  {imagine(c['img'], "", r, "100vw", eager=True)}
  <div class="ec-phero__veil"></div>
  <div class="ec-wrap ec-phero__in">
    <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>
      <a href="{r}apartamente-iasi/">Apartamente</a><span>/</span>{e(c['titlu'])}</nav>
    <p class="ec-eyebrow">{e(c['titlu'])}</p>
    <h1>{e(c['h1'])}</h1>
    <p class="ec-phero__sub">{e(c['lead'])}</p>
    <div class="ec-phero__cta">
      <a class="ec-btn ec-btn--white" href="#unitati">{ic("table-list")} Cele {len(disp)} apartamente disponibile</a>
      <a class="ec-btn ec-btn--outlight" href="#compartimentari">{ic("compass-drafting")} Compartimentări</a>
    </div>
  </div>
</section>

<div class="ec-figs-wrap">
  <div class="ec-wrap"><div class="ec-figs">{figuri}</div></div>
</div>

<div class="ec-wrap">
  <section class="ec-section" id="compartimentari">
    <div class="ec-shead">
      <div><span class="ec-shead__n">01 — Compartimentări</span>
        <h2>{len(tipuri)} tip{"" if len(tipuri) == 1 else "uri"} de apartament <em>disponibil{"" if len(tipuri) == 1 else "e"}</em></h2></div>
      <p class="ec-shead__p">
        Suprafețele, disponibilitatea și prețul de pornire pentru fiecare compartimentare.
      </p>
    </div>
    <div class="ec-tipuri" style="margin-top:2.5rem">{carduri}</div>
  </section>

  <section class="ec-section" id="galerie" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">02 — Galerie</span>
        <h2>Apartamentul-model, <em>în imagini</em></h2></div>
      <p class="ec-shead__p">
        Randări din apartamentele-model, cu finisajele incluse în preț.
      </p>
    </div>
    <div class="ec-pgal ec-pgal--3" style="margin-top:2.5rem">{galerie}</div>
  </section>

  <section class="ec-section" id="selectie" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">03 — Selecție rapidă</span>
        <h2>Selecție <em>după etaj și dotări</em></h2></div>
      <p class="ec-shead__p">
        Fiecare rând deschide lista filtrată. Numărul reprezintă apartamentele
        disponibile la data actualizării.
      </p>
    </div>
    <div class="ec-dotari" style="margin-top:2.5rem">
      {panou_filtru("După etaj", "building", "Nivelul apartamentului", et_lista)}
      {panou_filtru("După dotări", "list-check", "Curte, boxă, parcare", dot_lista)}
    </div>
  </section>

  <section class="ec-section" id="unitati" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">04 — Unități</span>
        <h2>Toate apartamentele <em>de {camere_txt(nr)}</em></h2></div>
      <p class="ec-shead__p">
        Primele 40 de unități, ordonate după preț. Lista completă, cu filtre,
        este în secțiunea de disponibilitate.
      </p>
    </div>
    <div class="ec-table" style="margin-top:2.5rem">
      <table>
        <caption class="ec-sr">Apartamente de {camere_txt(nr)}</caption>
        <thead><tr><th scope="col">Cod</th><th scope="col">Bloc</th><th scope="col">Etaj</th>
          <th scope="col">Tip</th><th scope="col">Suprafață</th><th scope="col">Orientare</th>
          <th scope="col">Preț</th><th scope="col">Preț/m²</th><th scope="col">Stare</th></tr></thead>
        <tbody>{randuri}</tbody>
      </table>
    </div>
    <div class="ec-center" style="margin-top:2rem">
      <a class="ec-btn" href="{lista}">{ic("table-list")} Lista completă, cu filtre</a>
      {f'<a class="ec-btn ec-btn--out" href="{lista}&amp;extra=curte">{ic("seedling")} Cele {len(curti)} cu curte proprie</a>' if curti else ''}
    </div>
  </section>
</div>

<div class="ec-wrap">
  {spot_curte}
</div>

<section class="ec-band" id="avantaje">
  <div class="ec-wrap">
    <div class="ec-section">
      <div class="ec-shead">
        <div><span class="ec-shead__n" style="color:var(--ec-brass)">06 — Avantaje</span>
          <h2>De ce <em>{e(c['titlu'].lower())}</em></h2></div>
        <p class="ec-shead__p">
          Patru criterii pentru care această compartimentare este cea potrivită.
        </p>
      </div>
      <div class="ec-why" style="margin-top:2.5rem">{argumente}</div>
    </div>
  </div>
</section>

<div class="ec-wrap">
  <section class="ec-section" id="intrebari">
    <div class="ec-shead">
      <div><span class="ec-shead__n">07 — Întrebări</span>
        <h2>Despre <em>{e(c['titlu'].lower())}</em></h2></div>
      <p class="ec-shead__p">
        {len(FAQ_CAT[nr])} întrebări despre suprafețe, compartimentări, dotări și condiții.
      </p>
    </div>
    <div class="ec-faq" style="margin-top:2.5rem">{faq}</div>
    <div class="ec-center" style="margin-top:2rem">
      <a class="ec-btn ec-btn--out" href="{r}finisaje/">{ic("list-check")} Dotări incluse</a>
      <a class="ec-btn ec-btn--out" href="{r}investitie-apartamente-iasi/">{ic("chart-line")} Calculator de randament</a>
    </div>
  </section>

  <section class="ec-section" style="padding-block:0 var(--ec-section)">
    {cta_dublu(r, c['slug'])}
  </section>

  {showroom(r, "08")}
</div>

<script>
(() => {{
  const nr = [...document.querySelectorAll('.ec-fig b[data-num]')];
  if (!nr.length || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const o = new IntersectionObserver(es => es.forEach(x => {{
    if (!x.isIntersecting) return;
    const el = x.target, tinta = parseFloat(el.dataset.num), t0 = performance.now();
    const pas = t => {{
      const p = Math.min((t - t0) / 1100, 1);
      el.textContent = Math.round(tinta * (1 - Math.pow(1 - p, 3))).toLocaleString('ro-RO');
      if (p < 1) requestAnimationFrame(pas);
    }};
    requestAnimationFrame(pas);
    o.unobserve(el);
  }}), {{ threshold: .4 }});
  nr.forEach(x => o.observe(x));
}})();
</script>"""

    return pagina(f"{c['titlu']} în Iași — {len(disp)} libere | Emerald City",
                  f"{len(disp)} {c['titlu'].lower()} disponibile în Iași, zona Păcurari, "
                  f"între {su_min:.0f} și {su_max:.0f} m², de la {euro(pmin) if pmin else '—'}. "
                  "Predare la cheie, vânzare directă de la dezvoltator.",
                  continut, r, schema, f"apartamente-iasi/{c['slug']}/")


# ======================================================= investitie ==
def chirie_estimata(su):
    """Estimare de piata pentru zona Pacurari, ~6,2 EUR/mp util."""
    return int(round(su * 6.2 / 10) * 10)


FAQ_INV = [
    ("Ce randament brut au apartamentele din Emerald City?",
     "La prețurile de listare și la chiriile observate în zona Păcurari, randamentul brut estimat "
     "se situează între aproximativ 4,5% și 5,5% pe an, cel mai ridicat fiind la garsoniere. "
     "Cifrele sunt estimări, nu valori garantate."),
    ("Cum este estimată chiria lunară?",
     "Chiria este calculată la aproximativ 6,2 €/m² util pe lună, o medie observată pentru "
     "locuințe noi, finisate la cheie, în zona Păcurari. Valoarea reală depinde de mobilare, "
     "etaj, orientare și de momentul închirierii."),
    ("Care este diferența dintre randamentul brut și cel net?",
     "Randamentul brut împarte chiria anuală la prețul de achiziție. Cel net scade perioadele "
     "neînchiriate, impozitul pe venit, cheltuielile de administrare și reparațiile. Calculatorul "
     "aplică un cost de aproximativ 8% și un grad de neocupare configurabil."),
    ("Ce costuri nu apar în calculator?",
     "Taxele notariale, intabularea, TVA-ul aferent, mobilarea și echiparea inițială, precum și "
     "eventualul comision al unei firme de administrare. Pentru o garsonieră, mobilarea completă "
     "pornește în general de la câteva mii de euro."),
    ("Apartamentele se predau finisate, gata de închiriat?",
     "Da. Predarea se face la cheie: parchet, gresie, faianță, obiecte sanitare, centrală proprie, "
     "încălzire în pardoseală, uși interioare și tâmplărie cu geam tripan. Rămân de adăugat "
     "mobilierul și electrocasnicele."),
    ("Pot fi achiziționate mai multe unități în același bloc?",
     "Da. Pentru achiziții multiple, echipa de vânzări poate pregăti o selecție de unități pe "
     "același palier sau în același bloc, cu o propunere comercială dedicată, în showroom."),
    ("Ce cerere de închiriere există în zona Păcurari?",
     "Iașul este al doilea centru universitar din țară, cu peste 60.000 de studenți, la care se "
     "adaugă angajații din IT și servicii. Păcurari se află la 4,8 km de centru și la circa 5 km "
     "de Copou, pe un culoar de transport public direct."),
    ("Informațiile de pe această pagină reprezintă consultanță de investiții?",
     "Nu. Cifrele sunt estimări bazate pe prețuri de listare și pe chirii observate în zonă și au "
     "rol informativ. Decizia de achiziție aparține cumpărătorului, care poate consulta un "
     "specialist financiar sau fiscal independent."),
]


def pagina_investitie(unitati):
    r = "../"
    disp = [u for u in unitati if u["status"] == "disponibil"]
    gars = [u for u in disp if u["nr_camere"] == 1]
    ref = min(gars, key=lambda u: u["pret_eur"]) if gars else min(disp, key=lambda u: u["pret_eur"])
    ch_ref = chirie_estimata(ref["su_utila"])
    rand = lambda u: chirie_estimata(u["su_utila"]) * 12 / u["pret_eur"] * 100
    r_max = max(rand(u) for u in disp)
    r_min = min(rand(u) for u in disp)
    ch_min = min(chirie_estimata(u["su_utila"]) for u in disp)

    # cele mai bune randamente estimate
    scor = sorted(disp, key=lambda u: -rand(u))[:12]
    randuri = ""
    for u in scor:
        ch = chirie_estimata(u["su_utila"])
        randuri += f"""<tr>
          <td><a href="{r}apartamente-iasi/{u['unit_id'].lower()}/"><b>{e(u['unit_id'])}</b></a></td>
          <td>{camere_txt(u['nr_camere'])} · tip {e(u['tip_apartament'])}</td>
          <td>{etaj_txt(u['etaj'])}, bloc {bloc(u['corp'])}</td>
          <td class="num">{mp(u['su_utila'])}</td>
          <td class="num"><b>{euro(u['pret_eur'])}</b></td>
          <td class="num">{euro(ch)}</td>
          <td class="num"><b style="color:var(--ec-emerald)">{f"{rand(u):.2f}".replace(".", ",")}%</b></td>
        </tr>"""

    figuri = "".join(
        f'<div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic(pic)}</span>'
        f'<span><b>{e(val)}</b><em>{e(et)}</em></span></div>'
        for val, et, pic in [
            (str(len(disp)), "Apartamente disponibile", "key"),
            (f"până la {r_max:.1f}%".replace(".", ","), "Randament brut estimat", "percent"),
            (f"de la {euro(ch_min)}", "Chirie lunară estimată", "house-chimney"),
            (euro(min(u["pret_eur"] for u in disp)), "Preț de pornire", "tag"),
        ])

    # trei scenarii, cate unul pe numar de camere
    scen = ""
    profil = {1: ("Garsonieră", "Student sau tânăr angajat", "user-graduate"),
              2: ("2 camere", "Cuplu tânăr sau doi colegi", "user-group"),
              3: ("3 camere", "Familie sau relocare corporate", "people-roof")}
    for n in (1, 2, 3):
        lot = [u for u in disp if u["nr_camere"] == n]
        if not lot:
            continue
        u = min(lot, key=lambda x: x["pret_eur"])
        ch = chirie_estimata(u["su_utila"])
        y = rand(u)
        net = ch * 12 * .92 * .92 / u["pret_eur"] * 100
        titlu, cine, pic = profil[n]
        scen += f"""<article class="ec-scen ec-rv">
      <div class="ec-scen__h"><span class="ec-scen__ic">{ic(pic)}</span>
        <span><b>{titlu}</b><em>{cine}</em></span></div>
      <div class="ec-scen__big"><b>{y:.1f}%</b><span>randament brut estimat</span></div>
      <ul class="ec-scen__l">
        <li><span>Unitate de referință</span><b>{e(u['unit_id'])} · {mp(u['su_utila'])}</b></li>
        <li><span>Preț de achiziție</span><b>{euro(u['pret_eur'])}</b></li>
        <li><span>Chirie lunară estimată</span><b>{euro(ch)}</b></li>
        <li><span>Randament net orientativ</span><b>{net:.1f}%</b></li>
        <li><span>Amortizare orientativă</span><b>{u['pret_eur'] / (ch * 12 * .92 * .92):.0f} ani</b></li>
        <li><span>Disponibile în această categorie</span><b>{len(lot)}</b></li>
      </ul>
      <a class="ec-scen__go" href="{r}investitie-apartamente-iasi/?pret={u['pret_eur']}&amp;su={u['su_utila']}#calculator">
        {ic("calculator")} Simulare cu aceste valori</a>
    </article>""".replace(f"{y:.1f}%", f"{y:.1f}%".replace(".", ",")).replace(f"{net:.1f}%", f"{net:.1f}%".replace(".", ","))

    argumente = "".join(
        f'<div class="ec-why__i ec-rv">{ic(pic)}<h3>{e(t)}</h3><p>{e(d)}</p></div>'
        for pic, t, d in [
            ("graduation-cap", "Cerere constantă de chirii",
             "Al doilea centru universitar din țară și un pol IT în creștere. Cererea pentru "
             "garsoniere și apartamente cu 2 camere nu depinde de un singur angajator."),
            ("route", "4,8 km de centru, 5 km de Copou",
             "Transport public direct spre universități și spre centrul orașului. Zona Păcurari "
             "este printre primele căutate de chiriașii care lucrează sau studiază în nord-vestul Iașului."),
            ("building-circle-check", "Clădire nouă, costuri de exploatare mici",
             "Anvelopă termică conform normelor actuale, centrală proprie și contorizare "
             "individuală: cheltuieli lunare previzibile și reparații rare în primii ani."),
            ("handshake", "Direct de la dezvoltator",
             "Fără comision de intermediere la achiziție și cu preț afișat pentru fiecare unitate. "
             "Economia se regăsește direct în randament."),
        ])

    ipoteze = panou_dotari("Metoda de calcul", "calculator", [
        ("house-chimney", "Chirie estimată la circa 6,2 €/m² util pe lună"),
        ("calendar-days", "Grad de neocupare configurabil, implicit 8% pe an"),
        ("percent", "Cheltuieli de administrare, impozit și reparații: circa 8%"),
        ("scale-balanced", "Randament brut = chirie anuală / preț de achiziție"),
        ("hourglass-half", "Amortizare = preț de achiziție / venit net anual"),
        ("circle-info", "Taxe notariale, mobilare și TVA nu sunt incluse"),
    ], "6 ipoteze")

    faq = "".join(f"<details><summary>{e(q)}</summary>"
                  f'<div class="ec-faq__a">{e(a)}</div></details>'
                  for q, a in FAQ_INV)

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebPage", "name": "Investiție în apartamente noi în Iași",
             "url": "https://emerald-city.ro/investitie-apartamente-iasi/"},
            {"@type": "FAQPage",
             "mainEntity": [{"@type": "Question", "name": q,
                             "acceptedAnswer": {"@type": "Answer", "text": a}}
                            for q, a in FAQ_INV]},
        ]}

    continut = f"""<section class="ec-phero">
  {imagine("living-01", "", r, "100vw", eager=True)}
  <div class="ec-phero__veil"></div>
  <div class="ec-wrap ec-phero__in">
    <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Investiție</nav>
    <p class="ec-eyebrow">Investiție și randament</p>
    <h1>Investiție în apartamente noi, în Iași</h1>
    <p class="ec-phero__sub">
      {len(gars)} de garsoniere și {len(disp) - len(gars)} de apartamente cu 2 și 3 camere disponibile,
      la prețuri afișate. Calculator de randament, selecția celor mai bune unități și
      costurile care trebuie luate în calcul înainte de achiziție.
    </p>
    <div class="ec-phero__cta">
      <a class="ec-btn ec-btn--white" href="#calculator">{ic("calculator")} Calculator de randament</a>
      <a class="ec-btn ec-btn--outlight" href="#selectie">{ic("chart-line")} Cele mai bune randamente</a>
    </div>
  </div>
</section>

<div class="ec-figs-wrap">
  <div class="ec-wrap"><div class="ec-figs">{figuri}</div></div>
</div>

<div class="ec-wrap">
  <section class="ec-section" id="calculator" style="padding-block:var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">01 — Calculator</span>
        <h2>Randamentul <em>unei achiziții</em></h2></div>
      <p class="ec-shead__p">
        Prețul, chiria și gradul de neocupare se ajustează liber. Rezultatele se recalculează
        instant și sunt orientative.
      </p>
    </div>
    <div class="ec-inv2" style="margin-top:2.5rem">
      {calc_randament(ref['pret_eur'], ch_ref)}
      {ipoteze}
    </div>
  </section>

  <section class="ec-section" id="scenarii" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">02 — Scenarii</span>
        <h2>Trei profiluri <em>de închiriere</em></h2></div>
      <p class="ec-shead__p">
        Pentru fiecare număr de camere, cea mai accesibilă unitate disponibilă și cifrele
        ei orientative.
      </p>
    </div>
    <div class="ec-scen3" style="margin-top:2.5rem">{scen}</div>
  </section>

  <section class="ec-section" id="selectie" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">03 — Selecție</span>
        <h2>Top 12 <em>randamente estimate</em></h2></div>
      <p class="ec-shead__p">
        Ordonate după randamentul brut. Fiecare cod deschide pagina unității, cu plan,
        galerie și simulare de rată.
      </p>
    </div>
    <div class="ec-table" style="margin-top:2.5rem">
      <table>
        <caption class="ec-sr">Apartamente ordonate după randamentul brut estimat</caption>
        <thead><tr><th>Cod</th><th>Compartimentare</th><th>Poziție</th><th>Suprafață</th>
          <th>Preț</th><th>Chirie estimată</th><th>Randament brut</th></tr></thead>
        <tbody>{randuri}</tbody>
      </table>
    </div>
    <div class="ec-inv__foot">
      <p class="ec-calc__note" style="margin:0">
        Chirii estimate la aproximativ 6,2 €/m² util pentru zona Păcurari. Valorile nu sunt
        garantate și nu constituie consultanță de investiții.
      </p>
      <a class="ec-btn ec-btn--out" href="{r}apartamente-iasi/disponibilitate/?status=disponibil&amp;camere=1">
        {ic("table-list")} Toate garsonierele disponibile</a>
    </div>
  </section>
</div>

<section class="ec-band" id="argumente">
  <div class="ec-wrap">
    <div class="ec-section">
      <div class="ec-shead">
        <div><span class="ec-shead__n" style="color:var(--ec-brass)">04 — Argumente</span>
          <h2>De ce Iași <em>și de ce Păcurari</em></h2></div>
        <p class="ec-shead__p">Patru factori care susțin cererea de închiriere pe termen lung.</p>
      </div>
      <div class="ec-why" style="margin-top:2.5rem">{argumente}</div>
    </div>
  </div>
</section>

<div class="ec-wrap">
  <section class="ec-section" id="pasi" style="padding-block:var(--ec-section) 0">
    <div class="ec-shead">
      <div><span class="ec-shead__n">05 — Parcurs</span>
        <h2>De la selecție <em>la primul chiriaș</em></h2></div>
      <p class="ec-shead__p">Trei etape, cu documente clare și termene cunoscute de la început.</p>
    </div>
    <div class="ec-steps" style="margin-top:2.5rem">
      <div class="ec-step ec-rv">
        <div class="ec-step__n">01</div>
        <h3>Selecție și rezervare</h3>
        <p>Alegerea unității din lista de disponibilitate, vizionarea apartamentului-model
           și rezervarea, cu blocarea prețului afișat.</p>
      </div>
      <div class="ec-step ec-rv" data-d="1">
        <div class="ec-step__n">02</div>
        <h3>Antecontract și plată</h3>
        <p>Avans la antecontract, apoi tranșe legate de stadiul lucrărilor. Plata se poate face
           din fonduri proprii sau prin credit ipotecar.</p>
      </div>
      <div class="ec-step ec-rv" data-d="2">
        <div class="ec-step__n">03</div>
        <h3>Predare la cheie și închiriere</h3>
        <p>Recepția apartamentului finisat, intabularea și, la cerere, recomandarea unui
           partener de administrare pentru închiriere.</p>
      </div>
    </div>
  </section>

  <section class="ec-section" id="informare" style="padding-block:var(--ec-section) 0">
    <div class="ec-shead">
      <div><span class="ec-shead__n">06 — Informare</span>
        <h2>Ce trebuie <em>luat în calcul</em></h2></div>
      <p class="ec-shead__p">Elementele care diferențiază o estimare de rezultatul real.</p>
    </div>
    <div class="ec-inv2" style="margin-top:2.5rem">
      <div class="ec-prose">
        <h2>Randament brut și randament net</h2>
        <p>
          Randamentul brut împarte chiria anuală la prețul de achiziție. Cel net scade
          perioadele neînchiriate, impozitul pe venit, cheltuielile de administrare și
          reparațiile. Diferența dintre cele două este, de regulă, de cel puțin un punct procentual.
        </p>
        <h3>Costuri care nu apar în calculator</h3>
        <p>
          Taxele notariale, intabularea, TVA-ul aferent, mobilarea și echiparea inițială și
          eventualul comision de administrare nu sunt incluse. Pentru o garsonieră, mobilarea
          completă pornește în general de la câteva mii de euro.
        </p>
        <h3>Caracterul informativ al cifrelor</h3>
        <p>
          Valorile de pe această pagină sunt estimări bazate pe prețuri de listare și pe chirii
          observate în zonă. Nu reprezintă consultanță financiară sau fiscală; decizia de achiziție
          aparține cumpărătorului, care poate consulta un specialist independent.
        </p>
      </div>
      {panou_dotari("Avantajele unei locuințe noi", "building-circle-check", [
          ("shield-halved", "Garanție de structură și de finisaje, conform legii"),
          ("fire-burner", "Centrală proprie și contorizare individuală"),
          ("temperature-arrow-down", "Consum redus: anvelopă termică și geam tripan"),
          ("couch", "Predare la cheie: chiriașul se poate muta după mobilare"),
          ("square-parking", "Parcare subterană și boxă, la cerere"),
          ("file-signature", "Documentație completă: autorizații și intabulare"),
      ], "6 elemente")}
    </div>
  </section>

  <section class="ec-section" id="intrebari" style="padding-block:var(--ec-section) 0">
    <div class="ec-shead">
      <div><span class="ec-shead__n">07 — Întrebări</span>
        <h2>Despre <em>investiție și randament</em></h2></div>
      <p class="ec-shead__p">{len(FAQ_INV)} întrebări despre chirii, costuri, cerere și metodă de calcul.</p>
    </div>
    <div class="ec-faq" style="margin-top:2.5rem">{faq}</div>
  </section>

  <section class="ec-section" style="padding-block:var(--ec-section) 0">
    {cta_dublu(r, "investitie")}
  </section>

  {showroom(r, "08")}
</div>
"""

    return pagina(
        "Investiție în apartamente noi în Iași — randament | Emerald City",
        "Calculator de randament pentru apartamente noi în Iași, zona Păcurari. "
        f"{len(gars)} de garsoniere disponibile, cu estimări de chirie și amortizare.",
        continut, r, schema, "investitie-apartamente-iasi/", "living-01")


# ======================================================= comparator ==
def pagina_comparator():
    r = "../"
    continut = f"""<div class="ec-wrap">
  <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Comparator de apartamente</nav>
  <header class="ec-phead">
    <p class="ec-eyebrow">Comparator</p>
    <h1 style="margin-top:1rem">Comparator de apartamentele salvate</h1>
    <p class="ec-body" style="max-width:62ch;font-size:var(--ec-lead)">
      Adaugă apartamente cu butonul „Salvează” de pe paginile de unitate, apoi trimite linkul
      acestei pagini cui vrei. Lista se păstrează și în adresă, deci funcționează și pe alt dispozitiv.
    </p>
  </header>
  <div id="cmpOut"></div>
  <p style="margin:2rem 0 4rem"><a class="ec-btn ec-btn--out" href="{r}apartamente-iasi/disponibilitate/">Alte apartamente</a></p>
</div>
<script src="{r}assets/js/compara.js"></script>"""
    return pagina("Comparator de apartamente — Emerald City Iași",
                  "Compară până la șase apartamente din Emerald City, Iași zona Păcurari.",
                  continut, r, None, "compara/", robots="noindex, follow")


# ========================================================== contact ==
FAQ_CONTACT = [
    ("Care este programul biroului de vânzări?",
     "Luni–vineri între 9:00 și 18:00 și sâmbătă între 10:00 și 14:00, la showroom-ul din "
     "Str. Dealul Zorilor 9, zona Păcurari, Iași. În afara programului, solicitările primite "
     "pe e-mail sau WhatsApp sunt preluate în prima zi lucrătoare."),
    ("În cât timp se primește un răspuns?",
     "Solicitările transmise prin formular sau e-mail primesc răspuns în aceeași zi lucrătoare, "
     "dacă sunt trimise până la ora 16:00. Apelurile telefonice sunt preluate direct în program."),
    ("Vizionarea se face doar cu programare?",
     "Da. Apartamentul-model și șantierul se vizitează cu programare, pentru ca un consultant "
     "să fie disponibil exclusiv pentru întâlnire. Programarea se face online, telefonic sau pe WhatsApp."),
    ("Se pot solicita planuri și liste de prețuri pe e-mail?",
     "Da. Lista completă de disponibilitate, planurile fiecărei compartimentări și condițiile de "
     "plată se transmit pe e-mail sau pe WhatsApp, la cerere."),
    ("Există parcare la showroom?",
     "Da, locuri de parcare gratuite în fața biroului de vânzări, pe Str. Dealul Zorilor. "
     "Zona este deservită și de transportul public, cu stație la circa 300 m."),
    ("Cine răspunde la solicitări?",
     "Echipa de vânzări a dezvoltatorului, Tala Sapphire S.R.L., parte a Green Stone Group. "
     "Nu se lucrează prin intermediari și nu se percep comisioane de agenție."),
]


def canal(pict, titlu, valoare, href, sub, brand=False):
    return (f'<a class="ec-canal ec-rv" href="{href}"{' target="_blank" rel="noopener"' if href.startswith("http") else ""}>'
            f'<span class="ec-canal__ic">{ic(pict, brand=brand)}</span>'
            f'<span class="ec-canal__t">{e(titlu)}</span><b>{e(valoare)}</b><em>{e(sub)}</em>'
            f'<span class="ec-canal__go">{ic("arrow-right")}</span></a>')


def pagina_contact():
    r = "../"
    canale = (
        canal("phone", "Telefon", SHOWROOM["tel"], TEL_LINK, "Luni–vineri 9–18, sâmbătă 10–14")
        + canal("whatsapp", "WhatsApp", SHOWROOM["tel"], WA, "Mesaje, planuri și liste de prețuri", brand=True)
        + canal("envelope", "E-mail", SHOWROOM["mail"], f"mailto:{SHOWROOM['mail']}", "Răspuns în aceeași zi lucrătoare")
        + canal("location-dot", "Showroom", "Str. Dealul Zorilor 9", f"{r}programare-vizionare/", "Zona Păcurari, Iași · cu programare")
    )
    faq = "".join(f"<details><summary>{e(q)}</summary>"
                  f'<div class="ec-faq__a">{e(a)}</div></details>' for q, a in FAQ_CONTACT)
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "ContactPage", "name": "Contact Emerald City Iași",
             "url": "https://emerald-city.ro/contact/"},
            {"@type": "RealEstateAgent", "name": "Emerald City — birou de vânzări",
             "url": "https://emerald-city.ro/", "telephone": "+40757707080",
             "email": SHOWROOM["mail"], "priceRange": "€€",
             "address": {"@type": "PostalAddress", "streetAddress": "Str. Dealul Zorilor 9",
                         "addressLocality": "Iași", "addressRegion": "Iași", "addressCountry": "RO"},
             "openingHoursSpecification": [
                 {"@type": "OpeningHoursSpecification",
                  "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                  "opens": "09:00", "closes": "18:00"},
                 {"@type": "OpeningHoursSpecification", "dayOfWeek": "Saturday",
                  "opens": "10:00", "closes": "14:00"}],
             "parentOrganization": {"@type": "Organization", "name": "Tala Sapphire S.R.L."}},
            {"@type": "FAQPage",
             "mainEntity": [{"@type": "Question", "name": q,
                             "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ_CONTACT]},
        ]}

    continut = f"""<section class="ec-phero">
  {imagine("hol-01", "", r, "100vw", eager=True)}
  <div class="ec-phero__veil"></div>
  <div class="ec-wrap ec-phero__in">
    <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Contact</nav>
    <p class="ec-eyebrow">Contact</p>
    <h1>Echipa de vânzări, la un mesaj distanță</h1>
    <p class="ec-phero__sub">
      Telefon, WhatsApp, e-mail sau o întâlnire în showroom. Solicitările primesc răspuns
      în aceeași zi lucrătoare, direct de la dezvoltator, fără intermediari.
    </p>
    <div class="ec-phero__cta">
      <a class="ec-btn ec-btn--white" href="{r}programare-vizionare/">{ic("calendar-check")} Programare vizionare</a>
      <a class="ec-btn ec-btn--outlight" href="{TEL_LINK}">{ic("phone")} {SHOWROOM["tel"]}</a>
    </div>
  </div>
</section>

<div class="ec-wrap">
  <section class="ec-section" id="canale" style="padding-block:var(--ec-section) 0">
    <div class="ec-shead">
      <div><span class="ec-shead__n">01 — Canale</span>
        <h2>Patru moduri <em>de a lua legătura</em></h2></div>
      <p class="ec-shead__p">Fiecare canal ajunge la aceeași echipă. Alegerea ține doar de preferință.</p>
    </div>
    <div class="ec-canale" style="margin-top:2.5rem">{canale}</div>
  </section>

  {showroom(r, "02", "Harta, datele de contact și formularul. Pentru o vizionare, pagina dedicată "
                     "permite alegerea zilei și a intervalului orar.")}

  <section class="ec-section" id="firma" style="padding-block:var(--ec-section) 0">
    <div class="ec-shead">
      <div><span class="ec-shead__n">03 — Dezvoltator</span>
        <h2>Date de <em>identificare</em></h2></div>
      <p class="ec-shead__p">Vânzarea se face direct de către societatea care dezvoltă ansamblul.</p>
    </div>
    <div class="ec-inv2" style="margin-top:2.5rem">
      {panou_dotari("Tala Sapphire S.R.L.", "building", [
          ("layer-group", "Parte a Green Stone Group, dezvoltator activ din 2007"),
          ("location-dot", "Sediu social: Str. Ion Nistor, Iași"),
          ("store", "Birou de vânzări: Str. Dealul Zorilor 9, zona Păcurari, Iași"),
          ("envelope", "vanzari@emerald-city.ro · protecția datelor: dpo@emerald-city.ro"),
          ("file-signature", "Contractele se semnează la notar, cu documentația completă a proiectului"),
          ("shield-halved", "Proiecte anterioare finalizate în Iași: Lapis Residence, Onyx Residence"),
      ], "Dezvoltatorul ansamblului")}
      {panou_dotari("Ce se poate solicita", "list-check", [
          ("table-list", "Lista completă de disponibilitate, cu prețuri actualizate"),
          ("compass-drafting", "Planurile detaliate ale fiecărei compartimentări"),
          ("file-invoice", "Condițiile de plată și eșalonarea pe stadii de execuție"),
          ("landmark", "Recomandări de bănci partenere pentru credit ipotecar"),
          ("helmet-safety", "Vizită pe șantier, însoțită, cu echipament de protecție"),
          ("newspaper", "Raportul lunar de stadiu al lucrărilor, pe e-mail"),
      ], "6 documente și servicii")}
    </div>
  </section>

  <section class="ec-section" id="intrebari" style="padding-block:var(--ec-section) 0">
    <div class="ec-shead">
      <div><span class="ec-shead__n">04 — Întrebări</span>
        <h2>Despre <em>contact și program</em></h2></div>
      <p class="ec-shead__p">{len(FAQ_CONTACT)} întrebări despre program, timp de răspuns și vizionări.</p>
    </div>
    <div class="ec-faq" style="margin-top:2.5rem">{faq}</div>
  </section>

  <section class="ec-section" style="padding-block:var(--ec-section)">
    {cta_dublu(r, "contact")}
  </section>
</div>"""
    return pagina("Contact — Emerald City Iași",
                  "Contact Emerald City, ansamblu rezidențial în Iași, zona Păcurari: telefon "
                  "0757 70 70 80, WhatsApp, e-mail și showroom pe Str. Dealul Zorilor 9.",
                  continut, r, schema, "contact/", "hol-01")


# ======================================================= programare ==
FAQ_VIZIONARE = [
    ("Cât durează o vizionare?",
     "Aproximativ 40 de minute: prezentarea apartamentului-model, a planurilor și a listei de "
     "disponibilitate, urmată de întrebări. La cerere, întâlnirea continuă cu o vizită pe șantier."),
    ("Ce se poate vedea la fața locului?",
     "Apartamentul-model complet finisat, mostrele de finisaje, planul de situație al ansamblului "
     "și, cu echipament de protecție, blocurile aflate în execuție."),
    ("Se poate programa o vizionare sâmbăta?",
     "Da, sâmbătă între 10:00 și 14:00. Intervalele de sâmbătă se ocupă mai repede, de aceea "
     "recomandăm programarea cu câteva zile înainte."),
    ("Programarea se confirmă?",
     "Da. După trimiterea formularului, un consultant confirmă telefonic ziua și ora, în aceeași "
     "zi lucrătoare. Programarea se poate modifica sau anula oricând, telefonic sau pe WhatsApp."),
    ("Este necesar un document sau o pregătire prealabilă?",
     "Nu. Este utilă doar o idee despre buget și despre numărul de camere dorit, pentru ca "
     "prezentarea să fie orientată către unitățile potrivite."),
    ("Pot participa mai multe persoane?",
     "Da. Familia, un consilier financiar sau un arhitect sunt bineveniți. Menționați numărul de "
     "persoane în formular, pentru organizarea întâlnirii."),
    ("Se poate rezerva un apartament în ziua vizionării?",
     "Da. Rezervarea blochează prețul afișat pentru unitatea aleasă, până la semnarea "
     "antecontractului, în condițiile comunicate la întâlnire."),
    ("Vizionarea implică vreo obligație?",
     "Nu. Vizionarea este gratuită și nu presupune nicio obligație de cumpărare."),
]


def pagina_programare(unitati):
    r = "../"
    disp = [u for u in unitati if u["status"] == "disponibil"]
    faq = "".join(f"<details><summary>{e(q)}</summary>"
                  f'<div class="ec-faq__a">{e(a)}</div></details>' for q, a in FAQ_VIZIONARE)
    slot = lambda v, et: (f'<label class="ec-slot"><input type="radio" name="interval" value="{v}">'
                          f'<span>{et}</span></label>')
    interes = lambda v, et: (f'<label class="ec-slot"><input type="radio" name="interes" value="{v}">'
                             f'<span>{et}</span></label>')
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebPage", "name": "Programare vizionare — Emerald City Iași",
             "url": "https://emerald-city.ro/programare-vizionare/"},
            {"@type": "FAQPage",
             "mainEntity": [{"@type": "Question", "name": q,
                             "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ_VIZIONARE]},
        ]}

    continut = f"""<section class="ec-phero">
  {imagine("living-02", "", r, "100vw", eager=True)}
  <div class="ec-phero__veil"></div>
  <div class="ec-wrap ec-phero__in">
    <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>
      <a href="{r}contact/">Contact</a><span>/</span>Programare vizionare</nav>
    <p class="ec-eyebrow">Programare vizionare</p>
    <h1>Vizionarea apartamentului-model, la ora dorită</h1>
    <p class="ec-phero__sub">
      O întâlnire de aproximativ 40 de minute în showroom-ul din Păcurari: apartamentul-model
      finisat, planurile pe masă și lista de disponibilitate, cu {len(disp)} de apartamente
      cu prețuri afișate.
    </p>
    <div class="ec-phero__cta">
      <a class="ec-btn ec-btn--white" href="#formular">{ic("calendar-check")} Alegeți ziua și ora</a>
      <a class="ec-btn ec-btn--outlight" href="{WA}" target="_blank" rel="noopener">{ic("whatsapp", brand=True)} Programare pe WhatsApp</a>
    </div>
  </div>
</section>

<div class="ec-figs-wrap">
  <div class="ec-wrap"><div class="ec-figs">
    <div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic("hourglass-half")}</span><span><b>40 min</b><em>Durata întâlnirii</em></span></div>
    <div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic("calendar-days")}</span><span><b>6 zile</b><em>Luni–sâmbătă</em></span></div>
    <div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic("key")}</span><span><b>{len(disp)}</b><em>Apartamente disponibile</em></span></div>
    <div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic("hand-holding-heart")}</span><span><b>Gratuit</b><em>Fără nicio obligație</em></span></div>
  </div></div>
</div>

<div class="ec-wrap">
  <section class="ec-section" id="formular" style="padding-block:var(--ec-section) 0">
    <div class="ec-shead">
      <div><span class="ec-shead__n">01 — Programare</span>
        <h2>Alegeți <em>ziua și intervalul</em></h2></div>
      <p class="ec-shead__p">
        Confirmarea se face telefonic, în aceeași zi lucrătoare. Programarea se poate
        modifica oricând.
      </p>
    </div>
    <div class="ec-inv2" style="margin-top:2.5rem">
      <div class="ec-form ec-book">
        <h2 class="ec-form__t">Formular de programare</h2>
        <p class="ec-form__i">Câmpurile marcate cu * sunt necesare pentru confirmare.</p>
        <form method="post" action="#" novalidate data-book>
          <div class="ec-form__grid">
            <div><label for="b-nume">Nume și prenume *</label><input id="b-nume" name="nume" type="text" autocomplete="name" required></div>
            <div><label for="b-tel">Telefon *</label><input id="b-tel" name="telefon" type="tel" autocomplete="tel" required></div>
            <div class="full"><label for="b-mail">E-mail</label><input id="b-mail" name="email" type="email" autocomplete="email"></div>
            <div class="full"><span class="ec-form__lbl">Apartament de interes</span>
              <div class="ec-slots ec-slots--4">
                {interes("1", "1 cameră")}{interes("2", "2 camere")}{interes("3", "3 camere")}{interes("nehotarat", "Nehotărât")}
              </div></div>
            <div><label for="b-data">Ziua preferată *</label><input id="b-data" name="data" type="date" required></div>
            <div><label for="b-pers">Număr de persoane</label>
              <select id="b-pers" name="persoane"><option>1</option><option selected>2</option><option>3</option><option>4 sau mai multe</option></select></div>
            <div class="full"><span class="ec-form__lbl">Interval orar *</span>
              <div class="ec-slots ec-slots--4">
                {slot("9-11", "9:00–11:00")}{slot("11-13", "11:00–13:00")}{slot("13-16", "13:00–16:00")}{slot("16-18", "16:00–18:00")}
              </div>
              <small class="ec-form__hint">Sâmbătă: 10:00–14:00. Pentru alt interval, menționați în mesaj.</small></div>
            <div class="full"><label for="b-msg">Mesaj</label><textarea id="b-msg" name="mesaj" rows="3" placeholder="Buget orientativ, etaj preferat, întrebări"></textarea></div>
            <div class="full ec-form__consent">
              <label><input type="checkbox" name="acord" required>
                <span>Sunt de acord cu prelucrarea datelor conform <a href="{r}politica-de-confidentialitate/">Politicii de confidențialitate</a>, în scopul programării vizionării. *</span></label>
            </div>
            <div class="full"><button class="ec-btn ec-btn--brass" type="submit">{ic("calendar-check")} Trimite programarea</button></div>
          </div>
          <p class="ec-form__note">Machetă de lucru — formularul nu trimite date.</p>
        </form>
      </div>
      <div class="ec-bookside">
        {panou_dotari("Ce include vizionarea", "clipboard-check", [
            ("couch", "Apartamentul-model, complet finisat și mobilat"),
            ("swatchbook", "Mostrele de finisaje: parchet, gresie, faianță, uși"),
            ("map", "Planul de situație: blocuri, etape, parcări, spații verzi"),
            ("table-list", "Lista de disponibilitate, cu prețul fiecărei unități"),
            ("file-invoice", "Condițiile de plată și simularea unei rate"),
            ("helmet-safety", "La cerere, vizită pe șantier cu echipament de protecție"),
        ], "6 elemente")}
        <div class="ec-panel ec-bookside__p">
          <h3>{ic("route")} Cum se ajunge</h3>
          <p>Str. Dealul Zorilor 9, zona Păcurari, Iași. Parcare gratuită în fața biroului.
             Transport public: stație la circa 300 m, pe Șoseaua Păcurari.</p>
          <a class="ec-btn ec-btn--out" href="https://www.google.com/maps/search/?api=1&amp;query=Strada+Dealul+Zorilor+9+Ia%C8%99i"
             target="_blank" rel="noopener">{ic("diamond-turn-right")} Indicații rutiere</a>
        </div>
      </div>
    </div>
  </section>

  <section class="ec-section" id="pasi" style="padding-block:var(--ec-section) 0">
    <div class="ec-shead">
      <div><span class="ec-shead__n">02 — Parcurs</span>
        <h2>Cum decurge <em>întâlnirea</em></h2></div>
      <p class="ec-shead__p">Trei pași, de la confirmare la propunerea personalizată.</p>
    </div>
    <div class="ec-steps" style="margin-top:2.5rem">
      <div class="ec-step ec-rv"><div class="ec-step__n">01</div>
        <h3>Confirmare telefonică</h3>
        <p>Un consultant confirmă ziua și ora în aceeași zi lucrătoare și notează preferințele:
           număr de camere, etaj, buget orientativ.</p></div>
      <div class="ec-step ec-rv" data-d="1"><div class="ec-step__n">02</div>
        <h3>Vizionare și prezentare</h3>
        <p>Apartamentul-model, mostrele de finisaje, planurile și lista de disponibilitate.
           La cerere, vizită însoțită pe șantier.</p></div>
      <div class="ec-step ec-rv" data-d="2"><div class="ec-step__n">03</div>
        <h3>Propunere personalizată</h3>
        <p>O selecție de 2–3 unități potrivite, cu preț, plan și eșalonarea plăților,
           transmisă pe e-mail după întâlnire.</p></div>
    </div>
  </section>

  <section class="ec-section" id="intrebari" style="padding-block:var(--ec-section) 0">
    <div class="ec-shead">
      <div><span class="ec-shead__n">03 — Întrebări</span>
        <h2>Despre <em>vizionare</em></h2></div>
      <p class="ec-shead__p">{len(FAQ_VIZIONARE)} întrebări despre durată, program și ce se poate vedea.</p>
    </div>
    <div class="ec-faq" style="margin-top:2.5rem">{faq}</div>
  </section>

  {showroom(r, "04")}
</div>
<script>
(() => {{
  const d = document.querySelector('#b-data');
  if (!d) return;
  const azi = new Date(); azi.setMinutes(azi.getMinutes() - azi.getTimezoneOffset());
  d.min = azi.toISOString().slice(0, 10);
  d.addEventListener('change', () => {{
    const zi = new Date(d.value).getDay();
    d.setCustomValidity(zi === 0 ? 'Duminica biroul este închis.' : '');
    d.reportValidity();
  }});
}})();
</script>"""
    return pagina("Programare vizionare — Emerald City Iași",
                  "Programați o vizionare a apartamentului-model Emerald City, Iași zona Păcurari: "
                  "alegeți ziua și intervalul orar, confirmarea se face telefonic în aceeași zi.",
                  continut, r, schema, "programare-vizionare/", "living-02")


# ================================================================== zona ==
# Distantele vin din assets/data/distante.json, calculate pe traseu rutier.
# Pagina nu mai tine o lista proprie, ca sa nu se contrazica cu harta.
_DIST = os.path.join(RAD, "assets", "data", "distante.json")
DISTANTE = json.load(open(_DIST, encoding="utf-8")) if os.path.exists(_DIST) else {"puncte": []}

# Pictograma fiecarui reper, dupa nume.
PICT_POI = {
    "Kaufland Păcurari": "cart-shopping",
    "Mall Moldova": "bag-shopping",
    "Palas Mall": "bag-shopping",
    "Parcul Copou": "tree",
    "Universitatea „Alexandru Ioan Cuza”": "graduation-cap",
    "Centrul orașului": "city",
    "Aeroportul Iași": "plane-departure",
}

# Reper indicat de client, fara coordonate confirmate, deci nu apare pe harta.
PE_JOS = ("Paradis International College", "400 m", "5 min pe jos", "school")

CARTIER = [
    ("cart-shopping", "Cumpărături zilnice",
     "Kaufland Păcurari la 1,1 km, plus magazinele de proximitate de pe artera Păcurari."),
    ("school", "Școli și grădinițe",
     "Paradis International College la 400 m, la 5 minute de mers pe jos."),
    ("graduation-cap", "Centrul universitar",
     "Universitatea „Alexandru Ioan Cuza” la 3,9 km, în Copou."),
    ("tree", "Spații verzi",
     "Parcul Copou la 4,4 km, plus cele 15.501,80 m² amenajate în interiorul ansamblului."),
    ("bus", "Transport public",
     "Linii constante pe artera Păcurari, spre centru și spre Copou."),
    ("road", "Ieșire din oraș",
     "DN28 spre Botoșani, pentru drumurile în afara Iașului."),
    ("hospital", "Servicii medicale",
     "Spitalul „Sf. Spiridon” și rețeaua privată din zona centrală."),
    ("bag-shopping", "Mall-uri",
     "Mall Moldova la 3,6 km și Palas la 6,1 km."),
]

PROFILURI = [
    ("people-roof", "Familii tinere",
     "Spațiu verde, locuri de joacă și parcare proprie, fără să ieși din oraș. "
     "Apartamentele de la parter au curte, între 13 și 51 m²."),
    ("chart-line", "Investitori",
     "Cererea de chirii e susținută de apropierea de centrul universitar. "
     "Garsonierele pornesc de la 53.500 €, cu estimare de randament disponibilă pe site."),
    ("briefcase", "Cei care lucrează în nord-vest",
     "Acces direct la artera Păcurari și la DN28, fără traversarea centrului."),
    ("key", "La prima locuință",
     "Garsonierele pornesc de la 53.500 €, cu TVA inclus. Se pot cumpăra cu credit "
     "ipotecar sau, în plafon, prin Noua Casă."),
]

FAQ_ZONA = [
    ("Unde se află mai exact Emerald City?",
     "În Iași, zona Păcurari, cu acces din Strada Ion Nistor. Ansamblul este la limita de "
     "nord-vest a orașului, în spatele ansamblului Contemporan Homes de pe Strada "
     "Dealul Zorilor."),
    ("Cât face până în centrul Iașului?",
     "Aproximativ 4,8 km, adică în jur de 8 minute cu mașina fără trafic."),
    ("Cât face până la universitate?",
     "3,9 km până la Universitatea „Alexandru Ioan Cuza”, aproximativ 7 minute cu mașina."),
    ("Există școli în apropiere?",
     "Paradis International College se află la aproximativ 400 de metri, la 5 minute de "
     "mers pe jos."),
    ("Cum stă zona cu cumpărăturile?",
     "Kaufland Păcurari este la 1,1 km, adică 3 minute cu mașina. Mall Moldova la 3,6 km "
     "și Palas la 6,1 km."),
    ("Cum se ajunge cu transportul public?",
     "Artera Păcurari are linii constante spre centru și spre Copou. Stația cea mai "
     "apropiată se află pe drumul de acces în ansamblu."),
    ("Cât face până la aeroport?",
     "11,3 km, aproximativ 18 minute cu mașina."),
    ("De ce zona Păcurari și nu altă zonă din Iași?",
     "Este una dintre puținele zone din Iași care mai are teren pentru ansambluri cu "
     "spațiu între clădiri, la distanță mică de Copou și de centrul universitar."),
]


def pagina_zona():
    r = "../"
    pct = DISTANTE.get("puncte", [])
    gasit = {p["nume"]: p for p in pct}

    def km(nume, implicit="—"):
        p = gasit.get(nume)
        return f'{str(p["km"]).replace(".", ",")} km' if p else implicit

    figuri = "".join(
        f'<div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic(pic)}</span>'
        f'<span><b>{e(val)}</b><em>{e(et)}</em></span></div>'
        for val, et, pic in [
            (PE_JOS[1], "Paradis International College", "school"),
            (km("Kaufland Păcurari"), "Kaufland Păcurari", "cart-shopping"),
            (km("Universitatea „Alexandru Ioan Cuza”"), "Universitatea „A.I. Cuza”", "graduation-cap"),
            (km("Centrul orașului"), "Centrul Iașului", "city"),
        ])

    randuri = "".join(
        f'<tr><td>{ic(PICT_POI.get(p["nume"], "location-dot"))} {e(p["nume"])}</td>'
        f'<td class="num">{str(p["km"]).replace(".", ",")} km</td>'
        f'<td class="num">{p["min"]} min</td>'
        f'<td>Cu mașina</td></tr>'
        for p in sorted(pct, key=lambda x: x["km"]))
    randuri = (f'<tr><td>{ic(PE_JOS[3])} {e(PE_JOS[0])}</td>'
               f'<td class="num">{e(PE_JOS[1])}</td>'
               f'<td class="num">5 min</td><td>Pe jos</td></tr>') + randuri

    cartier = "".join(
        f'<div class="ec-fisa__i ec-rv"><span class="ec-fisa__ic">{ic(pic)}</span>'
        f'<span><b>{e(t)}</b><span class="ec-fisa__d">{e(d)}</span></span></div>'
        for pic, t, d in CARTIER)

    profiluri = "".join(
        f'<div class="ec-why__i ec-rv">{ic(pic)}<h3>{e(t)}</h3><p>{e(d)}</p></div>'
        for pic, t, d in PROFILURI)

    faq = "".join(f"<details><summary>{e(q)}</summary>"
                  f'<div class="ec-faq__a">{e(a)}</div></details>'
                  for q, a in FAQ_ZONA)

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Place", "name": "Emerald City",
             "address": {"@type": "PostalAddress",
                         "streetAddress": "Str. Ion Nistor",
                         "addressLocality": "Iași", "addressRegion": "Iași",
                         "addressCountry": "RO"},
             "geo": {"@type": "GeoCoordinates",
                     "latitude": DISTANTE.get("lat"), "longitude": DISTANTE.get("lon")}},
            {"@type": "FAQPage",
             "mainEntity": [{"@type": "Question", "name": q,
                             "acceptedAnswer": {"@type": "Answer", "text": a}}
                            for q, a in FAQ_ZONA]},
        ]}

    continut = f"""<section class="ec-phero">
  {imagine("dining-01", "", r, "100vw", eager=True)}
  <div class="ec-phero__veil"></div>
  <div class="ec-wrap ec-phero__in">
    <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Zona Păcurari</nav>
    <p class="ec-eyebrow">Amplasament</p>
    <h1>Păcurari, la 5 minute de Copou</h1>
    <p class="ec-phero__sub">
      Una dintre puținele zone din Iași care mai dispune de teren pentru ansambluri cu
      densitate redusă, la distanță mică de centrul universitar. Emerald City se află la
      limita de nord-vest a orașului, cu acces din Strada Ion Nistor.
    </p>
    <div class="ec-phero__cta">
      <a class="ec-btn ec-btn--white" href="#harta">{ic("map-location-dot")} Harta interactivă</a>
      <a class="ec-btn ec-btn--outlight" href="{r}apartamente-iasi/disponibilitate/">{ic("table-list")} Disponibilitate și prețuri</a>
    </div>
  </div>
</section>

<div class="ec-figs-wrap">
  <div class="ec-wrap"><div class="ec-figs">{figuri}</div></div>
</div>

<div class="ec-wrap">
  <section class="ec-section" id="pozitie">
    <div class="ec-shead">
      <div><span class="ec-shead__n">01 — Poziția</span>
        <h2>Aproape de tot ce <em>folosești zilnic</em></h2></div>
      <p class="ec-shead__p">
        Școală, cumpărături, universitate și centru, la câteva minute pe artera Păcurari.
      </p>
    </div>
    <div class="ec-split" style="margin-top:2.5rem">
      <div class="ec-prose">
        <p>
          Păcurari este una dintre cele mai căutate zone rezidențiale din Iași: se află la câteva
          minute de Copou și de centrul universitar, dar suficient de aproape de limita
          orașului cât să permită ansambluri cu densitate redusă.
        </p>
        <p>
          Emerald City se află la limita de nord-vest a orașului, în spatele ansamblului
          Contemporan Homes de pe Strada Dealul Zorilor. Accesul se face din Strada
          Ion Nistor. Centrul Iașului este la {km("Centrul orașului")}, Copoul la
          {km("Parcul Copou")}, iar ieșirea spre Botoșani, pe DN28, la câteva minute.
        </p>
        <p>
          Ansamblul are 925 de apartamente în 18 blocuri cu regim 2D+P+3E, pe un teren de
          cinci hectare din care 30,85% rămâne spațiu verde amenajat. Este unul dintre cele
          mai mari proiecte rezidențiale din zonă.
        </p>
      </div>
      <figure style="margin:0">
        {imagine("living-01", "Apartament în ansamblul Emerald City, zona Păcurari", r,
                 "(min-width: 62rem) 46vw, 100vw")}
      </figure>
    </div>
  </section>

  <section class="ec-section" id="distante" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">02 — Distanțe</span>
        <h2>Cât face <em>până unde contează</em></h2></div>
      <p class="ec-shead__p">
        Distanțe și timpi măsurați pe traseu rutier real, fără trafic, de la amplasament.
      </p>
    </div>
    <div class="ec-table ec-table--vs" style="margin-top:2.5rem">
      <table>
        <caption class="ec-sr">Distanțe de la Emerald City</caption>
        <thead><tr><th scope="col">Destinație</th><th scope="col">Distanță</th>
          <th scope="col">Timp</th><th scope="col">Mod</th></tr></thead>
        <tbody>{randuri}</tbody>
      </table>
    </div>
    <p class="ec-fisa__note">
      {ic("circle-info")} Calculate pe traseu rutier (OpenStreetMap), fără trafic.
      Distanța până la Paradis International College este cea indicată de dezvoltator.
    </p>
  </section>

  <section class="ec-section" id="harta" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">03 — Harta</span>
        <h2>Trasee <em>către fiecare reper</em></h2></div>
      <p class="ec-shead__p">
        Selectarea unui reper afișează traseul rutier. Reperele pot fi filtrate pe categorii, iar fundalul poate fi comutat pe imagine din satelit.
      </p>
    </div>
    <div class="ec-harta ec-rv" id="ecHarta" data-sursa="{r}assets/data/distante.json"
         style="margin-top:2.5rem">
      <div class="ec-harta__panza" data-panza></div>
      <div class="ec-harta__ctrl" data-controale></div>
      <div class="ec-harta__side">
        <div class="ec-harta__head">
          <b>Puncte de interes</b>
          <span>Selectează un reper pentru afișarea traseului.</span>
        </div>
        <div class="ec-harta__lista" data-lista></div>
        <div class="ec-harta__foot">
          <button class="ec-btn ec-btn--out" type="button" data-reset>Revenire la ansamblu</button>
        </div>
      </div>
    </div>
  </section>

  <section class="ec-section" id="cartier" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">04 — În jur</span>
        <h2>Dotări <em>de proximitate</em></h2></div>
      <p class="ec-shead__p">
        Serviciile accesibile pe jos și cele aflate la câteva minute cu mașina.
      </p>
    </div>
    <div class="ec-fisa" style="margin-top:2.5rem">{cartier}</div>
  </section>

  <section class="ec-section" id="cui" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">05 — Pentru cine</span>
        <h2>Cui i se potrivește <em>zona</em></h2></div>
      <p class="ec-shead__p">Profilurile de cumpărător cărora zona li se potrivește.</p>
    </div>
    <div class="ec-why" style="margin-top:2.5rem">{profiluri}</div>
  </section>

  <section class="ec-section" id="intrebari" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">06 — Întrebări</span>
        <h2>Despre zonă <em>și acces</em></h2></div>
      <p class="ec-shead__p">
        {len(FAQ_ZONA)} întrebări despre poziție, distanțe și transport.
      </p>
    </div>
    <div class="ec-faq" style="margin-top:2.5rem">{faq}</div>
  </section>

  {showroom(r, "07")}
</div>

<script src="{r}assets/js/harta.js"></script>"""

    return pagina("Apartamente Iași, zona Păcurari — amplasament | Emerald City",
                  "Unde se află Emerald City în Iași, zona Păcurari: distanțe reale până la "
                  "Copou, centru, universitate și școli, hartă interactivă cu traseu și ghid "
                  "de zonă.",
                  continut, r, schema, "apartamente-iasi-pacurari/")


# ================================================================ stadiu ==
# Datele de mai jos sunt cele din raportul lunar de santier. Se inlocuiesc
# la fiecare actualizare; procentele conduc si cifrele din capul paginii.
ACTUALIZAT = "Septembrie 2026"

# Fazele de executie, in ordinea in care se succed pe santier. Ponderea
# fiecareia in totalul unei etape e cea uzuala pentru locuinte colective.
FAZE = [
    ("Terasamente și organizare", .06),
    ("Fundații și demisoluri",    .18),
    ("Structură de rezistență",   .26),
    ("Închideri și compartimentări", .14),
    ("Instalații",                .14),
    ("Finisaje",                  .16),
    ("Amenajări exterioare",      .06),
]

# Stadiul fiecarei etape, faza cu faza, in procente.
ETAPE_STADIU = [
    {"cod": "I", "blocuri": "Blocurile 1–6", "ap": 322,
     "termen": "Trimestrul IV 2027", "activa": True,
     "stadiu": [100, 100, 45, 0, 0, 0, 0]},
    {"cod": "II", "blocuri": "Blocurile 7–14", "ap": 423,
     "termen": "Trimestrul II 2029", "activa": False,
     "stadiu": [35, 0, 0, 0, 0, 0, 0]},
    {"cod": "III", "blocuri": "Blocurile 15–18", "ap": 180,
     "termen": "Trimestrul IV 2030", "activa": False,
     "stadiu": [0, 0, 0, 0, 0, 0, 0]},
]

JURNAL = [
    ("Septembrie 2026", "Etapa I — structură la nivelul etajului 2",
     "Turnarea planșeului peste etajul 1 s-a încheiat la blocurile 1–4. La blocurile 5 și 6 "
     "se lucrează la cofraje. A început săpătura pentru demisolurile blocurilor 7 și 8, "
     "primele din Etapa II."),
    ("August 2026", "Etapa I — fundații finalizate",
     "Fundațiile pentru blocurile 1–6 sunt turnate și recepționate, cu procesele-verbale de "
     "fază determinantă semnate. A început ridicarea structurii la blocurile 1 și 2."),
    ("Iulie 2026", "Organizare de șantier și terasamente",
     "Platforma de organizare a fost amenajată, drumurile de acces provizorii sunt "
     "funcționale, iar terasamentele pentru prima etapă sunt finalizate. Racordurile "
     "provizorii de utilități au fost puse în funcțiune."),
]


FAQ_STADIU = [
    ("Cât de des se actualizează pagina?",
     "Lunar. Se publică stadiul fiecărei etape, faza cu faza, împreună cu fotografii datate "
     f"din teren. Ultima actualizare: {ACTUALIZAT}."),
    ("Ce înseamnă procentele afișate?",
     "Fiecare etapă este împărțită în 7 faze de execuție, de la terasamente la amenajări "
     "exterioare. Procentul general al unei etape este media ponderată a fazelor, cu "
     "ponderile uzuale pentru clădiri de locuințe colective."),
    ("Se poate vizita șantierul?",
     "Da, cu programare și însoțit de un reprezentant, în echipament de protecție pus la "
     "dispoziție. Accesul neînsoțit nu este permis, din motive de securitate."),
    ("Termenele de predare sunt garantate?",
     "Termenul fiecărei etape se înscrie în antecontractul semnat la notar. Datele afișate "
     "aici sunt cele estimate la data ultimei actualizări; termenul contractual este cel "
     "care obligă."),
    ("Ce se întâmplă dacă lucrările întârzie?",
     "Antecontractul prevede termenul de predare și consecințele depășirii acestuia. Orice "
     "modificare de calendar se comunică din timp."),
    ("Raportul lunar poate fi primit pe e-mail?",
     "Da. La solicitare, raportul lunar cu fotografii se transmite pe e-mail imediat după "
     "publicare."),
]


def pagina_stadiu():
    r = "../"

    def procent(st):
        return sum(p * FAZE[i][1] for i, p in enumerate(st))

    total_ap = sum(x["ap"] for x in ETAPE_STADIU)
    general = sum(procent(x["stadiu"]) * x["ap"] for x in ETAPE_STADIU) / total_ap
    activa = next(x for x in ETAPE_STADIU if x["activa"])

    def _fig(val, suf, et, pic, num):
        # doar cifrele propriu-zise se anima; "I" sau "Septembrie" raman fixe
        attr = ' data-num="%s"' % e(val) if num else ""
        return (f'<div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic(pic)}</span>'
                f'<span><b{attr}>{e(val)}{e(suf)}</b><em>{e(et)}</em></span></div>')

    figuri = "".join(
        _fig(val, suf, et, pic, num)
        for val, suf, et, pic, num in [
            (f"{general:.0f}", "%", "Stadiu general", "chart-simple", True),
            ("I", "", "Etapa în execuție", "helmet-safety", False),
            (str(len(ETAPE_STADIU)), "", "Etape de construcție", "layer-group", True),
            (ACTUALIZAT.split()[0], "", "Ultima actualizare", "calendar-check", False),
        ])

    def card_etapa(x):
        p = procent(x["stadiu"])
        faze = "".join(
            f'<div class="ec-faza{" is-gata" if v >= 100 else ""}">'
            f'<b>{e(nume)}</b><u>{v}%</u>'
            f'<span class="ec-faza__b"><span data-w="{v}"></span></span></div>'
            for (nume, _), v in zip(FAZE, x["stadiu"]))
        return (f'<article class="ec-et{" is-activa" if x["activa"] else ""} ec-rv">'
                f'<div class="ec-et__top"><div>'
                f'<span class="ec-et__k">{e(x["blocuri"])}</span>'
                f'<h3>Etapa {e(x["cod"])}</h3></div>'
                f'<span class="ec-et__pc">{p:.0f}%<small>Stadiu</small></span></div>'
                f'<div class="ec-et__meta">'
                f'<span>{ic("building")}{x["ap"]} apartamente</span>'
                f'<span>{ic("calendar-days")}{e(x["termen"])}</span></div>'
                f'<div class="ec-et__faze">{faze}</div></article>')

    etape = "".join(card_etapa(x) for x in ETAPE_STADIU)

    poze = ('<div class="ec-jurnal__gal">'
            + '<div class="ec-jurnal__ph"><i class="fa-solid fa-camera" aria-hidden="true"></i>'
              'Fotografie de șantier<br>de furnizat</div>' * 3
            + '</div>')
    jurnal = "".join(
        f'<article class="ec-jurnal__i ec-rv">'
        f'<div class="ec-jurnal__d">{e(d)}'
        f'<small>{"Cea mai recentă" if i == 0 else "Arhivă"}</small></div>'
        f'<div><div class="ec-jurnal__t">{e(t)}</div><p>{e(c)}</p>{poze}</div></article>'
        for i, (d, t, c) in enumerate(JURNAL))

    faq = "".join(f"<details><summary>{e(q)}</summary>"
                  f'<div class="ec-faq__a">{e(a)}</div></details>'
                  for q, a in FAQ_STADIU)

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebPage", "name": "Stadiul lucrărilor — Emerald City",
             "url": "https://emerald-city.ro/stadiu-lucrari/"},
            {"@type": "FAQPage",
             "mainEntity": [{"@type": "Question", "name": q,
                             "acceptedAnswer": {"@type": "Answer", "text": a}}
                            for q, a in FAQ_STADIU]},
        ]}

    continut = f"""<section class="ec-phero">
  {imagine("hol-01", "", r, "100vw", eager=True)}
  <div class="ec-phero__veil"></div>
  <div class="ec-wrap ec-phero__in">
    <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Stadiul lucrărilor</nav>
    <p class="ec-eyebrow">Jurnal de șantier</p>
    <h1>Unde s-a ajuns, lună de lună</h1>
    <p class="ec-phero__sub">
      Publicăm stadiul fiecărei etape, faza cu faza, împreună cu fotografii datate din teren,
      astfel încât progresul să poată fi verificat independent.
    </p>
    <div class="ec-phero__cta">
      <a class="ec-btn ec-btn--white" href="#etape">{ic("chart-simple")} Stadiul pe etape</a>
      <a class="ec-btn ec-btn--outlight" href="#vizite">{ic("helmet-safety")} Programare vizită</a>
    </div>
  </div>
</section>

<div class="ec-figs-wrap">
  <div class="ec-wrap"><div class="ec-figs">{figuri}</div></div>
</div>


<div class="ec-wrap">
  <section class="ec-section" id="etape">
    <div class="ec-shead">
      <div><span class="ec-shead__n">01 — Stadiu pe etape</span>
        <h2>Fiecare etapă, <em>faza cu faza</em></h2></div>
      <p class="ec-shead__p">
        7 faze de execuție, de la terasamente la amenajări exterioare. Procentul general
        este media ponderată a fazelor, cu ponderile uzuale pentru locuințe colective.
      </p>
    </div>
    <div class="ec-santier" style="margin-top:2.5rem">{etape}</div>
    <p class="ec-fisa__note">
      {ic("circle-info")} Stadiul reflectă raportul de șantier din {e(ACTUALIZAT)}.
      Termenele afișate sunt estimative; cel contractual este cel din antecontract.
    </p>
  </section>
</div>

<section class="ec-band" id="jurnal">
  <div class="ec-wrap">
    <div class="ec-section">
      <div class="ec-shead">
        <div><span class="ec-shead__n" style="color:var(--ec-brass)">02 — Jurnal</span>
          <h2>Ce s-a lucrat <em>în ultimele luni</em></h2></div>
        <p class="ec-shead__p">
          Un raport pe lună, cu ce s-a executat efectiv și cu fotografii datate din teren.
        </p>
      </div>
      <div class="ec-panel" style="margin-top:2.5rem">
        <div class="ec-jurnal">{jurnal}</div>
      </div>
    </div>
  </div>
</section>

<div class="ec-wrap">
  <section class="ec-section" id="vizite">
    <div class="ec-shead">
      <div><span class="ec-shead__n">03 — Vizite pe șantier</span>
        <h2>Vizite <em>pe șantier</em></h2></div>
      <p class="ec-shead__p">
        Vizitele se organizează cu programare, însoțite. Echipamentul de protecție este pus la dispoziție.
      </p>
    </div>
    <div class="ec-why" style="margin-top:2.5rem">
      <div class="ec-why__i ec-rv">{ic("calendar-check")}
        <h3>Cu programare</h3>
        <p>Data și ora se stabilesc telefonic sau prin e-mail. Vizitele se desfășoară în zilele lucrătoare.</p></div>
      <div class="ec-why__i ec-rv">{ic("user-shield")}
        <h3>Însoțit</h3>
        <p>Un reprezentant însoțește vizita pe traseul autorizat și prezintă lucrările în execuție.</p></div>
      <div class="ec-why__i ec-rv">{ic("helmet-safety")}
        <h3>Echipament inclus</h3>
        <p>Cască și vestă reflectorizantă, furnizate la intrarea în incintă.</p></div>
      <div class="ec-why__i ec-rv">{ic("camera")}
        <h3>Fotografiere permisă</h3>
        <p>Fotografierea lucrărilor este permisă, fără restricții.</p></div>
    </div>
    
  </section>

  <section class="ec-section" style="padding-block:0 var(--ec-section)">
    {alerta("Primește raportul lunar de șantier",
            "Un e-mail pe lună, cu stadiul fiecărei etape și fotografii datate din teren. "
            "Se poate opri oricând.", "santier", "helmet-safety")}
  </section>

  {showroom(r, "04")}

  <section class="ec-section" id="intrebari" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">07 — Întrebări</span>
        <h2>Despre execuție <em>și termene</em></h2></div>
      <p class="ec-shead__p">
        {len(FAQ_STADIU)} întrebări despre urmărirea progresului și garanțiile contractuale.
      </p>
    </div>
    <div class="ec-faq" style="margin-top:2.5rem">{faq}</div>
    <div class="ec-inv__foot" style="margin-top:2rem">
      <p class="ec-calc__note" style="margin:0">Stadiul se corelează cu etapele din proiect și cu lista de disponibilitate pe etape.</p>
      <div class="ec-cta__btns" style="margin:0">
        <a class="ec-btn ec-btn--out" href="{r}proiect/#etape">{ic("layer-group")} Etapele proiectului</a>
        <a class="ec-btn ec-btn--out" href="{r}apartamente-iasi/disponibilitate/?etapa=I&amp;status=disponibil">{ic("table-list")} Apartamentele din Etapa I</a>
        <a class="ec-btn ec-btn--out" href="{r}noutati/">{ic("newspaper")} Noutăți din șantier</a>
      </div>
    </div>
  </section>
</div>

<script>
(() => {{
  const redus = matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* cifrele mari urca pana la valoarea reala */
  const nr = [...document.querySelectorAll('.ec-fig b[data-num]')];
  if (nr.length && !redus) {{
    const urca = el => {{
      const brut = el.dataset.num;
      const tinta = parseFloat(brut.replace(/\\./g, '').replace(',', '.'));
      const zec = (brut.split(',')[1] || '').length;
      const sufix = el.textContent.replace(brut, '');
      const t0 = performance.now(), dur = 1100;
      const pas = t => {{
        const p = Math.min((t - t0) / dur, 1);
        const v = tinta * (1 - Math.pow(1 - p, 3));
        el.textContent = v.toLocaleString('ro-RO', {{
          minimumFractionDigits: zec, maximumFractionDigits: zec }}) + sufix;
        if (p < 1) requestAnimationFrame(pas);
      }};
      requestAnimationFrame(pas);
    }};
    const o = new IntersectionObserver(es => es.forEach(x => {{
      if (x.isIntersecting) {{ urca(x.target); o.unobserve(x.target); }}
    }}), {{ threshold: .4 }});
    nr.forEach(x => o.observe(x));
  }}

  /* barele de faza cresc la intrarea in ecran */
  const b = [...document.querySelectorAll('.ec-faza__b span[data-w]')];
  if (b.length) {{
    const o = new IntersectionObserver(es => es.forEach(x => {{
      if (!x.isIntersecting) return;
      x.target.style.width = x.target.dataset.w + '%';
      o.unobserve(x.target);
    }}), {{ threshold: .2 }});
    b.forEach(x => o.observe(x));
  }}
}})();
</script>"""

    return pagina("Stadiul lucrărilor — jurnal de șantier | Emerald City Iași",
                  "Stadiul construcției Emerald City, Iași zona Păcurari: progresul fiecărei "
                  "etape, jurnal lunar cu fotografii datate și vizite pe șantier.",
                  continut, r, schema, "stadiu-lucrari/")


# ====================================================== despre dezvoltator ==
# Datele de portofoliu sunt cele publicate de Green Stone Group pe
# greenstone-group.ro/proiecte/. Se actualizeaza de acolo.
PORTOFOLIU_RO = [
 ("Emerald City", "Iași · în dezvoltare",
  "925 de apartamente în 18 blocuri cu regim 2D+P+3E, pe cinci hectare din care 30,85% "
  "rămâne spațiu verde amenajat. Predare la cheie, vânzare directă de la dezvoltator.",
  [("Apartamente", "925"), ("Blocuri", "18"), ("Etape", "3")],
  ("{r}proiect/", "Vezi proiectul")),
 ("Lapis Residence", "Iași · din 2023",
  "Ansamblu cu piste de biciclete în tot cartierul, panouri fotovoltaice și finisaje "
  "premium. Proiectul a început la finalul lui 2023 și este în curs de dezvoltare.",
  [("Oraș", "Iași"), ("Început", "2023"), ("Stadiu", "În dezvoltare")],
  ("https://www.lapis-residence.ro/", "lapis-residence.ro")),
 ("Onyx Residence", "Iași · din 2024",
  "Prelungirea ansamblului Lapis: 360 de apartamente în 8 blocuri similare ca structură "
  "și dotări, cu spații comerciale la parter. Împreună, cele două ajung la 740 de locuințe.",
  [("Apartamente", "360"), ("Blocuri", "8"), ("Început", "2024")],
  ("https://www.onyx-residence.ro/", "onyx-residence.ro")),
 ("Magnolia Residence", "Sibiu",
  "Faza I, finalizată: 1.132 de apartamente în vile P+2E+M și imobile P+4E și P+7E+R, "
  "plus o clădire comercială. Faza a II-a cuprinde 12 imobile, până la P+3E+ER.",
  [("Apartamente", "1.132"), ("Faza I", "Finalizată"), ("Faza a II-a", "În lucru")],
  ("https://greenstone-group.ro/proiecte/", "greenstone-group.ro")),
]

PORTOFOLIU_INT = [
 ("Apartamente de lux", "Marea Britanie · 2022–2024",
  "Complex cu 100 de apartamente pe cinci etaje — studio, o cameră și două camere, unele "
  "cu birou sau spațiu suplimentar de depozitare.",
  [("Apartamente", "100"), ("Valoare estimată", "25,5 mil. £")],
  ("https://greenstone-group.ro/proiecte/", "greenstone-group.ro")),
 ("Apartamente moderne", "Marea Britanie · 2020–2022",
  "Complex cu 94 de apartamente de înaltă calitate, cu specificații superioare în toate "
  "unitățile.",
  [("Apartamente", "94"), ("Valoare estimată", "29 mil. £")],
  ("https://greenstone-group.ro/proiecte/", "greenstone-group.ro")),
 ("Proiect de referință", "Israel · finalizat",
  "12 clădiri cu regim P+8 și 40.000 m² construiți, la care se adaugă 750 m² de spații "
  "comerciale pentru serviciile din incintă.",
  [("Construit", "40.000 m²"), ("Preț mediu", "5.500 €/m²")],
  ("https://greenstone-group.ro/proiecte/", "greenstone-group.ro")),
 ("Ansamblu rezidențial", "Israel · finalizat în 2016",
  "7 clădiri cu 245 de apartamente de lux și 35.000 m² construiți, într-unul dintre cele "
  "mai importante orașe din Israel.",
  [("Apartamente", "245"), ("Construit", "35.000 m²")],
  ("https://greenstone-group.ro/proiecte/", "greenstone-group.ro")),
 ("Apartamente de lux", "Israel · faza I în 2023",
  "9 clădiri cu 240 de apartamente și 31.500 m² construiți, plus 3.000 m² de spații "
  "comerciale în incintă.",
  [("Apartamente", "240"), ("Comercial", "3.000 m²")],
  ("https://greenstone-group.ro/proiecte/", "greenstone-group.ro")),
 ("Turn de birouri", "Israel · în construcție",
  "Turn de birouri cu aproximativ 40.000 m² de spații comerciale, cu fațadă proiectată "
  "în detaliu și planificare adaptată mediului construit.",
  [("Spații", "≈40.000 m²"), ("Stadiu", "În construcție")],
  ("https://greenstone-group.ro/proiecte/", "greenstone-group.ro")),
]

PRINCIPII = [
 ("city", "Regenerare urbană",
  "Grupul transformă zone degradate sau subutilizate în cartiere locuibile, nu doar în "
  "clădiri noi pe teren liber."),
 ("leaf", "Soluții ecologice",
  "Panouri fotovoltaice, piste de biciclete și spații verzi proiectate de la început, "
  "nu adăugate la final."),
 ("earth-europe", "Experiență internațională",
  "Proiecte în Marea Britanie, Israel și România — expertiză locală cu standarde aduse "
  "din piețe mai exigente."),
 ("handshake", "Vânzare directă",
  "Discuți prețul și termenele cu cel care construiește, fără comision de intermediere."),
]

FAQ_DEZV = [
 ("Cine dezvoltă Emerald City?",
  "Emerald City este dezvoltat de Tala Sapphire S.R.L., companie din Green Stone Group. "
  "Vânzarea se face direct, fără comision de intermediere."),
 ("Ce este Green Stone Group?",
  "Un grup de firme dedicat dezvoltării de proiecte imobiliare și regenerării urbane la "
  "nivel internațional, cu proiecte în Marea Britanie, Israel și România."),
 ("Ce alte proiecte are grupul în Iași?",
  "Lapis Residence, început la finalul lui 2023, și Onyx Residence, prelungirea acestuia, "
  "începută în 2024. Împreună, cele două ansambluri însumează 740 de apartamente."),
 ("Grupul a livrat proiecte finalizate?",
  "Da. Faza I de la Magnolia Residence, în Sibiu, cu 1.132 de apartamente, două complexuri "
  "în Marea Britanie și mai multe ansambluri în Israel, dintre care unul finalizat în 2016."),
 ("Ce înseamnă regenerare urbană?",
  "Transformarea zonelor degradate sau subutilizate ale orașului în spații locuibile, cu "
  "locuințe, facilități comerciale și spații publice — în loc de extinderea orașului pe "
  "teren agricol."),
 ("De ce contează cine este dezvoltatorul?",
  "Garanțiile, termenele și calitatea execuției depind de societatea care semnează "
  "contractul și de proiectele livrate anterior. Un dezvoltator cu ansambluri finalizate, "
  "care pot fi vizitate, poate fi verificat."),
 ("Pot vizita proiectele anterioare?",
  "Da. Ansamblurile din Iași pot fi vizitate; adresele și modul de acces se comunică la "
  "biroul de vânzări."),
 ("Ce garanții primesc la Emerald City?",
  "Structura de rezistență este garantată pe toată durata de existență a clădirii, iar "
  "viciile ascunse 10 ani de la recepție, conform Legii 10/1995 și Codului civil. "
  "Detaliile complete sunt pe pagina „Despre noi”."),
]


def pagina_dezvoltator():
    r = "../"

    ro_ap = 925 + 380 + 360 + 1132  # Emerald City, Lapis, Onyx, Magnolia faza I
    ro_txt = f"{ro_ap:,}".replace(",", ".")

    def _fig(val, et, pic, num=True):
        attr = ' data-num="%s"' % e(val) if num else ""
        return (f'<div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic(pic)}</span>'
                f'<span><b{attr}>{e(val)}</b><em>{e(et)}</em></span></div>')

    figuri = "".join(
        _fig(*x)
        for x in [
            ("3", "Țări", "earth-europe"),
            ("10", "Proiecte", "building"),
            (ro_txt, "Locuințe în România", "city"),
            ("2016", "Primul proiect livrat", "clock-rotate-left", False),
        ])

    def card(nume, loc, desc, perechi, legatura):
        adresa, eticheta = legatura
        adresa = adresa.replace("{r}", r)
        extern = adresa.startswith("http")
        atr = ' target="_blank" rel="noopener"' if extern else ""
        pict = "arrow-up-right-from-square" if extern else "arrow-right"
        return (f'<article class="ec-ref ec-rv">'
                f'<span class="ec-ref__ic">{ic("building-circle-check")}</span>'
                f'<span class="ec-ref__k">{e(loc)}</span>'
                f'<h3>{e(nume)}</h3><p>{e(desc)}</p><dl>'
                + "".join(f"<div><dt>{e(dt)}</dt><dd>{e(dd)}</dd></div>" for dt, dd in perechi)
                + f'</dl><a class="ec-ref__l" href="{e(adresa)}"{atr}>'
                f'{ic(pict)} {e(eticheta)}</a></article>')

    def carduri(lista):
        return "".join(card(*x) for x in lista)

    principii = "".join(
        f'<div class="ec-why__i ec-rv">{ic(pic)}<h3>{e(t)}</h3><p>{e(d)}</p></div>'
        for pic, t, d in PRINCIPII)

    faq = "".join(f"<details><summary>{e(q)}</summary>"
                  f'<div class="ec-faq__a">{e(a)}</div></details>'
                  for q, a in FAQ_DEZV)

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Organization",
             "name": "Green Stone Group",
             "url": "https://greenstone-group.ro/",
             "description": "Grup de firme dedicat dezvoltării de proiecte imobiliare și "
                            "regenerării urbane, cu proiecte în Marea Britanie, Israel și România.",
             "areaServed": ["România", "Marea Britanie", "Israel"],
             "subOrganization": {"@type": "Organization", "name": "Tala Sapphire S.R.L."}},
            {"@type": "FAQPage",
             "mainEntity": [{"@type": "Question", "name": q,
                             "acceptedAnswer": {"@type": "Answer", "text": a}}
                            for q, a in FAQ_DEZV]},
        ]}

    continut = f"""<section class="ec-phero">
  {imagine("gs-ansamblu", "", r, "100vw", eager=True)}
  <div class="ec-phero__veil"></div>
  <div class="ec-wrap ec-phero__in">
    <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Dezvoltator</nav>
    <p class="ec-eyebrow">Dezvoltator</p>
    <h1>Cine construiește Emerald City</h1>
    <p class="ec-phero__sub">
      Tala Sapphire S.R.L., companie din Green Stone Group — un grup care dezvoltă proiecte
      rezidențiale și de regenerare urbană în Marea Britanie, Israel și România. Emerald City
      este al treilea ansamblu al grupului în Iași.
    </p>
    <div class="ec-phero__cta">
      <a class="ec-btn ec-btn--white" href="#portofoliu">{ic("building")} Portofoliu</a>
      <a class="ec-btn ec-btn--outlight" href="{r}despre-emerald-city/#garantii">{ic("shield-halved")} Garanții</a>
    </div>
  </div>
</section>

<div class="ec-figs-wrap">
  <div class="ec-wrap"><div class="ec-figs">{figuri}</div></div>
</div>

<div class="ec-wrap">
  <section class="ec-section" id="grup">
    <div class="ec-shead">
      <div><span class="ec-shead__n">01 — Grupul</span>
        <h2>Green Stone Group, <em>„Delivering Home”</em></h2></div>
      <p class="ec-shead__p">
        Un grup de firme dedicat dezvoltării imobiliare și regenerării urbane, activ pe trei
        piețe.
      </p>
    </div>
    <div class="ec-split" style="margin-top:2.5rem">
      <div class="ec-prose">
        <p>
          Green Stone Group dezvoltă proiecte care îmbină designul contemporan cu soluții
          ecologice. Portofoliul acoperă locuințe, facilități comerciale și spații publice,
          cu accent pe revitalizarea zonelor urbane degradate sau subutilizate — în loc de
          extinderea orașului pe teren liber.
        </p>
        <p>
          Grupul activează în Marea Britanie, Israel și România, ceea ce înseamnă că
          standardele de execuție și de finisaj vin din piețe mai exigente decât cea locală.
          În România a livrat faza I de la Magnolia Residence, în Sibiu, cu 1.132 de
          apartamente, și dezvoltă în Iași ansamblurile Lapis și Onyx Residence.
        </p>
        <p>
          Emerald City este al treilea proiect al grupului în Iași și cel mai mare: 925 de
          apartamente pe cinci hectare, dezvoltat prin compania Tala Sapphire S.R.L.
        </p>
      </div>
      <figure style="margin:0">
        {imagine("gs-israel-01", "Ansamblu rezidențial Green Stone Group în Israel", r,
                 "(min-width: 62rem) 46vw, 100vw")}
      </figure>
    </div>
  </section>

  <section class="ec-section" id="principii" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">02 — Principii</span>
        <h2>Cum lucrează <em>grupul</em></h2></div>
      <p class="ec-shead__p">Patru constante ale proiectelor grupului.</p>
    </div>
    <div class="ec-why" style="margin-top:2.5rem">{principii}</div>
  </section>


  <section class="ec-section" id="galerie" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">03 — Galerie</span>
        <h2>Din proiectele <em>grupului</em></h2></div>
      <p class="ec-shead__p">
        Imagini din ansamblurile Green Stone Group, publicate de grup.
      </p>
    </div>
    <div class="ec-pgal" style="margin-top:2.5rem">
      <figure class="ec-pgal__i ec-rv">
        {imagine("gs-onyx", "Ansamblul Onyx Residence din Iași", r, "(min-width: 70rem) 25vw, 50vw")}
        <figcaption class="ec-pgal__c"><b>Onyx Residence</b><span>Iași</span></figcaption>
      </figure>
      <figure class="ec-pgal__i ec-rv">
        {imagine("gs-uk", "Complex de apartamente dezvoltat în Marea Britanie", r, "(min-width: 70rem) 25vw, 50vw")}
        <figcaption class="ec-pgal__c"><b>Complex de apartamente</b><span>Marea Britanie</span></figcaption>
      </figure>
      <figure class="ec-pgal__i ec-rv">
        {imagine("gs-israel-02", "Ansamblu rezidențial dezvoltat în Israel", r, "(min-width: 70rem) 25vw, 50vw")}
        <figcaption class="ec-pgal__c"><b>Ansamblu rezidențial</b><span>Israel</span></figcaption>
      </figure>
      <figure class="ec-pgal__i ec-rv">
        {imagine("gs-birouri", "Clădire de birouri dezvoltată de Green Stone Group", r, "(min-width: 70rem) 25vw, 50vw")}
        <figcaption class="ec-pgal__c"><b>Spații de birouri</b><span>Portofoliu comercial</span></figcaption>
      </figure>
    </div>
  </section>

  <section class="ec-section" id="portofoliu" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">04 — România</span>
        <h2>Proiectele <em>din țară</em></h2></div>
      <p class="ec-shead__p">
        {ro_txt} de locuințe în Iași și Sibiu, livrate sau în dezvoltare.
      </p>
    </div>
    <div class="ec-refs" style="margin-top:2.5rem">{carduri(PORTOFOLIU_RO)}</div>
  </section>
</div>

<section class="ec-band" id="international">
  <div class="ec-wrap">
    <div class="ec-section">
      <div class="ec-shead">
        <div><span class="ec-shead__n" style="color:var(--ec-brass)">05 — Internațional</span>
          <h2>Proiectele <em>din Marea Britanie și Israel</em></h2></div>
        <p class="ec-shead__p">
          Șase ansambluri rezidențiale și de birouri, finalizate sau în construcție.
        </p>
      </div>
      <div class="ec-refs" style="margin-top:2.5rem">{carduri(PORTOFOLIU_INT)}</div>
    </div>
  </div>
</section>

<div class="ec-wrap">
  <section class="ec-section" id="emerald">
    <div class="ec-shead">
      <div><span class="ec-shead__n">06 — Emerald City</span>
        <h2>Elemente <em>verificabile independent</em></h2></div>
      <p class="ec-shead__p">
        Elementele care pot fi verificate independent, înainte de semnare.
      </p>
    </div>
    <div class="ec-docs" style="margin-top:2.5rem">
      <div class="ec-docs__i ec-rv"><span class="ec-docs__c">{ic("check")}</span>
        <span><b>Proiecte care pot fi vizitate</b>
        <em>Lapis și Onyx Residence se află în Iași și pot fi vizitate.</em></span></div>
      <div class="ec-docs__i ec-rv"><span class="ec-docs__c">{ic("check")}</span>
        <span><b>Documentație completă</b>
        <em>Autorizația de construire, certificatul de urbanism și planșele, la cerere.</em></span></div>
      <div class="ec-docs__i ec-rv"><span class="ec-docs__c">{ic("check")}</span>
        <span><b>Garanții scrise</b>
        <em>Structura pe toată durata clădirii, viciile ascunse 10 ani, conform legii.</em></span></div>
      <div class="ec-docs__i ec-rv"><span class="ec-docs__c">{ic("check")}</span>
        <span><b>Stadiul publicat lunar</b>
        <em>Jurnal de șantier cu fotografii datate, pentru fiecare etapă.</em></span></div>
      <div class="ec-docs__i ec-rv"><span class="ec-docs__c">{ic("check")}</span>
        <span><b>Prețuri afișate</b>
        <em>Toate cele 925 de apartamente, cu preț, suprafață și disponibilitate.</em></span></div>
      <div class="ec-docs__i ec-rv"><span class="ec-docs__c">{ic("check")}</span>
        <span><b>Fără intermediari</b>
        <em>Contract direct cu dezvoltatorul, fără comision de agenție.</em></span></div>
    </div>
  </section>

  <section class="ec-section" id="date" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">07 — Date</span>
        <h2>Datele <em>proiectului</em></h2></div>
      <p class="ec-shead__p">
        Cine semnează, cine proiectează și în baza cărei documentații se construiește.
      </p>
    </div>
    <dl class="ec-specs" style="margin-top:2.5rem">
      <div class="ec-spec"><dt>Beneficiar</dt><dd>Tala Sapphire S.R.L.</dd></div>
      <div class="ec-spec"><dt>Grup</dt><dd>Green Stone Group</dd></div>
      <div class="ec-spec"><dt>Proiect</dt><dd>266/2023</dd></div>
      <div class="ec-spec"><dt>Fază</dt><dd>D.T.A.C.</dd></div>
      <div class="ec-spec"><dt>Proiectant</dt><dd>S.C. C.A.D. S.R.L., Iași</dd></div>
      <div class="ec-spec"><dt>Șef de proiect</dt><dd>arh. Ovidiu M. Murgu</dd></div>
      <div class="ec-spec"><dt>Certificat de urbanism</dt><dd>194/23.06.2023</dd></div>
      <div class="ec-spec"><dt>Amplasament</dt><dd>Str. Ion Nistor, Iași</dd></div>
    </dl>
  </section>

  <section class="ec-section" id="intrebari" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">08 — Întrebări</span>
        <h2>Despre grup <em>și portofoliu</em></h2></div>
      <p class="ec-shead__p">
        {len(FAQ_DEZV)} întrebări despre cine construiește și ce a livrat până acum.
      </p>
    </div>
    <div class="ec-faq" style="margin-top:2.5rem">{faq}</div>
  </section>

  {showroom(r, "09")}
</div>

<script>
(() => {{
  const nr = [...document.querySelectorAll('.ec-fig b[data-num]')];
  if (!nr.length) return;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const urca = el => {{
    const brut = el.dataset.num;
    const tinta = parseFloat(brut.replace(/\\./g, '').replace(',', '.'));
    const zec = (brut.split(',')[1] || '').length;
    const t0 = performance.now(), dur = 1100;
    const pas = t => {{
      const p = Math.min((t - t0) / dur, 1);
      const v = tinta * (1 - Math.pow(1 - p, 3));
      el.textContent = v.toLocaleString('ro-RO', {{
        minimumFractionDigits: zec, maximumFractionDigits: zec }});
      if (p < 1) requestAnimationFrame(pas);
    }};
    requestAnimationFrame(pas);
  }};
  const o = new IntersectionObserver(es => es.forEach(x => {{
    if (x.isIntersecting) {{ urca(x.target); o.unobserve(x.target); }}
  }}), {{ threshold: .4 }});
  nr.forEach(x => o.observe(x));
}})();
</script>"""

    return pagina("Dezvoltator — Green Stone Group | Emerald City Iași",
                  "Tala Sapphire S.R.L., companie din Green Stone Group, cu proiecte în Marea "
                  "Britanie, Israel și România. Portofoliu și datele proiectului.",
                  continut, r, schema, "despre-dezvoltator/")


# =============================================================== proiect ==
def mp_ro(n, zec=2):
    """15070.5 -> "15.070,50 m²" — punct la mii, virgula la zecimale."""
    intreg, _, frac = f"{n:,.{zec}f}".partition(".")
    return intreg.replace(",", ".") + ("," + frac if zec else "") + " m²"

# Nivelurile unui bloc, de sus in jos. Inaltimile sunt cele din documentatie:
# atic la 18,00 m fata de cota terenului.
NIVELURI = [
 ("solar-panel", "Terasă tehnică", "18,00 m",
  "Atic la cota maximă aprobată. Panourile fotovoltaice și echipamentele de instalații "
  "stau aici, nu pe fațadă.", False),
 ("building", "Etajul 3", "14,40 m",
  "Ultimul nivel locuibil, fără apartament deasupra.", False),
 ("building", "Etajul 2", "11,10 m",
  "Nivel curent, cu apartamente de 1, 2 și 3 camere pe același palier.", False),
 ("building", "Etajul 1", "7,80 m",
  "Nivel curent. Distanțele dintre blocuri permit iluminare naturală pe două laturi.", False),
 ("house-chimney", "Parterul", "±0,00 m",
  "Apartamentele de aici au curte proprie, între 13 și 51 m². La blocurile 6 și 12, "
  "parterul găzduiește spațiile comerciale.", False),
 ("square-parking", "Demisolul 1", "−3,00 m",
  "Parcare subterană și accesul cu liftul direct din parcaj în scară.", True),
 ("box-archive", "Demisolul 2", "−6,00 m",
  "Boxe de depozitare și spațiile tehnice ale blocului.", True),
]

# Bilantul terenului: 50.235 m² in total.
BILANT = [
 ("Construit la sol", 15070.5, "30%", "var(--ec-emerald)",
  "Amprenta celor 18 blocuri. Procentul de ocupare a terenului aprobat este de 30%."),
 ("Spațiu verde amenajat", 15501.8, "30,85%", "#6E9C7E",
  "Parc, alei, locuri de joacă și zonele verzi dintre blocuri. Nu este teren rămas liber, "
  "ci suprafață proiectată."),
 ("Circulații și parcaje", 19662.7, "39,15%", "#B8934F",
  "Drumurile de incintă, cele 682 de locuri de parcare la suprafață și platformele tehnice."),
]

ETAPE = [
 ("Blocurile 1–6",   "Etapa I",   6, 322, "Include spațiul comercial de la parterul blocului 6."),
 ("Blocurile 7–14",  "Etapa II",  8, 423, "Cea mai mare etapă, cu acces direct la parcul central."),
 ("Blocurile 15–18", "Etapa III", 4, 180, "Blocurile cu perspectiva cea mai deschisă spre oraș."),
]

DOCUMENTE_PROIECT = [
 ("Proiect", "266/2023"),
 ("Fază", "D.T.A.C."),
 ("Data", "06/2023"),
 ("Certificat de urbanism", "194/23.06.2023"),
 ("Proiectant", "S.C. C.A.D. S.R.L., Iași"),
 ("Șef de proiect", "arh. Ovidiu M. Murgu"),
 ("Beneficiar", "Tala Sapphire S.R.L."),
 ("Regim de înălțime", "2D+P+3E"),
]


FAQ_PROIECT = [
 ("Ce regim de înălțime au blocurile?",
  "2D+P+3E: două demisoluri, parter și trei etaje. Înălțimea maximă la atic este de 18,00 metri, "
  "aceeași pentru toate cele 18 blocuri."),
 ("Ce se află în cele două demisoluri?",
  "Primul demisol găzduiește parcarea subterană, cu 258 de locuri și acces cu liftul direct în "
  "scară. Al doilea demisol cuprinde boxele de depozitare și spațiile tehnice."),
 ("Ce înseamnă POT 30% și CUT 1,80?",
  "POT este procentul din teren pe care se poate construi la sol: 30% din cele 50.235 m², adică "
  "aproximativ 15.070 m². CUT este raportul dintre suprafața desfășurată și suprafața terenului; "
  "1,80 este valoarea aprobată pentru acest amplasament."),
 ("Cât spațiu verde are ansamblul?",
  "15.501,80 m², adică 30,85% din suprafața terenului — mai mult decât amprenta construită la sol."),
 ("În câte etape se construiește?",
  "În trei: 6 blocuri și 322 de apartamente în Etapa I, 8 blocuri și 423 de apartamente în "
  "Etapa II, 4 blocuri și 180 de apartamente în Etapa III."),
 ("Câte locuri de parcare sunt?",
  "940 în total: 258 subterane, în primul demisol, și 682 la suprafață, în incintă."),
 ("Ce spații comerciale sunt prevăzute?",
  "Două, la parterul blocurilor 6 și 12: 722,22 m² și 125,82 m², în total 848,04 m²."),
 ("Cine a proiectat ansamblul?",
  "Proiectul 266/2023, faza D.T.A.C., a fost întocmit de S.C. C.A.D. S.R.L. din Iași, cu "
  "arh. Ovidiu M. Murgu ca șef de proiect, pentru beneficiarul Tala Sapphire S.R.L."),
 ("Pot vedea documentația de autorizare?",
  "Da. Autorizația de construire, certificatul de urbanism și planșele pot fi consultate la "
  "biroul de vânzări, la cerere."),
 ("Fiecare bloc are lift?",
  "Da. Toate cele 18 blocuri au lift, care coboară până în primul demisol, unde se află "
  "parcarea subterană, astfel încât accesul din parcaj în scară se face direct."),
]


def _svg_sectiune():
    """Sectiune verticala schematica printr-un bloc: 2D+P+3E, atic la 18,00 m."""
    benzi = [
        # (y, inaltime, eticheta, opacitate, sub-teren)
        (34,  16, "Terasă tehnică", .30, False),
        (50,  50, "Etaj 3",         .92, False),
        (100, 50, "Etaj 2",         .84, False),
        (150, 50, "Etaj 1",         .76, False),
        (200, 56, "Parter",         .68, False),
        (256, 54, "Demisol 1",      .22, True),
        (310, 54, "Demisol 2",      .16, True),
    ]
    out = []
    for y, h, et, op, sub in benzi:
        umplere = "#B8934F" if sub else "#1F3E36"
        out.append(
            f'<rect x="96" y="{y}" width="196" height="{h - 2}" rx="2" '
            f'fill="{umplere}" fill-opacity="{op}"/>'
            f'<text x="194" y="{y + h / 2 + 1}" text-anchor="middle" '
            f'fill="{"#1F3E36" if (sub or op < .4) else "#fff"}" font-size="11" '
            f'font-family="Inter, sans-serif" font-weight="500">{et}</text>')
    benzi_svg = "".join(out)
    return f"""<svg viewBox="0 0 360 380" role="img"
     aria-label="Secțiune verticală printr-un bloc: două demisoluri, parter și trei etaje, atic la 18 metri">
  <!-- cota terenului -->
  <line x1="24" y1="256" x2="336" y2="256" stroke="#1F3E36" stroke-width="1.5" stroke-dasharray="5 4"/>
  <text x="336" y="252" text-anchor="end" fill="#1F3E36" font-size="10"
        font-family="Inter Tight, sans-serif" font-weight="600">±0,00</text>
  <text x="24" y="270" fill="#1F3E36" font-size="8.5" fill-opacity=".55"
        font-family="Inter, sans-serif" letter-spacing="1.1">COTA TERENULUI</text>
  {benzi_svg}
  <!-- linia de cota, de la atic la teren -->
  <line x1="66" y1="34" x2="66" y2="256" stroke="#B8934F" stroke-width="1.5"/>
  <path d="M62 39l4-5 4 5M62 251l4 5 4-5" stroke="#B8934F" stroke-width="1.5" fill="none"/>
  <text x="58" y="149" text-anchor="middle" fill="#B8934F" font-size="12"
        font-family="Inter Tight, sans-serif" font-weight="600"
        transform="rotate(-90 58 149)">18,00 m</text>
</svg>"""


def pagina_proiect(unitati):
    r = "../"
    total = len(unitati)
    pe_camere = defaultdict(list)
    for u in unitati:
        pe_camere[u["nr_camere"]].append(u)

    figuri = "".join(
        f'<div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic(pic)}</span>'
        f'<span><b data-num="{e(val)}">{e(val)}{e(suf)}</b><em>{e(et)}</em></span></div>'
        for val, suf, et, pic in [
            ("18", "", "Blocuri 2D+P+3E", "city"),
            (str(total), "", "Apartamente", "building"),
            ("5,02", " ha", "Suprafață teren", "ruler-combined"),
            ("3", "", "Etape de construcție", "layer-group"),
        ])

    niveluri = "".join(
        f'<div class="ec-niv__i{" ec-niv__i--sub" if sub else ""} ec-rv">'
        f'<span class="ec-niv__c">{ic(pic)}</span>'
        f'<span><b>{e(nume)}</b><em>{e(desc)}</em></span>'
        f'<span class="ec-niv__h">{e(cota)}</span></div>'
        for pic, nume, cota, desc, sub in NIVELURI)

    teren_total = sum(x[1] for x in BILANT)
    bare = "".join(
        f'<span class="ec-bilant__s" style="flex:{x[1]};background:{x[3]}">{e(x[2])}</span>'
        for x in BILANT)
    legenda = "".join(
        f'<div class="ec-bilant__l ec-rv"><i style="background:{x[3]}"></i>'
        f'<b>{mp_ro(x[1])}</b><u>{e(x[2])} din teren</u>'
        f'<span>{e(x[0])} — {e(x[4])}</span></div>'
        for x in BILANT)

    max_ap = max(x[3] for x in ETAPE)
    etape = "".join(
        f'<article class="ec-etapa ec-rv"><span class="ec-etapa__n">{e(cod)}</span>'
        f'<h3>{e(nume)}</h3>'
        f'<div class="ec-etapa__cif">'
        f'<div><b>{bl}</b><span>Blocuri</span></div>'
        f'<div><b>{ap}</b><span>Apartamente</span></div>'
        f'<div><b>{round(ap * 100 / total)}%</b><span>Din ansamblu</span></div></div>'
        f'<div class="ec-etapa__bar"><i style="width:{ap * 100 / max_ap:.0f}%"></i></div>'
        f'<p>{e(obs)}</p></article>'
        for cod, nume, bl, ap, obs in ETAPE)

    max_cam = max(len(v) for v in pe_camere.values())
    distr = "".join(
        f'<div class="ec-distr__i ec-rv">'
        f'<span class="ec-distr__t">{ic("door-open")}{e(camere_txt(k).capitalize())}</span>'
        f'<span class="ec-distr__bar"><i data-w="{len(v) * 100 / max_cam:.0f}"></i></span>'
        f'<span class="ec-distr__n">{len(v)}<small>{round(len(v) * 100 / total)}% din total</small></span>'
        f'<span class="ec-distr__m"><b>{min(x["su_utila"] for x in v):.0f}–'
        f'{max(x["su_utila"] for x in v):.0f} m²</b>de la '
        f'{euro(min(x["pret_eur"] for x in v))}</span></div>'
        for k, v in sorted(pe_camere.items()))

    docs = "".join(f'<div class="ec-spec"><dt>{e(a)}</dt><dd>{e(b)}</dd></div>'
                   for a, b in DOCUMENTE_PROIECT)

    faq = "".join(f"<details><summary>{e(q)}</summary>"
                  f'<div class="ec-faq__a">{e(a)}</div></details>'
                  for q, a in FAQ_PROIECT)

    cu_curte = sum(1 for u in unitati if u["su_curte"] > 0)

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebPage", "name": "Proiectul Emerald City",
             "url": "https://emerald-city.ro/proiect/"},
            {"@type": "FAQPage",
             "mainEntity": [{"@type": "Question", "name": q,
                             "acceptedAnswer": {"@type": "Answer", "text": a}}
                            for q, a in FAQ_PROIECT]},
        ]}

    continut = f"""<section class="ec-phero">
  {imagine("hero-living", "", r, "100vw", eager=True)}
  <div class="ec-phero__veil"></div>
  <div class="ec-wrap ec-phero__in">
    <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Proiect</nav>
    <p class="ec-eyebrow">Proiect</p>
    <h1>18 blocuri, nu 4 turnuri</h1>
    <p class="ec-phero__sub">
      Aceeași suprafață construită se poate obține din câteva turnuri sau din 18 blocuri
      de patru niveluri. A doua variantă consumă mai mult teren, dar modifică decisiv
      iluminarea naturală, nivelul de zgomot și distanțele dintre fațade.
    </p>
    <div class="ec-phero__cta">
      <a class="ec-btn ec-btn--white" href="#regim">{ic("layer-group")} Regimul de înălțime</a>
      <a class="ec-btn ec-btn--outlight" href="{r}apartamente-iasi-pacurari/">{ic("location-dot")} Amplasament</a>
    </div>
  </div>
</section>

<div class="ec-figs-wrap">
  <div class="ec-wrap"><div class="ec-figs">{figuri}</div></div>
</div>


<div class="ec-wrap">
  <section class="ec-section" id="concept">
    <div class="ec-shead">
      <div><span class="ec-shead__n">01 — Concept</span>
        <h2>De ce <em>patru niveluri</em></h2></div>
      <p class="ec-shead__p">
        Regimul de înălțime se stabilește o singură dată, la autorizare, și determină calitatea locuirii pe toată durata de exploatare.
      </p>
    </div>
    <div class="ec-split" style="margin-top:2.5rem">
      <div class="ec-prose">
        <p>
          Un ansamblu de 925 de apartamente poate fi dezvoltat în patru turnuri sau în
          18 blocuri cu regim 2D+P+3E. Prima variantă consumă mai puțin teren și are
          costuri mai mici. A fost aleasă a doua.
        </p>
        <p>
          Consecințele sunt măsurabile. Numărul redus de apartamente pe scară limitează
          încărcarea lifturilor și a spațiilor comune. Înălțimea mică a clădirilor reduce
          umbrirea reciprocă, astfel încât iluminarea naturală ajunge inclusiv la parter.
          Distanțele dintre blocuri depășesc minimul impus de normativ.
        </p>
        <p>
          Cele două demisoluri preiau parcarea și depozitarea, astfel încât spațiul dintre
          blocuri rămâne destinat aleilor, parcului și locurilor de joacă. {cu_curte}
          dintre apartamentele de la parter au curte proprie, între 13 și 51 m².
        </p>
      </div>
      <figure style="margin:0">
        {imagine("living-02", "Apartament finisat în ansamblul Emerald City", r,
                 "(min-width: 62rem) 46vw, 100vw")}
      </figure>
    </div>
  </section>

  <section class="ec-section" id="regim" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">02 — Regim de înălțime</span>
        <h2>Distribuția <em>pe niveluri</em></h2></div>
      <p class="ec-shead__p">
        2D+P+3E, cu aticul la 18,00 m. Același regim la toate cele 18 blocuri,
        fără excepții și fără etaje retrase.
      </p>
    </div>
    <div class="ec-sectiune" style="margin-top:2.5rem">
      <figure class="ec-sectiune__fig">
        {_svg_sectiune()}
        <figcaption>Secțiune schematică · cotele sunt orientative</figcaption>
      </figure>
      <div class="ec-niv">{niveluri}</div>
    </div>
  </section>

  <section class="ec-section" id="teren" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">03 — Bilanțul terenului</span>
        <h2>Cum se împart <em>cele 5 hectare</em></h2></div>
      <p class="ec-shead__p">
        50.235 m² în total. Spațiul verde amenajat depășește amprenta construită
        la sol — raport pe care puține ansambluri noi din Iași îl au.
      </p>
    </div>
    <div class="ec-bilant" style="margin-top:2.5rem">
      <div class="ec-bilant__bar">{bare}</div>
      <div class="ec-bilant__leg">{legenda}</div>
    </div>
    <dl class="ec-specs" style="margin-top:var(--ec-gap)">
      <div class="ec-spec"><dt>Suprafață teren</dt><dd>{mp_ro(teren_total, 0)}</dd></div>
      <div class="ec-spec"><dt>POT aprobat</dt><dd>30%</dd></div>
      <div class="ec-spec"><dt>CUT aprobat</dt><dd>1,80</dd></div>
      <div class="ec-spec"><dt>Înălțime maximă</dt><dd>18,00 m</dd></div>
    </dl>
  </section>
</div>

<section class="ec-band" id="etape">
  <div class="ec-wrap">
    <div class="ec-section">
      <div class="ec-shead">
        <div><span class="ec-shead__n" style="color:var(--ec-brass)">04 — Etape</span>
          <h2>Ansamblul se ridică <em>în trei etape</em></h2></div>
        <p class="ec-shead__p">
          Fiecare etapă se finalizează și se predă independent, cu spațiile verzi
          aferente amenajate, nu lăsate pentru final.
        </p>
      </div>
      <div class="ec-etape" style="margin-top:2.5rem">{etape}</div>
    </div>
  </div>
</section>

<div class="ec-wrap">
  <section class="ec-section" id="apartamente">
    <div class="ec-shead">
      <div><span class="ec-shead__n">05 — Apartamente</span>
        <h2>Cum se împart <em>cele {total} de locuințe</em></h2></div>
      <p class="ec-shead__p">
        5 compartimentări, de la garsonieră la 3 camere cu două grupuri sanitare.
        Fiecare apartament are balcon.
      </p>
    </div>
    <div class="ec-distr" style="margin-top:2.5rem">{distr}</div>
    <div class="ec-center" style="margin-top:2rem">
      <a class="ec-btn" href="{r}apartamente-iasi/disponibilitate/">{ic("table-list")} Toate cele {total} de apartamente</a>
      <a class="ec-btn ec-btn--out" href="{r}apartamente-iasi/">{ic("compass-drafting")} Compartimentări</a>
    </div>
  </section>

  <section class="ec-section" id="parcare" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">06 — Parcare și depozitare</span>
        <h2>940 de locuri, <em>258 sub clădiri</em></h2></div>
      <p class="ec-shead__p">
        Parcarea subterană este prevăzută din proiect, cu acces direct cu liftul din parcaj în scară.
      </p>
    </div>
    <div class="ec-why" style="margin-top:2.5rem">
      <div class="ec-why__i ec-rv">{ic("square-parking")}
        <h3>258 locuri subterane</h3>
        <p>În primul demisol al fiecărui bloc, cu acces cu liftul direct în scară.</p></div>
      <div class="ec-why__i ec-rv">{ic("car")}
        <h3>682 locuri la suprafață</h3>
        <p>În incintă, de-a lungul drumurilor interioare, separate de zonele de joacă.</p></div>
      <div class="ec-why__i ec-rv">{ic("box-archive")}
        <h3>Boxe de depozitare</h3>
        <p>În al doilea demisol, pentru bagaje, biciclete și lucrurile de sezon.</p></div>
      <div class="ec-why__i ec-rv">{ic("charging-station")}
        <h3>Preechipare pentru încărcare</h3>
        <p>Traseele electrice sunt pregătite din construcție pentru stații de încărcare auto.</p></div>
    </div>
  </section>

  <section class="ec-section" id="comercial" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">07 — Spații comerciale</span>
        <h2>848 m² <em>la parter</em></h2></div>
      <p class="ec-shead__p">
        Două spații comerciale în incintă, destinate serviciilor de proximitate.
      </p>
    </div>
    <dl class="ec-specs" style="margin-top:2.5rem">
      <div class="ec-spec"><dt>Blocul 6</dt><dd>722,22 m²</dd></div>
      <div class="ec-spec"><dt>Blocul 12</dt><dd>125,82 m²</dd></div>
      <div class="ec-spec"><dt>Total comercial</dt><dd>848,04 m²</dd></div>
      <div class="ec-spec"><dt>Amplasare</dt><dd>La parter, cu acces din incintă</dd></div>
    </dl>
  </section>

  <section class="ec-section" id="documentatie" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">08 — Documentație</span>
        <h2>Proiectul <em>și echipa</em></h2></div>
      <p class="ec-shead__p">
        Datele de autorizare. Documentele pot fi consultate la biroul de vânzări.
      </p>
    </div>
    <dl class="ec-specs" style="margin-top:2.5rem">{docs}</dl>
    <div class="ec-center" style="margin-top:2rem">
      <a class="ec-btn ec-btn--out" href="{r}despre-emerald-city/#garantii">{ic("shield-halved")} Garanții și documente predate</a>
      <a class="ec-btn ec-btn--out" href="{r}stadiu-lucrari/">{ic("helmet-safety")} Jurnal de șantier</a>
    </div>
  </section>

  <section class="ec-section" id="intrebari" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">09 — Întrebări</span>
        <h2>Despre proiect <em>și indicatori</em></h2></div>
      <p class="ec-shead__p">
        {len(FAQ_PROIECT)} întrebări despre cum este gândit ansamblul, cu cifrele din documentație.
      </p>
    </div>
    <div class="ec-faq" style="margin-top:2.5rem">{faq}</div>
  </section>

  {showroom(r, "10")}
</div>

<script>
/* cifrele mari urca pana la valoarea reala, o singura data */
(() => {{
  const nr = [...document.querySelectorAll('.ec-fig b[data-num]')];
  if (nr.length && !matchMedia('(prefers-reduced-motion: reduce)').matches) {{
    const urca = el => {{
      const brut = el.dataset.num;
      const tinta = parseFloat(brut.replace(/\\./g, '').replace(',', '.'));
      const zec = (brut.split(',')[1] || '').length;
      const sufix = el.textContent.replace(brut, '');
      const t0 = performance.now(), dur = 1100;
      const pas = t => {{
        const p = Math.min((t - t0) / dur, 1);
        const v = tinta * (1 - Math.pow(1 - p, 3));
        el.textContent = v.toLocaleString('ro-RO', {{
          minimumFractionDigits: zec, maximumFractionDigits: zec }}) + sufix;
        if (p < 1) requestAnimationFrame(pas);
      }};
      requestAnimationFrame(pas);
    }};
    const o = new IntersectionObserver(es => es.forEach(x => {{
      if (x.isIntersecting) {{ urca(x.target); o.unobserve(x.target); }}
    }}), {{ threshold: .4 }});
    nr.forEach(x => o.observe(x));
  }}
}})();

/* barele de distributie cresc la intrarea in ecran */
(() => {{
  const b = [...document.querySelectorAll('.ec-distr__bar i[data-w]')];
  if (!b.length) return;
  const o = new IntersectionObserver(es => es.forEach(x => {{
    if (!x.isIntersecting) return;
    x.target.style.width = x.target.dataset.w + '%';
    o.unobserve(x.target);
  }}), {{ threshold: .3 }});
  b.forEach(x => o.observe(x));
}})();
</script>"""

    return pagina(f"Proiectul Emerald City — {total} de apartamente în 18 blocuri | Iași",
                  f"Ansamblul Emerald City din Iași: 18 blocuri cu regim 2D+P+3E, {total} de "
                  "apartamente, 5 hectare, indicatori urbanistici și etape.",
                  continut, r, schema, "proiect/")


# ============================================================== finisaje ==
# Fisa de finisaje (FINISAJE) e definita o singura data, langa pagina
# "Despre noi", si e folosita de ambele pagini.
CAMERE_FIN = [
 ("living-01", "Living și dining", [
   "Parchet laminat de 10 mm, clasă de trafic intens",
   "Încălzire în pardoseală, fără calorifere pe pereți",
   "Pereți gletuiți și vopsiți lavabil",
   "Tâmplărie PVC cu 7 camere, geam tripan",
   "Prize și întrerupătoare montate",
 ]),
 ("bucatarie-01", "Bucătărie", [
   "Gresie montată pe toată suprafața",
   "Racorduri pregătite pentru chiuvetă și mașina de spălat vase",
   "Circuit electric dedicat, cu siguranță proprie",
   "Priză pentru plită și cuptor",
   "Preechipare pentru hotă",
 ]),
 ("dormitor-01", "Dormitor", [
   "Parchet laminat de 10 mm",
   "Încălzire în pardoseală, cu reglaj pe cameră",
   "Ușă interioară montată, cu toc și feronerie",
   "Pereți finisați, gata de mobilat",
   "Tâmplărie cu geam tripan și sticlă Low-E",
 ]),
 ("baie-01", "Grup sanitar", [
   "Gresie și faianță montate",
   "Vas de toaletă și rezervor",
   "Lavoar cu baterie",
   "Baterie și racorduri pentru duș sau cadă",
   "Ventilație și priză cu protecție",
 ]),
 ("hol-01", "Hol și intrare", [
   "Ușă metalică de intrare, izolată, cu închidere în mai multe puncte",
   "Videointerfon cu post interior",
   "Tablou electric echipat și etichetat",
   "Parchet sau gresie, după compartimentare",
   "Spațiu de depozitare la compartimentările care îl includ",
 ]),
 ("living-02", "Balcon și curte", [
   "Balcon la fiecare apartament",
   "Curte proprie la parter, între 13 și 51 m²",
   "Pardoseală exterioară antiderapantă",
   "Balustradă montată",
   "Priză exterioară la apartamentele cu curte",
 ]),
]


COMPARATIE_FIN = [
 ("Pardoseli", "Montate", "De cumpărat și montat", "Șapă brută"),
 ("Gresie și faianță", "Montate", "De cumpărat și montat", "Nimic"),
 ("Obiecte sanitare", "Montate", "De cumpărat și montat", "Nimic"),
 ("Pereți", "Gletuiți și vopsiți", "Tencuiți, de gletuit", "Zidărie brută"),
 ("Uși interioare", "Montate", "De cumpărat și montat", "Goluri"),
 ("Instalație electrică", "Cu aparataj montat", "Trasă, fără aparataj", "Doar tuburi"),
 ("Încălzire", "În pardoseală, funcțională", "Distribuție, fără centrală", "Nimic"),
 ("Timp până te muți", "Imediat după recepție", "2–4 luni de lucrări", "6–12 luni de lucrări"),
]

FAQ_FIN = [
 ("Ce înseamnă predare la cheie?",
  "Apartamentul se predă complet finisat: pardoseli montate, pereți gletuiți și vopsiți, "
  "grup sanitar echipat, uși montate, instalație electrică cu aparataj și încălzire în "
  "pardoseală funcțională. Este gata de mobilat la recepție."),
 ("Finisajele sunt incluse în preț?",
  "Da. Prețul afișat include TVA și toate cele 10 poziții de finisaj. Nu există costuri "
  "suplimentare pentru execuția lor."),
 ("Ce nu este inclus?",
  "Mobilierul, electrocasnicele, corpurile de iluminat decorative și amenajarea curții. "
  "Racordurile și circuitele pentru ele sunt însă pregătite."),
 ("Pot schimba finisajele?",
  "Modificările se analizează la biroul de vânzări, în funcție de faza de execuție a "
  "blocului. Numărul de opțiuni disponibile scade pe măsură ce lucrările avansează."),
 ("Ce garanție am pentru finisaje?",
  "Finisajele sunt garantate conform anexei tehnice a contractului, iar instalațiile și "
  "echipamentele conform garanției fiecărui producător. Structura și viciile ascunse sunt "
  "acoperite separat, prin lege."),
 ("De ce încălzire în pardoseală și nu calorifere?",
  "Căldura se distribuie uniform de la sol în sus și funcționează la temperatură joasă, "
  "deci consumă mai puțin. În plus, peretele rămâne liber pentru mobilier."),
 ("Ce înseamnă tâmplărie cu 7 camere?",
  "Numărul de camere de aer din profilul ferestrei. Șapte camere, combinate cu geam "
  "tripan și sticlă Low-E, izolează termic și fonic la nivelul cerut clădirilor noi."),
 ("Cât economisesc cu centrala în condensație?",
  "Până la 35% la consumul de gaz față de o centrală clasică, pentru că recuperează "
  "căldura din gazele de ardere în loc să o evacueze pe horn."),
]


def pagina_finisaje():
    r = "../"

    figuri = "".join(
        f'<div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic(pic)}</span>'
        f'<span><b>{e(val)}</b><em>{e(et)}</em></span></div>'
        for val, et, pic in [
            (str(len(FINISAJE)), "Poziții incluse", "list-check"),
            ("10 mm", "Parchet laminat", "grip-lines"),
            ("7 camere", "Tâmplărie PVC", "border-all"),
            ("35%", "Economie la gaz", "gauge-high"),
        ])

    fisa = "".join(
        f'<div class="ec-fisa__i ec-rv"><span class="ec-fisa__ic">{ic(k)}</span>'
        f'<span><b>{e(nume)}</b><span class="ec-fisa__s">{e(spec)}</span>'
        f'<span class="ec-fisa__d">{e(desc)}</span></span></div>'
        for k, nume, spec, desc in FINISAJE)

    camere = "".join(
        f'<article class="ec-cam ec-rv">'
        f'<figure>{imagine(img, "Finisaje " + nume.lower() + " la Emerald City", r, "(min-width: 64rem) 32vw, (min-width: 44rem) 48vw, 100vw")}</figure>'
        f'<div class="ec-cam__b"><h3>{e(nume)}</h3><ul>'
        + "".join(f"<li>{e(x)}</li>" for x in puncte)
        + "</ul></div></article>"
        for img, nume, puncte in CAMERE_FIN)

    comparatie = "".join(
        f'<tr><td>{e(a)}</td><td class="yes">{e(b)}</td><td>{e(c)}</td>'
        f'<td class="no">{e(d)}</td></tr>' for a, b, c, d in COMPARATIE_FIN)

    faq = "".join(f"<details><summary>{e(q)}</summary>"
                  f'<div class="ec-faq__a">{e(a)}</div></details>'
                  for q, a in FAQ_FIN)

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebPage", "name": "Finisaje incluse — Emerald City",
             "url": "https://emerald-city.ro/finisaje/"},
            {"@type": "FAQPage",
             "mainEntity": [{"@type": "Question", "name": q,
                             "acceptedAnswer": {"@type": "Answer", "text": a}}
                            for q, a in FAQ_FIN]},
        ]}

    continut = f"""<section class="ec-phero">
  {imagine("living-01", "", r, "100vw", eager=True)}
  <div class="ec-phero__veil"></div>
  <div class="ec-wrap ec-phero__in">
    <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Finisaje</nav>
    <p class="ec-eyebrow">Finisaje</p>
    <h1>Dotări incluse la cheie</h1>
    <p class="ec-phero__sub">
      {len(FINISAJE)} poziții de finisaj incluse în preț, montate și garantate. Apartamentul
      se predă complet finisat, gata de mobilat.
    </p>
    <div class="ec-phero__cta">
      <a class="ec-btn ec-btn--white" href="#fisa">{ic("list-check")} Lista completă a dotărilor</a>
      <a class="ec-btn ec-btn--outlight" href="{r}apartamente-iasi/disponibilitate/">{ic("table-list")} Prețuri și disponibilitate</a>
    </div>
  </div>
</section>

<div class="ec-figs-wrap">
  <div class="ec-wrap"><div class="ec-figs">{figuri}</div></div>
</div>

<div class="ec-wrap">
  <section class="ec-section" id="fisa">
    <div class="ec-shead">
      <div><span class="ec-shead__n">01 — Incluse în preț</span>
        <h2>{len(FINISAJE)} avantaje, <em>fără cost suplimentar</em></h2></div>
      <p class="ec-shead__p">
        Fiecare dotare, cu specificația tehnică alături și cu avantajul concret
        la utilizare.
      </p>
    </div>
    <div class="ec-fisa" style="margin-top:2.5rem">{fisa}</div>
    <p class="ec-fisa__note">
      {ic("circle-info")} Specificațiile tehnice și mărcile exacte se confirmă în anexa
      tehnică a contractului de vânzare.
    </p>
  </section>

  <section class="ec-section" id="camere" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">02 — Cameră cu cameră</span>
        <h2>Dotări <em>pe fiecare încăpere</em></h2></div>
      <p class="ec-shead__p">
        Aceleași dotări, defalcate pe încăperi.
      </p>
    </div>
    <div class="ec-cams" style="margin-top:2.5rem">{camere}</div>
  </section>
</div>


<div class="ec-wrap">
  <section class="ec-section" id="comparatie">
    <div class="ec-shead">
      <div><span class="ec-shead__n">03 — Comparație</span>
        <h2>Diferența <em>față de un apartament la gri</em></h2></div>
      <p class="ec-shead__p">
        Aceleași finisaje, executate separat, la un apartament semifinisat sau la gri.
      </p>
    </div>
    <div class="ec-table ec-table--vs ec-table--4" style="margin-top:2.5rem">
      <table>
        <caption class="ec-sr">Ce include fiecare tip de predare</caption>
        <thead><tr><th scope="col">Element</th>
          <th scope="col">{ic("circle-check")} La cheie, Emerald City</th>
          <th scope="col">Semifinisat</th>
          <th scope="col">La gri</th></tr></thead>
        <tbody>{comparatie}</tbody>
      </table>
    </div>
  </section>

  <section class="ec-section" id="intrebari" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">04 — Întrebări</span>
        <h2>Despre finisaje <em>și garanții</em></h2></div>
      <p class="ec-shead__p">
        {len(FAQ_FIN)} întrebări despre ce este inclus, ce nu și ce se poate schimba.
      </p>
    </div>
    <div class="ec-faq" style="margin-top:2.5rem">{faq}</div>
    <div class="ec-center" style="margin-top:2rem">
      <a class="ec-btn ec-btn--out" href="{r}despre-emerald-city/#garantii">{ic("shield-halved")} Garanții</a>
      <a class="ec-btn ec-btn--out" href="{r}apartamente-iasi/">{ic("compass-drafting")} Compartimentări</a>
    </div>
  </section>

  {showroom(r, "05")}
</div>

{cta_preturi(r, "bucatarie-01")}"""

    return pagina("Finisaje incluse în preț — predare la cheie | Emerald City",
                  f"Cele {len(FINISAJE)} poziții de finisaj incluse în preț: încălzire în pardoseală, "
                  "tâmplărie cu 7 camere, parchet de 10 mm, grupuri sanitare echipate.",
                  continut, r, schema, "finisaje/")


# ================================================================= presa ==
# ATENTIE: intrarile de mai jos sunt MACHETE, scrise ca sa se vada cum arata
# sectiunea. Nu sunt articole reale. Se inlocuiesc cu aparitiile adevarate
# inainte de lansare, iar odata cu ele se scoate si `macheta: True`.
ARTICOLE = [
 {"pub": "Ziarul de Iași", "url": "https://www.ziaruldeiasi.ro",
  "data": "2026-09-12", "afisat": "12 septembrie 2026", "macheta": True,
  "titlu": "Emerald City: 925 de apartamente pe cinci hectare în zona Păcurari",
  "rezumat": "Cel mai mare ansamblu rezidențial din nord-vestul Iașului intră în etapa a "
             "doua de construcție. Proiectul mizează pe densitate mică — 18 blocuri cu "
             "regim 2D+P+3E — și pe 30,85% spațiu verde amenajat."},
 {"pub": "BZI", "url": "https://www.bzi.ro",
  "data": "2026-08-28", "afisat": "28 august 2026", "macheta": True,
  "titlu": "Cum arată un cartier în care spațiul verde depășește suprafața construită",
  "rezumat": "La Emerald City, cele 15.501,80 m² de spațiu verde amenajat sunt mai mult "
             "decât amprenta la sol a celor 18 blocuri. Parcarea se rezolvă cu 940 de "
             "locuri, dintre care 258 subterane."},
 {"pub": "APIX", "url": "https://www.apix.ro",
  "data": "2026-07-15", "afisat": "15 iulie 2026", "macheta": True,
  "titlu": "Piața rezidențială din Iași: cererea se mută spre ansamblurile cu dotări",
  "rezumat": "Cumpărătorii ieșeni aleg tot mai des proiectele care includ finisaje, "
             "parcare și spații comune. Emerald City, din zona Păcurari, predă "
             "apartamentele complet finisate, cu încălzire în pardoseală."},
 {"pub": "7Iași", "url": "https://7iasi.ro",
  "data": "2026-06-04", "afisat": "4 iunie 2026", "macheta": True,
  "titlu": "Investiție în Păcurari: 18 blocuri și 940 de locuri de parcare",
  "rezumat": "Ansamblul dezvoltat de Tala Sapphire, companie din Green Stone Group, se "
             "construiește în trei etape, pe un teren de 50.235 m² la limita de "
             "nord-vest a Iașului."},
]

DATE_PRESA = [
 ("Denumire", "Emerald City"),
 ("Dezvoltator", "Tala Sapphire S.R.L."),
 ("Grup", "Green Stone Group"),
 ("Amplasament", "Str. Ion Nistor, Iași"),
 ("Apartamente", "925, în 18 blocuri"),
 ("Regim de înălțime", "2D+P+3E · Hmax 18,00 m"),
 ("Suprafață teren", "50.235 m²"),
 ("Spațiu verde", "15.501,80 m² · 30,85%"),
 ("Parcare", "940 locuri · 258 subterane"),
 ("Etape", "3 · 322 / 423 / 180 apartamente"),
 ("Proiectant", "S.C. C.A.D. S.R.L., Iași"),
 ("Contact presă", "presa@emerald-city.ro"),
]

MATERIALE = [
 ("image", "Randări de interior",
  "Imagini de rezoluție mare din apartamentele-model, pentru print și online."),
 ("compass-drafting", "Planuri și secțiuni",
  "Planurile celor 5 compartimentări și secțiunea verticală prin bloc."),
 ("file-lines", "Fișa de proiect",
  "Un document cu toate cifrele verificate: suprafețe, indicatori, etape, termene."),
 ("copyright", "Elemente de identitate",
  "Logo în variantele pe fond deschis și închis, plus paleta de culori."),
]


def pagina_presa():
    r = "../"

    articole = "".join(
        '<article class="ec-art ec-rv">'
        f'<div class="ec-art__top"><span class="ec-art__pub">{e(a["pub"])}</span>'
        + ('<span class="ec-art__badge">Machetă</span>' if a.get("macheta") else "")
        + '</div>'
        f'<h3><a href="{e(a["url"])}" target="_blank" rel="noopener nofollow">{e(a["titlu"])}</a></h3>'
        f'<p>{e(a["rezumat"])}</p>'
        f'<div class="ec-art__foot"><time datetime="{e(a["data"])}">{e(a["afisat"])}</time>'
        f'<a class="ec-art__go" href="{e(a["url"])}" target="_blank" rel="noopener nofollow">'
        f'Citește pe {e(a["pub"])}{ic("arrow-up-right-from-square")}</a></div>'
        '</article>'
        for a in ARTICOLE)

    date_presa = "".join(f'<div class="ec-spec"><dt>{e(k)}</dt><dd>{e(v)}</dd></div>'
                         for k, v in DATE_PRESA)

    materiale = "".join(
        f'<div class="ec-fisa__i ec-rv"><span class="ec-fisa__ic">{ic(pic)}</span>'
        f'<span><b>{e(t)}</b><span class="ec-fisa__d">{e(d)}</span></span></div>'
        for pic, t, d in MATERIALE)

    figuri = "".join(
        f'<div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic(pic)}</span>'
        f'<span><b data-num="{e(val)}">{e(val)}{e(suf)}</b><em>{e(et)}</em></span></div>'
        for val, suf, et, pic in [
            ("925", "", "Apartamente", "building"),
            ("18", "", "Blocuri 2D+P+3E", "city"),
            ("50.235", " m²", "Suprafață teren", "ruler-combined"),
            ("30,85", "%", "Spațiu verde", "tree"),
        ])

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "CollectionPage", "name": "Apariții în presă — Emerald City",
             "url": "https://emerald-city.ro/aparitii-presa/"},
        ]}

    continut = f"""<section class="ec-phero">
  {imagine("hero-living", "", r, "100vw", eager=True)}
  <div class="ec-phero__veil"></div>
  <div class="ec-wrap ec-phero__in">
    <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Apariții în presă</nav>
    <p class="ec-eyebrow">Presă</p>
    <h1>Ce s-a scris despre Emerald City</h1>
    <p class="ec-phero__sub">
      Articole apărute în publicații locale și naționale, cu link către sursa originală.
      Mai jos sunt datele verificate ale proiectului, puse la dispoziția jurnaliștilor.
    </p>
    <div class="ec-phero__cta">
      <a class="ec-btn ec-btn--white" href="#articole">{ic("newspaper")} Aparițiile în presă</a>
      <a class="ec-btn ec-btn--outlight" href="mailto:presa@emerald-city.ro">{ic("envelope")} Contact presă</a>
    </div>
  </div>
</section>

<div class="ec-figs-wrap">
  <div class="ec-wrap"><div class="ec-figs">{figuri}</div></div>
</div>

<div class="ec-wrap">
  <section class="ec-section" id="articole">
    <div class="ec-shead">
      <div><span class="ec-shead__n">01 — Apariții</span>
        <h2>Articole <em>despre proiect</em></h2></div>
      <p class="ec-shead__p">
        Fiecare intrare conține publicația, data și link către articolul original.
      </p>
    </div>
    <div class="ec-arts" style="margin-top:2.5rem">{articole}</div>
  </section>

  <section class="ec-section" id="date" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">02 — Date pentru presă</span>
        <h2>Cifrele <em>verificate</em></h2></div>
      <p class="ec-shead__p">
        Datele din documentația de autorizare, disponibile pentru preluare ca atare.
      </p>
    </div>
    <dl class="ec-specs" style="margin-top:2.5rem">{date_presa}</dl>
  </section>

  <section class="ec-section" id="materiale" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">03 — Materiale</span>
        <h2>Ce punem <em>la dispoziție</em></h2></div>
      <p class="ec-shead__p">
        Materiale de rezoluție mare, transmise la cerere în aceeași zi lucrătoare.
      </p>
    </div>
    <div class="ec-fisa" style="margin-top:2.5rem">{materiale}</div>
    <div class="ec-center" style="margin-top:2rem">
      <a class="ec-btn" href="mailto:presa@emerald-city.ro">{ic("envelope")} Solicitare materiale</a>
      <a class="ec-btn ec-btn--out" href="{r}proiect/">{ic("compass-drafting")} Datele proiectului</a>
    </div>
  </section>

  {showroom(r, "04")}
</div>

<script>
(() => {{
  const nr = [...document.querySelectorAll('.ec-fig b[data-num]')];
  if (!nr.length) return;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const urca = el => {{
    const brut = el.dataset.num;
    const tinta = parseFloat(brut.replace(/\\./g, '').replace(',', '.'));
    const zec = (brut.split(',')[1] || '').length;
    const sufix = el.textContent.replace(brut, '');
    const t0 = performance.now(), dur = 1100;
    const pas = t => {{
      const p = Math.min((t - t0) / dur, 1);
      const v = tinta * (1 - Math.pow(1 - p, 3));
      el.textContent = v.toLocaleString('ro-RO', {{
        minimumFractionDigits: zec, maximumFractionDigits: zec }}) + sufix;
      if (p < 1) requestAnimationFrame(pas);
    }};
    requestAnimationFrame(pas);
  }};
  const o = new IntersectionObserver(es => es.forEach(x => {{
    if (x.isIntersecting) {{ urca(x.target); o.unobserve(x.target); }}
  }}), {{ threshold: .4 }});
  nr.forEach(x => o.observe(x));
}})();
</script>"""

    return pagina("Apariții în presă — Emerald City Iași",
                  "Articole despre ansamblul Emerald City din Iași, zona Păcurari, apărute "
                  "în publicații locale și naționale. Date de proiect și materiale pentru "
                  "jurnaliști.",
                  continut, r, schema, "aparitii-presa/")



# ============================================================== noutati ==
# Articole editoriale; fiecare cu sectiuni (titlu, paragrafe), cifre-cheie si legaturi.
ARTICOLE_BLOG = [
 {"slug": "etapa-1-structura-etajul-2", "cat": "Jurnal de șantier", "pict": "helmet-safety",
  "data": "2026-09-20", "afisat": "20 septembrie 2026", "minute": 4, "img": "hol-01",
  "seo_titlu": 'Etapa I: structura la etajul 2 în blocurile 1–4', "seo_desc": 'Stadiul din septembrie 2026 la Emerald City Iași: planșee turnate la blocurile 1–4, cofraje la 5–6 și săpături pentru Etapa II.',
  "titlu": "Etapa I: structura a ajuns la etajul 2 în blocurile 1–4",
  "rezumat": "Planșeul peste etajul 1 este turnat la primele patru blocuri, iar la blocurile 5 și 6 "
             "se montează cofrajele. Ce urmează până la finalul anului și ce înseamnă pentru termenele de predare.",
  "sectiuni": [
   ("Unde s-a ajuns în septembrie", [
    "Raportul de șantier din septembrie consemnează turnarea planșeului peste etajul 1 la blocurile 1, 2, 3 și 4, cu procesele-verbale de fază determinantă semnate de dirigintele de șantier și de proiectant. La blocurile 5 și 6, cofrajele pentru stâlpii etajului 1 sunt montate, iar armarea este în curs.",
    "În paralel, la blocurile 7 și 8 — primele din Etapa II — a început săpătura pentru cele două demisoluri. Platforma de organizare a fost extinsă către latura de vest a terenului, astfel încât circulația utilajelor să nu intersecteze zona blocurilor aflate deja în structură."]),
   ("Ce înseamnă „fază determinantă”", [
    "Fazele determinante sunt punctele de control impuse de lege în care execuția nu poate continua fără verificarea și semnătura dirigintelui de șantier, a proiectantului și, după caz, a Inspectoratului de Stat în Construcții. Fundațiile, fiecare planșeu și structura completă sunt astfel de puncte.",
    "Pentru cumpărător, existența acestor procese-verbale înseamnă că structura a fost verificată independent la fiecare etapă, nu doar la recepția finală. Documentele intră în cartea tehnică a construcției, predată odată cu apartamentul."]),
   ("Calendarul până la finalul anului", [
    "Până în decembrie, la blocurile 1–4 se estimează finalizarea structurii la nivelul etajului 3 și începerea închiderilor exterioare la nivelurile inferioare. La blocurile 5 și 6, structura ar urma să ajungă la etajul 2. Săpăturile și fundațiile pentru blocurile 7 și 8 sunt planificate pentru trimestrul IV.",
    "Termenele afișate sunt estimări la data raportului. Termenul contractual pentru fiecare unitate este cel înscris în antecontract și nu se modifică prin actualizările din jurnal."]),
   ("Cum se poate verifica stadiul", [
    "Pagina de stadiu al lucrărilor se actualizează lunar, cu fotografii datate din teren. Vizitele pe șantier se organizează cu programare, însoțite de un reprezentant, cu echipament de protecție pus la dispoziție. Raportul lunar poate fi primit și pe e-mail, la cerere."]),
  ],
  "fapte": [("Blocuri cu planșeul peste etajul 1", "4"), ("Blocuri în cofrare", "2"),
            ("Etapa II — săpături începute", "blocurile 7 și 8"), ("Următoarea actualizare", "octombrie 2026")],
  "legaturi": [("stadiu-lucrari/", "Stadiul lucrărilor, faza cu faza"), ("proiect/", "Datele proiectului"),
               ("apartamente-iasi/disponibilitate/?etapa=I&status=disponibil", "Apartamentele disponibile în Etapa I")]},

 {"slug": "ghid-cumparare-apartament-nou-iasi", "cat": "Ghid de achiziție", "pict": "file-signature",
  "data": "2026-09-12", "afisat": "12 septembrie 2026", "minute": 6, "img": "living-01",
  "seo_titlu": 'Cum se cumpără un apartament nou în Iași: 5 pași', "seo_desc": 'Ghid practic: vizionare, rezervare, antecontract la notar, construcție și recepție — ce se semnează și ce se verifică la fiecare pas.',
  "titlu": "Cum se cumpără un apartament nou în Iași: cei 5 pași, cu documentele fiecăruia",
  "rezumat": "De la vizionare la intabulare, ce se semnează, ce se plătește și ce se verifică la fiecare pas. "
             "Un ghid practic pentru prima achiziție de la dezvoltator.",
  "sectiuni": [
   ("1. Vizionarea și lista de disponibilitate", [
    "Primul pas este întâlnirea în showroom: apartamentul-model, planurile fiecărei compartimentări și lista de disponibilitate cu prețul fiecărei unități. Este momentul în care se clarifică bugetul, etajul, orientarea și dotările suplimentare — loc de parcare, boxă, curte.",
    "Documente de cerut: autorizația de construire (număr și dată), certificatul de urbanism cu indicatorii aprobați, extrasul de carte funciară al terenului și anexa tehnică de finisaje. Un dezvoltator serios le pune la dispoziție fără rezerve."]),
   ("2. Rezervarea", [
    "Rezervarea blochează unitatea aleasă pe numele cumpărătorului și menține prețul afișat pentru o perioadă stabilită, de regulă până la semnarea antecontractului. Se semnează un document scurt, în care se menționează unitatea, prețul și termenul de valabilitate.",
    "În această perioadă cumpărătorul poate obține pre-aprobarea creditului, dacă finanțează prin bancă. Documentația necesară băncii — planuri, autorizație, extras CF — se pune la dispoziție de dezvoltator."]),
   ("3. Antecontractul, la notar", [
    "Antecontractul de vânzare-cumpărare se semnează în formă autentică, la notar. Fixează unitatea, suprafețele, prețul, eșalonarea plăților, termenul de predare și consecințele întârzierii. La semnare se achită avansul — la Emerald City, 15% din preț.",
    "De verificat înainte de semnare: concordanța dintre planul anexat și unitatea vizitată, lista de finisaje poziție cu poziție, termenul de predare exprimat ca dată, nu ca „trimestru estimat”, și clauzele de penalitate în ambele sensuri."]),
   ("4. Construcția și plățile intermediare", [
    "Pe durata execuției, cumpărătorul poate urmări progresul în jurnalul de șantier și poate vizita șantierul cu programare. Plățile intermediare, dacă există, sunt legate de stadii fizice verificabile — structură finalizată, închideri, instalații — nu de date calendaristice.",
    "Creditul ipotecar se trage de regulă la semnarea contractului final, după recepție. Până atunci, banca lucrează cu antecontractul și cu documentația proiectului."]),
   ("5. Recepția, contractul final și intabularea", [
    "La finalizare, apartamentul se verifică împreună cu un reprezentant al dezvoltatorului, pe baza unei liste de verificare: finisaje, instalații, tâmplărie, echipamente. Observațiile se consemnează în procesul-verbal și se remediază înainte de predare.",
    "Urmează contractul de vânzare-cumpărare la notar, plata diferenței și intabularea pe numele cumpărătorului. Odată cu cheile se predau cartea tehnică, certificatul energetic, documentația cadastrală și garanțiile echipamentelor."]),
  ],
  "fapte": [("Avans la antecontract", "15%"), ("Comision de intermediere", "0"),
            ("Garanție structură", "durata clădirii"), ("Vicii ascunse", "10 ani")],
  "legaturi": [("despre-emerald-city/", "Procesul complet, pas cu pas"), ("finisaje/", "Ce include predarea la cheie"),
               ("programare-vizionare/", "Programare vizionare")]},

 {"slug": "incalzire-in-pardoseala-vs-calorifere", "cat": "Finisaje și tehnic", "pict": "fire-flame-simple",
  "data": "2026-09-05", "afisat": "5 septembrie 2026", "minute": 5, "img": "dormitor-01",
  "seo_titlu": 'Încălzire în pardoseală sau calorifere?', "seo_desc": 'Cum funcționează încălzirea în pardoseală cu centrală în condensație, ce economie aduce (până la 35%) și ce trebuie știut la mobilare.',
  "titlu": "Încălzire în pardoseală sau calorifere: ce se schimbă la confort și la factură",
  "rezumat": "Toate cele 925 de apartamente au încălzire în pardoseală, cu centrală proprie în condensație. "
             "Explicăm cum funcționează sistemul, ce economie aduce și ce trebuie știut la mobilare.",
  "sectiuni": [
   ("Cum funcționează", [
    "Încălzirea în pardoseală distribuie apa caldă prin serpentine montate în șapă, sub parchet sau gresie. Suprafața întregii pardoseli devine element de încălzire, la o temperatură a apei de 30–40 °C, față de 60–70 °C la calorifere.",
    "Fiecare cameră are circuit propriu, cu reglaj individual de la distribuitor și termostat. Temperatura se poate seta diferit în dormitor față de living, iar camerele nefolosite pot fi menținute la un nivel minim."]),
   ("De ce consumă mai puțin", [
    "Centrala în condensație are randamentul cel mai ridicat exact la temperaturi joase ale apei, pentru că recuperează căldura din gazele de ardere în loc să o evacueze pe horn. Combinația cu încălzirea în pardoseală o menține în regimul optim aproape tot sezonul.",
    "Rezultatul, la același confort, este un consum de gaz cu până la 35% mai mic decât la o centrală clasică cu calorifere. La o garsonieră de 37 m² cu anvelopă termică nouă, diferența se simte direct în factura de iarnă."]),
   ("Confortul: căldura de jos în sus", [
    "Distribuția uniformă a căldurii de la sol elimină zonele reci de lângă ferestre și curenții de aer produși de calorifere. Temperatura resimțită este cu 1–2 °C mai mare decât cea măsurată, ceea ce permite o setare mai joasă a termostatului.",
    "Pereții rămân liberi: fără calorifere sub ferestre, mobilierul se poate așeza oriunde, iar tâmplăria până în pardoseală devine posibilă."]),
   ("Ce trebuie știut la mobilare", [
    "Parchetul laminat de 10 mm livrat în apartamente este compatibil cu încălzirea în pardoseală. La mobilare se recomandă evitarea covoarelor groase pe suprafețe mari și a mobilierului fără picioare, care reduc transferul de căldură.",
    "Sistemul are inerție: se încălzește și se răcește lent. Programarea termostatului pe intervale, nu pornirea și oprirea repetată, este modul eficient de utilizare."]),
  ],
  "fapte": [("Temperatura apei în circuit", "30–40 °C"), ("Economie față de centrala clasică", "până la 35%"),
            ("Reglaj", "pe fiecare cameră"), ("Inclus în preț", "toate apartamentele")],
  "legaturi": [("finisaje/", "Lista completă a finisajelor"), ("despre-emerald-city/#garantii", "Garanțiile instalațiilor"),
               ("apartamente-iasi/", "Apartamentele disponibile")]},

 {"slug": "pacurari-ghidul-cartierului", "cat": "Zona", "pict": "map-location-dot",
  "data": "2026-08-28", "afisat": "28 august 2026", "minute": 5, "img": "dining-01",
  "seo_titlu": 'Păcurari, în cifre: distanțe reale', "seo_desc": 'Distanțe măsurate de la Emerald City: școală la 300 m, Universitate la 5 km, centru la 4,8 km, aeroport la 12 km. Cui i se potrivește zona.',
  "titlu": "Păcurari, în cifre: distanțe reale până la școală, universitate și centru",
  "rezumat": "Am măsurat pe traseu rutier drumurile care contează zilnic — Copou, Universitate, Kaufland, "
             "Paradis International College. Ce înseamnă poziția ansamblului pentru o familie, un student sau un investitor.",
  "sectiuni": [
   ("Poziția pe hartă", [
    "Emerald City se află la limita de nord-vest a Iașului, cu acces din Strada Ion Nistor, în spatele ansamblului Contemporan Homes de pe Strada Dealul Zorilor. Este una dintre puținele zone ale orașului care mai dispune de teren pentru ansambluri cu densitate redusă, la distanță mică de centrul universitar.",
    "Distanțele de mai jos sunt calculate pe traseu rutier real, fără trafic, de la amplasament, cu date OpenStreetMap. Singura excepție este Paradis International College, pentru care distanța pietonală este cea indicată de dezvoltator."]),
   ("Școală, cumpărături, universitate", [
    "Paradis International College se află la aproximativ 300 de metri, 4 minute de mers pe jos. Kaufland Păcurari este la 1,5 km, iar magazinele de proximitate de pe artera Păcurari la câteva minute. Universitatea „Alexandru Ioan Cuza” este la 5 km, în Copou, aproximativ 12 minute cu mașina.",
    "Centrul orașului — Piața Unirii — este la 4,8 km, iar Palas Mall la 5,5 km. Aeroportul Iași se află la 12 km, aproximativ 22 de minute fără trafic."]),
   ("Transport public și ieșirea din oraș", [
    "Artera Păcurari are linii constante spre centru și spre Copou, cu stație pe drumul de acces în ansamblu. Ieșirea spre Botoșani, pe DN28, este la câteva minute — utilă pentru drumurile în afara orașului fără traversarea centrului.",
    "Pentru cei care lucrează în nord-vestul Iașului, accesul direct la artera Păcurari evită aglomerația din zona centrală la orele de vârf."]),
   ("Cui i se potrivește zona", [
    "Familiilor tinere: școală la 4 minute pe jos, loc de joacă și parc în incintă, curte proprie la apartamentele de la parter. Studenților și tinerilor angajați: Copou și centrul universitar la 5 km, transport direct. Investitorilor: cerere de chirii susținută de cei peste 60.000 de studenți ai orașului.",
    "Harta interactivă de pe pagina zonei permite selectarea fiecărui reper și afișarea traseului rutier."]),
  ],
  "fapte": [("Centrul orașului", "4,8 km"), ("Universitatea „A.I. Cuza”", "5 km"),
            ("Paradis International College", "300 m, pe jos"), ("Aeroport", "12 km")],
  "legaturi": [("apartamente-iasi-pacurari/", "Ghidul complet al zonei, cu hartă"), ("apartamente-iasi/", "Apartamentele disponibile"),
               ("investitie-apartamente-iasi/", "Randament pentru investitori")]},

 {"slug": "randament-chirii-iasi-2026", "cat": "Investiție", "pict": "chart-line",
  "data": "2026-08-19", "afisat": "19 august 2026", "minute": 6, "img": "living-02",
  "seo_titlu": 'Randamentul chiriilor în Iași 2026, apartament nou', "seo_desc": 'Randament brut estimat 4,5–5,5%, cu garsonierele în frunte. Metoda de calcul, costurile neincluse și de ce un apartament nou se închiriază mai repede.',
  "titlu": "Randamentul chiriilor în Iași, 2026: ce arată cifrele pentru un apartament nou",
  "rezumat": "Între 4,5% și 5,5% brut, cu garsonierele în frunte. Cum am calculat, ce costuri lipsesc din estimare "
             "și de ce un apartament nou, finisat la cheie, se închiriază mai repede.",
  "sectiuni": [
   ("Metoda de calcul", [
    "Randamentul brut împarte chiria anuală la prețul de achiziție. Pentru estimare am folosit o chirie de aproximativ 6,2 €/m² util pe lună — o medie observată pentru locuințe noi, finisate, în zona Păcurari — și prețurile de listare ale unităților disponibile.",
    "Randamentul net scade perioadele neînchiriate (implicit 8% pe an) și aproximativ 8% cheltuieli de administrare, impozit și reparații. Diferența dintre brut și net este, de regulă, de cel puțin un punct procentual."]),
   ("Ce rezultă pe categorii", [
    "Garsonierele, de la 53.500 €, au randamentul brut cel mai ridicat — în jur de 5,2% — și cel mai scurt timp de ocupare pe piața de închirieri din Iași. Apartamentele cu 2 camere, de la 74.000 €, se situează la un nivel apropiat, cu o cerere mai stabilă din partea cuplurilor și a tinerilor profesioniști.",
    "Apartamentele cu 3 camere au randamente brute ușor mai mici, în jur de 5,1%, dar se adresează unui segment distinct: familii și relocări corporate, cu contracte pe termen mai lung."]),
   ("De ce contează că este nou și finisat", [
    "Un apartament predat la cheie — parchet, gresie, faianță, obiecte sanitare, uși, centrală proprie, încălzire în pardoseală — se poate închiria după mobilare, fără luni de lucrări. Costurile de exploatare mici și contorizarea individuală sunt argumente în plus pentru chiriaș.",
    "Garanțiile legale — structura pe toată durata clădirii, viciile ascunse 10 ani — reduc riscul de reparații neprevăzute în primii ani, exact perioada în care se recuperează costurile inițiale."]),
   ("Costuri care nu apar în calculator", [
    "Taxele notariale, intabularea, TVA-ul aferent, mobilarea și echiparea inițială și eventualul comision al unei firme de administrare nu sunt incluse. Pentru o garsonieră, mobilarea completă pornește în general de la câteva mii de euro.",
    "Cifrele sunt estimări bazate pe prețuri de listare și pe chirii observate în zonă, cu rol informativ. Nu reprezintă consultanță de investiții; decizia aparține cumpărătorului, care poate consulta un specialist independent."]),
  ],
  "fapte": [("Randament brut estimat", "4,5–5,5%"), ("Chirie estimată", "≈ 6,2 €/m²/lună"),
            ("Garsonieră, de la", "53.500 €"), ("Studenți în Iași", "peste 60.000")],
  "legaturi": [("investitie-apartamente-iasi/", "Calculatorul de randament"), ("apartamente-iasi/apartamente-1-camera/", "Garsonierele disponibile"),
               ("apartamente-iasi/disponibilitate/", "Toate prețurile")]},

 {"slug": "etapa-2-intra-in-vanzare", "cat": "Proiect", "pict": "building-circle-check",
  "data": "2026-08-10", "afisat": "10 august 2026", "minute": 4, "img": "hero-living",
  "seo_titlu": 'Etapa II în vânzare: 423 de apartamente noi', "seo_desc": 'Blocurile 7–14 din Emerald City Iași, în jurul parcului central: compartimentări 1A–3B, prețuri de pornire neschimbate, rezervare la showroom.',
  "titlu": "Etapa II intră în vânzare: 423 de apartamente în 8 blocuri, în jurul parcului central",
  "rezumat": "Cea mai mare etapă a ansamblului, cu blocurile 7–14 și acces direct la parcul dendrologic. "
             "Ce compartimentări sunt disponibile, la ce prețuri și cum se rezervă.",
  "sectiuni": [
   ("Ce cuprinde Etapa II", [
    "Etapa II include blocurile 7–14, cu 423 de apartamente — aproape jumătate din ansamblu. Blocurile sunt dispuse în jurul parcului central, astfel încât majoritatea apartamentelor au vedere spre spațiul verde, nu spre parcări.",
    "Regimul de înălțime rămâne același ca în toate cele 18 blocuri: două demisoluri, parter și trei etaje, cu înălțimea maximă de 15 metri. Parcarea subterană și boxele sunt în demisoluri, cu lift direct din parcaj în scară."]),
   ("Compartimentări și prețuri", [
    "Sunt disponibile toate cele cinci compartimentări: garsoniere de tip 1A, apartamente cu 2 camere de tip 2A și 2B și apartamente cu 3 camere de tip 3A și 3B, cu suprafețe utile între 37 și 81 m². Apartamentele de la parter au curte proprie, între 20 și 65 m².",
    "Prețurile de pornire sunt aceleași ca în Etapa I, cu TVA inclus și cu toate finisajele. Lista completă, cu prețul fiecărei unități, este publicată în secțiunea de disponibilitate și se filtrează după etapă."]),
   ("Calendar și condiții", [
    "Săpăturile pentru blocurile 7 și 8 au început în septembrie; structura celorlalte blocuri urmează progresiv. Termenul de predare al fiecărei unități se înscrie în antecontract. Condițiile de plată sunt cele standard: 15% avans la antecontract, diferența la predare, plăți intermediare opționale.",
    "Rezervarea se face la biroul de vânzări, cu blocarea prețului afișat până la semnarea antecontractului."]),
  ],
  "fapte": [("Apartamente în Etapa II", "423"), ("Blocuri", "7–14"),
            ("Suprafețe utile", "37–81 m²"), ("Avans la antecontract", "15%")],
  "legaturi": [("apartamente-iasi/disponibilitate/?etapa=II&status=disponibil", "Apartamentele din Etapa II"),
               ("proiect/#etape", "Etapele ansamblului"), ("programare-vizionare/", "Programare vizionare")]},
]
ARTICOLE_BLOG_SLUG = {a["slug"]: a for a in ARTICOLE_BLOG}


def card_articol(a, r, mare=False):
    return f"""<article class="ec-post ec-rv{' ec-post--mare' if mare else ''}">
      <a class="ec-post__img" href="{r}noutati/{a['slug']}/" aria-label="{e(a['titlu'])}">
        {imagine(a['img'], a['titlu'], r, "(min-width: 60rem) 33vw, 100vw")}
        <span class="ec-post__cat">{ic(a['pict'])} {e(a['cat'])}</span>
      </a>
      <div class="ec-post__b">
        <div class="ec-post__meta"><time datetime="{a['data']}">{e(a['afisat'])}</time><span>·</span><span>{a['minute']} min de citit</span></div>
        <h3><a href="{r}noutati/{a['slug']}/">{e(a['titlu'])}</a></h3>
        <p>{e(a['rezumat'])}</p>
        <a class="ec-post__go" href="{r}noutati/{a['slug']}/">Citește articolul {ic("arrow-right")}</a>
      </div>
    </article>"""


def pagina_noutati():
    r = "../"
    carduri = "".join(card_articol(a, r) for a in ARTICOLE_BLOG)
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "CollectionPage", "name": "Noutăți Emerald City",
             "url": "https://emerald-city.ro/noutati/"},
            {"@type": "ItemList", "itemListElement": [
                {"@type": "ListItem", "position": i,
                 "url": f"https://emerald-city.ro/noutati/{a['slug']}/", "name": a["titlu"]}
                for i, a in enumerate(ARTICOLE_BLOG, 1)]},
        ]}
    continut = f"""<section class="ec-phero">
  {imagine("dormitor-02", "", r, "100vw", eager=True)}
  <div class="ec-phero__veil"></div>
  <div class="ec-wrap ec-phero__in">
    <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Noutăți</nav>
    <p class="ec-eyebrow">Noutăți</p>
    <h1>Noutăți din șantier, ghiduri și analize</h1>
    <p class="ec-phero__sub">
      Stadiul lucrărilor, explicații tehnice despre finisaje, ghiduri de achiziție și cifre
      despre zonă și piața de închirieri. Articole semnate de echipa Emerald City, actualizate lunar.
    </p>
    <div class="ec-phero__cta">
      <a class="ec-btn ec-btn--white" href="#articole">{ic("newspaper")} Cele {len(ARTICOLE_BLOG)} articole</a>
      <a class="ec-btn ec-btn--outlight" href="{r}stadiu-lucrari/">{ic("helmet-safety")} Jurnal de șantier</a>
    </div>
  </div>
</section>

<div class="ec-wrap">
  <section class="ec-section" id="articole" style="padding-block:var(--ec-section) 0">
    <div class="ec-shead">
      <div><span class="ec-shead__n">01 — Articole</span>
        <h2>Cele mai recente <em>publicate</em></h2></div>
      <p class="ec-shead__p">Șantier, ghid de achiziție, finisaje, zonă, investiție și proiect — câte un articol pe temă.</p>
    </div>
    <div class="ec-blog" style="margin-top:2.5rem">{carduri}</div>
  </section>

  <section class="ec-section" style="padding-block:var(--ec-section) 0">
    {alerta("Primiți articolele noi pe e-mail", "Un e-mail pe lună, cu stadiul lucrărilor și articolele publicate. Se poate opri oricând.", "noutati", "envelope-open-text")}
  </section>

  <section class="ec-section" style="padding-block:var(--ec-section) 0">
    {cta_dublu(r, "noutati")}
  </section>

  {showroom(r, "02")}
</div>"""
    return pagina("Noutăți — șantier, ghiduri și analize | Emerald City Iași",
                  "Noutăți de la Emerald City, Iași zona Păcurari: stadiul lucrărilor, ghiduri de achiziție, "
                  "explicații despre finisaje, cifre despre zonă și randamentul chiriilor.",
                  continut, r, schema, "noutati/", "dormitor-02")


def pagina_articol(a):
    r = "../../"
    corp = ""
    cuprins = ""
    for i, (t, paragrafe) in enumerate(a["sectiuni"], 1):
        cuprins += f'<li><a href="#s{i}">{e(t)}</a></li>'
        corp += f'<h2 id="s{i}">{e(t)}</h2>' + "".join(f"<p>{e(x)}</p>" for x in paragrafe)
    fapte = "".join(f'<div class="ec-artf__i"><span>{e(k)}</span><b>{e(v)}</b></div>' for k, v in a["fapte"])
    legaturi = "".join(f'<li><a href="{r}{h}">{ic("arrow-right")} {e(t)}</a></li>' for h, t in a["legaturi"])
    altele = [x for x in ARTICOLE_BLOG if x["slug"] != a["slug"]][:3]
    similare = "".join(card_articol(x, r) for x in altele)
    text = " ".join(p for _, ps in a["sectiuni"] for p in ps)
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Article", "headline": a["titlu"], "description": a["rezumat"],
             "datePublished": a["data"], "dateModified": a["data"],
             "articleSection": a["cat"], "wordCount": len(text.split()),
             "image": f"https://emerald-city.ro/assets/img/{a['img']}.jpg",
             "author": {"@type": "Organization", "name": "Emerald City — echipa de vânzări",
                        "url": "https://emerald-city.ro/despre-emerald-city/"},
             "publisher": {"@type": "Organization", "name": "Tala Sapphire S.R.L.",
                           "logo": {"@type": "ImageObject", "url": "https://emerald-city.ro/brand/logo-verde.svg"}},
             "mainEntityOfPage": f"https://emerald-city.ro/noutati/{a['slug']}/",
             "inLanguage": "ro"},
        ]}
    continut = f"""<section class="ec-phero ec-phero--art">
  {imagine(a['img'], a['titlu'], r, "100vw", eager=True)}
  <div class="ec-phero__veil"></div>
  <div class="ec-wrap ec-phero__in">
    <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>
      <a href="{r}noutati/">Noutăți</a><span>/</span>{e(a['cat'])}</nav>
    <p class="ec-eyebrow">{ic(a['pict'])} {e(a['cat'])}</p>
    <h1>{e(a['titlu'])}</h1>
    <p class="ec-phero__sub">{e(a['rezumat'])}</p>
    <div class="ec-artmeta">
      <span>{ic("calendar-days")} <time datetime="{a['data']}">{e(a['afisat'])}</time></span>
      <span>{ic("clock")} {a['minute']} min de citit</span>
      <span>{ic("user-pen")} Echipa Emerald City</span>
    </div>
  </div>
</section>

<div class="ec-wrap">
  <div class="ec-artgrid">
    <article class="ec-artbody">
      {corp}
      <div class="ec-artnote">
        <b>{ic("circle-info")} Notă</b>
        <p>Informațiile reflectă situația la data publicării. Cifrele contractuale — suprafețe, prețuri,
           termene — sunt cele din documentele semnate între părți.</p>
      </div>
      <div class="ec-artshare">
        <span>Distribuiți:</span>
        <a href="https://www.facebook.com/sharer/sharer.php?u=https://emerald-city.ro/noutati/{a['slug']}/" target="_blank" rel="noopener" aria-label="Facebook">{ic("facebook-f", brand=True)}</a>
        <a href="https://wa.me/?text=https://emerald-city.ro/noutati/{a['slug']}/" target="_blank" rel="noopener" aria-label="WhatsApp">{ic("whatsapp", brand=True)}</a>
        <a href="mailto:?subject={e(a['titlu'])}&amp;body=https://emerald-city.ro/noutati/{a['slug']}/" aria-label="E-mail">{ic("envelope")}</a>
      </div>
    </article>
    <aside class="ec-artside">
      <div class="ec-artside__p">
        <b>Cuprins</b>
        <ol class="ec-arttoc">{cuprins}</ol>
      </div>
      <div class="ec-artside__p ec-artf">
        <b>Cifre-cheie</b>
        {fapte}
      </div>
      <div class="ec-artside__p">
        <b>Legături utile</b>
        <ul class="ec-artlinks">{legaturi}</ul>
      </div>
      <div class="ec-artside__p ec-artside__cta">
        <b>Vizionare în showroom</b>
        <p>Apartamentul-model, planurile și lista de disponibilitate, într-o întâlnire de 40 de minute.</p>
        <a class="ec-btn ec-btn--brass" href="{r}programare-vizionare/">{ic("calendar-check")} Programare vizionare</a>
      </div>
    </aside>
  </div>

  <section class="ec-section" style="padding-block:var(--ec-section) 0">
    <div class="ec-shead">
      <div><span class="ec-shead__n">Alte articole</span>
        <h2>Continuați <em>lectura</em></h2></div>
      <p class="ec-shead__p">Trei articole pe teme apropiate.</p>
    </div>
    <div class="ec-blog" style="margin-top:2.5rem">{similare}</div>
  </section>

  <section class="ec-section" style="padding-block:var(--ec-section) 0">
    {cta_dublu(r, a['slug'])}
  </section>

  {showroom(r, "")}
</div>"""
    return pagina(f"{a.get('seo_titlu', a['titlu'])} | Emerald City", a.get("seo_desc", a["rezumat"]), continut, r, schema,
                  f"noutati/{a['slug']}/", a["img"])


# ========================================================= pagini legale ==
LEGALE = {
    "termeni-si-conditii": ("Termeni și condiții",
        "Condițiile de utilizare a site-ului emerald-city.ro: informații publicate, solicitări prin formulare, "
        "proprietate intelectuală și limitarea răspunderii."),
    "politica-de-confidentialitate": ("Politica de confidențialitate",
        "Cum colectează, folosește, păstrează și protejează Tala Sapphire S.R.L. datele cu caracter "
        "personal transmise prin acest site, prin telefon sau în showroom."),
    "politica-de-cookies": ("Politica de cookies",
        "Ce module cookie și tehnologii similare folosește site-ul, în ce scop, pe ce durată și cum "
        "poate fi gestionat sau retras acordul."),
    "informare-gdpr": ("Informare GDPR",
        "Informarea persoanei vizate conform art. 13 și 14 din Regulamentul (UE) 2016/679: "
        "operator, scopuri, temeiuri, destinatari, durate și drepturi."),
}

OPERATOR = ("Tala Sapphire S.R.L., cu sediul în Str. Ion Nistor, Iași, județul Iași, România, "
            "înregistrată la Oficiul Registrului Comerțului sub nr. [J22/…/…], CUI [RO…], "
            "parte a Green Stone Group")
DATA_ACT = "25 septembrie 2026"

# Fiecare document: lista de (titlu de sectiune, [paragrafe sau liste]). O intrare care
# incepe cu "- " devine element de lista; un tuplu (cap, randuri) devine tabel.
TEXTE_LEGALE = {
"termeni-si-conditii": [
 ("Obiectul și acceptarea termenilor", [
  f"Prezentul document stabilește condițiile în care poate fi utilizat site-ul emerald-city.ro "
  f"(„Site-ul”), operat de {OPERATOR} („Dezvoltatorul”, „noi”). Accesarea și utilizarea Site-ului "
  "presupun acceptarea integrală a acestor termeni. Persoanele care nu sunt de acord cu ei sunt "
  "rugate să nu utilizeze Site-ul.",
  "Termenii se aplică tuturor vizitatorilor, indiferent dacă transmit sau nu o solicitare prin "
  "formularele disponibile. Pentru raporturile contractuale privind achiziția unui apartament se "
  "aplică exclusiv documentele semnate între părți (rezervare, antecontract, contract de "
  "vânzare-cumpărare), care prevalează asupra oricărei informații publicate pe Site."]),
 ("Caracterul informativ al conținutului", [
  "Site-ul prezintă ansamblul rezidențial Emerald City din Iași, zona Păcurari, în scop de "
  "informare și promovare. Informațiile despre suprafețe, compartimentări, finisaje, dotări, "
  "prețuri, disponibilitate, stadiu al lucrărilor, termene și distanțe sunt orientative și pot "
  "fi actualizate fără notificare prealabilă.",
  "Randările, fotografiile, planurile și schițele au rol ilustrativ. Culorile, mobilierul, "
  "vegetația, obiectele de decor și amenajările exterioare prezentate nu fac parte din obiectul "
  "vânzării decât dacă sunt menționate expres în contract. Suprafețele finale rezultă din "
  "măsurătorile cadastrale efectuate la recepție și pot prezenta diferențe în limitele legale.",
  "Nicio informație de pe Site nu constituie ofertă în sensul Codului civil, promisiune de "
  "vânzare sau garanție privind disponibilitatea unei unități la un anumit preț. Prețurile "
  "afișate sunt exprimate în euro, includ sau nu TVA conform mențiunilor din pagină și devin "
  "ferme numai prin semnarea unui document de rezervare sau a unui antecontract."]),
 ("Calculatoare, estimări și informații financiare", [
  "Calculatorul de rată, calculatorul de randament și orice alte simulări disponibile pe Site "
  "sunt instrumente orientative, bazate pe ipoteze generale (dobânzi, durate, chirii medii "
  "observate). Rezultatele nu reprezintă ofertă de creditare, consultanță financiară, fiscală "
  "sau de investiții și nu angajează Dezvoltatorul sau vreo instituție de credit.",
  "Deciziile de achiziție, finanțare sau investiție aparțin exclusiv utilizatorului, care este "
  "încurajat să consulte un specialist independent și să solicite instituțiilor de credit "
  "oferte personalizate."]),
 ("Solicitări transmise prin formulare", [
  "Formularele de contact, de programare a unei vizionări și de abonare la notificări permit "
  "transmiterea unor solicitări către echipa de vânzări. Transmiterea unei solicitări nu creează "
  "nicio obligație de cumpărare pentru utilizator și nicio obligație de rezervare pentru "
  "Dezvoltator.",
  "Utilizatorul garantează că datele transmise sunt corecte, complete și îi aparțin sau are "
  "dreptul de a le furniza. Este interzisă transmiterea de conținut ilegal, ofensator, publicitar "
  "sau automatizat (spam). Solicitările care nu respectă aceste condiții pot fi ignorate.",
  "Programarea unei vizionări devine efectivă numai după confirmarea telefonică de către un "
  "consultant. Dezvoltatorul poate modifica sau anula o programare din motive obiective "
  "(condiții de șantier, indisponibilitate), cu informarea utilizatorului."]),
 ("Proprietate intelectuală", [
  "Conținutul Site-ului — texte, structură, denumirea și sigla Emerald City, randări, "
  "fotografii, planuri, elemente grafice, cod sursă și baze de date — este protejat de legislația "
  "privind drepturile de autor și proprietatea industrială și aparține Dezvoltatorului sau "
  "partenerilor săi licențiatori.",
  "Este permisă vizualizarea și descărcarea materialelor exclusiv pentru uz personal, "
  "necomercial, în scopul evaluării unei achiziții. Reproducerea, distribuirea, publicarea, "
  "modificarea sau utilizarea comercială a oricărui element, integral sau parțial, fără acordul "
  "scris prealabil al Dezvoltatorului, sunt interzise. Agențiile imobiliare nu pot prelua "
  "listările, prețurile sau imaginile fără un acord scris de colaborare."]),
 ("Legături către terți", [
  "Site-ul poate conține legături către pagini ale unor terți (Google Maps, publicații de presă, "
  "site-urile grupului sau ale partenerilor). Aceste pagini au propriile condiții de utilizare și "
  "politici de confidențialitate, pentru care Dezvoltatorul nu răspunde. Prezența unei legături nu "
  "reprezintă o recomandare sau o garanție a conținutului respectiv."]),
 ("Disponibilitatea Site-ului și securitatea", [
  "Dezvoltatorul depune diligențe rezonabile pentru funcționarea continuă a Site-ului, fără a "
  "garanta lipsa întreruperilor, a erorilor sau compatibilitatea cu orice dispozitiv. Site-ul poate "
  "fi suspendat temporar pentru mentenanță sau actualizări.",
  "Este interzisă orice acțiune care poate afecta funcționarea Site-ului: accesul neautorizat, "
  "extragerea automată de date (scraping), introducerea de cod malițios, testarea "
  "vulnerabilităților fără acord, supraîncărcarea serverelor."]),
 ("Limitarea răspunderii", [
  "În limitele permise de lege, Dezvoltatorul nu răspunde pentru prejudicii directe sau indirecte "
  "rezultate din utilizarea sau imposibilitatea utilizării Site-ului, din încrederea acordată "
  "informațiilor orientative publicate, din erori sau omisiuni ori din acțiunile unor terți.",
  "Nimic din prezentul document nu limitează răspunderea Dezvoltatorului pentru obligațiile "
  "asumate prin contractele semnate cu cumpărătorii, garanțiile legale privind calitatea în "
  "construcții sau drepturile consumatorilor prevăzute de legislația în vigoare."]),
 ("Protecția datelor cu caracter personal", [
  "Prelucrarea datelor cu caracter personal ale utilizatorilor este descrisă în Politica de "
  "confidențialitate, Informarea GDPR și Politica de cookies, care fac parte integrantă din "
  "prezentul document."]),
 ("Modificarea termenilor", [
  "Dezvoltatorul poate modifica oricând acești termeni. Versiunea în vigoare este cea publicată pe "
  "Site, cu data ultimei actualizări menționată la începutul documentului. Continuarea utilizării "
  "Site-ului după publicarea modificărilor reprezintă acceptarea lor."]),
 ("Legea aplicabilă și soluționarea litigiilor", [
  "Prezentul document este guvernat de legea română. Eventualele litigii se soluționează pe cale "
  "amiabilă, iar în caz contrar de instanțele competente din Iași, cu respectarea drepturilor "
  "consumatorilor.",
  "Consumatorii pot apela la Autoritatea Națională pentru Protecția Consumatorilor (anpc.ro), la "
  "procedura de soluționare alternativă a litigiilor (SAL) și la platforma europeană de "
  "soluționare online a litigiilor (ec.europa.eu/consumers/odr)."]),
 ("Contact", [
  "Pentru întrebări privind acești termeni: vanzari@emerald-city.ro, telefon 0757 70 70 80, sau "
  "în scris la sediul Dezvoltatorului. Birou de vânzări: Str. Dealul Zorilor 9, zona Păcurari, Iași."]),
],

"politica-de-confidentialitate": [
 ("Cine suntem și la ce se aplică politica", [
  f"Operatorul datelor este {OPERATOR} („Operatorul”). Politica descrie prelucrarea datelor cu "
  "caracter personal ale vizitatorilor site-ului emerald-city.ro, ale persoanelor care transmit "
  "solicitări prin formulare, telefon, e-mail sau WhatsApp, ale celor care vizitează showroom-ul "
  "și ale potențialilor cumpărători, până la semnarea unui contract.",
  "Prelucrarea se face în conformitate cu Regulamentul (UE) 2016/679 (GDPR), Legea nr. 190/2018 "
  "și Legea nr. 506/2004 privind prelucrarea datelor în sectorul comunicațiilor electronice.",
  "Responsabil cu protecția datelor: dpo@emerald-city.ro."]),
 ("Ce date colectăm", [
  "- Date de identificare și contact: nume, prenume, număr de telefon, adresă de e-mail.",
  "- Conținutul solicitării: apartamentul sau categoria de interes, buget orientativ, ziua și "
  "intervalul dorit pentru vizionare, numărul de persoane, mesajul liber.",
  "- Date de tranzacție precontractuală (numai în showroom, la rezervare): datele din actul de "
  "identitate, adresa de domiciliu, modalitatea de finanțare avută în vedere.",
  "- Date tehnice, colectate automat: adresa IP, tipul dispozitivului și al browserului, paginile "
  "vizitate, sursa de trafic, module cookie (detaliate în Politica de cookies).",
  "- Preferințe salvate local în browser: lista de apartamente salvate pentru comparare, modul de "
  "afișare a listei de disponibilitate. Aceste preferințe rămân pe dispozitivul dumneavoastră și "
  "nu sunt transmise Operatorului.",
  "- Înregistrări ale comunicărilor: e-mailuri, mesaje WhatsApp și notițe ale consultanților "
  "privind discuțiile telefonice sau din showroom.",
  "Nu colectăm categorii speciale de date (origine etnică, opinii politice, sănătate etc.) și nu "
  "ne adresăm minorilor; Site-ul este destinat persoanelor cu vârsta de cel puțin 18 ani."]),
 ("Scopurile și temeiurile prelucrării", [
  ("Scop / Temei juridic / Detalii", [
   ["Răspuns la solicitări și programarea vizionărilor", "Demersuri precontractuale la cererea persoanei vizate (art. 6 alin. 1 lit. b GDPR)", "Contactare telefonică sau prin e-mail pentru confirmarea programării și transmiterea informațiilor cerute"],
   ["Transmiterea listelor de prețuri, planurilor și ofertelor personalizate", "Demersuri precontractuale (art. 6 alin. 1 lit. b)", "Documente transmise pe e-mail sau WhatsApp, la cerere"],
   ["Rezervarea unei unități și pregătirea antecontractului", "Executarea contractului și obligații legale (art. 6 alin. 1 lit. b și c)", "Date de identificare necesare actelor notariale"],
   ["Notificări de disponibilitate și comunicări comerciale", "Consimțământ (art. 6 alin. 1 lit. a)", "Numai la abonare explicită; retragere oricând, din fiecare mesaj"],
   ["Statistici de trafic și îmbunătățirea Site-ului", "Interes legitim (art. 6 alin. 1 lit. f) sau consimțământ pentru cookie-uri neesențiale", "Date agregate, fără identificarea persoanei"],
   ["Securitatea Site-ului și prevenirea abuzurilor", "Interes legitim (art. 6 alin. 1 lit. f)", "Jurnale de server, filtrare anti-spam"],
   ["Apărarea drepturilor în justiție și conformare legală", "Obligație legală și interes legitim (art. 6 alin. 1 lit. c și f)", "Arhivare, răspuns la solicitările autorităților"],
  ]),
  "Atunci când temeiul este interesul legitim, am evaluat ca acesta să nu prevaleze asupra "
  "drepturilor și libertăților persoanei vizate; evaluarea este disponibilă la cerere."]),
 ("Cum colectăm datele", [
  "Direct de la dumneavoastră, prin formularele Site-ului, telefon, e-mail, WhatsApp, rețele "
  "sociale sau în showroom. Automat, prin module cookie și tehnologii similare, la vizitarea "
  "Site-ului. Ocazional, de la terți: platforme imobiliare prin care ați solicitat informații "
  "despre proiect sau persoane care ne-au recomandat cu acordul dumneavoastră."]),
 ("Cui transmitem datele", [
  "- Persoane împuternicite care ne furnizează servicii: găzduire web și e-mail, furnizorul "
  "sistemului de gestiune a clienților (CRM), furnizori de servicii de comunicare (telefonie, "
  "WhatsApp Business), agenția care administrează campaniile de promovare. Aceștia prelucrează "
  "datele numai pe baza instrucțiunilor noastre și a unui contract de prelucrare.",
  "- Societăți din Green Stone Group, în scop de raportare internă și administrare, pe baza "
  "interesului legitim.",
  "- Notari publici, bănci și brokeri de credite, numai la cererea dumneavoastră, în vederea "
  "rezervării sau finanțării.",
  "- Autorități publice, instanțe, consultanți juridici și contabili, când legea o impune sau "
  "pentru apărarea drepturilor noastre.",
  "Nu vindem și nu închiriem date cu caracter personal către terți."]),
 ("Transferuri în afara Spațiului Economic European", [
  "Unele servicii folosite (de exemplu Google Maps pentru harta de pe Site sau platforma "
  "WhatsApp) pot implica transferul datelor către furnizori cu sediul în afara SEE. Astfel de "
  "transferuri se realizează numai către țări cu decizie de adecvare a Comisiei Europene sau pe "
  "baza clauzelor contractuale standard și a măsurilor suplimentare adecvate."]),
 ("Cât timp păstrăm datele", [
  ("Categorie / Durata de păstrare", [
   ["Solicitări care nu au condus la o rezervare", "24 de luni de la ultima interacțiune, apoi ștergere sau anonimizare"],
   ["Abonări la notificări de disponibilitate", "Până la retragerea consimțământului sau la finalizarea vânzărilor din ansamblu"],
   ["Date din rezervări și antecontracte", "Durata contractului plus 10 ani, conform legislației fiscale și civile"],
   ["Jurnale tehnice de server", "Maximum 12 luni"],
   ["Module cookie", "Conform duratelor din Politica de cookies"],
  ]),
  "La expirarea termenelor, datele sunt șterse în siguranță sau anonimizate ireversibil."]),
 ("Cum protejăm datele", [
  "Aplicăm măsuri tehnice și organizatorice adecvate: transmiterea datelor prin conexiuni "
  "criptate (HTTPS), controlul accesului pe bază de rol, autentificare pentru sistemele interne, "
  "copii de siguranță, instruirea personalului și obligații de confidențialitate pentru "
  "consultanți și furnizori. În cazul unei încălcări a securității care prezintă risc ridicat "
  "pentru drepturile dumneavoastră, vă vom informa conform art. 34 GDPR."]),
 ("Drepturile dumneavoastră", [
  "Aveți dreptul de acces, rectificare, ștergere, restricționare a prelucrării, portabilitate, "
  "opoziție (inclusiv față de marketing direct) și de a nu face obiectul unei decizii bazate "
  "exclusiv pe prelucrare automatizată. Consimțământul poate fi retras oricând, fără a afecta "
  "legalitatea prelucrării anterioare. Detalii și modul de exercitare se găsesc în Informarea GDPR.",
  "Solicitările se transmit la dpo@emerald-city.ro și primesc răspuns în cel mult o lună. Aveți "
  "de asemenea dreptul de a depune o plângere la Autoritatea Națională de Supraveghere a "
  "Prelucrării Datelor cu Caracter Personal (dataprotection.ro)."]),
 ("Marketing direct și rețele sociale", [
  "Comunicările comerciale prin e-mail sau mesaje se transmit numai cu acordul prealabil, "
  "iar fiecare mesaj conține o opțiune de dezabonare. Paginile noastre de pe Facebook, Instagram, "
  "TikTok și YouTube sunt guvernate și de politicile platformelor respective, cu care putem avea "
  "calitatea de operatori asociați pentru statisticile de pagină."]),
 ("Actualizări", [
  f"Politica poate fi actualizată pentru a reflecta modificări legislative sau operaționale. "
  f"Versiunea curentă, cu data actualizării ({DATA_ACT}), este publicată pe Site. Modificările "
  "semnificative vor fi semnalate vizibil."]),
 ("Contact", [
  "Responsabil cu protecția datelor: dpo@emerald-city.ro. Echipa de vânzări: "
  "vanzari@emerald-city.ro, 0757 70 70 80. Birou de vânzări: Str. Dealul Zorilor 9, zona "
  "Păcurari, Iași."]),
],

"politica-de-cookies": [
 ("Ce sunt modulele cookie", [
  "Modulele cookie sunt fișiere text de mici dimensiuni, stocate de browser pe dispozitivul "
  "dumneavoastră la vizitarea unui site. Ele permit recunoașterea dispozitivului la vizitele "
  "următoare, memorarea unor preferințe și măsurarea traficului. Tehnologiile similare includ "
  "stocarea locală a browserului (localStorage), pixelii de urmărire și identificatorii de "
  "dispozitiv.",
  f"Prezenta politică este emisă de {OPERATOR} și se completează cu Politica de confidențialitate."]),
 ("Temeiul juridic", [
  "Modulele strict necesare funcționării Site-ului se folosesc pe baza interesului legitim și "
  "nu necesită acord. Toate celelalte categorii (preferințe, statistică, marketing) se activează "
  "numai după exprimarea consimțământului prin bannerul de cookie-uri, conform art. 4 din Legea "
  "nr. 506/2004 și GDPR. Consimțământul poate fi retras oricând, cu efect pentru viitor."]),
 ("Categoriile folosite pe Site", [
  ("Categorie / Scop / Exemple / Durata", [
   ["Strict necesare", "Funcționarea paginilor, securitate, reținerea alegerii privind cookie-urile", "Preferința de consimțământ (ec-consent)", "12 luni"],
   ["Preferințe (stocare locală)", "Memorarea listei de apartamente salvate pentru comparare și a modului de afișare a listei", "ec-lista, ec-vedere (localStorage — nu se transmit serverului)", "Până la ștergerea de către utilizator"],
   ["Statistică", "Măsurarea anonimizată a traficului și a paginilor vizitate, pentru îmbunătățirea Site-ului", "Instrument de analiză web, activat numai cu acord", "Până la 13 luni"],
   ["Marketing", "Măsurarea eficienței campaniilor și afișarea de anunțuri relevante pe alte platforme", "Pixeli ai platformelor publicitare, activați numai cu acord", "Până la 13 luni"],
   ["Terți încorporați", "Afișarea hărții Google Maps și a eventualelor materiale video", "Cookie-uri Google, setate la încărcarea hărții", "Conform politicii Google"],
  ]),
  "La data actualizării, Site-ul nu utilizează instrumente de statistică sau marketing active. "
  "Lista de mai sus include categoriile care pot fi activate ulterior; orice activare se va face "
  "numai după actualizarea acestei politici și obținerea acordului."]),
 ("Conținut de la terți", [
  "Harta din secțiunea „Showroom” este furnizată de Google Maps. La încărcarea ei, Google poate "
  "seta propriile module cookie și poate prelucra adresa IP conform politicii sale de "
  "confidențialitate (policies.google.com/privacy). Legăturile către Facebook, Instagram, TikTok, "
  "YouTube și WhatsApp deschid platformele respective, care aplică propriile reguli."]),
 ("Cum gestionați modulele cookie", [
  "- Prin bannerul de consimțământ afișat la prima vizită, unde puteți accepta sau refuza fiecare "
  "categorie și puteți reveni oricând asupra alegerii din legătura „Setări cookie-uri” din subsol.",
  "- Din setările browserului: Chrome, Firefox, Safari, Edge permit blocarea sau ștergerea "
  "modulelor cookie și a stocării locale. Blocarea celor strict necesare poate afecta funcționarea "
  "unor secțiuni (de exemplu, lista de comparare).",
  "- Prin instrumentele de dezactivare ale furnizorilor de statistică și publicitate, când "
  "acestea sunt active, și prin youronlinechoices.eu pentru publicitatea comportamentală."]),
 ("Date colectate și drepturi", [
  "Datele obținute prin module cookie sunt tratate conform Politicii de confidențialitate. "
  "Drepturile persoanei vizate (acces, ștergere, opoziție etc.) sunt descrise în Informarea GDPR "
  "și se exercită la dpo@emerald-city.ro."]),
 ("Actualizări", [
  f"Politica se revizuiește la fiecare modificare a instrumentelor folosite. Ultima actualizare: "
  f"{DATA_ACT}."]),
],

"informare-gdpr": [
 ("Identitatea și datele de contact ale operatorului", [
  f"{OPERATOR}. Responsabil cu protecția datelor: dpo@emerald-city.ro. Echipa de vânzări: "
  "vanzari@emerald-city.ro, 0757 70 70 80. Birou de vânzări: Str. Dealul Zorilor 9, zona "
  "Păcurari, Iași.",
  "Prezenta informare este furnizată în temeiul art. 13 și 14 din Regulamentul (UE) 2016/679 "
  "(GDPR) și se adresează vizitatorilor Site-ului, persoanelor care ne contactează, vizitatorilor "
  "showroom-ului și potențialilor cumpărători."]),
 ("Scopurile și temeiul prelucrării", [
  "- Răspunsul la solicitări, programarea și desfășurarea vizionărilor — demersuri "
  "precontractuale la cererea dumneavoastră (art. 6 alin. 1 lit. b).",
  "- Transmiterea ofertelor personalizate, planurilor și condițiilor de plată — demersuri "
  "precontractuale (art. 6 alin. 1 lit. b).",
  "- Rezervarea unei unități și încheierea actelor — executarea contractului și obligații legale "
  "fiscale și notariale (art. 6 alin. 1 lit. b și c).",
  "- Notificări de disponibilitate și comunicări comerciale — consimțământ (art. 6 alin. 1 lit. a).",
  "- Securitatea Site-ului, statistici agregate, apărarea drepturilor — interes legitim "
  "(art. 6 alin. 1 lit. f).",
  "- Supravegherea video în showroom, dacă este cazul — interes legitim privind siguranța "
  "persoanelor și bunurilor, cu semnalizare la intrare."]),
 ("Categoriile de date și sursa lor", [
  "Date de identificare și contact, conținutul solicitărilor, preferințe de achiziție, date "
  "precontractuale (la rezervare), date tehnice de navigare și înregistrări ale comunicărilor. "
  "Datele provin direct de la dumneavoastră sau, în cazuri limitate, de la platforme imobiliare "
  "prin care ați solicitat informații ori de la persoane care v-au recomandat cu acordul dumneavoastră."]),
 ("Destinatarii datelor", [
  "Persoane împuternicite (găzduire, e-mail, CRM, comunicații, agenție de promovare), societăți "
  "din Green Stone Group, notari, bănci și brokeri de credit la cererea dumneavoastră, autorități "
  "publice și consultanți profesionali când legea o impune. Detalii în Politica de confidențialitate."]),
 ("Transferul către țări terțe", [
  "Anumiți furnizori (Google, Meta/WhatsApp) pot prelucra date în afara Spațiului Economic "
  "European, exclusiv pe baza deciziilor de adecvare sau a clauzelor contractuale standard "
  "aprobate de Comisia Europeană, cu garanții suplimentare."]),
 ("Durata de stocare", [
  "Solicitările fără rezervare: 24 de luni de la ultima interacțiune. Abonările la notificări: "
  "până la retragerea consimțământului. Datele contractuale: durata contractului plus 10 ani. "
  "Jurnalele tehnice: maximum 12 luni. Modulele cookie: conform Politicii de cookies."]),
 ("Drepturile persoanei vizate", [
  "- Dreptul de acces (art. 15): confirmarea prelucrării și o copie a datelor.",
  "- Dreptul la rectificare (art. 16): corectarea datelor inexacte sau completarea celor incomplete.",
  "- Dreptul la ștergere (art. 17): în cazurile prevăzute de lege, de exemplu când datele nu mai "
  "sunt necesare sau consimțământul a fost retras.",
  "- Dreptul la restricționarea prelucrării (art. 18).",
  "- Dreptul la portabilitatea datelor (art. 20): primirea datelor într-un format structurat, "
  "utilizat în mod curent, pentru prelucrările bazate pe consimțământ sau contract.",
  "- Dreptul la opoziție (art. 21), inclusiv, oricând și fără justificare, față de marketingul direct.",
  "- Dreptul de a nu face obiectul unei decizii bazate exclusiv pe prelucrare automatizată "
  "(art. 22). Nu utilizăm astfel de decizii.",
  "- Dreptul de a retrage consimțământul oricând, fără a afecta legalitatea prelucrării anterioare.",
  "- Dreptul de a depune plângere la autoritatea de supraveghere."]),
 ("Cum vă exercitați drepturile", [
  "Trimiteți o solicitare la dpo@emerald-city.ro sau în scris la sediul operatorului, indicând "
  "dreptul invocat și datele de identificare necesare. Răspundem în cel mult o lună de la primire; "
  "termenul poate fi prelungit cu două luni în cazuri complexe, cu informarea dumneavoastră. "
  "Exercitarea drepturilor este gratuită, cu excepția cererilor vădit nefondate sau excesive.",
  "Pentru protejarea datelor, putem solicita informații suplimentare de verificare a identității "
  "înainte de a răspunde."]),
 ("Autoritatea de supraveghere", [
  "Autoritatea Națională de Supraveghere a Prelucrării Datelor cu Caracter Personal (ANSPDCP), "
  "B-dul G-ral. Gheorghe Magheru nr. 28-30, sector 1, București, cod poștal 010336; telefon "
  "+40 318 059 211; e-mail anspdcp@dataprotection.ro; www.dataprotection.ro."]),
 ("Caracterul furnizării datelor", [
  "Furnizarea datelor de contact este necesară pentru a răspunde solicitărilor și pentru a "
  "programa o vizionare; fără ele, solicitarea nu poate fi procesată. Furnizarea datelor pentru "
  "notificări și comunicări comerciale este voluntară. Datele de identificare complete sunt "
  "cerute de lege pentru încheierea actelor de rezervare și vânzare."]),
 ("Actualizarea informării", [
  f"Informarea se actualizează ori de câte ori scopurile, destinatarii sau duratele se modifică. "
  f"Ultima actualizare: {DATA_ACT}."]),
],
}


def pagina_legala(slug):
    r = "../"
    titlu, descriere = LEGALE[slug]
    sectiuni = TEXTE_LEGALE[slug]
    cuprins = "".join(f'<li><a href="#s{i}"><span>{i:02d}</span>{e(t)}</a></li>'
                      for i, (t, _) in enumerate(sectiuni, 1))
    corp = ""
    for i, (t, elems) in enumerate(sectiuni, 1):
        corp += f'<section class="ec-legal__s" id="s{i}"><h2><span>{i:02d}</span>{e(t)}</h2>'
        lista = []
        def goleste():
            nonlocal corp, lista
            if lista:
                corp += "<ul>" + "".join(f"<li>{e(x)}</li>" for x in lista) + "</ul>"
                lista = []
        for el in elems:
            if isinstance(el, tuple):
                goleste()
                cap, randuri = el
                th = "".join(f"<th>{e(c.strip())}</th>" for c in cap.split("/"))
                tr = "".join("<tr>" + "".join(f"<td>{e(c)}</td>" for c in rd) + "</tr>" for rd in randuri)
                corp += f'<div class="ec-table ec-legal__t"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'
            elif el.startswith("- "):
                lista.append(el[2:])
            else:
                goleste()
                corp += f"<p>{e(el)}</p>"
        goleste()
        corp += "</section>"

    altele = "".join(
        f'<a class="ec-legal__alt" href="{r}{sl}/">{ic("file-lines")} {e(LEGALE[sl][0])}</a>'
        for sl in LEGALE if sl != slug)

    continut = f"""<div class="ec-wrap">
  <header class="ec-legal__h">
    <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>{e(titlu)}</nav>
    <p class="ec-eyebrow">Informații legale</p>
    <h1>{e(titlu)}</h1>
    <p class="ec-legal__lead">{e(descriere)}</p>
    <div class="ec-legal__meta">
      <span>{ic("calendar-days")} Ultima actualizare: {DATA_ACT}</span>
      <span>{ic("building")} Tala Sapphire S.R.L. · Green Stone Group</span>
      <span>{ic("envelope")} dpo@emerald-city.ro</span>
    </div>
  </header>

  <div class="ec-legal">
    <aside class="ec-legal__nav">
      <div class="ec-legal__navi">
        <b>Cuprins</b>
        <ol>{cuprins}</ol>
        <div class="ec-legal__alte">{altele}</div>
      </div>
    </aside>
    <article class="ec-legal__body">{corp}
      <div class="ec-legal__foot">
        <p>Pentru orice întrebare legată de acest document: <a href="mailto:dpo@emerald-city.ro">dpo@emerald-city.ro</a>
           sau <a href="{r}contact/">pagina de contact</a>.</p>
      </div>
    </article>
  </div>

  <section class="ec-section" style="padding-block:var(--ec-section)">
    {cta_dublu(r, slug)}
  </section>
</div>
<script>
(() => {{
  const leg = [...document.querySelectorAll('.ec-legal__navi a[href^="#s"]')];
  const sec = leg.map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
  if (!sec.length) return;
  const o = new IntersectionObserver(es => es.forEach(x => {{
    if (!x.isIntersecting) return;
    leg.forEach(a => a.classList.toggle('is-on', a.getAttribute('href') === '#' + x.target.id));
  }}), {{ rootMargin: '-20% 0px -70% 0px' }});
  sec.forEach(s => o.observe(s));
}})();
</script>"""
    return pagina(f"{titlu} — Emerald City Iași", descriere, continut, r, None, slug + "/")


# ==================================================================== rulare
# ========================================================== despre noi ==
# Pictogramele vin din Font Awesome 6, incarcat in invelisul paginii.
def ic(nume, extra="", brand=False):
    fam = "fa-brands" if brand else "fa-solid"
    return f'<i class="{fam} fa-{nume}{extra}" aria-hidden="true"></i>'


# Nivelul tehnic agreat pentru ansamblu. Marcile exacte se confirma in anexa
# tehnica a contractului, deci pagina nu numeste furnizori.
FINISAJE = [
 ("fire-flame-simple", "Încălzire în pardoseală", "În toate camerele, distribuitor individual",
  "Căldura se distribuie uniform de la sol, fără calorifere pe pereți. Peretele rămâne liber pentru "
  "mobilier, iar consumul scade, instalația lucrând la temperatură joasă."),
 ("gauge-high", "Centrală în condensație", "Randament ridicat, reglaj pe cameră",
  "Recuperează căldura din gazele de ardere, așa că scoate mai multă energie din același metru "
  "cub de gaz. Diferența la factură ajunge până la 35% față de o centrală clasică."),
 ("layer-group", "Termosistem de fațadă", "Izolație continuă, fără punți termice",
  "Fațada este izolată pe tot conturul, inclusiv la planșee și buiandrugi, ceea ce reduce "
  "pierderile de căldură iarna, aportul termic vara și zgomotul din exterior."),
 ("border-all", "Tâmplărie PVC cu 7 camere", "Geam tripan, sticlă Low-E",
  "Profilul cu șapte camere și geamul cu trei foi izolează termic și fonic la nivelul cerut "
  "clădirilor noi. Stratul Low-E reflectă căldura înapoi în încăpere."),
 ("grip-lines", "Parchet laminat de 10 mm", "Clasă de trafic intens",
  "Grosime de 10 mm, dimensionată pentru trafic intens. Montajul pe strat fonoabsorbant "
  "reduce transmiterea zgomotului de impact către nivelul inferior."),
 ("bath", "Grupuri sanitare complet finisate", "Gresie, faianță, obiecte sanitare, baterii",
  "Placările, vasul de toaletă, lavoarul, bateriile și racordurile sunt montate. Nu sunt "
  "necesare lucrări suplimentare după predare."),
 ("bolt", "Instalație electrică completă", "Aparataj montat, tablou cu siguranțe",
  "Prizele și întrerupătoarele sunt montate, tabloul este echipat și etichetat, iar circuitele "
  "sunt dimensionate separat pentru bucătărie, grup sanitar și camere."),
 ("paint-roller", "Pereți finisați", "Glet fin și vopsea lavabilă",
  "Pereții și tavanele sunt gletuite și vopsite. Suprafața este pregătită pentru mobilare "
  "imediată sau pentru aplicarea altei culori, fără pregătiri suplimentare."),
 ("door-closed", "Uși interioare montate", "Finisaj mat, feronerie inclusă",
  "Toate ușile interioare sunt montate, cu tocuri, pervazuri și feronerie. Ușa de intrare este "
  "metalică, cu izolație și închidere în mai multe puncte."),
 ("video", "Videointerfon", "Post interior în fiecare apartament",
  "Permite identificarea vizitatorilor înainte de deschiderea accesului. Intrarea în bloc și "
  "în parcarea subterană se face controlat, cu cartelă sau cod."),
]

GARANTII = [
 ("Structura de rezistență", "Toată durata de existență a clădirii",
  "Legea 10/1995 privind calitatea în construcții"),
 ("Vicii ascunse ale construcției", "10 ani de la recepția finală",
  "Legea 10/1995 și Codul civil"),
 ("Vicii aparente", "1 an de la predare", "Codul civil"),
 ("Instalații și echipamente", "Conform garanției fiecărui producător",
  "Certificatele predate la recepție"),
 ("Finisaje și dotări", "Conform anexei tehnice a contractului",
  "Contractul de vânzare"),
]

DOCUMENTE = [
 ("Autorizația de construire",
  "Emisă de autoritatea locală, împreună cu certificatul de urbanism care a stat la baza proiectului."),
 ("Cartea tehnică a construcției",
  "Dosarul complet al clădirii: proiectul, avizele, procesele-verbale și instrucțiunile de exploatare."),
 ("Procesul-verbal de recepție",
  "Documentul care consemnează predarea clădirii, semnat de comisia de recepție."),
 ("Documentația cadastrală",
  "Măsurătorile și planurile apartamentului, depuse pentru înscrierea în cartea funciară."),
 ("Extrasul de carte funciară",
  "Dovada intabulării pe numele cumpărătorului, cu suprafețele și cotele indivize."),
 ("Certificatul de performanță energetică",
  "Clasa energetică a apartamentului și consumul estimat, calculate de un auditor autorizat."),
]

DRUM = [
 ("eye", "01", "Vizionare",
  "Prezentarea amplasamentului și a apartamentului-model, împreună cu lista de "
  "disponibilitate, cu prețuri și suprafețe.", "Aceeași zi"),
 ("bookmark", "02", "Rezervare",
  "Apartamentul ales se blochează pe numele cumpărătorului, iar prețul se menține pe perioada rezervării.",
  "1–3 zile"),
 ("file-signature", "03", "Antecontract",
  "Antecontractul se semnează la notar, cu un avans de 15%. Suprafețele, prețul și "
  "termenul de predare se fixează în contract.", "La notar"),
 ("helmet-safety", "04", "Construcție",
  "Progresul poate fi urmărit în jurnalul de șantier, actualizat lunar cu fotografii datate din teren.",
  "Conform etapei"),
 ("key", "05", "Recepție și chei",
  "Apartamentul se verifică împreună cu un reprezentant, se semnează contractul final, "
  "se efectuează intabularea și se predau cheile.", "La finalizare"),
]

VS = [
 ("Costul lunar cu încălzirea",
  "Redus — termosistem continuu, centrală în condensație, încălzire în pardoseală",
  "Ridicat — izolație parțială, distribuție veche"),
 ("Starea instalațiilor", "Noi, cu garanție și carte tehnică",
  "Vechi de 30–50 de ani, adesea de înlocuit"),
 ("Finisajele", "Incluse în preț, montate și garantate",
  "De refăcut integral, cost separat"),
 ("Parcarea", "Loc propriu, subteran sau la suprafață",
  "Nealocată, ocupată în ordinea sosirii"),
 ("Structura", "Proiectată la normele antiseismice actuale",
  "Conform normelor din anul construcției"),
 ("Spațiul verde", "15.501,80 m² amenajați, 30,85% din teren",
  "Variabil, de regulă neamenajat"),
 ("Actele", "Intabulare directă de la dezvoltator, fără istoric",
  "Verificări de istoric, posibile litigii sau moșteniri"),
 ("Comisionul", "Zero — vânzare directă de la dezvoltator",
  "De regulă 2–3% pentru agenție"),
]

REFERINTE = [
 ("Lapis Residence", "Iași",
  "Ansamblu al Green Stone Group, cu piste de biciclete în tot cartierul, panouri "
  "fotovoltaice și finisaje premium. Proiectul a început la finalul lui 2023.",
  [("Oraș", "Iași"), ("Predare", "La cheie")]),
 ("Onyx Residence", "Iași",
  "Prelungirea ansamblului Lapis: 360 de apartamente în 8 blocuri, cu spații comerciale la "
  "parter. Împreună, cele două ajung la 740 de locuințe.",
  [("Oraș", "Iași"), ("Predare", "La cheie")]),
]

# Cifrele mari din capul paginii: valoare, sufix, eticheta, pictograma.
FIGURI = [
 ("925", "", "Apartamente", "building"),
 ("18", "", "Blocuri P+3E", "city"),
 ("30,85", "%", "Spațiu verde", "tree"),
 ("940", "", "Locuri de parcare", "square-parking"),
]

# Ancorele din bara lipita
# numarul din bara trebuie sa fie acelasi cu cel din capul sectiunii
ANCORE = [
 ("01", "viziune",    "Viziune"),
 ("02", "finisaje",   "Finisaje"),
 ("03", "garantii",   "Garanții"),
 ("04", "documente",  "Documente"),
 ("05", "proces",     "Proces"),
 ("06", "comparatie", "Comparație"),
 ("08", "proiecte",   "Experiență"),
 ("10", "dotari",     "Dotări"),
 ("11", "intrebari",  "Întrebări"),
 ("12", "birou",      "Birou"),
]

FAQ_DESPRE = [
 ("Cine dezvoltă Emerald City?",
  "Tala Sapphire S.R.L., companie din Green Stone Group. Vânzarea se face direct de la "
  "dezvoltator, fără comision de intermediere."),
 ("Ce experiență are dezvoltatorul?",
  "Emerald City este dezvoltat de Tala Sapphire S.R.L., companie din Green Stone Group — un "
  "grup cu proiecte în Marea Britanie, Israel și România. În Iași, grupul dezvoltă și "
  "ansamblurile Lapis și Onyx Residence, iar în Sibiu a livrat faza I de la Magnolia "
  "Residence, cu 1.132 de apartamente."),
 ("Ce garanție am pentru structura clădirii?",
  "Structura de rezistență este garantată pe toată durata de existență a clădirii, conform "
  "Legii 10/1995 privind calitatea în construcții."),
 ("Cât timp răspunde dezvoltatorul pentru vicii ascunse?",
  "10 ani de la recepția finală, conform Legii 10/1995 și Codului civil. Viciile aparente se "
  "semnalează în primul an de la predare."),
 ("Ce documente primesc la predare?",
  "Procesul-verbal de recepție, cartea tehnică a construcției, documentația cadastrală, extrasul "
  "de carte funciară cu intabularea pe numele cumpărătorului și certificatul de performanță energetică."),
 ("Apartamentele se predau finisate?",
  "Da, complet finisate. Parchet, gresie și faianță montate, grupuri sanitare echipate, pereți "
  "gletuiți și vopsiți, uși montate, instalație electrică cu aparataj, încălzire în pardoseală. "
  "Apartamentul este gata de mobilat la data recepției."),
 ("Ce înseamnă centrală în condensație?",
  "Recuperează căldura din gazele de ardere în loc să o evacueze pe horn. La același confort, "
  "consumă până la 35% mai puțin gaz decât o centrală clasică."),
 ("Ce avantaj are încălzirea în pardoseală?",
  "Căldura se distribuie uniform de la sol în sus, fără calorifere pe pereți, și funcționează la "
  "temperatură joasă, deci consumă mai puțin. În plus, pereții rămân liberi pentru mobilier."),
 ("De ce să cumpăr direct de la dezvoltator?",
  "Nu se percepe comision de intermediere, prețul și termenele se stabilesc direct cu "
  "dezvoltatorul, lista de disponibilitate este publică, iar stadiul lucrărilor poate fi "
  "urmărit lunar."),
 ("Ce avans se cere la antecontract?",
  "15% din preț la semnarea antecontractului la notar, iar diferența la predare. Etapele de plată "
  "se stabilesc în contract."),
 ("Pot cumpăra cu credit ipotecar?",
  "Da. Apartamentele se pot achiziționa cu credit ipotecar standard, iar cele care se încadrează "
  "în plafonul programului pot fi cumpărate și prin Noua Casă. Echipa de vânzări prezintă "
  "varianta potrivită fiecărui buget."),
 ("Prețurile includ TVA?", "Da, prețurile afișate includ TVA."),
 ("Ce dotări are cartierul?",
  "Piste de biciclete, zone de fitness, locuri de joacă, parcări private, preechipare pentru "
  "stații de încărcare auto, lifturi, panouri fotovoltaice, spații verzi și parc, colectare "
  "îngropată a deșeurilor."),
 ("Cât spațiu verde are ansamblul?",
  "15.501,80 m² de spațiu verde amenajat, adică 30,85% din suprafața terenului de 50.235 m². "
  "Procentul de ocupare a terenului este 30%, iar coeficientul de utilizare 1,80."),
 ("Când se finalizează ansamblul?",
  "Construcția este împărțită în trei etape: 322 de apartamente în Etapa I, 423 în Etapa II și "
  "180 în Etapa III. Termenul fiecărei etape se confirmă în contract."),
 ("Unde este biroul de vânzări?",
  "Str. Dealul Zorilor 9, zona Păcurari, Iași. Program: luni–vineri 9–18 și sâmbătă 10–14. "
  "Telefon 0757 70 70 80."),
]


def pagina_despre():
    r = "../"

    figuri = "".join(
        f'<div class="ec-fig ec-rv"><span class="ec-fig__ic">{ic(pic)}</span>'
        f'<span><b data-num="{e(val)}">{e(val)}{e(suf)}</b><em>{e(et)}</em></span></div>'
        for val, suf, et, pic in FIGURI)

    ancore = "".join(f'<a href="#{a}"><b>{n}</b>{e(t)}</a>'
                     for n, a, t in ANCORE)

    fisa = "".join(
        f'<div class="ec-fac__i ec-rv"><i>{ic(k)}</i><span>{e(nume)}</span></div>'
        for k, nume, spec, desc in FINISAJE)

    garantii = "".join(f"<tr><td>{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td></tr>"
                       for a, b, c in GARANTII)

    docs = "".join(
        f'<div class="ec-docs__i ec-rv"><span class="ec-docs__c">{ic("check")}</span>'
        f'<span><b>{e(t)}</b><em>{e(d)}</em></span></div>'
        for t, d in DOCUMENTE)

    drum = "".join(
        f'<div class="ec-drum__i ec-rv"><span class="ec-drum__ic">{ic(pic)}</span>'
        f'<span class="ec-drum__n">{n}</span>'
        f'<h3>{e(t)}</h3><p>{e(d)}</p>'
        f'<span class="ec-drum__t">{e(cand)}</span></div>'
        for pic, n, t, d, cand in DRUM)

    vs = "".join(f'<tr><td>{e(a)}</td><td class="yes">{e(b)}</td>'
                 f'<td class="no">{e(c)}</td></tr>' for a, b, c in VS)

    refs = "".join(
        f'<article class="ec-ref ec-rv"><span class="ec-ref__ic">{ic("building-circle-check")}</span>'
        f'<span class="ec-ref__k">{e(oras)}</span>'
        f'<h3>{e(nume)}</h3><p>{e(desc)}</p><dl>'
        + "".join(f"<div><dt>{e(dt)}</dt><dd>{e(dd)}</dd></div>" for dt, dd in perechi)
        + "</dl></article>"
        for nume, oras, desc, perechi in REFERINTE)

    faq = "".join(f"<details><summary>{e(q)}</summary>"
                  f'<div class="ec-faq__a">{e(a)}</div></details>'
                  for q, a in FAQ_DESPRE)

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "AboutPage", "name": "Despre Emerald City",
             "url": "https://emerald-city.ro/despre-emerald-city/"},
            {"@type": "Organization",
             "name": "Tala Sapphire S.R.L.",
             "url": "https://emerald-city.ro/",
             "telephone": "+40757707080",
             "email": "vanzari@emerald-city.ro",
             "address": {"@type": "PostalAddress",
                         "streetAddress": "Str. Dealul Zorilor 9",
                         "addressLocality": "Iași",
                         "addressRegion": "Iași",
                         "addressCountry": "RO"}},
            {"@type": "FAQPage",
             "mainEntity": [{"@type": "Question", "name": q,
                             "acceptedAnswer": {"@type": "Answer", "text": a}}
                            for q, a in FAQ_DESPRE]},
        ]}

    continut = f"""<section class="ec-phero">
  {imagine("dining-01", "", r, "100vw", eager=True)}
  <div class="ec-phero__veil"></div>
  <div class="ec-wrap ec-phero__in">
    <nav class="ec-crumbs"><a href="{r}">Acasă</a><span>/</span>Despre noi</nav>
    <p class="ec-eyebrow">Despre noi</p>
    <h1>Un cartier construit ca să rămână</h1>
    <p class="ec-phero__sub">
      925 de apartamente pe cinci hectare în Iași, zona Păcurari, ridicate în blocuri de
      patru niveluri, cu aproape o treime din teren lăsată spațiu verde. Se predau complet
      finisate, direct de la dezvoltator.
    </p>
    <div class="ec-phero__cta">
      <a class="ec-btn ec-btn--white" href="#finisaje">{ic("list-check")} Dotări incluse</a>
      <a class="ec-btn ec-btn--outlight" href="{r}apartamente-iasi/disponibilitate/">{ic("table-list")} Disponibilitate și prețuri</a>
    </div>
  </div>
</section>

<div class="ec-figs-wrap">
  <div class="ec-wrap"><div class="ec-figs">{figuri}</div></div>
</div>

<div class="ec-subnav">
  <div class="ec-wrap"><nav class="ec-subnav__in">{ancore}</nav></div>
</div>

<div class="ec-wrap">
  <section class="ec-section" id="viziune">
    <div class="ec-shead">
      <div><span class="ec-shead__n">01 — Viziunea</span>
        <h2>Densitate mică, <em>spațiu de trăit</em></h2></div>
      <p class="ec-shead__p">
        Regimul de înălțime și densitatea determină calitatea locuirii pe termen lung.
      </p>
    </div>
    <div class="ec-split" style="margin-top:2.5rem">
      <div class="ec-prose">
        <p>
          Ansamblul este dezvoltat pe orizontală, nu pe verticală. Cele 18 blocuri au parter și
          trei etaje, cu înălțimea maximă de 18 metri. Consecințele sunt măsurabile:
          iluminare naturală inclusiv la parter, număr redus de apartamente pe scară,
          încărcare mică a lifturilor și distanțe generoase între clădiri.
        </p>
        <p>
          Din cele 50.235 m² de teren, 15.501,80 m² sunt spațiu verde amenajat, adică 30,85%.
          Suprafața cuprinde alei, parc, locuri de joacă și piste de biciclete, prevăzute
          din planul de ansamblu. Parcarea este asigurată cu 940 de locuri, dintre care
          258 subterane, astfel încât circulația auto să nu ocupe spațiile pietonale.
        </p>
        <p>
          Apartamentele se predau complet finisate, cu încălzire în pardoseală și tâmplărie
          performantă. Cele de la parter au curte proprie, iar toate au balcon. Vânzarea
          se face direct, fără comision de intermediere.
        </p>
      </div>
      <figure style="margin:0">
        {imagine("living-01", "Interior de apartament finisat la Emerald City", r,
                 "(min-width: 62rem) 46vw, 100vw")}
      </figure>
    </div>
  </section>

  <section class="ec-section" id="finisaje" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">02 — Finisaje</span>
        <h2>Ce înseamnă <em>predare la cheie</em></h2></div>
      <p class="ec-shead__p">
        10 poziții incluse în preț, montate și garantate. Specificațiile complete
        sunt pe pagina de finisaje.
      </p>
    </div>
    <div class="ec-fac" style="margin-top:2.5rem">{fisa}</div>
    <div class="ec-center" style="margin-top:2rem">
      <a class="ec-btn" href="{r}finisaje/">{ic("list-check")} Fișa tehnică completă</a>
    </div>
  </section>

  <section class="ec-section" id="garantii" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">03 — Garanții</span>
        <h2>Ce garantăm și <em>pe ce temei</em></h2></div>
      <p class="ec-shead__p">
        Garanțiile sunt obligații legale. Termenele și temeiul normativ, în tabelul de mai jos.
      </p>
    </div>
    <div class="ec-table ec-table--vs" style="margin-top:2.5rem">
      <table>
        <thead><tr><th scope="col">{ic("shield-halved")} Ce este garantat</th>
          <th scope="col">{ic("hourglass-half")} Cât timp</th>
          <th scope="col">{ic("scale-balanced")} Temei</th></tr></thead>
        <tbody>{garantii}</tbody>
      </table>
    </div>
  </section>

  <section class="ec-section" id="documente" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">04 — Documente</span>
        <h2>Documente predate <em>odată cu cheile</em></h2></div>
      <p class="ec-shead__p">
        Documentele predate odată cu apartamentul, la recepție și la intabulare.
      </p>
    </div>
    <div class="ec-docs" style="margin-top:2.5rem">{docs}</div>
  </section>
</div>

<section class="ec-band" id="proces">
  <div class="ec-wrap">
    <div class="ec-section">
      <div class="ec-shead">
        <div><span class="ec-shead__n" style="color:var(--ec-brass)">05 — Proces</span>
          <h2>De la vizionare <em>la chei</em></h2></div>
        <p class="ec-shead__p">
          5 pași, cu operațiunile și documentele aferente fiecăruia.
        </p>
      </div>
      <div class="ec-drum" style="margin-top:2.5rem">{drum}</div>
    </div>
  </div>
</section>

<div class="ec-wrap">
  <section class="ec-section" id="comparatie">
    <div class="ec-shead">
      <div><span class="ec-shead__n">06 — Comparație</span>
        <h2>Apartament nou <em>sau bloc vechi</em></h2></div>
      <p class="ec-shead__p">
        Diferența de preț pe metru pătrat se compensează prin costurile de exploatare și prin lucrările care nu mai sunt necesare.
      </p>
    </div>
    <div class="ec-table ec-table--vs" style="margin-top:2.5rem">
      <table>
        <thead><tr><th scope="col">Criteriu</th>
          <th scope="col">{ic("circle-check")} Emerald City</th>
          <th scope="col">{ic("circle-minus")} Apartament vechi</th></tr></thead>
        <tbody>{vs}</tbody>
      </table>
    </div>
  </section>

  <section class="ec-section" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">07 — Direct dezvoltator</span>
        <h2>Avantajele <em>achiziției directe</em></h2></div>
      <p class="ec-shead__p">Patru diferențe verificabile.</p>
    </div>
    <div class="ec-why" style="margin-top:2.5rem">
      <div class="ec-why__i ec-rv">{ic("percent")}
        <h3>Zero comision</h3>
        <p>Fără comision de agenție de 2–3%. Prețul afișat este prețul din actul notarial.</p></div>
      <div class="ec-why__i ec-rv">{ic("list-check")}
        <h3>Lista completă</h3>
        <p>Toate cele 925 de apartamente sunt afișate, cu preț, suprafață, etaj și orientare.</p></div>
      <div class="ec-why__i ec-rv">{ic("file-signature")}
        <h3>Contract direct</h3>
        <p>Termenele și etapele de plată se stabilesc direct cu dezvoltatorul, fără intermediar.</p></div>
      <div class="ec-why__i ec-rv">{ic("helmet-safety")}
        <h3>Progres verificabil</h3>
        <p>Publicăm lunar stadiul lucrărilor, cu fotografii datate din teren.</p></div>
    </div>
  </section>

  <section class="ec-section" id="proiecte" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">08 — Experiență</span>
        <h2>Proiecte <em>livrate anterior</em></h2></div>
      <p class="ec-shead__p">
        Emerald City este dezvoltat de Tala Sapphire S.R.L., companie din Green Stone Group.
        În Iași, grupul dezvoltă și ansamblurile de mai jos.
      </p>
    </div>
    <div class="ec-refs" style="margin-top:2.5rem">{refs}</div>
    <div class="ec-center" style="margin-top:2rem">
      <a class="ec-btn ec-btn--out" href="{r}despre-dezvoltator/">{ic("building")} Portofoliul complet al grupului</a>
    </div>
  </section>

  <section class="ec-section" style="padding-block:0 var(--ec-section)">
    <div class="ec-spot">
      <div class="ec-spot__b">
        <p class="ec-eyebrow" style="color:var(--ec-brass)">09 — Verifică</p>
        <h2>Criterii de verificare a unui dezvoltator</h2>
        <p>
          Criteriile de mai jos permit verificarea oricărui proiect rezidențial înainte de semnarea unui antecontract.
        </p>
        <ul class="ec-spot__list">
          <li>Autorizația de construire, cu numărul și data emiterii</li>
          <li>Certificatul de urbanism și indicatorii aprobați: POT și CUT</li>
          <li>Situația juridică a terenului și extrasul de carte funciară</li>
          <li>Anexa tehnică de finisaje, poziție cu poziție</li>
          <li>Termenul de predare scris în antecontract, nu spus verbal</li>
          <li>Proiecte livrate anterior, care pot fi vizitate</li>
          <li>Cine execută structura și cine verifică proiectul</li>
        </ul>
        <div class="ec-spot__cta">
          <a class="ec-btn ec-btn--white" href="{r}proiect/">{ic("compass-drafting")} Datele proiectului</a>
          <a class="ec-btn ec-btn--outlight" href="{r}stadiu-lucrari/">{ic("helmet-safety")} Jurnal de șantier</a>
        </div>
      </div>
      <figure>
        {imagine("hol-01", "Hol de acces într-un bloc Emerald City", r,
                 "(min-width: 60rem) 48vw, 100vw")}
      </figure>
    </div>
  </section>

  <section class="ec-section" id="dotari" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">10 — Dotări</span>
        <h2>Dotări <em>și facilități</em></h2></div>
      <p class="ec-shead__p">
        Dotările locuinței și facilitățile de folosință comună.
      </p>
    </div>
    <div class="ec-dotari" style="margin-top:2.5rem">
      {panou_dotari("În apartament", "house-chimney", DOTARI_LOCUINTA, "Incluse în preț")}
      {panou_dotari("În cartier", "tree-city", DOTARI_CARTIER, "Folosință comună")}
    </div>
  </section>

  <section class="ec-section" id="intrebari" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">11 — Întrebări</span>
        <h2>Despre dezvoltator, <em>calitate și garanții</em></h2></div>
      <p class="ec-shead__p">
        {len(FAQ_DESPRE)} întrebări la care răspundem cel mai des, cu cifre și termene concrete.
      </p>
    </div>
    <div class="ec-faq" style="margin-top:2.5rem">{faq}</div>
  </section>

  {showroom(r, "12")}
</div>

<script>
/* cifrele mari urca pana la valoarea reala, o singura data */
(() => {{
  const nr = [...document.querySelectorAll('.ec-fig b[data-num]')];
  if (!nr.length) return;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const urca = el => {{
    const brut = el.dataset.num;
    const tinta = parseFloat(brut.replace(/\\./g, '').replace(',', '.'));
    const zec = (brut.split(',')[1] || '').length;
    const sufix = el.textContent.replace(brut, '');
    const t0 = performance.now(), dur = 1100;
    const pas = t => {{
      const p = Math.min((t - t0) / dur, 1);
      const v = tinta * (1 - Math.pow(1 - p, 3));
      el.textContent = v.toLocaleString('ro-RO', {{
        minimumFractionDigits: zec, maximumFractionDigits: zec }}) + sufix;
      if (p < 1) requestAnimationFrame(pas);
    }};
    requestAnimationFrame(pas);
  }};
  const o = new IntersectionObserver(es => es.forEach(x => {{
    if (x.isIntersecting) {{ urca(x.target); o.unobserve(x.target); }}
  }}), {{ threshold: .4 }});
  nr.forEach(x => o.observe(x));
}})();

/* bara de sectiuni: evidentiaza sectiunea aflata in dreptul ecranului */
(() => {{
  const bara = document.querySelector('.ec-subnav');
  if (!bara) return;
  const leg = [...bara.querySelectorAll('a')];
  const sect = leg.map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
  if (!sect.length) return;
  const o = new IntersectionObserver(es => {{
    es.forEach(x => {{
      if (!x.isIntersecting) return;
      leg.forEach(a => a.classList.toggle('is-on',
        a.getAttribute('href') === '#' + x.target.id));
    }});
  }}, {{ rootMargin: '-20% 0px -70% 0px' }});
  sect.forEach(s => o.observe(s));
}})();
</script>"""

    return pagina("Despre Emerald City — finisaje și garanții | Iași",
                  "Ce include predarea la cheie, ce garanții și ce documente se predau. "
                  "925 de apartamente în Iași, zona Păcurari, direct de la dezvoltator.",
                  continut, r, schema, "despre-emerald-city/")


def main():
    NUM = {"etaj": int, "nr_camere": int, "su_utila": float, "su_balcon": float,
           "su_curte": float, "pret_eur": int, "pret_mp_eur": float, "cota_teren": float}
    unitati = []
    for row in csv.DictReader(open(CSV, encoding="utf-8")):
        unitati.append({k: NUM[k](v) if k in NUM else v for k, v in row.items()})

    for d in ("apartamente-iasi", "investitie-apartamente-iasi", "compara", "contact",
              "apartamente-iasi-pacurari", "stadiu-lucrari", "despre-dezvoltator",
              "proiect", "aparitii-presa", "despre-emerald-city", "finisaje", *LEGALE):
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

    # pagini de sine statatoare
    for nume, continut in (("investitie-apartamente-iasi", pagina_investitie(unitati)),
                           ("compara", pagina_comparator()),
                           ("contact", pagina_contact()),
                           ("programare-vizionare", pagina_programare(unitati)),
                           ("apartamente-iasi-pacurari", pagina_zona()),
                           ("stadiu-lucrari", pagina_stadiu()),
                           ("despre-emerald-city", pagina_despre()),
                           ("despre-dezvoltator", pagina_dezvoltator()),
                           ("proiect", pagina_proiect(unitati)),
                           ("aparitii-presa", pagina_presa()),
                           ("finisaje", pagina_finisaje())):
        d = os.path.join(RAD, nume)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(continut)

    d = os.path.join(RAD, "noutati")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina_noutati())
    for a in ARTICOLE_BLOG:
        d = os.path.join(RAD, "noutati", a["slug"])
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(pagina_articol(a))

    for slug in LEGALE:
        d = os.path.join(RAD, slug)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(pagina_legala(slug))

    # compartimentari, in silozul categoriei
    for cod, us in grupe.items():
        d = os.path.join(RAD, *slug_tip(cod).rstrip("/").split("/"))
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(pagina_tip(cod, us, grupe))

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
              for d in ("apartamente-iasi",)
              for dp, _, fs in os.walk(os.path.join(RAD, d)) for f in fs)
    print("  apartamente-iasi/              hub + 3 categorii + disponibilitate")
    print(f"  apartamente-iasi/<cod>/            {n_unit} pagini de unitate")
    print(f"  apartamente-iasi/<cat>/tip-<cod>/   {len(grupe)} compartimentari")
    print(f"\n  total {n_unit + len(grupe) + 2} pagini, {dim/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()
