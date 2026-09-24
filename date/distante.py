#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calculeaza distantele rutiere de la amplasament la punctele de interes.

Reper: Strada Dealul Zorilor, Iasi (Contemporan Homes) — ansamblul Emerald City
se afla imediat in spatele acestuia, conform indicatiei clientului.

Geocodare: Nominatim (OpenStreetMap). Rutare: OSRM public.
Rezultatul se scrie in assets/data/distante.json si e folosit de generator.
"""

import json, os, subprocess, time, urllib.parse

RAD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "EmeraldCityDev/1.0 (calcul distante pentru site)"}

# Amplasamentul: parcela libera dintre Strada Dealul Zorilor si Cimitirul
# Evreiesc din Canta, indicata de client pe harta. Coordonatele sunt fixate
# direct, nu geocodate — terenul nu are inca adresa postala in OSM.
REPER = "Emerald City, Strada Dealul Zorilor, Iasi"
REPER_COORD = (47.18050, 27.53420)

PUNCTE = [
    ("Kaufland Păcurari",                    "Kaufland, Soseaua Pacurari, Iasi, Romania"),
    ("Mall Moldova",                          "Moldova Mall, Iasi, Romania"),
    ("Palas Mall",                            "Palas Mall, Iasi, Romania"),
    ("Parcul Copou",                          "Parcul Copou, Iasi, Romania"),
    ("Universitatea „Alexandru Ioan Cuza”",   "Universitatea Alexandru Ioan Cuza, Iasi, Romania"),
    ("Centrul orașului",                      "Piata Unirii, Iasi, Romania"),
    ("Spitalul Sf. Spiridon",                 "Spitalul Sfantul Spiridon Iasi"),
    ("Școala Paradis",                        "Scoala Paradis, Valea Adanca, Iasi"),
    ("Era Shopping Park",                     "Era Park Iasi"),
    ("Aeroportul Iași",                       "Aeroportul International Iasi, Romania"),
]


def cere(url):
    """Prin curl: OSRM are certificatul expirat, iar curl are alt magazin de CA."""
    out = subprocess.run(
        ["curl", "-sS", "--max-time", "25", "-A", UA["User-Agent"], url],
        capture_output=True, text=True, encoding="utf-8")
    if out.returncode or not out.stdout.strip():
        raise RuntimeError(out.stderr.strip()[:120] or "raspuns gol")
    return json.loads(out.stdout)


def geocode(q):
    u = ("https://nominatim.openstreetmap.org/search?format=json&limit=1&q="
         + urllib.parse.quote(q))
    d = cere(u)
    return (float(d[0]["lat"]), float(d[0]["lon"]), d[0]["display_name"]) if d else None


def ruta(a, b):
    """Distanta si durata rutiera, prin OSRM."""
    u = (f"http://router.project-osrm.org/route/v1/driving/"
         f"{a[1]},{a[0]};{b[1]},{b[0]}?overview=false")
    d = cere(u)
    if d.get("code") != "Ok" or not d.get("routes"):
        return None
    r = d["routes"][0]
    return r["distance"] / 1000.0, r["duration"] / 60.0


def main():
    origine = (REPER_COORD[0], REPER_COORD[1], REPER)
    print("Reper: %.5f, %.5f  (fixat manual)" % (origine[0], origine[1]))


    rezultat = []
    for eticheta, interogare in PUNCTE:
        g = geocode(interogare)
        time.sleep(1.1)
        if not g:
            print(f"  !! negasit: {eticheta}")
            continue
        r = ruta(origine, g)
        if not r:
            print(f"  !! fara ruta: {eticheta}")
            continue
        km, minute = r
        rezultat.append({"nume": eticheta, "km": round(km, 1), "min": int(round(minute)),
                         "lat": round(g[0], 6), "lon": round(g[1], 6)})
        print(f"  {eticheta:38} {km:5.1f} km   {minute:4.0f} min")

    cale = os.path.join(RAD, "assets", "data", "distante.json")
    with open(cale, "w", encoding="utf-8") as f:
        json.dump({"reper": REPER, "lat": round(origine[0], 6), "lon": round(origine[1], 6),
                   "puncte": rezultat}, f, ensure_ascii=False, indent=1)
    print(f"\n  scris {cale}")


if __name__ == "__main__":
    main()
