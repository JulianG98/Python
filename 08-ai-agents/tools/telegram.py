"""
Telegram Bot API Client.

Sendet Parzellen-Rapporte, Luftbilder (Swisstopo swissimage) und GPS-Pins.
Setup: Bot via @BotFather erstellen → Token in .env eintragen.
Chat-ID: Einmal /start an deinen Bot senden, dann:
  curl https://api.telegram.org/bot<TOKEN>/getUpdates
"""

import io
import os
import requests

TG_BASE = "https://api.telegram.org/bot"
SWISSTOPO_WMS = "https://wms.geo.admin.ch/"


def _creds() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN und TELEGRAM_CHAT_ID fehlen in .env")
    return token, chat_id


def send_message(text: str, parse_mode: str = "Markdown") -> dict:
    """Sendet eine Textnachricht via Telegram."""
    token, chat_id = _creds()
    resp = requests.post(
        f"{TG_BASE}{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def send_photo_bytes(image_bytes: bytes, caption: str = "") -> dict:
    """Sendet Bild-Bytes direkt als Telegram-Foto."""
    token, chat_id = _creds()
    resp = requests.post(
        f"{TG_BASE}{token}/sendPhoto",
        data={"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"},
        files={"photo": ("karte.jpg", io.BytesIO(image_bytes), "image/jpeg")},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def send_location(lat: float, lng: float) -> dict:
    """Sendet einen GPS-Pin (klickbares Standort-Icon in Telegram)."""
    token, chat_id = _creds()
    resp = requests.post(
        f"{TG_BASE}{token}/sendLocation",
        json={"chat_id": chat_id, "latitude": lat, "longitude": lng},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def get_swisstopo_aerial(lat: float, lng: float, zoom_m: float = 300.0) -> bytes:
    """
    Lädt Luftbild vom Swisstopo WMS (ch.swisstopo.swissimage).
    zoom_m = halbe Seitenlänge in Metern (Standard: 300m → 600m × 600m Ausschnitt).
    Gibt JPEG-Bytes zurück.
    """
    deg_per_m_lat = 1 / 111_000
    deg_per_m_lng = 1 / (111_000 * __import__("math").cos(__import__("math").radians(lat)))
    offset_lat = zoom_m * deg_per_m_lat
    offset_lng = zoom_m * deg_per_m_lng

    bbox = f"{lng - offset_lng},{lat - offset_lat},{lng + offset_lng},{lat + offset_lat}"

    params = {
        "SERVICE": "WMS",
        "REQUEST": "GetMap",
        "VERSION": "1.1.1",
        "LAYERS": "ch.swisstopo.swissimage",
        "STYLES": "default",
        "FORMAT": "image/jpeg",
        "SRS": "EPSG:4326",
        "BBOX": bbox,
        "WIDTH": "900",
        "HEIGHT": "900",
    }
    resp = requests.get(SWISSTOPO_WMS, params=params, timeout=30)
    resp.raise_for_status()
    if "image" not in resp.headers.get("content-type", ""):
        raise RuntimeError(f"Swisstopo WMS gab kein Bild zurück: {resp.text[:200]}")
    return resp.content


def send_parcel_rapport(parcel: dict, regulations: dict | None = None, potential: dict | None = None) -> list[dict]:
    """
    Kompletter Parzellen-Rapport via Telegram:
      1. Luftbild (Swisstopo aerial)
      2. GPS-Pin
      3. Formatierter Text-Rapport (Markdown)

    parcel: Ergebnis aus geogis_be.analyze_parcel()
    regulations: Ergebnis aus building_regs.extract_regulations_with_ai()
    potential: Ergebnis aus building_regs.calculate_development_potential()
    """
    results = []
    lat = parcel.get("lat")
    lng = parcel.get("lng")

    # 1. Luftbild senden
    try:
        aerial_bytes = get_swisstopo_aerial(lat, lng)
        address = parcel.get("address", "")
        caption = f"📍 *{address}*\nSwisstopo Luftbild | Parzelle {parcel.get('parcel_sqm', '?')} m²"
        results.append(send_photo_bytes(aerial_bytes, caption))
    except Exception as e:
        results.append({"error": f"Luftbild fehlgeschlagen: {e}"})

    # 2. GPS-Pin senden
    if lat and lng:
        try:
            results.append(send_location(lat, lng))
        except Exception as e:
            results.append({"error": f"Location fehlgeschlagen: {e}"})

    # 3. Text-Rapport senden
    try:
        rapport = _format_rapport(parcel, regulations, potential)
        results.append(send_message(rapport))
    except Exception as e:
        results.append({"error": f"Rapport fehlgeschlagen: {e}"})

    return results


def _format_rapport(parcel: dict, regulations: dict | None, potential: dict | None) -> str:
    """Erstellt formatierten Telegram-Rapport (Markdown)."""
    s = parcel.get("surroundings", {})
    r = parcel.get("road_access", {})
    z = parcel.get("zone", {})

    # Header
    text = f"""🏠 *PARZELLEN-ANALYSE – KANTON BERN*
━━━━━━━━━━━━━━━━━━━━━━━

📍 *{parcel.get('address', 'Adresse unbekannt')}*
Gemeinde: {parcel.get('gemeinde', '—')}
Koordinaten: `{parcel.get('lat', '—')}, {parcel.get('lng', '—')}`

*🏗 GEBÄUDE*
• Baujahr: {parcel.get('baujahr', '—')}
• Parzellegrösse: {parcel.get('parcel_sqm', 'nicht ermittelt')} m²

*🏙 UMGEBUNG*
• MFH-Anteil (200m): {s.get('mfh_ratio_percent', '—')}%  {'✅' if s.get('qualifies') else '❌'}
• Gebäude im Umkreis: {s.get('total_buildings', '—')} ({s.get('mfh_count', '—')} MFH)
• Hangneigung: {parcel.get('slope_percent', '—')}%  {'✅' if parcel.get('slope_percent', 99) < 15 else '❌'}
• Strassenanbindung: {'✅ vorhanden' if r.get('qualifies') else '❌ nicht gefunden'}
• Bauzone: {z.get('zone_name', '—')}"""

    if regulations:
        text += f"""

*📋 BAUREGLEMENT ({parcel.get('gemeinde', '')})*
• Geschosse: {regulations.get('geschosse', '—')}
• Traufhöhe: {regulations.get('traufhoehe_m', '—')}
• Firsthöhe: {regulations.get('firsthoehe_m', '—')}
• Gebäudelänge: {regulations.get('gebaeudelaenge_m', '—')}
• Grenzabstand (klein): {regulations.get('grenzabstand_klein_m', '—')}
• Grenzabstand (gross): {regulations.get('grenzabstand_gross_m', '—')}
• Ausnutzungsziffer: {regulations.get('ausnutzungsziffer', '—')}
• Grünziffer: {regulations.get('gruenziffer', '—')}
• Schutzgebiete: {regulations.get('schutzgebiete', '—')}"""

    if potential:
        emoji = "🟢" if "HOCH" in str(potential.get("entwicklungspotenzial", "")) else "🟡"
        text += f"""

*📈 ENTWICKLUNGSPOTENZIAL*
{emoji} *{potential.get('entwicklungspotenzial', '—')}*
• Max. BGF: {potential.get('max_bgf_m2', '—')} m²
• Pflichtgrünfläche: {potential.get('pflichtgruen_m2', '—')} m²"""

    # Grundbuch-Link
    text += f"""

*🔑 EIGENTÜMER-ABFRAGE*
[Grundbuch Kanton Bern öffnen](https://www.grundbuch.apps.be.ch)
[Karte Kanton Bern](https://www.map.apps.be.ch/?lang=de&topic=oereb)

_Für Direktkontakt mit Eigentümer → Grundbuchabfrage erforderlich_"""

    return text


def send_error(message: str) -> dict:
    """Sendet Fehler-Benachrichtigung via Telegram."""
    return send_message(f"⚠️ *Fehler im Agenten-System*\n\n{message}")


def send_status(message: str) -> dict:
    """Sendet Status-Update via Telegram."""
    return send_message(f"ℹ️ {message}")
