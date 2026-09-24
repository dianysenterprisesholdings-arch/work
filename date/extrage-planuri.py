#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrage planurile de apartament din PDF-urile de concept, ca imagine de
rezolutie mare plus pozitiile camerelor, pentru planul interactiv.

Planurile sunt vectoriale si au fiecare camera etichetata cu nume si
suprafata ("Living Room" / "S: 21,93 m2"), deci hotspot-urile nu se
deseneaza de mana: se deduc din pozitia etichetelor.

ATENTIE: PDF-urile provin din proiectul LAPIS, rebranduit pe coperta.
Planurile sunt corecte ca mecanism, dar trebuie inlocuite cu cele
Emerald City inainte de productie.

Scrie:
  assets/img/planuri/<tip>.png
  assets/data/planuri.json
"""

import io, json, os, re, glob
import pymupdf
from PIL import Image

RAD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(RAD, "documentatie", "26.07.31 - Prezentare concept 2 Randari")
OUT_IMG = os.path.join(RAD, "assets", "img", "planuri")
OUT_JSON = os.path.join(RAD, "assets", "data", "planuri.json")

# tipologiile noastre <- PDF-ul care contine planul
SURSA = {"2A": "2A", "3A": "3A", "3B": "3B"}

RO = {
    "Living Room": "Living", "Living room": "Living",
    "Kitchen": "Bucătărie", "Bedroom": "Dormitor",
    "Bedroom 1": "Dormitor 1", "Bedroom 2": "Dormitor 2",
    "Bathroom": "Baie", "Entrance Hall": "Hol de intrare",
    "Vestibule": "Vestibul", "Office": "Birou", "Balcony": "Balcon",
    "Living Room + Kitchen": "Living și bucătărie",
}

DPI = 200


def gaseste_pagina(doc):
    """Pagina de plan: cea cu cele mai multe etichete de tip S: xx m2."""
    best, best_n = None, 0
    for i in range(len(doc)):
        n = len(re.findall(r"S:\s*[\d,\.]+\s*m", doc[i].get_text()))
        if n > best_n:
            best, best_n = i, n
    return best, best_n


def etichete(pg):
    """Perechi (nume camera, suprafata) cu pozitia lor pe pagina."""
    linii = []
    for b in pg.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            t = "".join(s["text"] for s in l["spans"]).strip()
            if t:
                linii.append((t, l["bbox"]))

    camere = []
    for i, (t, bb) in enumerate(linii):
        m = re.match(r"S:\s*([\d,\.]+)\s*m", t)
        if not m:
            continue
        # numele e linia de deasupra, cea mai apropiata pe verticala
        nume, dist = None, 1e9
        for t2, bb2 in linii:
            if t2 is t or re.match(r"S:", t2):
                continue
            dx = abs((bb2[0] + bb2[2]) / 2 - (bb[0] + bb[2]) / 2)
            dy = bb[1] - bb2[3]
            if 0 <= dy < 14 and dx < 60 and dy < dist:
                nume, dist = t2, dy
        if not nume:
            continue
        camere.append({
            "nume": RO.get(nume, nume),
            "aria": float(m.group(1).replace(",", ".")),
            "x": (bb[0] + bb[2]) / 2,
            "y": (bb[1] + bb[3]) / 2,
        })
    return camere


def main():
    os.makedirs(OUT_IMG, exist_ok=True)
    rezultat = {}

    for tip, marca in SURSA.items():
        pdfs = [p for p in glob.glob(os.path.join(SRC, "*.pdf")) if f"APARTAMENT {marca} " in p]
        if not pdfs:
            print(f"  {tip}: PDF negasit"); continue
        doc = pymupdf.open(pdfs[0])
        pno, n = gaseste_pagina(doc)
        if pno is None:
            print(f"  {tip}: nicio pagina de plan"); doc.close(); continue

        pg = doc[pno]
        cam = etichete(pg)
        if not cam:
            print(f"  {tip}: etichete necitite"); doc.close(); continue

        # decupez in jurul planului, cu o margine generoasa
        xs = [c["x"] for c in cam]; ys = [c["y"] for c in cam]
        mx, my = 95, 80
        clip = pymupdf.Rect(max(0, min(xs) - mx), max(0, min(ys) - my),
                            min(pg.rect.x1, max(xs) + mx), min(pg.rect.y1, max(ys) + my))

        pix = pg.get_pixmap(dpi=DPI, clip=clip)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        if img.width > 1500:
            img = img.resize((1500, round(img.height * 1500 / img.width)), Image.LANCZOS)
        cale = os.path.join(OUT_IMG, f"{tip.lower()}.png")
        img.save(cale, "PNG", optimize=True)

        # pozitiile trec in procente fata de decupaj, ca sa fie independente de rezolutie
        w, h = clip.width, clip.height
        for c in cam:
            c["x"] = round((c["x"] - clip.x0) / w * 100, 2)
            c["y"] = round((c["y"] - clip.y0) / h * 100, 2)

        rezultat[tip] = {
            "img": f"assets/img/planuri/{tip.lower()}.png",
            "w": img.width, "h": img.height,
            "total": round(sum(c["aria"] for c in cam), 2),
            "camere": sorted(cam, key=lambda c: -c["aria"]),
        }
        kb = os.path.getsize(cale) / 1024
        print(f"  {tip}: pagina {pno+1}, {len(cam)} camere, {img.width}x{img.height}, {kb:.0f} KB")
        for c in rezultat[tip]["camere"]:
            print(f"        {c['nume']:20} {c['aria']:6.2f} m²   ({c['x']:5.1f}%, {c['y']:5.1f}%)")
        doc.close()

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(rezultat, f, ensure_ascii=False, indent=1)
    print(f"\n  scris {OUT_JSON} ({len(rezultat)} tipologii)")


if __name__ == "__main__":
    main()
