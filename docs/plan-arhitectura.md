# Emerald City — plan de arhitectură web

Document de lucru. Bazat pe documentația din `documentatie/` (proiect 266/2023, faza DTAC)
și pe analiza site-ului de referință lapis-residence.ro.

---

## 0. Datele proiectului (confirmate din planșe)

| | |
|---|---|
| Denumire comercială | Emerald City (fost Tala Sapphire) |
| Beneficiar | S.C. Tala Sapphire S.R.L. |
| Amplasament | Jud. Iași, com. Rediu, sat Rediu, nr. cad. 70147 |
| Acces | DE 1538 — Strada Ion Nistor |
| Proiectant | S.C. C.A.D. S.R.L., șef proiect arh. Ovidiu M. Murgu |
| Teren | 50.235,00 m² (UTR 1: 42.537,40 m²) |
| POT / CUT | 30,00 % / 1,80 |
| Corpuri | 18 (C1–C18), toate **2D+P+3E**, Hmax 18,00 m |
| Apartamente | **925** |
| Rezidențial | 51.104,38 m² (medie **55,2 m²**/apartament) |
| Balcoane | 6.263,12 m² |
| Comercial | C6 = 722,22 m², C12 = 125,82 m² |
| Parcare | 258 subteran + 682 suprateran = **940** |
| Spațiu verde | 15.501,80 m² (**30,85 %**) |
| Diferență de nivel teren | ~31 m (cote +75,26 … +106,66) |
| Etapizare | I: C1–C6 (322 ap.) · II: C7–C14 (423 ap.) · III: C15–C18 (180 ap.) |

**Apartamente pe corp:** C1/C2 45 · C3/C4 61 · C5–C8 55 · C9/C10 45 · C11 55 · C12–C14 56 · C15–C18 45

### Avertismente

1. **Titlul DTAC acoperă doar C1–C6.** Tabelul de indicatori acoperă 18 corpuri. De verificat ce e
   autorizat înainte de a publica 925 de apartamente. Expunere legală pe publicitate imobiliară.
2. **Inconsecvență de 1.349 m²** între planșă (AU TOTAL 65.431,50) și Excel (64.082,23). Comercial:
   722,22 vs 700. Se stabilește o sursă unică de adevăr înainte de Schema Markup.
3. **PDF-urile de interior sunt Lapis.** Cartușul spune „LAPIS 2 – INTERIOR"; numerotarea
   (ap. 04/13/22/31/40, pas 9, **5 niveluri**) nu corespunde cu 2D+P+3E = 4 niveluri. Suprafețele
   2A = 45,73 / 3A = 70,69 / 3B = 65,42 m² sunt Lapis, nu Emerald City.
4. **Datele pe apartament lipsesc.** Până la primirea lor se folosește `date/unitati-demo.csv`
   (925 rânduri, structural corecte, valori individuale inventate).

---

## 1. Arhitectura informației

### Principiul de bază

Lapis are două ierarhii care nu se închid: bloc → etaj → apartament (vizuală) și tipologie
(editorială). Din tipologie nu te poți întoarce la unitate. La 925 de unități asta devine
inutilizabil. Emerald City are **o singură ierarhie canonică**, cu tipologia ca vedere secundară.

### Sitemap

```
/                                     Homepage
/ansamblul/                           Povestea: teren terasat, parc dendrologic, masterplan
  /ansamblul/amplasament/             Rediu, acces, distanțe, hartă
  /ansamblul/facilitati/              Parc, loc de joacă, comercial, parcare
  /ansamblul/etape/                   Etapa I / II / III, stadiu, termene
/apartamente/                         HUB — selectorul principal (toate cele 925)
  /apartamente/{corp}/                Pagină de corp (18)            ex. /apartamente/c3/
  /apartamente/{corp}/etaj-{n}/       Plan de etaj (72)              ex. /apartamente/c3/etaj-2/
  /apartamente/{corp}/{unitate}/      UNITATE (925)                  ex. /apartamente/c3/a-2-14/
/tipologii/                           Vedere editorială pe tipologie
  /tipologii/{n}-camere/              Hub pe camere (3–4)
  /tipologii/{cod}/                   Tipologie individuală          ex. /tipologii/2a/
/finisaje/                            Aici intră randările Omini Concept
/preturi-si-plata/                    Prețuri, TVA, avans, credit
/despre-dezvoltator/                  E-E-A-T: Tala Sapphire, proiectant, autorizații
/stadiu-lucrari/                      Jurnal de șantier (lunar)
/blog/                                Conținut local SEO
/contact/
```

**Decizie:** fiecare unitate are URL propriu. 925 de pagini generate din date, nu scrise de mână.
Motivul e GEO/AEO: un AI care răspunde la „apartament 2 camere Rediu sub 90.000 €" are nevoie de o
entitate adresabilă cu preț și disponibilitate, nu de un rând într-un tabel.

**Indexare:** unitățile `vândut` și `în curând` primesc `noindex, follow` — altfel se generează
sute de pagini thin care diluează autoritatea. Rămân accesibile utilizatorului (social proof),
dar nu intră în index.

### Organizarea datelor

Sursa unică: un custom post type `unitate`, alimentat prin import CSV/CRM, expus prin REST.
Nimic scris de mână în page builder.

---

## 2. Conceptul UX/UI

### Problema centrală de design

Brief-ul cere fuziunea Azabudai (poveste, natură) + Lapis (conversie). Dar materialul vizual
existent nu susține partea de natură: randările de interior arată **blocuri vecine prin ferestre**,
paletă greige-bej caldă, zero verde smarald, trei stiluri diferite între 2A/3A/3B.

**Soluția:** povestea de natură se spune cu **materialul de sit**, nu cu interioarele.
Emerald City chiar are ce arăta — 31 m de terasare pe curbe de nivel, parc dendrologic, 30,85%
verde. Interioarele coboară la `/finisaje/`, unde universul cald funcționează ca promisiune de
confort, nu ca argument de peisaj.

Tranziția poveste → vânzare nu se face printr-o ruptură, ci printr-o **strângere progresivă a
ritmului**: secțiuni full-bleed cu mult aer sus → grilă din ce în ce mai densă → tabel. Scroll-ul
însuși devine drumul de la viziune la decizie.

### Homepage, secțiune cu secțiune

| # | Secțiune | Rol | Note |
|---|---|---|---|
| 1 | **Hero** — video/randare aeriană a ansamblului terasat, logo centrat, o singură propoziție | Azabudai | Fundal închis `#1F3E36`. Fără formular. Un singur CTA discret jos: „Vezi apartamentele" |
| 2 | **Cifrele care contează** — 925 apartamente · 18 corpuri · 30,85% spațiu verde · 31 m diferență de nivel | Credibilitate imediată | Contoare animate la intrare în viewport |
| 3 | **Terenul** — secțiune de teren animată la scroll, arătând terasarea pe cote | Diferențiatorul real | SVG animat, nu video. Aici e povestea pe care Lapis nu o are |
| 4 | **Parcul dendrologic** — full-bleed, fotografie/randare de peisagistică | Natură | |
| 5 | **Masterplan interactiv** — cele 18 corpuri, hover pe corp → disponibilitate | **Pivotul** | Prima interacțiune cu datele. De aici începe Lapis |
| 6 | **Găsește-ți apartamentul** — filtru compact (camere / buget / etapă) + 6 rezultate | Conversie | Trimite în `/apartamente/` cu filtrele aplicate |
| 7 | **Tipologii** — 3–5 carduri cu plan + interval de suprafață și preț | | |
| 8 | **Finisaje** — randările Omini, carusel | Confort | Etichetat clar ca amenajare orientativă |
| 9 | **Stadiu lucrări** — ultimele 3 actualizări | Încredere | |
| 10 | **Amplasament** — hartă + distanțe reale (centru Iași, școli, spitale) | SEO local | |
| 11 | **FAQ** — 15–20 întrebări | GEO/AEO + `FAQPage` | |
| 12 | **Contact** | | |

### Schema cromatică

Pornind de la `#1F3E36` (extras programatic din logo, nu estimat) și de la paleta reală a
randărilor:

| Rol | Token | HEX | Sursă |
|---|---|---|---|
| Brand primar | `--ec-emerald` | `#1F3E36` | logo |
| Emerald închis (hero, footer) | `--ec-emerald-900` | `#142B25` | derivat |
| Emerald deschis (hover, accente) | `--ec-emerald-400` | `#3D6B5C` | derivat |
| Fundal cald (secțiuni) | `--ec-sand` | `#EDE8E0` | randări (perete ivoire) |
| Fundal secundar | `--ec-greige` | `#D6CEC2` | randări |
| Lemn / accent cald | `--ec-oak` | `#D9C5A8` | randări (parchet stejar) |
| Accent conversie | `--ec-brass` | `#B8934F` | randări 3A (alamă) |
| Text | `--ec-ink` | `#1A1D1B` | |
| Disponibil | `--ec-available` | `#2E7D5B` | |
| Rezervat | `--ec-reserved` | `#B8863B` | |
| Vândut | `--ec-sold` | `#8C3A33` | randări 2A (bordo) |

Notă: statusurile nu folosesc verde/roșu clasic. Verdele de disponibilitate e derivat din brand,
iar „vândut" folosește bordo-ul din randarea 2A — rămâne în universul proiectului și evită
semaforul generic. Contrastul se verifică la AA pe fundalurile `--ec-sand` și `--ec-emerald-900`.

**Tipografie:** logo-ul e sans geometric bold cu tracking foarte larg. Se reia: titluri cu
`letter-spacing` 0.12–0.18em pe majuscule pentru eyebrow-uri și numere, corp de text
într-un sans neutru cu lizibilitate bună la corp mic (tabelele au 925 de rânduri).

---

## 3. Selectorul de apartamente

### Ce nu funcționează la Lapis (și de ce nu se copiază)

| Problemă | Consecință la 925 unități |
|---|---|
| Fără model de date — fiecare unitate e un `<tr>` scris de mână | ~925 rânduri + ~925 poligoane întreținute manual |
| Datele există în 2 locuri (tabel + hotspot), nesincronizate | Divergență garantată |
| Contoarele („3 din 50", „94% vândut") sunt hardcodate | 4–5 editări la fiecare vânzare |
| Hotspot-urile din planul de etaj au toate `href="#"` | Cea mai gravă scurgere din funnel |
| Filtrare doar pe status | Cumpărătorul filtrează după camere + buget + etaj |
| Formularul nu trimite ce apartament vrea clientul | Lead orb |
| CTA „Verifică disponibilitate" duce înapoi la pasul 1 | Context pierdut |

### Modelul de date

CPT `unitate` + taxonomii `corp`, `tipologie`, `etapa`, `status`. Câmpuri: etaj, nr. camere,
suprafață utilă / balcon / curte, orientare, preț, €/mp, boxă, parcare, plan PDF, ID hotspot SVG.

Filtrarea **nu** se face nici pur client-side (925 de rânduri în HTML = pagină inutilizabilă),
nici cu reîncărcare. Abordarea:

1. Un endpoint REST `/wp-json/ec/v1/unitati` întoarce un **JSON compact** (doar câmpurile de
   filtrare, ~60 KB pentru 925 de unități, gzip ~12 KB), cache-uit agresiv, invalidat la salvare.
2. Filtrarea și sortarea se fac în JS pe acest set, instant, fără cereri.
3. Randarea listei e **virtualizată** — se desenează doar rândurile vizibile.
4. Starea filtrelor se scrie în URL (`?camere=2&pret-max=90000&etapa=1`) — shareable, iar
   server-side se poate pre-randa pentru SEO.

### Filtre

Camere (butoane multi-select) · Buget (slider dublu) · Suprafață (slider dublu) ·
Etaj (butoane P/1/2/3) · Corp (dropdown multi) · Etapă · Orientare · Status ·
Extra (boxă, parcare, curte proprie, balcon >8 m²)

Fiecare filtru afișează contorul rezultatelor **calculat**, niciodată hardcodat.

### Fluxul UX — de la schiță la formular

Lapis are 4 pași și se termină într-un pop-up fără CTA. Emerald City:

```
Intrare A (rapidă):    /apartamente/ → filtre → card → /apartamente/c3/a-2-14/
Intrare B (vizuală):   masterplan → corp → plan etaj (SVG) → /apartamente/c3/a-2-14/
Intrare C (editorială): /tipologii/2a/ → "14 unități disponibile de acest tip" → listă filtrată
```

Toate trei converg în **pagina de unitate**, care are URL propriu și e capătul drumului, nu o
fundătură. Regula: din orice hotspot se ajunge la o pagină reală, niciodată la `href="#"`.

Planurile de etaj se generează **din date, ca SVG**, nu se desenează manual ca image map.
Poligoanele se desenează o dată per tip de etaj (nu 72 de ori), iar statusul și numărul de
apartament se leagă prin `data-unit-id`. Planurile 2D din PDF-urile Omini sunt vectoriale și
au deja camerele delimitate și etichetate cu suprafață — se extrag ca SVG.

### Pagina de unitate

1. Breadcrumb + H1 „Apartament 2 camere, 58,4 m² — corp C3, etaj 2"
2. Status vizibil imediat + preț total + €/mp + TVA aplicabil
3. Plan interactiv (hover pe cameră → suprafața) + PDF descărcabil
4. Poziția în corp și pe masterplan (unde e pe teren, la ce cotă, ce vede)
5. Suprafețe defalcate pe cameră
6. Finisaje incluse
7. **Formular cu unitatea preîncărcată** — hidden input `unit_id`, plus textul vizibil
   „Întreb despre apartamentul C3-E2-14". Consultantul primește lead-ul cu context complet.
8. „Unități similare" — aceeași tipologie, alt corp/etaj (recuperează utilizatorul dacă e vândut)
9. FAQ specific + Schema

**Fără fundături:** dacă unitatea e vândută, pagina rămâne, dar CTA-ul devine
„Vezi 12 apartamente similare disponibile".

---

## 4. Strategia SEO și GEO

### Poziționare

Emerald City e în **com. Rediu**, nu în Iași. Asta e simultan o slăbiciune de căutare
(„apartamente Iași" e dominat de proiecte urbane) și o oportunitate: intenția „apartamente noi
Rediu" e aproape necontestată, iar „apartamente Iași nord" e slab acoperit.

Trei clustere:
- **Local:** apartamente noi Rediu, apartamente Rediu Iași, ansamblu rezidențial Rediu
- **Tipologic:** apartament 2 camere Rediu, garsonieră Iași nord, apartament 3 camere cu curte
- **Intenție de cumpărare:** apartamente Iași TVA 9%, avans, credit Prima Casă, direct dezvoltator

### E-E-A-T

Real estate e YMYL. Semnalele necesare:
- Pagină de dezvoltator cu **Tala Sapphire S.R.L.**, CUI, proiectant (C.A.D. S.R.L.,
  arh. Ovidiu M. Murgu), autorizație (CU 194/23.06.2023, Primăria Rediu), proiect 266/2023
- **Jurnal de șantier lunar cu fotografii datate** — cel mai puternic semnal de „Experience"
- Prețuri publice cu condiții explicite (TVA, avans) — transparență verificabilă
- Autor real pe articolele de blog, nu „admin"

### GEO/AEO

Un motor generativ are nevoie de fapte extractabile, nu de proză de marketing. Concret:

- Fiecare pagină de unitate expune **un singur fapt principal** într-o structură stabilă:
  tip, suprafață, etaj, corp, preț, status, disponibilitate.
- **Un tabel HTML real** (`<table>`) pe paginile de tipologie — modelele extrag tabele mult mai
  fiabil decât div-uri stilizate.
- FAQ scris ca **întrebare exactă → răspuns direct în prima propoziție**, apoi detaliu.
  Nu „Vă întrebați poate care sunt prețurile?" ci „Prețurile încep de la X €."
- O pagină `/date-proiect/` cu toate cifrele oficiale într-un tabel — targetul pentru interogări
  de tip „câte apartamente are Emerald City".

### Schema Markup (JSON-LD)

Lapis afișează prețuri dar **nu are `offers` în schema `Apartment`** — rich result ratat.
La Emerald City, `offers` e obligatoriu pe fiecare unitate disponibilă.

**Homepage** — graf cu `Organization` (dezvoltator), `RealEstateListing` (ansamblul),
`Place` (Rediu, cu `geo`), `FAQPage`, `BreadcrumbList`.

**Pagină de unitate:**

```json
{
  "@context": "https://schema.org",
  "@type": "Apartment",
  "@id": "https://emerald-city.ro/apartamente/c3/a-2-14/#apartament",
  "name": "Apartament 2 camere, 58,4 m² — Emerald City, corp C3",
  "numberOfRooms": 2,
  "numberOfBathroomsTotal": 1,
  "floorSize": { "@type": "QuantitativeValue", "value": 58.4, "unitCode": "MTK" },
  "floorLevel": "2",
  "petsAllowed": true,
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "Strada Ion Nistor",
    "addressLocality": "Rediu",
    "addressRegion": "Iași",
    "postalCode": "—",
    "addressCountry": "RO"
  },
  "geo": { "@type": "GeoCoordinates", "latitude": "—", "longitude": "—" },
  "amenityFeature": [
    { "@type": "LocationFeatureSpecification", "name": "Balcon", "value": true },
    { "@type": "LocationFeatureSpecification", "name": "Boxă", "value": true },
    { "@type": "LocationFeatureSpecification", "name": "Parcare subterană", "value": true }
  ],
  "containedInPlace": { "@id": "https://emerald-city.ro/#ansamblu" },
  "offers": {
    "@type": "Offer",
    "price": "92000",
    "priceCurrency": "EUR",
    "availability": "https://schema.org/InStock",
    "validFrom": "2026-09-24",
    "seller": { "@id": "https://emerald-city.ro/#dezvoltator" }
  }
}
```

`availability` se mapează: disponibil → `InStock`, rezervat → `LimitedAvailability`,
vândut → `SoldOut`, în curând → `PreOrder`.

Coordonatele: planșa are Stereo70 (X: 691953, Y: 634574) — se convertesc în WGS84.

**Pagini de corp:** `ItemList` cu unitățile, pentru a lega entitățile între ele.

### Performanță

Lapis are TTFB 46 ms (bine) dar 122 de cereri și 58 de scripturi, jQuery legacy, imagini de
563 KB needimensionate, dublu GA4 și 5 sisteme de tracking. De evitat:

- Fără page builder pentru conținutul de vânzare. Șabloane PHP.
- Fără jQuery.
- Imagini: AVIF/WebP, `srcset`, dimensiuni explicite, `loading="lazy"` sub fold.
- Un singur sistem de analytics (GA4 prin GTM). Pixelii de remarketing se încarcă după consimțământ.
- Planurile de etaj: SVG inline, nu JPG de 376 KB.
- Cache la nivel de server + invalidare la salvarea unei unități.
- Buget: LCP < 2,0 s pe 4G, INP < 200 ms cu 925 de unități în filtru.

---

## Ce blochează începerea

1. Datele pe apartament (925 rânduri) — schema în `date/template-unitati.csv`
2. Randări exterioare și de peisagistică — fără ele nu există homepage premium
3. Decizia pe prețuri: publice sau la cerere
4. Clarificarea autorizației (C1–C6 vs 18 corpuri)
5. Sursa unică de adevăr pentru arii (diferența de 1.349 m²)
