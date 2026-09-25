# -*- coding: utf-8 -*-
"""
Limbile site-ului: harta de directoare RO -> EN si cateva ajutoare comune
generatorului, traducatorului si exportului.
"""

DOMENIU = "https://emerald-city.ro"

# directoare cu nume tradus; tot ce nu apare aici (codurile de unitati,
# assets, brand) ramane la fel
SLUGURI = {
    "apartamente-iasi": "apartments-iasi",
    "disponibilitate": "availability",
    "apartamente-1-camera": "1-room-apartments",
    "apartamente-2-camere": "2-room-apartments",
    "apartamente-3-camere": "3-room-apartments",
    "tip-1a": "type-1a", "tip-2a": "type-2a", "tip-2b": "type-2b",
    "tip-3a": "type-3a", "tip-3b": "type-3b",
    "apartamente-iasi-pacurari": "location-iasi-pacurari",
    "investitie-apartamente-iasi": "investment-apartments-iasi",
    "despre-emerald-city": "about-emerald-city",
    "despre-dezvoltator": "developer",
    "stadiu-lucrari": "construction-progress",
    "aparitii-presa": "press",
    "finisaje": "finishes",
    "proiect": "project",
    "contact": "contact",
    "programare-vizionare": "book-a-viewing",
    "compara": "compare",
    "termeni-si-conditii": "terms-and-conditions",
    "politica-de-confidentialitate": "privacy-policy",
    "politica-de-cookies": "cookie-policy",
    "informare-gdpr": "gdpr-notice",
}
SLUGURI_INV = {v: k for k, v in SLUGURI.items()}


def cale_en(canonic):
    """'apartamente-iasi/disponibilitate/' -> 'en/apartments-iasi/availability/'."""
    parti = [SLUGURI.get(p, p) for p in canonic.strip("/").split("/") if p]
    return "en/" + ("/".join(parti) + "/" if parti else "")


def cale_ro(cale_en_):
    parti = [SLUGURI_INV.get(p, p) for p in cale_en_.strip("/").split("/") if p]
    parti = parti[1:] if parti and parti[0] == "en" else parti
    return ("/".join(parti) + "/") if parti else ""


def hreflang(canonic):
    """Legaturile alternate pentru ambele versiuni; x-default este romana."""
    ro = f"{DOMENIU}/{canonic}"
    en = f"{DOMENIU}/{cale_en(canonic)}"
    return (f'<link rel="alternate" hreflang="ro" href="{ro}">\n'
            f'<link rel="alternate" hreflang="en" href="{en}">\n'
            f'<link rel="alternate" hreflang="x-default" href="{ro}">')


STEAG_RO = ('<svg viewBox="0 0 3 2" width="18" height="12" aria-hidden="true">'
            '<rect width="1" height="2" fill="#002B7F"/><rect x="1" width="1" height="2" fill="#FCD116"/>'
            '<rect x="2" width="1" height="2" fill="#CE1126"/></svg>')
STEAG_EN = ('<svg viewBox="0 0 60 30" width="18" height="12" aria-hidden="true">'
            '<clipPath id="ecuk"><path d="M0 0v30h60V0z"/></clipPath>'
            '<path d="M0 0v30h60V0z" fill="#012169"/>'
            '<path d="M0 0l60 30m0-30L0 30" stroke="#fff" stroke-width="6"/>'
            '<path d="M0 0l60 30m0-30L0 30" clip-path="url(#ecuk)" stroke="#C8102E" stroke-width="4"/>'
            '<path d="M30 0v30M0 15h60" stroke="#fff" stroke-width="10"/>'
            '<path d="M30 0v30M0 15h60" stroke="#C8102E" stroke-width="6"/></svg>')


def comutator(canonic, activ="ro"):
    """RO | EN in topbar, cu steaguri; legaturile sunt absolute."""
    ro = "/" + canonic
    en = "/" + cale_en(canonic)
    a_ro = ' class="is-on" aria-current="true"' if activ == "ro" else ""
    a_en = ' class="is-on" aria-current="true"' if activ == "en" else ""
    return (f'<span class="ec-lang" aria-label="Limba / Language">'
            f'<a href="{ro}" hreflang="ro" lang="ro"{a_ro} title="Română">{STEAG_RO}<span>RO</span></a>'
            f'<a href="{en}" hreflang="en" lang="en"{a_en} title="English">{STEAG_EN}<span>EN</span></a>'
            f'</span>')
