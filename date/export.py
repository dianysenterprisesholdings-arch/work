#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scrie o copie curata a site-ului in `export/`, gata de urcat pe server.

Include doar ce serveste site-ul: paginile, assets-urile si brandul.
Lasa afara sursele (date/, documentatie/, docs/), fisierele de lucru si git.
Genereaza in plus sitemap.xml si robots.txt.
"""

import os, shutil, sys
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limbi import cale_en, cale_ro
from datetime import date

RAD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IESIRE = os.path.join(RAD, "export")
DOMENIU = "https://emerald-city.ro"

# directoarele care intra in export
DIRECTOARE = [
    "assets", "brand",
    "apartamente-iasi",
    "investitie-apartamente-iasi", "contact", "programare-vizionare", "noutati",
    "apartamente-iasi-pacurari", "stadiu-lucrari",
    "despre-emerald-city", "despre-dezvoltator",
    "proiect", "aparitii-presa", "finisaje",
    "termeni-si-conditii", "politica-de-confidentialitate",
    "politica-de-cookies", "informare-gdpr", "en",
]
FISIERE = ["index.html"]

# paginile care nu au ce cauta in index: unitatile vandute si cele in curand
# raman accesibile, dar nu intra in sitemap
def in_sitemap(cale_rel):
    return True


def curata():
    if os.path.isdir(IESIRE):
        shutil.rmtree(IESIRE)
    os.makedirs(IESIRE)


def copiaza():
    n = 0
    for d in DIRECTOARE:
        sursa = os.path.join(RAD, d)
        if not os.path.isdir(sursa):
            print(f"  ! lipseste {d}")
            continue
        tinta = os.path.join(IESIRE, d)
        shutil.copytree(sursa, tinta)
        n += sum(len(f) for _, _, f in os.walk(tinta))
    for f in FISIERE:
        shutil.copy2(os.path.join(RAD, f), os.path.join(IESIRE, f))
        n += 1
    return n


def minifica_css():
    """Comentariile si spatiile inutile din CSS nu ajung in export (~30% mai putin)."""
    import re
    f = os.path.join(IESIRE, "assets", "css", "main.css")
    if not os.path.exists(f):
        return
    t = open(f, encoding="utf-8").read()
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    t = re.sub(r"\s*([{}:;,>])\s*", r"\1", t)
    t = re.sub(r";}", "}", t)
    t = re.sub(r"\s+", " ", t).strip()
    open(f, "w", encoding="utf-8", newline="\n").write(t)


def sitemap():
    """Toate paginile, cu prioritate mai mare pe cele de vanzare."""
    azi = date.today().isoformat()
    urls = []
    for dp, _, fis in os.walk(IESIRE):
        for f in fis:
            if f != "index.html":
                continue
            rel = os.path.relpath(os.path.join(dp, f), IESIRE).replace("\\", "/")
            cale = "" if rel == "index.html" else rel[: -len("index.html")]
            if not in_sitemap(cale):
                continue
            # unitatile individuale sunt multe; prioritate mai mica
            if cale.startswith("en/"):
                ro, en, baza = cale_ro(cale), cale, cale[3:]
            else:
                ro, en, baza = cale, cale_en(cale), cale
            adanc = baza.count("/")
            pri = "1.0" if baza == "" else "0.8" if adanc <= 1 else "0.6"
            alt = (f'    <xhtml:link rel="alternate" hreflang="ro" href="{DOMENIU}/{ro}"/>\n'
                   f'    <xhtml:link rel="alternate" hreflang="en" href="{DOMENIU}/{en}"/>\n'
                   f'    <xhtml:link rel="alternate" hreflang="x-default" href="{DOMENIU}/{ro}"/>\n')
            urls.append(f"  <url>\n    <loc>{DOMENIU}/{cale}</loc>\n{alt}"
                        f"    <lastmod>{azi}</lastmod>\n    <priority>{pri}</priority>\n  </url>")

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
           + "\n".join(urls) + "\n</urlset>\n")
    with open(os.path.join(IESIRE, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write(xml)
    return len(urls)


def robots():
    txt = (
        "# Macheta de lucru. Inainte de lansare, sterge linia Disallow.\n"
        "User-agent: *\n"
        "Disallow: /\n"
        "\n"
        f"Sitemap: {DOMENIU}/sitemap.xml\n"
    )
    with open(os.path.join(IESIRE, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write(txt)


def marime(cale):
    return sum(os.path.getsize(os.path.join(dp, f))
               for dp, _, fs in os.walk(cale) for f in fs)


def main():
    curata()
    n = copiaza()
    minifica_css()
    u = sitemap()
    robots()
    print(f"  {n} fisiere copiate in export/")
    print(f"  sitemap.xml cu {u} adrese")
    print(f"  robots.txt scris — momentan blocheaza indexarea")
    print(f"\n  total {marime(IESIRE) / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
