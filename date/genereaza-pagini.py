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

TEL = "+40757707080"
TEL_AFIS = "0757 70 70 80"
WA = "https://wa.me/40757707080"
TEL_LINK = "tel:+40757707080"

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
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css" integrity="sha512-Evv84Mr4kqVGRNSgIGL/F/aIDqQb7xQ2vcrdIwxfjThSH8CSR7PBEakCr51Ck+w+/U6swU2Im1vVX0SVk9ABhg==" crossorigin="anonymous" referrerpolicy="no-referrer">
<link rel="stylesheet" href="{r}assets/css/main.css">
{ld}
</head>
<body data-radacina="{r}">

<div class="ec-topbar">
  <div class="ec-topbar__in">
    <span class="ec-topbar__l"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s7-6.2 7-11a7 7 0 10-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.6"/></svg> Apartamente Iași, zona Păcurari — <strong>DIRECT DEZVOLTATOR</strong></span>
    <div class="ec-topbar__right">
      <a href="tel:+40757707080"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4.5 4h3l1.5 4-2 1.5a12 12 0 006 6L14.5 13l4 1.5v3a2 2 0 01-2.2 2A16 16 0 012.5 6.2 2 2 0 014.5 4z"/></svg> 0757 70 70 80</a>
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
            <img src="{r}assets/img/hol-01-800.jpg" alt="" width="800" height="450" loading="lazy">
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
            <div class="ec-mega__tipuri"><a class="ec-mega__t" href="{r}tipologii/1a/"><b>1A</b><span>37–39 m²</span><i>109 libere</i></a><a class="ec-mega__t" href="{r}tipologii/2a/"><b>2A</b><span>51–54 m²</span><i>163 libere</i></a><a class="ec-mega__t" href="{r}tipologii/2b/"><b>2B</b><span>57–61 m²</span><i>122 libere</i></a><a class="ec-mega__t" href="{r}tipologii/3a/"><b>3A</b><span>69–74 m²</span><i>70 libere</i></a><a class="ec-mega__t" href="{r}tipologii/3b/"><b>3B</b><span>76–81 m²</span><i>53 libere</i></a></div>
            <a class="ec-mega__i" href="{r}apartamente-iasi/disponibilitate/"><span class="ec-mega__ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/></svg></span><span class="ec-mega__tx"><b>Disponibilitate și prețuri</b><em>Toate cele 925, cu filtre</em></span></a>
            <a class="ec-mega__i" href="{r}investitie-apartamente-iasi/"><span class="ec-mega__ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 12h2M12 12h2M16 12h.01M8 16h2M12 16h2M16 16h.01"/></svg></span><span class="ec-mega__tx"><b>Investiție și randament</b><em>Calculator de chirie și amortizare</em></span></a>
          </div>
          <a class="ec-mega__card" href="{r}apartamente-iasi/">
            <img src="{r}assets/img/living-01-800.jpg" alt="" width="800" height="450" loading="lazy">
            <span class="ec-mega__cardb"><b>517 apartamente disponibile</b>
              <em>Preț și disponibilitate actualizate din tabelul de vânzări</em></span>
          </a>
        </div>
      </span>
      <a href="{r}apartamente-iasi/disponibilitate/">Disponibilitate</a>
      <a href="{r}investitie-apartamente-iasi/">Investiție</a>
      <a href="{r}contact/">Contact</a>
    </nav>
    <a class="ec-btn" href="{r}contact/"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg> Programare vizionare</a>
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
        <ul>{"".join(f'<li><a href="{r}tipologii/{c.lower()}/">Apartament Tip {c}</a></li>' for c in CAMERE_TIP)}</ul>
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
                    f'<div class="ec-statrow"><svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="4" width="8" height="16" rx="1"/><rect x="12" y="9" width="8" height="11" rx="1"/><path d="M6.5 8h3M6.5 12h3M6.5 16h3M15 13h2M15 17h2"/></svg><b>{mp(c["aria"])}</b></li>')

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
  <p class="ec-body" style="margin-bottom:1.25rem">Un consultant revine cu un răspuns în aceeași zi lucrătoare.</p>
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
      <div class="ec-panel">
        <div class="ec-acces">
          <div><span class="ec-acces__i"><i class="fa-solid fa-location-dot" aria-hidden="true"></i></span>
            <div><b>Adresă</b><span>{e(SHOWROOM["adresa"])}</span></div></div>
          <div><span class="ec-acces__i"><i class="fa-solid fa-phone" aria-hidden="true"></i></span>
            <div><b>Telefon</b><span><a href="tel:{SHOWROOM["tel_link"]}">{e(SHOWROOM["tel"])}</a></span></div></div>
          <div><span class="ec-acces__i"><i class="fa-solid fa-envelope" aria-hidden="true"></i></span>
            <div><b>E-mail</b><span><a href="mailto:{SHOWROOM["mail"]}">{e(SHOWROOM["mail"])}</a></span></div></div>
          <div><span class="ec-acces__i"><i class="fa-solid fa-clock" aria-hidden="true"></i></span>
            <div><b>Program</b><span>{e(SHOWROOM["program"])}</span></div></div>
        </div>
        <div class="ec-cta__btns" style="margin-top:2rem">
          <a class="ec-btn" href="tel:{SHOWROOM["tel_link"]}"><i class="fa-solid fa-phone" aria-hidden="true"></i> Contact telefonic</a>
          <a class="ec-btn ec-btn--out" href="https://wa.me/40757707080"><i class="fa-brands fa-whatsapp" aria-hidden="true"></i> Contact WhatsApp</a>
        </div>
      </div>
      {formular(None, r)}
    </div>
  </section>"""


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
      <h3>Achiziție în scop investițional</h3>
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
            <div><span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 21V7l9-4 9 4v14"/><path d="M3 12h18M12 3v18"/></svg> Camere</span><b>{us[0]['nr_camere']}</b></div>
            <div><span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 15l12-12 6 6-12 12z"/><path d="M7 11l2 2M10 8l2 2M13 5l2 2"/></svg> Suprafață</span><b>{mp(min(u['su_utila'] for u in us))} – {mp(max(u['su_utila'] for u in us))}</b></div>
            <div><span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="8" cy="15" r="4"/><path d="M11 12l9-9 2 2-2 2 2 2-3 3-2-2-2 2"/></svg> Disponibile</span><b>{len(disp)} din {len(us)}</b></div>
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
        tipuri += f"""<a class="ec-type ec-rv" href="{r}tipologii/{cod.lower()}/">
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
        stare = f"{len(d)} disponibile" if d else "În curând"
        etape += (f'<tr><td><b>Etapa {cod}</b></td>'
                  f'<td>Blocurile {blocuri[0]}–{blocuri[-1]}</td>'
                  f'<td class="num">{len(us)}</td>'
                  f'<td class="num">{e(stare)}</td>'
                  f'<td class="num">{euro(pm) if pm else "—"}</td>'
                  f'<td><a href="{lista}?etapa={cod}">Vezi lista</a></td></tr>')

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
        <h2>Ce se vinde <em>în fiecare etapă</em></h2></div>
      <p class="ec-shead__p">
        Ansamblul se construiește în trei etape, fiecare intrând în vânzare la momentul corespunzător.
      </p>
    </div>
    <div class="ec-table ec-table--vs" style="margin-top:2.5rem">
      <table>
        <caption class="ec-sr">Disponibilitate pe etape</caption>
        <thead><tr><th scope="col">Etapă</th><th scope="col">Blocuri</th>
          <th scope="col">Total</th><th scope="col">Stare</th>
          <th scope="col">De la</th><th scope="col"></th></tr></thead>
        <tbody>{etape}</tbody>
      </table>
    </div>
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

<script>
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

    return pagina("Apartamente noi în Iași, zona Păcurari — prețuri și disponibilitate | Emerald City",
                  f"{len(disp)} apartamente noi disponibile în Iași, zona Păcurari: 1, 2 și 3 camere, "
                  f"între {su_min:.0f} și {su_max:.0f} m², de la {euro(p_min)}. Predare la cheie, "
                  "vânzare directă de la dezvoltator.",
                  continut, r, schema, "apartamente-iasi/")


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
            <div><span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 15l12-12 6 6-12 12z"/><path d="M7 11l2 2M10 8l2 2M13 5l2 2"/></svg> Suprafață</span><b>{mp(min(u['su_utila'] for u in tu))} – {mp(max(u['su_utila'] for u in tu))}</b></div>
            <div><span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="8" cy="15" r="4"/><path d="M11 12l9-9 2 2-2 2 2 2-3 3-2-2-2 2"/></svg> Disponibile</span><b>{len(td)} din {len(tu)}</b></div>
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

    return pagina("Apartamente în Iași, zona Păcurari — amplasament și distanțe | Emerald City",
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

  {showroom(r, "04")}

  <section class="ec-section" id="intrebari" style="padding-block:0 var(--ec-section)">
    <div class="ec-shead">
      <div><span class="ec-shead__n">05 — Întrebări</span>
        <h2>Despre execuție <em>și termene</em></h2></div>
      <p class="ec-shead__p">
        {len(FAQ_STADIU)} întrebări despre urmărirea progresului și garanțiile contractuale.
      </p>
    </div>
    <div class="ec-faq" style="margin-top:2.5rem">{faq}</div>
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
                  "Stadiul real al construcției Emerald City, Iași zona Păcurari: progresul "
                  "fiecărei etape faza cu faza, jurnal lunar cu fotografii datate și vizite "
                  "pe șantier cu programare.",
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

    return pagina("Dezvoltator — Tala Sapphire și Green Stone Group | Emerald City Iași",
                  "Cine construiește Emerald City: Tala Sapphire S.R.L., companie din Green "
                  "Stone Group, cu proiecte în Marea Britanie, Israel și România. Portofoliu, "
                  "principii și datele proiectului.",
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
      <a class="ec-btn ec-btn--out" href="{r}tipologii/">{ic("compass-drafting")} Compartimentări</a>
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
                  "Cum este gândit ansamblul Emerald City din Iași: 18 blocuri cu regim 2D+P+3E, "
                  f"{total} de apartamente, 5 hectare, bilanțul terenului, indicatori "
                  "urbanistici și etape de construcție.",
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
      <a class="ec-btn ec-btn--out" href="{r}tipologii/">{ic("compass-drafting")} Compartimentări</a>
    </div>
  </section>

  {showroom(r, "05")}
</div>"""

    return pagina("Finisaje incluse — ce înseamnă predare la cheie | Emerald City Iași",
                  f"Cele {len(FINISAJE)} poziții de finisaj incluse în prețul apartamentelor "
                  "Emerald City din Iași: încălzire în pardoseală, tâmplărie cu 7 camere, "
                  "parchet de 10 mm, grupuri sanitare complet echipate. Ce este inclus și ce nu.",
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


# ========================================================= pagini legale ==
LEGALE = {
    "termeni-si-conditii": ("Termeni și condiții",
        "Condițiile de utilizare a site-ului emerald-city.ro și regulile aplicabile "
        "solicitărilor transmise prin formularele de contact."),
    "politica-de-confidentialitate": ("Politica de confidențialitate",
        "Cum sunt colectate, folosite și păstrate datele cu caracter personal transmise "
        "prin acest site."),
    "politica-de-cookies": ("Politica de cookies",
        "Ce module cookie folosește site-ul, în ce scop și cum poate fi retras acordul."),
    "informare-gdpr": ("Informare GDPR",
        "Drepturile persoanei vizate asupra datelor cu caracter personal conform Regulamentului "
        "(UE) 2016/679 și modul în care pot fi exercitate."),
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
      pentru orice întrebare privind datele personale sau condițiile de utilizare, ne
      scrie la <a href="mailto:vanzari@emerald-city.ro">vanzari@emerald-city.ro</a>.
    </p>
    <h3>Operator de date</h3>
    <p>Tala Sapphire S.R.L., Str. Ion Nistor, Iași.</p>
    <h3>Soluționarea reclamațiilor</h3>
    <p>
      Pentru soluționarea alternativă a litigiilor sunt disponibile platforma
      <a href="https://anpc.ro/ce-este-sal/" rel="nofollow noopener" target="_blank">ANPC SAL</a>
      sau platforma europeană
      <a href="https://ec.europa.eu/consumers/odr" rel="nofollow noopener" target="_blank">SOL</a>.
    </p>
  </div>

  <div style="margin-bottom:4rem">{formular(None, r)}</div>
</div>"""
    return pagina(f"{titlu} — Emerald City Iași", descriere, continut, r, None, slug + "/")


# ==================================================================== rulare
# ========================================================== despre noi ==
# Pictogramele vin din Font Awesome 6, incarcat in invelisul paginii.
def ic(nume, extra=""):
    return f'<i class="fa-solid fa-{nume}{extra}" aria-hidden="true"></i>'


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

    return pagina("Despre noi — dezvoltator, finisaje și garanții | Emerald City Iași",
                  "Cine construiește Emerald City, ce include predarea la cheie, ce garanții și "
                  "ce documente se predau. 925 de apartamente în Iași, zona Păcurari, direct de "
                  "la dezvoltator.",
                  continut, r, schema, "despre-emerald-city/")


def main():
    NUM = {"etaj": int, "nr_camere": int, "su_utila": float, "su_balcon": float,
           "su_curte": float, "pret_eur": int, "pret_mp_eur": float, "cota_teren": float}
    unitati = []
    for row in csv.DictReader(open(CSV, encoding="utf-8")):
        unitati.append({k: NUM[k](v) if k in NUM else v for k, v in row.items()})

    for d in ("apartamente-iasi", "tipologii", "investitie-apartamente-iasi", "compara", "contact",
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

    with open(os.path.join(RAD, "tipologii", "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina_hub_tipologii(grupe))

    # pagini de sine statatoare
    for nume, continut in (("investitie-apartamente-iasi", pagina_investitie(unitati)),
                           ("compara", pagina_comparator()),
                           ("contact", pagina_contact()),
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
