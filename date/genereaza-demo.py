#!/usr/bin/env python3
"""
Generator de date DEMO pentru selectorul de apartamente Emerald City.

ATENTIE: suprafetele, preturile si statusurile PE APARTAMENT sunt INVENTATE.
Ce este REAL (preluat din "TS-PS ARII UTILE.pdf", proiect 266/2023, faza DTAC):
  - numarul de apartamente pe fiecare corp (total 925)
  - suprafata rezidentiala totala pe corp (se respecta la +/- 0.5 mp)
  - suprafata totala de balcoane pe corp
  - regimul 2D+P+3E => apartamentele stau pe 4 niveluri (P, 1, 2, 3)
  - care corpuri au depozitare (boxe) si care au parcare la demisol
Scop: dezvoltarea si testarea filtrului pe volumul real de date.
Se inlocuieste integral cand vine exportul dezvoltatorului.
"""

import csv
import random
from pathlib import Path

random.seed(20260924)  # rulari reproductibile

# ---------------------------------------------------------------- date reale
# corp: (etapa, nr_apartamente, mp_rezidential, mp_balcoane, mp_depozitare, mp_parcare_demisol, mp_comercial)
CORPURI = {
    "C1":  ("I",   45, 2573.90, 393.97,   0.00, 560.00,   0.00),
    "C2":  ("I",   45, 2573.90, 393.97,   0.00, 560.00,   0.00),
    "C3":  ("I",   61, 3307.42, 434.11, 236.11,   0.00,   0.00),
    "C4":  ("I",   61, 3307.42, 434.11, 236.11,   0.00,   0.00),
    "C5":  ("I",   55, 3068.70, 434.11,   0.00, 682.93,   0.00),
    "C6":  ("I",   55, 2996.40, 434.11,   0.00,   0.00, 722.22),
    "C7":  ("II",  55, 3068.70, 434.11,   0.00, 682.93,   0.00),
    "C8":  ("II",  55, 3068.70, 434.11,   0.00, 682.93,   0.00),
    "C9":  ("II",  45, 2492.40, 282.82,   0.00, 573.11,   0.00),
    "C10": ("II",  45, 2492.40, 282.82,   0.00, 573.11,   0.00),
    "C11": ("II",  55, 3019.31, 293.40, 221.12,   0.00,   0.00),
    "C12": ("II",  56, 3055.67, 293.40,  59.96,   0.00, 125.82),
    "C13": ("II",  56, 3054.93, 293.40, 183.31,   0.00,   0.00),
    "C14": ("II",  56, 3054.93, 293.40, 183.31,   0.00,   0.00),
    "C15": ("III", 45, 2492.40, 282.82,   0.00, 573.11,   0.00),
    "C16": ("III", 45, 2492.40, 282.82,   0.00, 573.11,   0.00),
    "C17": ("III", 45, 2492.40, 282.82,   0.00, 573.11,   0.00),
    "C18": ("III", 45, 2492.40, 282.82,   0.00, 573.11,   0.00),
}

# cote +/-0.00 reale per corp (din planul de situatie) - dau "inaltimea" reala pe teren
COTE = {
    "C1": 85.10, "C2": 82.10, "C3": 91.20, "C4": 88.20, "C5": 85.20, "C6": 84.80,
    "C7": 86.90, "C8": 88.40, "C9": 91.40, "C10": 94.40, "C11": 103.10, "C12": 100.10,
    "C13": 97.10, "C14": 94.10, "C15": 97.00, "C16": 100.00, "C17": 103.00, "C18": 106.00,
}

# ------------------------------------------------------------ tipologii DEMO
# cod: (nr_camere, mp_tinta, pondere_in_mix)
# mixul este calibrat ca media ponderata sa cada in jurul a 55.2 mp
TIPOLOGII = {
    "1A": (1, 37.5, 0.22),
    "2A": (2, 52.0, 0.31),
    "2B": (2, 58.5, 0.24),
    "3A": (3, 71.0, 0.13),
    "3B": (3, 78.0, 0.10),
}

NIVELURI = [0, 1, 2, 3]          # P + 3E
NIVEL_ETICHETA = {0: "Parter", 1: "Etaj 1", 2: "Etaj 2", 3: "Etaj 3"}
ORIENTARI = ["N", "NE", "E", "SE", "S", "SV", "V", "NV"]

# preturi DEMO: euro/mp util, creste cu etajul si cu cota terenului
PRET_MP_BAZA = 1450


def mix_tipologii(n):
    """Aloca n apartamente pe tipologii respectand ponderile, apoi ajusteaza."""
    coduri = list(TIPOLOGII)
    alocare = {c: int(n * TIPOLOGII[c][2]) for c in coduri}
    while sum(alocare.values()) < n:
        rest = sorted(coduri, key=lambda c: n * TIPOLOGII[c][2] - alocare[c], reverse=True)
        alocare[rest[0]] += 1
    while sum(alocare.values()) > n:
        rest = sorted(coduri, key=lambda c: alocare[c] - n * TIPOLOGII[c][2], reverse=True)
        alocare[rest[0]] -= 1
    lista = []
    for c, k in alocare.items():
        lista += [c] * k
    random.shuffle(lista)
    return lista


def distribuie_pe_niveluri(n):
    """n apartamente pe 4 niveluri; parterul primeste mai putine (acces/tehnic)."""
    baza, rest = divmod(n, len(NIVELURI))
    pe_nivel = {niv: baza for niv in NIVELURI}
    for i in range(rest):                      # restul urca la etajele superioare
        pe_nivel[NIVELURI[-(i + 1)]] += 1
    if pe_nivel[0] > 1 and rest == 0:          # parter cedeaza 1 catre etaj 1
        pe_nivel[0] -= 1
        pe_nivel[1] += 1
    return pe_nivel


def genereaza():
    rows = []
    for corp, (etapa, n_ap, mp_total, mp_balc, mp_depoz, mp_park, mp_com) in CORPURI.items():
        tipuri = mix_tipologii(n_ap)
        pe_nivel = distribuie_pe_niveluri(n_ap)

        # scalare ca suma suprafetelor sa dea exact mp_total din planse
        suma_tinta = sum(TIPOLOGII[t][1] for t in tipuri)
        factor = mp_total / suma_tinta

        idx_tip = 0
        unitati_corp = []
        for niv in NIVELURI:
            for poz in range(1, pe_nivel[niv] + 1):
                tip = tipuri[idx_tip]
                idx_tip += 1
                camere, mp_baza, _ = TIPOLOGII[tip]
                su = round(mp_baza * factor, 2)

                # balcon: parterul primeste curte in loc de balcon
                are_curte = niv == 0 and random.random() < 0.55
                orientare = random.choice(ORIENTARI)
                sudic = orientare in ("S", "SE", "SV")

                pret_mp = PRET_MP_BAZA + niv * 22 + (35 if sudic else 0)
                pret_mp += int((COTE[corp] - 82.0) * 2.5)     # cota mai sus = priveliste
                pret = int(round(su * pret_mp / 500.0) * 500)

                r = random.random()
                status = "vandut" if r < 0.18 else "rezervat" if r < 0.30 else "disponibil"
                if etapa == "III":                             # etapa III nu e la vanzare
                    status = "in_curand"
                elif etapa == "II" and r > 0.75:
                    status = "disponibil"

                unitati_corp.append({
                    "unit_id": f"{corp}-{'P' if niv == 0 else 'E' + str(niv)}-{poz:02d}",
                    "corp": corp,
                    "etapa": etapa,
                    "etaj": niv,
                    "etaj_eticheta": NIVEL_ETICHETA[niv],
                    "tip_apartament": tip,
                    "nr_camere": camere,
                    "su_utila": su,
                    "su_balcon": 0.0,
                    "su_curte": 0.0,
                    "orientare": orientare,
                    "pret_eur": pret,
                    "pret_mp_eur": round(pret / su, 0),
                    "status": status,
                    "boxa_disponibila": "da" if mp_depoz > 0 else "nu",
                    "parcare_subterana": "da" if mp_park > 0 else "nu",
                    "cota_teren": COTE[corp],
                    "_are_curte": are_curte,
                })

        # balcoanele: se distribuie mp_balc pe unitatile fara curte
        cu_balcon = [u for u in unitati_corp if not u["_are_curte"]]
        cu_curte = [u for u in unitati_corp if u["_are_curte"]]
        if cu_balcon:
            pond = sum(u["su_utila"] for u in cu_balcon)
            for u in cu_balcon:
                u["su_balcon"] = round(mp_balc * u["su_utila"] / pond, 2)
        for u in cu_curte:
            u["su_curte"] = round(u["su_utila"] * random.uniform(0.35, 0.70), 2)

        for u in unitati_corp:
            del u["_are_curte"]
        rows += unitati_corp
    return rows


def raport(rows):
    print(f"Total unitati generate: {len(rows)}")
    print(f"Suprafata utila totala: {sum(r['su_utila'] for r in rows):,.2f} mp")
    print(f"Media pe apartament:    {sum(r['su_utila'] for r in rows)/len(rows):.2f} mp")
    print(f"Balcoane total:         {sum(r['su_balcon'] for r in rows):,.2f} mp")
    print()
    print("Verificare pe corp (generat vs. planse):")
    for corp, (_, n_ap, mp_total, mp_balc, *_rest) in CORPURI.items():
        sel = [r for r in rows if r["corp"] == corp]
        gen_mp = sum(r["su_utila"] for r in sel)
        gen_b = sum(r["su_balcon"] for r in sel)
        ok = "OK" if len(sel) == n_ap and abs(gen_mp - mp_total) < 0.5 and abs(gen_b - mp_balc) < 0.5 else "!!"
        print(f"  {ok} {corp:4} ap {len(sel):3}/{n_ap:<3} "
              f"mp {gen_mp:9.2f}/{mp_total:<9.2f} balc {gen_b:7.2f}/{mp_balc:<7.2f}")
    print()
    print("Mix tipologii:")
    for tip in TIPOLOGII:
        sel = [r for r in rows if r["tip_apartament"] == tip]
        print(f"  {tip}  {len(sel):3} ap ({len(sel)/len(rows)*100:4.1f}%)  "
              f"{sum(r['su_utila'] for r in sel)/len(sel):5.1f} mp mediu")
    print()
    print("Status:")
    for st in ("disponibil", "rezervat", "vandut", "in_curand"):
        sel = [r for r in rows if r["status"] == st]
        print(f"  {st:12} {len(sel):3} ({len(sel)/len(rows)*100:4.1f}%)")


if __name__ == "__main__":
    rows = genereaza()
    out = Path(__file__).parent / "unitati-demo.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    raport(rows)
    print(f"\nScris: {out}")
