#!/usr/bin/env python3
"""
Firmennetzwerk AI-Agenten System
=================================
Administrator koordiniert:
  - Immobilien-Agent: Off-Market Parzellen-Suche, Kanton Bern
  - Content-Agent:    Higgsfield + Instagram Content-Produktion

Verwendung:
  python main.py                          # Interaktiver Modus
  python main.py "Suche Parzellen in Köniz"
  python main.py "Poste Video über Immobilien auf Instagram"
  python main.py --immobilien Köniz Ostermundigen
  python main.py --baureglement "Köniz" "W3" 1200
  python main.py --content "Nachhaltiges Bauen" --type image
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# .env laden (aus demselben Verzeichnis wie main.py)
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Anthropic Key prüfen
if not os.environ.get("ANTHROPIC_API_KEY"):
    print("FEHLER: ANTHROPIC_API_KEY nicht gesetzt.")
    print("Kopiere .env.example zu .env und trage deinen API-Key ein.")
    sys.exit(1)

from agents import AdministratorAgent
from agents.real_estate_agent import RealEstateAgent
from agents.building_regulation_agent import BuildingRegulationAgent
from agents.content_agent import ContentAgent


def print_banner():
    print("\n" + "=" * 60)
    print("  FIRMENNETZWERK AI-AGENTEN SYSTEM")
    print("  Immobilien · Content · Instagram")
    print("=" * 60)


def interactive_mode():
    """Interaktiver Chat-Modus mit dem Administrator-Agenten."""
    print_banner()
    print("\nBefehle:")
    print("  Natürlichsprachige Eingabe (Deutsch)")
    print("  'exit' oder 'quit' zum Beenden")
    print("  'hilfe' für Befehlsübersicht\n")

    admin = AdministratorAgent()

    while True:
        try:
            user_input = input("Sie: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAuf Wiedersehen!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "beenden"):
            print("Auf Wiedersehen!")
            break

        if user_input.lower() in ("hilfe", "help", "?"):
            print_help()
            continue

        print("\nAgent arbeitet...\n")
        try:
            result = admin.run(user_input)
            print(f"Agent: {result}\n")
        except Exception as e:
            print(f"Fehler: {e}\n")


def print_help():
    print("""
BEFEHLSBEISPIELE:
  Immobilien:
    "Suche Parzellen in Köniz und Ostermundigen"
    "Analysiere das Baureglement von Muri bei Bern, Zone W3"
    "Finde Entwicklungsgrundstücke mit hohem Potenzial in Kanton Bern"

  Content:
    "Erstelle ein Instagram-Reel über nachhaltiges Bauen"
    "Poste ein Bild mit dem Thema Stadtentwicklung Bern"
    "Zeige meine letzten Instagram-Posts"
    "Wie viele Follower hat mein Account?"
""")


def main():
    args = sys.argv[1:]

    if not args:
        interactive_mode()
        return

    # --immobilien [gemeinde1] [gemeinde2] ...
    if args[0] == "--immobilien":
        municipalities = args[1:] if len(args) > 1 else None
        agent = RealEstateAgent()
        print_banner()
        print(f"\nImmobilien-Suche startet...")
        if municipalities:
            print(f"Gemeinden: {', '.join(municipalities)}\n")
        result = agent.search_in_municipalities(municipalities)
        print(result)
        return

    # --baureglement <gemeinde> [zone] [parcel_sqm]
    if args[0] == "--baureglement":
        if len(args) < 2:
            print("Verwendung: python main.py --baureglement <Gemeinde> [Zone] [Parzelle_m2]")
            sys.exit(1)
        gemeinde = args[1]
        zone = args[2] if len(args) > 2 else ""
        sqm = float(args[3]) if len(args) > 3 else 1200.0
        agent = BuildingRegulationAgent()
        print_banner()
        print(f"\nBaureglement-Analyse: {gemeinde}, Zone {zone or 'unbekannt'}, {sqm} m²\n")
        result = agent.analyze(gemeinde, zone, sqm)
        print(result)
        return

    # --content <thema> [--type video|image]
    if args[0] == "--content":
        if len(args) < 2:
            print("Verwendung: python main.py --content <Thema> [--type video|image]")
            sys.exit(1)
        topic_parts = []
        content_type = "video"
        i = 1
        while i < len(args):
            if args[i] == "--type" and i + 1 < len(args):
                content_type = args[i + 1]
                i += 2
            else:
                topic_parts.append(args[i])
                i += 1
        topic = " ".join(topic_parts)
        agent = ContentAgent()
        print_banner()
        print(f"\nContent-Produktion: '{topic}' ({content_type})\n")
        result = agent.create_and_post(topic, content_type)
        print(result)
        return

    # Freier Text → Administrator
    user_input = " ".join(args)
    print_banner()
    print(f"\nBefehl: {user_input}\n")
    admin = AdministratorAgent()
    result = admin.run(user_input)
    print(result)


if __name__ == "__main__":
    main()
