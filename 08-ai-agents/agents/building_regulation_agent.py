"""
Baureglement-Agent – analysiert Gemeinde-Baureglemente für Kanton Bern.

Findet das Baureglement online, extrahiert alle relevanten Kennzahlen
via Claude und berechnet das Entwicklungspotenzial.
"""

from .base import BaseAgent
from tools import building_regs


SYSTEM_PROMPT = """Du bist ein Baurechts-Experte für den Kanton Bern, Schweiz.

Deine Aufgabe:
1. Finde das Baureglement der angegebenen Gemeinde online
2. Extrahiere alle relevanten Bauparameter (Geschosse, Höhen, AZ, GZ, Abstände etc.)
3. Berechne das maximale Entwicklungspotenzial für die gegebene Parzellengrösse
4. Weise auf Schutzgebiete und Einschränkungen hin
5. Gib eine klare Einschätzung des Potenzials

Verwende Schweizer Bauterminologie (Ausnutzungsziffer, Grünziffer, etc.)
Antworte präzise und strukturiert auf Deutsch."""

TOOLS = [
    {
        "name": "find_baureglement",
        "description": "Sucht URL des Baureglements einer Berner Gemeinde via Web-Suche.",
        "input_schema": {
            "type": "object",
            "properties": {
                "gemeinde": {"type": "string", "description": "Name der Gemeinde in Kanton Bern"},
            },
            "required": ["gemeinde"],
        },
    },
    {
        "name": "download_and_read_document",
        "description": "Lädt PDF oder HTML-Dokument herunter und gibt den Textinhalt zurück.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL des Baureglements"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "extract_regulations",
        "description": "Extrahiert Bauparameter aus einem Reglement-Text via Claude AI.",
        "input_schema": {
            "type": "object",
            "properties": {
                "document_text": {"type": "string", "description": "Rohtext des Baureglements"},
                "gemeinde": {"type": "string"},
                "zone": {"type": "string", "description": "Bauzone, z.B. 'W3', 'MZ'"},
            },
            "required": ["document_text", "gemeinde"],
        },
    },
    {
        "name": "calculate_potential",
        "description": "Berechnet max. Bruttogeschossfläche und Entwicklungspotenzial.",
        "input_schema": {
            "type": "object",
            "properties": {
                "parcel_sqm": {"type": "number", "description": "Parzellenfläche in m²"},
                "regulations": {
                    "type": "object",
                    "description": "Extrahierte Bauparameter als Dict",
                },
            },
            "required": ["parcel_sqm", "regulations"],
        },
    },
]


class BuildingRegulationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            tool_handlers={
                "find_baureglement": lambda gemeinde: building_regs.find_baureglement_url(gemeinde),
                "download_and_read_document": lambda url: {"text": building_regs.download_document_text(url)},
                "extract_regulations": lambda document_text, gemeinde, zone="": building_regs.extract_regulations_with_ai(document_text, gemeinde, zone),
                "calculate_potential": lambda parcel_sqm, regulations: building_regs.calculate_development_potential(parcel_sqm, regulations),
            },
        )

    def analyze(self, gemeinde: str, zone: str, parcel_sqm: float) -> str:
        prompt = f"""Analysiere das Baureglement für:
Gemeinde: {gemeinde}
Zone: {zone}
Parzellengrösse: {parcel_sqm} m²

Schritte:
1. Finde das Baureglement der Gemeinde {gemeinde} online
2. Lade es herunter und lies den Inhalt
3. Extrahiere alle Bauparameter für Zone {zone}
4. Berechne das Entwicklungspotenzial für {parcel_sqm} m²
5. Erstelle einen strukturierten Report mit allen Kennzahlen"""

        return self.run(prompt)
