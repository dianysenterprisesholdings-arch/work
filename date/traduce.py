# -*- coding: utf-8 -*-
"""
Versiunea in engleza a site-ului: /en/...

Porneste de la paginile generate in romana si le traduce segment cu segment,
cu dictionarele din date/traduceri/. Rescrie legaturile catre arborele /en/,
canonicalul, limba documentului, formatul numerelor si datele structurate.
Segmentele fara traducere raman in romana si sunt raportate.

Rulare: python date/traduce.py  (dupa genereaza-pagini.py)
"""
import glob, html, importlib.util, io, json, os, re, sys

RAD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limbi import SLUGURI, cale_en, DOMENIU  # noqa: E402

IESIRE = os.path.join(RAD, "en")
NECUNOSCUTE = os.path.join(RAD, "date", "traduceri", "necunoscute.txt")

# ------------------------------------------------------------ dictionar ----
T, REGULI = {}, []
for f in sorted(glob.glob(os.path.join(RAD, "date", "traduceri", "en_*.py"))):
    spec = importlib.util.spec_from_file_location(os.path.basename(f)[:-3], f)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    T.update(getattr(m, "T", {}))
    REGULI += [(re.compile(p), r) for p, r in getattr(m, "REGULI", [])]

NUM = re.compile(r"\d[\d.,]*(?:\s?[–-]\s?\d[\d.,]*)?")
necunoscute = {}


def norm(x):
    return re.sub(r"\s+", " ", x.strip())


def numar_en(n):
    """53.500 -> 53,500 ; 36,6 -> 36.6 ; 37–81 ramane."""
    def unu(s):
        miez = s.rstrip(".,"); coada = s[len(miez):]
        return _fmt(miez) + coada

    def _fmt(s):
        if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", s):
            s = s.replace(".", "\x00").replace(",", ".").replace("\x00", ",")
        elif re.fullmatch(r"\d+,\d+", s):
            s = s.replace(",", ".")
        return s
    return re.sub(r"\d[\d.,]*", lambda m: unu(m.group(0)), n)


def tradu_segment(text, pagina=""):
    """Traduce un fragment de text (fara marcaj). Pastreaza spatiile de la capete."""
    if not text:
        return text
    if not re.search(r"[A-Za-zăâîșțĂÂÎȘȚ]", text) and NUM.sub("{n}", norm(text)) not in T:
        return re.sub(r"\d[\d.,]*", lambda m: numar_en(m.group(0)), text)
    stanga = text[: len(text) - len(text.lstrip())]
    dreapta = text[len(text.rstrip()):]
    mij = norm(text)

    # reguli cu expresii regulate (titluri de unitati, descrieri patternizate)
    for rx, rep in REGULI:
        m = rx.fullmatch(mij)
        if m:
            out = rep(m) if callable(rep) else m.expand(rep)
            out = re.sub(r"\d[\d.,]*", lambda x: numar_en(x.group(0)), out)
            return stanga + out + dreapta

    numere = NUM.findall(mij)
    cheie = NUM.sub("{n}", mij)
    if cheie in T:
        out = _completeaza(T[cheie], numere)
        return stanga + out + dreapta

    # propozitie cu propozitie (textele de unitate sunt compuse din bucati fixe)
    prop = re.split(r"(?<=[.!?])\s+", mij)
    if len(prop) > 1:
        parti, ok = [], True
        for p in prop:
            nr = NUM.findall(p); k = NUM.sub("{n}", p)
            if k in T:
                parti.append(_completeaza(T[k], nr))
            else:
                ok = False; break
        if ok:
            return stanga + " ".join(parti) + dreapta

    necunoscute.setdefault(cheie, pagina)
    return text


def _completeaza(sablon, numere):
    """Pune numerele la loc (formatate in engleza), in ordine sau dupa indice."""
    numere = [numar_en(n.rstrip('.,')) for n in numere]
    if "{0}" in sablon or "{1}" in sablon:
        for i, n in enumerate(numere):
            sablon = sablon.replace("{%d}" % i, n)
        return sablon
    it = iter(numere)
    return re.sub(r"\{n\}", lambda m: next(it, "{n}"), sablon)


# ------------------------------------------------------------ legaturi ----
def cale_absoluta(href, dir_ro):
    """Rezolva un href relativ fata de directorul paginii (ex. 'apartamente-iasi/c1-e1-01')."""
    baza = [p for p in dir_ro.split("/") if p]
    parti = href.split("/")
    for p in parti[:-1]:
        if p == "..":
            if baza: baza.pop()
        elif p and p != ".":
            baza.append(p)
    ultim = parti[-1]
    if ultim and ultim not in (".", ".."):
        baza.append(ultim)
    elif ultim == "..":
        if baza: baza.pop()
    return baza


def tradu_href(href, dir_ro):
    if not href or href.startswith(("http:", "https:", "mailto:", "tel:", "#", "javascript:", "data:", "//", "/")):
        return href
    coada = ""
    m = re.match(r"([^?#]*)([?#].*)?$", href)
    cale, coada = m.group(1), m.group(2) or ""
    if not cale:
        return href
    e_dir = cale.endswith("/") or "." not in cale.split("/")[-1]
    segm = cale_absoluta(cale, dir_ro)
    if segm and segm[0] in ("assets", "brand"):
        return "/" + "/".join(segm) + coada
    if segm and segm[-1] == "index.html":
        segm = segm[:-1]; e_dir = True
    segm = [SLUGURI.get(p, p) for p in segm]
    out = "/en/" + "/".join(segm)
    if segm and e_dir and not out.endswith("/"):
        out += "/"
    return out + coada


def tradu_url_absolut(u):
    """https://emerald-city.ro/x/ -> https://emerald-city.ro/en/<x tradus>/"""
    if not u.startswith(DOMENIU + "/"):
        return u
    rest = u[len(DOMENIU) + 1:]
    if rest.startswith(("assets/", "brand/", "en/")):
        return u
    return DOMENIU + "/" + cale_en(rest)


# ------------------------------------------------------------ pagina -----
ATTR_TEXT = ("alt", "title", "placeholder", "aria-label", "data-et", "content", "label")
ATTR_URL = ("href", "src", "poster", "action", "data-sursa")


JSON_FARA = {"@type", "@context", "@id", "dayOfWeek", "unitCode", "priceCurrency", "opens", "closes",
             "telephone", "email", "availability", "inLanguage", "sku", "streetAddress",
             "addressLocality", "addressRegion", "addressCountry", "postalCode", "latitude", "longitude",
             "contactType", "availableLanguage", "sameAs", "areaServed", "logo", "image"}


def tradu_json(obj, pagina):
    if isinstance(obj, dict):
        return {k: (tradu_url_absolut(v) if isinstance(v, str) and v.startswith("http")
                    else v if k in JSON_FARA else tradu_json(v, pagina)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [tradu_json(x, pagina) for x in obj]
    if isinstance(obj, str):
        return tradu_segment(obj, pagina)
    return obj


def tradu_pagina(h, dir_ro):
    pagina = dir_ro or "home"

    # 1. scripturile: JSON-LD tradus ca date; celelalte doar cu sirurile din dictionar
    def script(m):
        atr, corp = m.group(1), m.group(2)
        if "ld+json" in atr:
            try:
                d = json.loads(corp)
                return f"<script{atr}>{json.dumps(tradu_json(d, pagina), ensure_ascii=False)}</script>"
            except ValueError:
                return m.group(0)
        if "src=" in atr:
            return re.sub(r'src="([^"]*)"', lambda x: f'src="{tradu_href(x.group(1), dir_ro)}"', m.group(0))
        corp2 = re.sub(r"'([^'\\\n]{3,}?)'", lambda x: "'" + (T.get(NUM.sub("{n}", x.group(1)), x.group(1)) if re.search(r"[ăâîșț]", x.group(1)) or NUM.sub("{n}", x.group(1)) in T else x.group(1)) + "'", corp)
        return f"<script{atr}>{corp2}</script>"
    h = re.sub(r"<script([^>]*)>(.*?)</script>", script, h, flags=re.S)

    # 2. atributele
    def atribut(m):
        nume, val = m.group(1), m.group(2)
        if nume in ATTR_URL:
            return f'{nume}="{tradu_href(val, dir_ro)}"'
        if nume == "srcset":
            return 'srcset="' + ", ".join(
                (lambda p: tradu_href(p[0], dir_ro) + (" " + p[1] if len(p) > 1 else ""))(x.strip().split())
                for x in val.split(",")) + '"'
        if nume in ATTR_TEXT:
            if nume == "content" and (val.startswith("http") or "device-width" in val or val == "noindex, follow"
                                      or re.fullmatch(r"[\w_-]+", val)):
                return m.group(0)
            return f'{nume}="{html.escape(tradu_segment(html.unescape(val), pagina), quote=True)}"'
        return m.group(0)
    h = re.sub(r'\b(href|src|poster|action|data-sursa|srcset|alt|title|placeholder|aria-label|data-et|content|label)="([^"]*)"', atribut, h)

    # 3. nodurile de text (in afara <style>)
    def text(m):
        t = m.group(1)
        if not t.strip():
            return m.group(0)
        return ">" + html.escape(tradu_segment(html.unescape(t), pagina), quote=False).replace("&#x27;", "'") + "<"
    parti = re.split(r"(<style.*?</style>|<script.*?</script>)", h, flags=re.S)
    h = "".join(p if p.startswith(("<style", "<script")) else re.sub(r">([^<]+)<", text, p) for p in parti)

    # 4. metadatele documentului
    h = h.replace('<html lang="ro">', '<html lang="en">', 1)
    h = h.replace('content="ro_RO"', 'content="en_GB"', 1)
    h = re.sub(r'<link rel="canonical" href="([^"]*)">',
               lambda m: f'<link rel="canonical" href="{tradu_url_absolut(m.group(1))}">', h, count=1)
    h = re.sub(r'(<meta property="og:url" content=")([^"]*)(")',
               lambda m: m.group(1) + tradu_url_absolut(m.group(2)) + m.group(3), h, count=1)
    if 'data-radacina="' in h:
        h = h.replace('data-radacina="', 'data-lang="en" data-assets="/" data-radacina="', 1)
    else:
        h = h.replace("<body>", '<body data-lang="en" data-assets="/" data-radacina="/en/">', 1)
    # radacina pentru scripturi: /en/
    h = re.sub(r'data-radacina="[^"]*"', 'data-radacina="/en/"', h, count=1)

    # 5. comutatorul de limba: EN devine activ
    h = re.sub(r'(<a href="[^"]*" hreflang="ro" lang="ro") class="is-on" aria-current="true"', r"\1", h, count=1)
    h = re.sub(r'(<a href="[^"]*" hreflang="en" lang="en")', r'\1 class="is-on" aria-current="true"', h, count=1)
    return h


# ------------------------------------------------------------ rulare -----
def ruleaza():
    os.makedirs(os.path.dirname(NECUNOSCUTE), exist_ok=True)
    n = 0
    for dp, dirs, fis in os.walk(RAD):
        rel = os.path.relpath(dp, RAD).replace("\\", "/")
        if rel == ".":
            rel = ""
        prim = rel.split("/")[0]
        if prim in ("export", "en", ".git", "assets", "brand", "date", "node_modules"):
            dirs[:] = []
            continue
        if "index.html" not in fis:
            continue
        h = io.open(os.path.join(dp, "index.html"), encoding="utf-8").read()
        out = tradu_pagina(h, rel)
        dest = os.path.join(IESIRE, *[SLUGURI.get(p, p) for p in rel.split("/") if p])
        os.makedirs(dest, exist_ok=True)
        for incercare in range(6):
            try:
                io.open(os.path.join(dest, "index.html"), "w", encoding="utf-8", newline="\n").write(out)
                break
            except OSError:
                if incercare == 5:
                    raise
                import time; time.sleep(.6)
        n += 1
    with io.open(NECUNOSCUTE, "w", encoding="utf-8") as f:
        for k, pg in sorted(necunoscute.items(), key=lambda x: x[1]):
            f.write(f"{pg}\t{k}\n")
    print(f"  {n} pagini in engleza; {len(T)} segmente in dictionar; "
          f"{len(necunoscute)} segmente fara traducere -> {os.path.relpath(NECUNOSCUTE, RAD)}")


if __name__ == "__main__":
    ruleaza()
