"""
Immobilien-Such-Agent – Off-Market Parzellen in Kanton Bern.

Sucht nach alten EFH auf großen Parzellen (900-2000 m²), die von MFH umgeben sind.
Ziel: Direktkontakt mit Eigentümern vor dem Verkaufsentscheid.
"""

import os
from .base import BaseAgent
from tools import geogis_be


SYSTEM_PROMPT = """Du bist ein Immobilien-Analyse-Agent, spezialisiert auf Off-Market
Entwicklungsgrundstücke in Kanton Bern, Schweiz.

Deine Aufgabe:
1. Suche in angegebenen Gemeinden nach alten Einfamilienhäusern (EFH, Baujahr < 1985)
2. Prüfe ob die Parzelle 900-2000 m² gross ist
3. Prüfe ob die Umgebung zu ≥60% mit Mehrfamilienhäusern (MFH) bebaut ist
4. Prüfe ob das Gelände flach ist (Hangneigung < 15%)
5. Prüfe ob die Parzelle gut erschlossen ist (Strasse vorhanden)
6. Für qualifizierte Parzellen: Analysiere das Baureglement
7. Erstelle einen detaillierten Report mit Grundbuch-Link für direkte Eigentümerkontakt

Sei systematisch, präzise und erkläre deine Bewertung klar auf Deutsch.
Fokus: Parzellen mit hohem Nachverdichtungs-Potenzial für den Auftraggeber."""

TOOLS = [
    {
        "name": "search_efh_buildings",
        "description": "Sucht alte EFH-Gebäude (Baujahr < 1985) in einer Gemeinde über das GWR.",
        "input_schema": {
            "type": "object",
            "properties": {
                "gemeinde": {"type": "string", "description": "Gemeindename, z.B. 'Köniz'"},
                "max_baujahr": {"type": "integer", "description": "Maximales Baujahr (Standard: 1985)"},
            },
            "required": ["gemeinde"],
        },
    },
    {
        "name": "analyze_parcel",
        "description": "Vollständige Analyse einer Parzelle: Fläche, MFH-Umgebung, Hangneigung, Erschliessung, Bauzone.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Breitengrad (WGS84)"},
                "lng": {"type": "number", "description": "Längengrad (WGS84)"},
                "gemeinde": {"type": "string"},
                "address": {"type": "string"},
                "baujahr": {"type": "integer"},
            },
            "required": ["lat", "lng", "gemeinde", "address", "baujahr"],
        },
    },
    {
        "name": "get_grundbuch_info",
        "description": "Erstellt Link zum Berner Grundbuch für Eigentümer-Abfrage (manuelle Abfrage nötig).",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lng": {"type": "number"},
                "gemeinde": {"type": "string"},
            },
            "required": ["lat", "lng", "gemeinde"],
        },
    },
]


def _search_efh_buildings(gemeinde: str, max_baujahr: int = 1985) -> list[dict]:
    return geogis_be.search_gwr_buildings(gemeinde, gkat=geogis_be.GKAT_EFH, max_year=max_baujahr)


def _analyze_parcel(lat: float, lng: float, gemeinde: str, address: str, baujahr: int) -> dict:
    return geogis_be.analyze_parcel(lat, lng, gemeinde, address, baujahr)


def _get_grundbuch_info(lat: float, lng: float, gemeinde: str) -> dict:
    return geogis_be.get_parcel_grundbuch_link(lat, lng, gemeinde)


class RealEstateAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            tool_handlers={
                "search_efh_buildings": _search_efh_buildings,
                "analyze_parcel": _analyze_parcel,
                "get_grundbuch_info": _get_grundbuch_info,
            },
        )

    def search_in_municipalities(self, municipalities: list[str] | None = None) -> str:
        if not municipalities:
            env_val = os.environ.get("RE_MUNICIPALITIES", "")
            municipalities = [m.strip() for m in env_val.split(",") if m.strip()] if env_val else []

        if not municipalities:
            return "Keine Gemeinden konfiguriert. Bitte RE_MUNICIPALITIES in .env setzen."

        gemeinden_str = ", ".join(municipalities)
        min_sqm = os.environ.get("RE_MIN_PLOT_SQM", "900")
        max_sqm = os.environ.get("RE_MAX_PLOT_SQM", "2000")

        prompt = f"""Analysiere folgende Gemeinden in Kanton Bern nach Entwicklungs-Parzellen:
Gemeinden: {gemeinden_str}
Parzellegrösse: {min_sqm}–{max_sqm} m²
Gebäudetyp: Altes EFH (Baujahr < 1985)
Umgebung: Mindestens 60% MFH im 200m Radius
Topographie: Hangneigung < 15%, gut erschlossen

Gehe systematisch vor:
1. Suche EFH-Gebäude in jeder Gemeinde
2. Analysiere die vielversprechendsten Parzellen (max. 5 pro Gemeinde)
3. Für qualifizierte Parzellen: hole Grundbuch-Info
4. Erstelle abschliessend einen übersichtlichen Report aller Funde

Priorisiere Parzellen mit dem höchsten Nachverdichtungs-Potenzial."""

        return self.run(prompt)
