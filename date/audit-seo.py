# -*- coding: utf-8 -*-
"""
Audit SEO / GEO / AEO / E-E-A-T / legaturi interne, pe toate paginile (RO + EN).
Rulare: python date/audit-seo.py  -> raport in consola + date/audit-seo.json
"""
import glob, io, json, os, re, sys
from collections import Counter, defaultdict

RAD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(RAD)
DOM = "https://emerald-city.ro"


def pagini():
    for f in sorted(glob.glob("**/index.html", recursive=True)):
        f = f.replace("\\", "/")
        if f.startswith(("export/", "assets/", "brand/", "date/", "node_modules/")) or "/_" in f:
            continue
        yield f


def cale(f):
    return "" if f == "index.html" else f[: -len("index.html")]


def text_vizibil(h):
    h = re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>", " ", h, flags=re.S)
    h = re.sub(r"<(nav|header|footer)\b.*?</\1>", " ", h, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip()


def rezolva(href, dir_ro):
    if href.startswith("/"):
        return href.split("#")[0].split("?")[0].lstrip("/")
    baza = [p for p in dir_ro.split("/") if p]
    for p in href.split("#")[0].split("?")[0].split("/"):
        if p == "..":
            if baza: baza.pop()
        elif p and p != ".":
            baza.append(p)
    out = "/".join(baza)
    return out + ("/" if out and not out.endswith("/") and "." not in out.split("/")[-1] else "")


P = {}
intrari = Counter()
ancore = defaultdict(set)
probleme = defaultdict(list)

for f in pagini():
    h = io.open(f, encoding="utf-8").read()
    c = cale(f)
    en = c.startswith("en/")
    d = {"en": en, "url": c}
    d["title"] = (re.search(r"<title>([^<]*)</title>", h) or [None, ""])[1].strip()
    d["desc"] = (re.search(r'name="description" content="([^"]*)"', h) or [None, ""])[1]
    d["canonical"] = (re.search(r'rel="canonical" href="([^"]*)"', h) or [None, ""])[1]
    d["lang"] = (re.search(r'<html lang="(\w+)"', h) or [None, ""])[1]
    d["h1"] = re.findall(r"<h1[^>]*>(.*?)</h1>", h, flags=re.S)
    d["h2"] = len(re.findall(r"<h2\b", h)); d["h3"] = len(re.findall(r"<h3\b", h))
    d["hreflang"] = dict(re.findall(r'hreflang="([\w-]+)" href="([^"]*)"', h))
    d["og"] = {k: v for k, v in re.findall(r'property="og:(\w+)" content="([^"]*)"', h)}
    d["twitter"] = len(re.findall(r'name="twitter:', h))
    d["viewport"] = 'name="viewport"' in h
    imgs = re.findall(r"<img\b[^>]*>", h)
    d["img"] = len(imgs)
    d["img_fara_alt"] = sum(1 for i in imgs if not re.search(r'\balt="[^"]+"', i))
    d["img_alt_gol"] = sum(1 for i in imgs if re.search(r'\balt=""', i))
    d["img_lazy"] = sum(1 for i in imgs if 'loading="lazy"' in i)
    d["img_dim"] = sum(1 for i in imgs if re.search(r'\bwidth="', i) and re.search(r'\bheight="', i))
    # date structurate
    d["schema"] = []
    d["schema_err"] = 0
    for s in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, flags=re.S):
        try:
            j = json.loads(s)
            items = j.get("@graph", [j]) if isinstance(j, dict) else j
            for it in items:
                d["schema"].append(it.get("@type"))
        except ValueError:
            d["schema_err"] += 1
    d["faq"] = "FAQPage" in d["schema"]
    d["faq_n"] = len(re.findall(r"<details>", h))
    d["breadcrumb"] = "BreadcrumbList" in d["schema"]
    txt = text_vizibil(h)
    d["cuvinte"] = len(txt.split())
    # legaturi
    corp = re.sub(r"<(nav|header|footer)\b.*?</\1>", " ", re.sub(r"<script.*?</script>", "", h, flags=re.S), flags=re.S)
    d["link_ext"] = 0; d["link_int"] = 0; d["link_ext_fara_rel"] = 0; d["ancore_slabe"] = 0
    for m in re.finditer(r'<a\b([^>]*)href="([^"]*)"([^>]*)>(.*?)</a>', corp, flags=re.S):
        atr = m.group(1) + m.group(3); href = m.group(2)
        anc = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(4))).strip()
        if href.startswith(("http://", "https://")) and DOM not in href:
            d["link_ext"] += 1
            if 'target="_blank"' in atr and "noopener" not in atr:
                d["link_ext_fara_rel"] += 1
            continue
        if href.startswith(("mailto:", "tel:", "#", "javascript:")):
            continue
        d["link_int"] += 1
        tinta = rezolva(href.replace(DOM + "/", "/") if href.startswith("http") else href, c)
        if tinta.startswith(("assets/", "brand/")):
            continue
        intrari[tinta] += 1
        if anc:
            ancore[tinta].add(anc.lower()[:60])
        if anc.lower() in ("aici", "click", "click aici", "here", "click here", "vezi", "mai mult", "read more"):
            d["ancore_slabe"] += 1
    # E-E-A-T / GEO semnale in corp
    d["autor"] = bool(re.search(r'"author"', h))
    d["org"] = any(t in ("Organization", "RealEstateAgent") for t in d["schema"])
    d["contact_vizibil"] = "0757 70 70 80" in h
    d["datePublished"] = '"datePublished"' in h
    P[c] = d

# ---------------------------------------------------------------- verificari --
titluri = Counter(d["title"] for d in P.values())
descrieri = Counter(d["desc"] for d in P.values())
for c, d in P.items():
    pr = probleme[c]
    if not d["title"]: pr.append("fara <title>")
    elif len(d["title"]) > 65: pr.append(f"title lung ({len(d['title'])})")
    elif len(d["title"]) < 25: pr.append(f"title scurt ({len(d['title'])})")
    if titluri[d["title"]] > 1: pr.append("title duplicat")
    if not d["desc"]: pr.append("fara meta description")
    elif len(d["desc"]) > 165: pr.append(f"description lunga ({len(d['desc'])})")
    elif len(d["desc"]) < 70: pr.append(f"description scurta ({len(d['desc'])})")
    if descrieri[d["desc"]] > 1: pr.append("description duplicata")
    if len(d["h1"]) != 1: pr.append(f"{len(d['h1'])} x H1")
    if d["canonical"] != f"{DOM}/{c}": pr.append(f"canonical gresit: {d['canonical']}")
    if d["lang"] != ("en" if d["en"] else "ro"): pr.append(f"lang={d['lang']}")
    hl = d["hreflang"]
    if set(hl) != {"ro", "en", "x-default"}: pr.append("hreflang incomplet")
    else:
        propriu = hl["en" if d["en"] else "ro"]
        if propriu != f"{DOM}/{c}": pr.append("hreflang propriu nu corespunde")
        # reciprocitate
        alt = hl["ro" if d["en"] else "en"].replace(DOM + "/", "")
        if alt not in P: pr.append(f"alternate lipsa: {alt}")
        elif P[alt]["hreflang"].get("en" if d["en"] else "ro") != f"{DOM}/{c}": pr.append("hreflang nereciproc")
    for k in ("title", "description", "image", "url", "type", "locale"):
        if k not in d["og"]: pr.append(f"og:{k} lipsa")
    if d["og"].get("url") and d["og"]["url"] != f"{DOM}/{c}": pr.append("og:url diferit de canonical")
    if d["twitter"] < 3: pr.append("twitter cards incomplete")
    if d["schema_err"]: pr.append("JSON-LD invalid")
    if not d["breadcrumb"] and c and c != "en/": pr.append("fara BreadcrumbList")
    if d["img_fara_alt"]: pr.append(f"{d['img_fara_alt']} img fara alt")
    if d["img"] and d["img_dim"] < d["img"]: pr.append(f"{d['img'] - d['img_dim']} img fara width/height")
    if d["cuvinte"] < 250: pr.append(f"continut subtire ({d['cuvinte']} cuvinte)")
    if d["link_int"] < 3: pr.append(f"doar {d['link_int']} legaturi interne in corp")
    if d["link_ext_fara_rel"]: pr.append(f"{d['link_ext_fara_rel']} linkuri externe _blank fara noopener")
    if d["ancore_slabe"]: pr.append(f"{d['ancore_slabe']} ancore generice")
    if not d["contact_vizibil"]: pr.append("telefon lipsa din pagina")

orfane = [c for c in P if c and intrari[c] == 0]
unitati = [c for c in P if re.search(r"/c\d+-", "/" + c)]
neunitati = [c for c in P if c not in unitati]

# ---------------------------------------------------------------- raport ------
def sec(t): print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)

sec("REZUMAT")
print(f"pagini: {len(P)} ({sum(1 for d in P.values() if not d['en'])} RO / {sum(1 for d in P.values() if d['en'])} EN); "
      f"din care unitati: {len(unitati)}")
tot = Counter()
for c, pr in probleme.items():
    for x in pr: tot[re.sub(r"\(.*?\)|: .*", "", x).strip()] += 1
print("\nprobleme pe categorii (numar de pagini afectate):")
for k, v in tot.most_common(): print(f"  {v:5d}  {k}")

sec("PAGINI NE-UNITATE CU PROBLEME")
for c in neunitati:
    if probleme[c]: print(f"  /{c}\n     - " + "\n     - ".join(probleme[c]))

sec("UNITATI — esantion de probleme distincte")
vaz = set()
for c in unitati:
    for x in probleme[c]:
        k = re.sub(r"\(.*?\)|: .*", "", x).strip()
        if k not in vaz:
            vaz.add(k); print(f"  /{c}: {x}")

sec("LEGATURI INTERNE — pagini orfane (fara nicio legatura din corpul altor pagini)")
print("  " + ("\n  ".join("/" + c for c in orfane) if orfane else "niciuna"))

sec("LEGATURI INTERNE — cele mai putin legate pagini ne-unitate (intrari din corp)")
for c in sorted(neunitati, key=lambda x: intrari[x])[:15]:
    print(f"  {intrari[c]:4d}  /{c}  ancore: {', '.join(sorted(ancore[c])[:4])}")

sec("AEO / GEO — intrebari frecvente, date structurate, autor")
for c in neunitati:
    d = P[c]
    print(f"  /{c:52s} cuv={d['cuvinte']:5d} FAQ={'da' if d['faq'] else '- '}({d['faq_n']:2d}) "
          f"schema={','.join(sorted(set(str(x) for x in d['schema'])))}")

sec("E-E-A-T")
print(f"  pagini cu Organization/RealEstateAgent in schema: {sum(1 for d in P.values() if d['org'])}")
print(f"  pagini cu author: {sum(1 for d in P.values() if d['autor'])} (articole)")
print(f"  pagini cu datePublished: {sum(1 for d in P.values() if d['datePublished'])}")
print(f"  pagini cu telefon vizibil: {sum(1 for d in P.values() if d['contact_vizibil'])}/{len(P)}")
print(f"  robots.txt: {io.open('export/robots.txt').read().strip().splitlines() if os.path.exists('export/robots.txt') else 'lipsa'}")

json.dump({"pagini": P, "probleme": probleme, "intrari": intrari, "orfane": orfane},
          io.open("date/audit-seo.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=list)
