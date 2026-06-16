"""
Administrator-Agent – koordiniert Immobilien- und Content-Agent.

Empfängt Befehle in natürlicher Sprache (Deutsch) und leitet sie
an den richtigen Sub-Agenten weiter.
"""

import os
from .base import BaseAgent
from .real_estate_agent import RealEstateAgent
from .building_regulation_agent import BuildingRegulationAgent
from .content_agent import ContentAgent


SYSTEM_PROMPT = """Du bist der Administrator eines Firmennetzwerk-Agenten-Systems.
Du koordinierst zwei spezialisierte Sub-Agenten:

1. IMMOBILIEN-AGENT: Sucht Off-Market Entwicklungsparzellen in Kanton Bern (Schweiz)
   - Findet alte EFH auf grossen Parzellen (900-2000 m²) in MFH-Umgebungen
   - Analysiert Baureglement und Entwicklungspotenzial
   - Liefert Grundbuch-Links für Direktkontakt mit Eigentümern

2. CONTENT-AGENT: Erstellt KI-generierten Content für Instagram
   - Generiert Videos und Bilder via Higgsfield AI
   - Postet auf Instagram mit optimierten Captions und Hashtags

3. BAUREGLEMENT-AGENT: Analysiert spezifische Gemeinde-Baureglemente
   - Extrahiert Kennzahlen (AZ, GZ, Geschosse, Abstände etc.)
   - Berechnet Entwicklungspotenzial

Verstehe den Nutzer-Befehl und leite ihn an den richtigen Agenten weiter.
Antworte immer auf Deutsch. Gib klare, strukturierte Reports aus."""

TOOLS = [
    {
        "name": "call_real_estate_agent",
        "description": "Startet Immobilien-Suche in Kanton Bern. Optional: Liste von Gemeinden.",
        "input_schema": {
            "type": "object",
            "properties": {
                "instruction": {
                    "type": "string",
                    "description": "Detaillierter Auftrag für den Immobilien-Agenten",
                },
                "municipalities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optionale Liste von Gemeinden (leer = aus .env)",
                },
            },
            "required": ["instruction"],
        },
    },
    {
        "name": "call_building_regulation_agent",
        "description": "Analysiert Baureglement einer spezifischen Gemeinde.",
        "input_schema": {
            "type": "object",
            "properties": {
                "gemeinde": {"type": "string", "description": "Gemeindename in Kanton Bern"},
                "zone": {"type": "string", "description": "Bauzone, z.B. 'W3', 'MZ'"},
                "parcel_sqm": {"type": "number", "description": "Parzellenfläche in m²"},
            },
            "required": ["gemeinde"],
        },
    },
    {
        "name": "call_content_agent",
        "description": "Erstellt und postet Instagram-Content via Higgsfield AI.",
        "input_schema": {
            "type": "object",
            "properties": {
                "instruction": {
                    "type": "string",
                    "description": "Content-Auftrag, z.B. Thema, Stil, Zielgruppe",
                },
                "content_type": {
                    "type": "string",
                    "enum": ["video", "image"],
                    "description": "'video' für Reels, 'image' für Feed-Post",
                },
            },
            "required": ["instruction"],
        },
    },
]


def _call_real_estate(instruction: str, municipalities: list | None = None) -> str:
    agent = RealEstateAgent()
    if municipalities:
        return agent.search_in_municipalities(municipalities)
    return agent.run(instruction)


def _call_building_regulations(gemeinde: str, zone: str = "", parcel_sqm: float = 1200.0) -> str:
    agent = BuildingRegulationAgent()
    return agent.analyze(gemeinde, zone, parcel_sqm)


def _call_content(instruction: str, content_type: str = "video") -> str:
    agent = ContentAgent()
    return agent.create_and_post(instruction, content_type)


class AdministratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            tool_handlers={
                "call_real_estate_agent": lambda instruction, municipalities=None: _call_real_estate(instruction, municipalities),
                "call_building_regulation_agent": lambda gemeinde, zone="", parcel_sqm=1200.0: _call_building_regulations(gemeinde, zone, parcel_sqm),
                "call_content_agent": lambda instruction, content_type="video": _call_content(instruction, content_type),
            },
            max_iterations=10,
        )
