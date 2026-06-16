"""
Baureglement-Tools für Kanton Bern.

Workflow:
  1. Gemeinde-Baureglement via Web-Suche finden (DuckDuckGo → kein API-Key nötig)
  2. PDF oder HTML herunterladen
  3. Claude analysiert Dokument und extrahiert Bauparameter
  4. Entwicklungspotenzial berechnen
"""

import re
import time
import requests
import fitz  # PyMuPDF
import anthropic
from bs4 import BeautifulSoup


DDGO_URL = "https://html.duckduckgo.com/html/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RealEstateBot/1.0)"}


def _ddgo_search(query: str, max_results: int = 5) -> list[dict]:
    """DuckDuckGo HTML-Suche (kein API-Key erforderlich)."""
    try:
        resp = requests.post(
            DDGO_URL,
            data={"q": query, "kl": "ch-de"},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        results = []
        for a in soup.select(".result__a")[:max_results]:
            href = a.get("href", "")
            title = a.get_text(strip=True)
            if href.startswith("http"):
                results.append({"title": title, "url": href})
        return results
    except Exception as e:
        return [{"error": str(e)}]


def find_baureglement_url(gemeinde: str) -> dict:
    """
    Sucht URL des Baureglements für eine Gemeinde in Kanton Bern.
    Probiert mehrere Suchterme und bevorzugt PDF-Links.
    """
    queries = [
        f"Baureglement {gemeinde} Kanton Bern PDF",
        f"Zonenreglement {gemeinde} BE Bauverwaltung",
        f"site:{gemeinde.lower().replace(' ', '-')}.ch Baureglement",
    ]

    for query in queries:
        results = _ddgo_search(query)
        time.sleep(1)

        for r in results:
            url = r.get("url", "")
            title = r.get("title", "").lower()
            if not url:
                continue
            if ".pdf" in url.lower() and any(kw in title for kw in ["baureglement", "zonenreglement", "bau"]):
                return {"url": url, "type": "pdf", "title": r.get("title"), "gemeinde": gemeinde}
            if any(kw in title for kw in ["baureglement", "zonenreglement"]):
                return {"url": url, "type": "html", "title": r.get("title"), "gemeinde": gemeinde}

    return {"url": None, "error": f"Kein Baureglement für {gemeinde} gefunden", "gemeinde": gemeinde}


def download_document_text(url: str) -> str:
    """Lädt PDF oder HTML herunter und gibt Rohtext zurück."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")

        if "pdf" in content_type or url.lower().endswith(".pdf"):
            doc = fitz.open(stream=resp.content, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text[:50_000]  # Max 50k Zeichen für Claude

        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)[:50_000]

    except Exception as e:
        return f"Fehler beim Herunterladen: {str(e)}"


def extract_regulations_with_ai(
    document_text: str,
    gemeinde: str,
    zone: str = "",
) -> dict:
    """
    Nutzt Claude um Bauparameter aus dem Reglement-Text zu extrahieren.
    Gibt strukturiertes Dict mit allen relevanten Werten zurück.
    """
    client = anthropic.Anthropic()

    system = """Du bist ein Schweizer Baurechts-Experte. Analysiere Baureglemente und Zonenpläne
    von Schweizer Gemeinden (Kanton Bern). Extrahiere präzise die baulichen Kennzahlen.
    Antworte immer auf Deutsch. Wenn ein Wert nicht gefunden wird, setze null."""

    prompt = f"""Analysiere dieses Baureglement für Gemeinde {gemeinde}, Zone: {zone or "unbekannt"}.

Extrahiere folgende Werte als strukturierte JSON-ähnliche Antwort:

1. Geschosse (max. Anzahl Vollgeschosse)
2. Gebäudehöhe (Traufhöhe und/oder Firsthöhe in Metern)
3. Gebäudelänge (max. in Metern)
4. Gebäudefläche (max. Grundfläche in m²)
5. Grenzabstand klein (in Metern)
6. Grenzabstand gross (in Metern)
7. Gebäudeabstand (zwischen zwei Gebäuden, in Metern)
8. Ausnutzungsziffer AZ (dimensionslose Zahl, z.B. 0.8 oder 80%)
9. Grünziffer GZ (Anteil Grünfläche, z.B. 0.3 oder 30%)
10. Überbauungsziffer ÜZ (falls vorhanden)
11. GRZ / GFZ (falls DE-Normen verwendet)
12. Schutzgebiete (Naturschutz, Grundwasser, Lärmzone, NNSS etc.)
13. Lärmempfindlichkeitsstufe (ES I-IV)
14. Besondere Vorschriften / Einschränkungen

DOKUMENT:
{document_text[:30_000]}

Antworte im Format:
ZONE: [Zonenbezeichnung]
GESCHOSSE: [Zahl oder Bereich]
TRAUFHÖHE: [x.x m]
FIRSTHÖHE: [x.x m]
GEBÄUDELÄNGE: [x m]
GEBÄUDEFLÄCHE: [x m²]
GRENZABSTAND_KLEIN: [x m]
GRENZABSTAND_GROSS: [x m]
GEBÄUDEABSTAND: [x m]
AUSNUTZUNGSZIFFER: [0.x]
GRÜNZIFFER: [0.x]
ÜBERBAUUNGSZIFFER: [0.x oder null]
SCHUTZGEBIETE: [Liste oder "keine"]
LÄRMZONE: [ES I/II/III/IV oder null]
BEMERKUNGEN: [wichtige Einschränkungen]"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text

        def extract_val(key: str, text: str):
            pattern = rf"{key}:\s*(.+)"
            m = re.search(pattern, text, re.IGNORECASE)
            return m.group(1).strip() if m else None

        return {
            "zone": extract_val("ZONE", raw),
            "geschosse": extract_val("GESCHOSSE", raw),
            "traufhoehe_m": extract_val("TRAUFHÖHE", raw),
            "firsthoehe_m": extract_val("FIRSTHÖHE", raw),
            "gebaeudelaenge_m": extract_val("GEBÄUDELÄNGE", raw),
            "gebaeudeflaeche_m2": extract_val("GEBÄUDEFLÄCHE", raw),
            "grenzabstand_klein_m": extract_val("GRENZABSTAND_KLEIN", raw),
            "grenzabstand_gross_m": extract_val("GRENZABSTAND_GROSS", raw),
            "gebaeudeabstand_m": extract_val("GEBÄUDEABSTAND", raw),
            "ausnutzungsziffer": extract_val("AUSNUTZUNGSZIFFER", raw),
            "gruenziffer": extract_val("GRÜNZIFFER", raw),
            "ueberbauungsziffer": extract_val("ÜBERBAUUNGSZIFFER", raw),
            "schutzgebiete": extract_val("SCHUTZGEBIETE", raw),
            "laermzone": extract_val("LÄRMZONE", raw),
            "bemerkungen": extract_val("BEMERKUNGEN", raw),
            "raw_response": raw,
            "source_gemeinde": gemeinde,
        }
    except Exception as e:
        return {"error": str(e), "source_gemeinde": gemeinde}


def calculate_development_potential(parcel_sqm: float, regulations: dict) -> dict:
    """
    Berechnet maximale Bruttogeschossfläche (BGF) basierend auf Parzellenfläche
    und Baureglement-Kennzahlen.
    """
    az_raw = regulations.get("ausnutzungsziffer")
    gz_raw = regulations.get("gruenziffer")
    geschosse_raw = regulations.get("geschosse")

    az = None
    if az_raw:
        m = re.search(r"[\d.]+", str(az_raw))
        if m:
            az = float(m.group())
            if az > 5:  # Prozentangabe → umrechnen
                az = az / 100

    gz = None
    if gz_raw:
        m = re.search(r"[\d.]+", str(gz_raw))
        if m:
            gz = float(m.group())
            if gz > 1:
                gz = gz / 100

    geschosse = None
    if geschosse_raw:
        m = re.search(r"\d+", str(geschosse_raw))
        if m:
            geschosse = int(m.group())

    max_bgf = round(parcel_sqm * az, 0) if az else None
    pflichtgruen_m2 = round(parcel_sqm * gz, 0) if gz else None
    nutzbare_flaeche = round(parcel_sqm - (pflichtgruen_m2 or 0), 0)

    if max_bgf and max_bgf > 600:
        potenzial = "HOCH ★★★"
    elif max_bgf and max_bgf > 400:
        potenzial = "MITTEL ★★☆"
    elif max_bgf:
        potenzial = "GERING ★☆☆"
    else:
        potenzial = "UNBEKANNT (AZ fehlt)"

    return {
        "parcel_sqm": parcel_sqm,
        "ausnutzungsziffer": az,
        "max_bgf_m2": max_bgf,
        "gruenziffer": gz,
        "pflichtgruen_m2": pflichtgruen_m2,
        "nutzbare_grundflaeche_m2": nutzbare_flaeche,
        "geschosse": geschosse,
        "entwicklungspotenzial": potenzial,
    }
