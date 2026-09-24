#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pregateste imaginile pentru web:
  1. gradare unitara — aceeasi corectie pe toate randarile, altfel diferenta
     de temperatura dintre ele se vede pe aceeasi pagina
  2. WebP la doua praguri, cu JPEG ca rezerva
  3. LQIP: o miniatura de 20px codificata base64, pentru blur-up la incarcare

Scrie assets/data/lqip.json, folosit de generator si de homepage.
"""

import base64, glob, io, json, os
from PIL import Image, ImageEnhance

RAD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(RAD, "assets", "img")

# corectie blanda, aceeasi pentru toate: randarile 3A sunt usor reci si plate
CONTRAST, SATURATIE, LUMINA = 1.04, 1.03, 1.01


def graduare(im):
    im = ImageEnhance.Contrast(im).enhance(CONTRAST)
    im = ImageEnhance.Color(im).enhance(SATURATIE)
    im = ImageEnhance.Brightness(im).enhance(LUMINA)
    return im


def lqip(im):
    mic = im.copy()
    mic.thumbnail((20, 20), Image.LANCZOS)
    buf = io.BytesIO()
    mic.save(buf, "JPEG", quality=40)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def main():
    surse = sorted(f for f in glob.glob(os.path.join(IMG, "*.jpg")) if "-800" not in f)
    date, castig = {}, 0

    for f in surse:
        nume = os.path.splitext(os.path.basename(f))[0]
        im = graduare(Image.open(f).convert("RGB"))

        for w in (1600, 800):
            r = im if im.width == w else im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
            suf = "" if w == 1600 else "-800"
            jpg = os.path.join(IMG, f"{nume}{suf}.jpg")
            wbp = os.path.join(IMG, f"{nume}{suf}.webp")
            vechi = os.path.getsize(jpg) if os.path.exists(jpg) else 0
            r.save(jpg, "JPEG", quality=82 if w == 1600 else 78, optimize=True)
            r.save(wbp, "WEBP", quality=78 if w == 1600 else 72, method=6)
            if w == 1600:
                castig += vechi - os.path.getsize(wbp)

        date[nume] = lqip(im)
        print(f"  {nume:18} jpg {os.path.getsize(os.path.join(IMG, nume + '.jpg'))/1024:5.0f} KB"
              f"  webp {os.path.getsize(os.path.join(IMG, nume + '.webp'))/1024:5.0f} KB"
              f"  lqip {len(date[nume])} car.")

    with open(os.path.join(RAD, "assets", "data", "lqip.json"), "w", encoding="utf-8") as fh:
        json.dump(date, fh, ensure_ascii=False, indent=0)

    print(f"\n  {len(date)} imagini · WebP economiseste {castig/1024:.0f} KB la varianta mare")


if __name__ == "__main__":
    main()
