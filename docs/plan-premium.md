# Emerald City — plan de ridicare la nivel premium

Document de lucru. Ordonat după impact real, nu după efort.

---

## Diagnostic: de ce un site citește „poor"

Un client care spune „design is poor" rareori se referă la layout. Se referă la trei
lucruri, în ordinea asta:

1. **Imaginile** — dacă fotografia e slabă, inconsistentă sau lipsește, nimic din CSS nu
   compensează. Site-urile premium sunt 70% fotografie.
2. **Coerența** — când elementele par să vină din proiecte diferite, creierul citește
   „amatori" înainte să analizeze de ce.
3. **Finisajul mișcării** — tranziții bruște, imagini care apar pocnit, hover-uri fără
   răspuns. Se simte ieftin chiar dacă statica e corectă.

Structura paginii e deja pe referințele cerute. Restul e material și finisaj.

---

## Nivelul 1 — blocante reale

### 1.1 Coerența randărilor (de făcut imediat, cost zero)

**Problema pe care am creat-o:** cele 12 imagini din pagină provin din trei scheme de
design complet diferite:

| Sursă | Universul ei |
|---|---|
| Apartament 2A | bordo-terracotta + bleumarin-petrol, candelabru roșu, mobilier colorat |
| Apartament 3A | ivoire + alamă + marmură Calacatta, ton-pe-ton, cel mai luxos |
| Apartament 3B | nuc închis + negru mat + verde măsliniu, japandi sobru |

Amestecate pe aceeași pagină, arată ca trei proiecte diferite. **Aceasta este probabil
prima cauză a senzației de incoerență.**

**Soluție:** se alege o singură schemă ca limbaj vizual al site-ului. Recomandarea mea
este **3A (ivoire + alamă)** — e cea mai apropiată de „premium" în sensul în care îl
folosește clientul, și se leagă cel mai bine cu alama deja folosită ca accent în interfață.
Din cele 51 de randări extrase, seria 3A oferă 27 de imagini, suficient pentru tot site-ul.

Celelalte două scheme rămân pentru paginile de tipologie, unde diferența e explicată și
justificată („fiecare tipologie are propria amenajare").

### 1.2 Randări exterioare

Fără ele, hero-ul rămâne un interior — ceea ce niciun ansamblu rezidențial premium nu face.
Necesar, în ordinea priorității:

- o vedere aeriană sau semi-aeriană a ansamblului
- o perspectivă de la nivelul pietonului, cu oameni și vegetație
- o imagine de seară, cu ferestre luminate (cea mai „vândută" imagine din imobiliare)
- amenajarea peisagistică: alei, loc de joacă, parc

Dacă nu există buget de randare nouă: se poate filma/fotografia macheta fizică, dacă
există, sau se folosește o imagine de detaliu foarte apropiată (fațadă, tâmplărie,
material) în locul unei perspective generale. Un detaliu bine ales e mai premium decât o
perspectivă slabă.

### 1.3 Datele reale ale apartamentelor

925 de rânduri cu suprafețe, etaje, prețuri și status. Fără ele, tot ce ține de
disponibilitate rămâne demonstrativ. Schema cerută: `date/template-unitati.csv`.

---

## Nivelul 2 — finisajul care se simte

### 2.1 Tratamentul imaginii

- **Gradare unitară.** Toate imaginile trec prin aceeași corecție: temperatură, contrast,
  saturație. Chiar și randări din aceeași serie diferă suficient cât să se observe.
- **Blur-up la încărcare.** Se generează o miniatură de ~20px, se pune ca fundal blurat,
  iar imaginea reală apare în fade după `decode()`. Elimină pocnetul la scroll.
- **AVIF + WebP cu `<picture>`**, fallback JPEG. Reduce încărcarea cu 40–60%.
- **`srcset` pe trei praguri** (800 / 1400 / 2000), ca mobilul să nu descarce 1600px.
- **Zoom fin la hover** pe imaginile din carduri: `scale(1.04)` în 600ms, cu `overflow:hidden`
  pe figură. Azabudai face exact asta și e jumătate din senzația de calitate.

### 2.2 Mișcare

- **Reveal în cascadă**, nu simultan: elementele dintr-un card intră decalat cu 60–80 ms.
- **Parallax intern** pe imaginile din carduri: imaginea se mișcă cu ~8% mai lent decât
  pagina. Subtil, dar e semnătura site-urilor scumpe.
- **Ken Burns pe hero**: zoom foarte lent, 20s, `scale(1)` → `scale(1.06)`.
- **Numere care urcă** la intrarea în viewport (există deja, de reactivat pe secțiunea
  de cifre dacă se reintroduce).
- **Tranziție la schimbarea filtrului**: rezultatele ies în fade și intră decalat, în loc
  să se schimbe brusc.
- Totul respectă `prefers-reduced-motion`.

### 2.3 Tipografie

- **Optical sizing** și tracking negativ pe titlurile mari (`-0.02em` peste 2rem).
- **Fără orfani** în titluri: `text-wrap: balance` pe titluri, `pretty` pe paragrafe
  (parțial pus deja).
- **Cifre tabulare** peste tot unde apar prețuri și suprafețe (pus deja).
- **O singură scară**, cu pași clari. Momentan sunt prea multe dimensiuni apropiate.
- Luat în calcul: un font cu mai multă personalitate pentru titluri. Inter Tight e sigur,
  dar neutru. Alternative care rămân sobre: Geist, Söhne, Neue Haas Grotesk Display.

### 2.4 Detalii de execuție

- Niciun negru pur și niciun gri rece — totul cu subton verde, ca să se lege de brand.
- Umbre: maximum două niveluri, foarte difuze, niciodată pe carduri statice.
- Borduri de 1px la `rgba(…, .1)`, nu linii gri.
- Colțuri: sau totul drept, sau totul cu aceeași rază. Momentan butoanele sunt pastile,
  cardurile sunt drepte — e o decizie, dar trebuie ținută consecvent.
- Stări de focus vizibile și elegante, nu conturul implicit al browserului (pus deja).

---

## Nivelul 3 — profunzime de conținut

Azabudai nu e premium doar pentru că arată bine, ci pentru că **fiecare card duce undeva
real**. La noi, momentan, cardurile trimit la ancore în aceeași pagină. Asta se simte gol.

De construit, în ordine:

1. **Pagina de unitate** (925 URL-uri generate din date) — cea mai importantă, și pentru
   conversie, și pentru GEO/AEO
2. **Pagini de tipologie** cu plan interactiv și randările schemei respective
3. **Pagina de amplasament** ca pagină SEO pe „apartamente Iași Păcurari", cu hartă,
   distanțe măsurate și context de cartier
4. **Jurnal de șantier** lunar cu fotografii datate — cel mai puternic semnal de încredere
   și de E-E-A-T pe care îl poate avea un dezvoltator
5. **Pagina de dezvoltator** cu proiecte anterioare, echipă, autorizații
6. **Blog local**: „cum se cumpără o locuință nouă", „ce înseamnă TVA 9%", „cartierul
   Păcurari" — traficul organic real vine de aici

---

## Nivelul 4 — conversie

Preluate din Lapis, unde funcționează:

- **Bară de ofertă cu countdown** (discount lunar, termen de rezervare)
- **Tabel de disponibilitate complet**, cu sortare pe coloane și filtre reale
- **Formular care preia unitatea** — `unit_id` în câmp ascuns, plus text vizibil
  „Întreb despre apartamentul 3-E2-14"
- **Tur virtual 360°** pe apartamentele-model
- **PDF descărcabil** cu planul, per tipologie
- **WhatsApp flotant** (pus deja) și `tel:` pe mobil

De adăugat peste Lapis:
- **Comparator** de până la 3 apartamente
- **Notificare la disponibilitate** pentru tipologiile epuizate — recuperează lead-uri
  care altfel se pierd

---

## Nivelul 5 — performanță ca semnal de calitate

Un site premium se încarcă instant. Lapis are TTFB de 46 ms, dar 122 de cereri și 58 de
scripturi. Bugetul nostru:

| Metrică | Țintă |
|---|---|
| LCP | < 2,0 s pe 4G |
| INP | < 200 ms cu 925 de unități în filtru |
| CLS | < 0,05 |
| Cereri | < 40 |
| JS total | < 60 KB |

Măsuri: imagini AVIF cu dimensiuni explicite, fonturi `preload` + `font-display: swap`,
un singur sistem de analytics, pixelii de remarketing încărcați după consimțământ, CSS
critic inline.

---

## Ordinea în care aș lucra

1. Unificarea randărilor pe schema 3A — o oră, efect imediat și vizibil
2. Tratamentul imaginii: hover zoom, blur-up, AVIF, srcset
3. Mișcarea: cascadă, parallax intern, Ken Burns
4. Pagina de unitate + tipologii (cu date demo, până vin cele reale)
5. Restul depinde de primirea randărilor exterioare și a datelor
