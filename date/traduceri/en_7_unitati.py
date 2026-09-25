# -*- coding: utf-8 -*-
# Paginile de unitate (925): titluri si descrieri patternizate (REGULI), propozitiile
# fixe din care se compune povestea unitatii, fisa, costuri, cartier.
T = {
"Ferestrele sunt orientate spre nord: lumină constantă, difuză, fără soare direct — potrivită pentru birou.": "The windows face north: constant, diffuse light with no direct sun — ideal for a home office.",
"Ferestrele sunt orientate spre nord-est: soare dimineața devreme, răcoare în a doua parte a zilei.": "The windows face north-east: early morning sun and a cooler second half of the day.",
"Ferestrele sunt orientate spre est: soare de dimineață, până spre prânz.": "The windows face east: morning sun until around noon.",
"Ferestrele sunt orientate spre sud-est: soare de dimineață și până după-amiaza.": "The windows face south-east: sun from the morning into the afternoon.",
"Ferestrele sunt orientate spre sud: soare pe cea mai mare parte a zilei.": "The windows face south: sun for most of the day.",
"Ferestrele sunt orientate spre sud-vest: soare de la prânz până seara.": "The windows face south-west: sun from noon until the evening.",
"Ferestrele sunt orientate spre vest: soare de după-amiază, apusuri din living.": "The windows face west: afternoon sun and sunsets from the living room.",
"Ferestrele sunt orientate spre nord-vest: lumină caldă spre seară, răcoare dimineața.": "The windows face north-west: warm light towards the evening, cool mornings.",
"Este la parter, deci se intră direct, fără scări și fără lift.": "It is on the ground floor, so you walk straight in, with no stairs and no lift.",
"Este la parter, cu ieșire directă în curte, fără scări și fără lift.": "It is on the ground floor, with direct access to the garden, no stairs and no lift.",
"Primul etaj rămâne aproape de sol, dar deasupra nivelului aleilor.": "The first floor stays close to the ground, yet above the level of the paths.",
"Etajul al doilea are priveliște deschisă peste spațiile verzi dintre blocuri.": "The second floor has an open view over the green spaces between the buildings.",
"Ultimul etaj nu are apartament deasupra, deci nu se aud pași de la vecini.": "The top floor has no apartment above, so there are no footsteps from neighbours.",
"Balconul de {n} m² se deschide din zona de zi.": "The {n} m² balcony opens off the living area.",
"Curtea de {n} m² este în folosință exclusivă, cu pardoseală exterioară executată și priză proprie.": "The {n} m² garden is for exclusive use, with outdoor flooring laid and its own socket.",
"La demisol este disponibilă o boxă de depozitare, care se contractează separat.": "A storage room is available in the basement, contracted separately.",
"Preț pe metru pătrat": "Price per square metre",
"{n} €/m² · TVA inclus · avans {n}% la antecontract": "€{n}/m² · VAT included · {n}% deposit at the pre-sale agreement",
"{n} — Compartimentare": "{n} — Layout",
"Planul": "The apartment's",
"apartamentului": "floor plan",
"Planul compartimentării, cu suprafețele pe cameră. Cotele exacte se confirmă în anexa contractului.": "The layout plan, with the area of each room. Exact dimensions are confirmed in the contract annex.",
"{n} — Detalii": "{n} — Details",
"Fișa": "Unit",
"unității": "sheet",
"Datele din tabelul de vânzări, pentru această unitate.": "The data from the sales ledger for this unit.",
"Cod unitate": "Unit code",
"Bloc și etaj": "Building and floor",
"{n} · Etaj {n}": "{n} · Floor {n}",
"{n} · Parter": "{n} · Ground floor",
"Subterană": "Underground",
"La suprafață": "Surface level",
"{n} — Cartierul": "{n} — The neighbourhood",
"Ce urmează": "What lies",
"dincolo de ușă": "beyond the door",
"Ansamblul are {n} hectare, din care {n}% spațiu verde amenajat, în Iași, zona Păcurari.": "The development covers {n} hectares, {n}% of it landscaped green space, in Iași, Păcurari area.",
"Distanțe": "Distances",
"Pe traseu rutier": "By road",
"În incintă": "On site",
"Parc și spații verzi amenajate": "Park and landscaped green spaces",
"Piste de biciclete în incintă": "Cycle lanes on site",
"{n} de locuri de parcare": "{n} parking spaces",
"Harta zonei": "Area map",
"{n} — Costuri": "{n} — Costs",
"Cât ar însemna": "What it would",
"lunar": "cost monthly",
"Simulare orientativă de rată, pornind de la prețul acestei unități. Oferta finală se stabilește cu banca.": "An indicative mortgage simulation, based on this unit's price. The final offer is set with the bank.",
"Cât ar fi rata lunară": "What the monthly payment would be",
"Simulare orientativă pentru un credit ipotecar. Nu este o ofertă de creditare.": "An indicative simulation for a mortgage. It is not a credit offer.",
"Avans": "Deposit",
"Dobândă anuală": "Annual interest rate",
"Perioadă": "Term",
"Sumă finanțată": "Amount financed",
"Diferența dintre preț și avans.": "The difference between the price and the deposit.",
"Rată lunară": "Monthly payment",
"Cost total": "Total cost",
"Discută cu un consultant": "Talk to a consultant",
"Calculul folosește formula de anuitate și nu include comisioane, asigurări sau taxe notariale. Dobânda reală depinde de bancă și de profilul tău.": "The calculation uses the annuity formula and does not include fees, insurance or notary costs. The actual interest rate depends on the bank and your profile.",
"Achiziție în scop investițional": "Buying as an investment",
"Estimare de randament și de amortizare, pornind de la prețul acestei unități și de la chiriile practicate în zona Păcurari.": "A yield and payback estimate, based on this unit's price and the rents charged in the Păcurari area.",
"similare": "similar",
"Apartamente similare": "Similar apartments",
"Aceeași compartimentare, la alt etaj sau în alt bloc, cu prețuri apropiate.": "The same layout, on another floor or in another building, at similar prices.",
"Calculator de randament": "Yield calculator",
"Ferestrele sunt orientate spre": "The windows face",
}

# Sabloane cu expresii regulate pentru titlurile si descrierile paginilor de unitate.
# Se aplica pe textul normalizat (numerele raman in text); grupurile se refolosesc.
_OR = {"nord": "north", "nord-est": "north-east", "est": "east", "sud-est": "south-east",
       "sud": "south", "sud-vest": "south-west", "vest": "west", "nord-vest": "north-west"}
_OR_RX = "(" + "|".join(sorted(_OR, key=len, reverse=True)) + ")"


def _orient(m):
    return _OR[m]


REGULI = [
    # <title>
    (r"(C\d+-(?:E\d+|P)(?:-\d+)?) — apartament (\d+) (?:camere|cameră) ([\d,]+) m², blocul (\d+) \| Emerald City",
     r"\1 — \2-room apartment, \3 m², building \4 | Emerald City"),
    # H1
    (r"Apartament (\d+) (?:camere|cameră), ([\d,]+) m² — blocul (\d+),? etaj (\d+)",
     r"\1-room apartment, \2 m² — building \3, floor \4"),
    (r"Apartament (\d+) (?:camere|cameră), ([\d,]+) m² — blocul (\d+),? parter",
     r"\1-room apartment, \2 m² — building \3, ground floor"),
    # meta description
    (r"Apartamentul (C\d+-E\d+(?:-\d+)?): (\d+) (?:camere|cameră), ([\d,]+) m², blocul (\d+),? etaj (\d+),? orientare " + _OR_RX + r"\. ([\d.]+) €, predare la cheie, în Iași, zona Păcurari\.",
     lambda m: f"Apartment {m.group(1)}: {m.group(2)}-room, {m.group(3)} m², building {m.group(4)}, floor {m.group(5)}, facing {_OR[m.group(6)]}. €{m.group(7)}, turnkey handover, in Iași, Păcurari area."),
    (r"Apartamentul (C\d+-P(?:-\d+)?): (\d+) (?:camere|cameră), ([\d,]+) m², blocul (\d+),? parter, orientare " + _OR_RX + r"\. ([\d.]+) €, predare la cheie, în Iași, zona Păcurari\.",
     lambda m: f"Apartment {m.group(1)}: {m.group(2)}-room, {m.group(3)} m², building {m.group(4)}, ground floor, facing {_OR[m.group(5)]}. €{m.group(6)}, turnkey handover, in Iași, Păcurari area."),
]
