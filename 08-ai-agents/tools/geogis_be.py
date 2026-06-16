"""
GeoGIS Tools für Kanton Bern – Parzellen-Suche via öffentliche Schweizer Geodaten.

Datenquellen:
  - api3.geo.admin.ch  : Swisstopo (Bundesgeoddaten, kostenlos)
  - GWR-API            : Gebäude- und Wohnungsregister (BFS)
  - Overpass API       : OpenStreetMap für Umgebungsanalyse
  - geodesy.geo.admin.ch : Koordinatentransformation LV95 ↔ WGS84
"""

import math
import time
import requests

SWISSTOPO_BASE = "https://api3.geo.admin.ch/rest/services"
GWR_LAYER = "ch.bfs.gebaeude_wohnungs_register"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
REFRAME_URL = "https://geodesy.geo.admin.ch/reframe/lv95towgs84"
HEIGHT_URL = f"{SWISSTOPO_BASE}/height"
ZONE_LAYER = "ch.are.bauzonen"

BERN_CANTON_BBOX_WGS84 = {
    "min_lng": 6.86, "min_lat": 46.32,
    "max_lng": 8.57, "max_lat": 47.30,
}

GKAT_EFH = 1021


def lv95_to_wgs84(east: float, north: float) -> tuple[float, float]:
    """Koordinatentransformation LV95 (EPSG:2056) → WGS84 via Swisstopo Reframe API."""
    resp = requests.get(REFRAME_URL, params={"east": east, "north": north, "format": "json"}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return float(data["latitude"]), float(data["longitude"])


def get_elevation(lat: float, lng: float) -> float:
    """Höhe über Meer in Metern via Swisstopo DHM."""
    resp = requests.get(
        HEIGHT_URL,
        params={"easting": lng, "northing": lat, "sr": 4326},
        timeout=10,
    )
    resp.raise_for_status()
    return float(resp.json().get("height", 0))


def calculate_slope_percent(lat: float, lng: float, offset_deg: float = 0.001) -> float:
    """
    Schätzt Hangneigung in % durch Höhendifferenz über 4 Messpunkte.
    offset_deg ≈ 80m in CH-Mittelland.
    """
    try:
        h_center = get_elevation(lat, lng)
        h_north  = get_elevation(lat + offset_deg, lng)
        h_south  = get_elevation(lat - offset_deg, lng)
        h_east   = get_elevation(lat, lng + offset_deg)
        h_west   = get_elevation(lat, lng - offset_deg)

        dist_m = offset_deg * 111_000
        dz_ns = abs(h_north - h_south) / (2 * dist_m) * 100
        dz_ew = abs(h_east  - h_west)  / (2 * dist_m) * 100
        return round(math.sqrt(dz_ns**2 + dz_ew**2), 1)
    except Exception:
        return -1.0


def analyze_surroundings(lat: float, lng: float, radius_m: int = 200) -> dict:
    """
    Analysiert Bebauung im Umkreis via Overpass API (OpenStreetMap).
    Zählt Mehrfamilienhäuser (building:levels >= 3) und Gesamtgebäude.
    """
    query = f"""
    [out:json][timeout:25];
    (
      way["building"](around:{radius_m},{lat},{lng});
      relation["building"](around:{radius_m},{lat},{lng});
    );
    out body;
    """
    try:
        resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=30)
        resp.raise_for_status()
        elements = resp.json().get("elements", [])

        total = len(elements)
        mfh_count = 0
        for el in elements:
            tags = el.get("tags", {})
            levels = tags.get("building:levels", "0")
            try:
                if int(levels) >= 3:
                    mfh_count += 1
                    continue
            except ValueError:
                pass
            btype = tags.get("building", "")
            if btype in ("apartments", "residential") and int(levels or 1) >= 2:
                mfh_count += 1

        mfh_ratio = round(mfh_count / total * 100, 1) if total > 0 else 0
        return {
            "total_buildings": total,
            "mfh_count": mfh_count,
            "mfh_ratio_percent": mfh_ratio,
            "qualifies": mfh_ratio >= 60 and total >= 5,
        }
    except Exception as e:
        return {"error": str(e), "qualifies": False}


def check_road_access(lat: float, lng: float) -> dict:
    """Distanz zur nächsten Strasse in Metern via Overpass API."""
    query = f"""
    [out:json][timeout:15];
    way["highway"~"residential|secondary|primary|tertiary|unclassified"](around:100,{lat},{lng});
    out body;
    """
    try:
        resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=20)
        resp.raise_for_status()
        elements = resp.json().get("elements", [])
        accessible = len(elements) > 0
        return {
            "road_found_within_100m": accessible,
            "qualifies": accessible,
        }
    except Exception as e:
        return {"error": str(e), "qualifies": False}


def search_gwr_buildings(gemeinde: str, gkat: int = GKAT_EFH, max_year: int = 1985) -> list[dict]:
    """
    Sucht Gebäude im GWR (Gebäude- und Wohnungsregister) nach Gemeinde und Typ.
    GKAT 1021 = Einfamilienhaus, GBAUJ = Baujahr.
    """
    url = f"{SWISSTOPO_BASE}/ech/MapServer/{GWR_LAYER}/find"
    params = {
        "searchText": gemeinde,
        "searchField": "GDENAME",
        "contains": "true",
        "lang": "de",
        "returnGeometry": "true",
        "sr": "4326",
    }
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        results = resp.json().get("results", [])

        buildings = []
        for r in results:
            attrs = r.get("attributes", {})
            gkat_val = attrs.get("GKAT")
            gbauj_val = attrs.get("GBAUJ")

            if gkat_val != gkat:
                continue
            if gbauj_val and int(gbauj_val) >= max_year:
                continue

            geom = r.get("geometry", {})
            buildings.append({
                "egid": attrs.get("EGID"),
                "address": f"{attrs.get('STRNAME', '')} {attrs.get('DEINR', '')}, {attrs.get('PLZ4', '')} {attrs.get('GDENAME', '')}",
                "gemeinde": attrs.get("GDENAME"),
                "baujahr": gbauj_val,
                "lat": geom.get("y"),
                "lng": geom.get("x"),
                "gkat": gkat_val,
            })
        return buildings
    except Exception as e:
        return [{"error": str(e)}]


def get_parcel_area(lat: float, lng: float) -> dict:
    """
    Versucht Parzellfläche via Swisstopo Identify Service zu ermitteln.
    Schicht: ch.swisstopo-vd.amtliche-vermessung (kantonale AV-Daten).
    """
    url = f"{SWISSTOPO_BASE}/api/MapServer/identify"
    params = {
        "geometry": f"{lng},{lat}",
        "geometryType": "esriGeometryPoint",
        "imageDisplay": "1,1,96",
        "mapExtent": f"{lng-0.001},{lat-0.001},{lng+0.001},{lat+0.001}",
        "tolerance": 10,
        "layers": "all:ch.swisstopo-vd.amtliche-vermessung",
        "lang": "de",
        "sr": 4326,
        "returnGeometry": "false",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        for r in results:
            attrs = r.get("attributes", {})
            area = attrs.get("flaechenmass") or attrs.get("area") or attrs.get("AREA")
            if area:
                return {"parcel_sqm": float(area), "source": "swisstopo-av"}
        return {"parcel_sqm": None, "source": "not_found"}
    except Exception as e:
        return {"parcel_sqm": None, "error": str(e)}


def get_zone_info(lat: float, lng: float) -> dict:
    """Ermittelt Bauzone (W2, W3, MZ etc.) via Swisstopo ch.are.bauzonen Layer."""
    url = f"{SWISSTOPO_BASE}/api/MapServer/identify"
    params = {
        "geometry": f"{lng},{lat}",
        "geometryType": "esriGeometryPoint",
        "imageDisplay": "1,1,96",
        "mapExtent": f"{lng-0.0005},{lat-0.0005},{lng+0.0005},{lat+0.0005}",
        "tolerance": 5,
        "layers": f"all:{ZONE_LAYER}",
        "lang": "de",
        "sr": 4326,
        "returnGeometry": "false",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if results:
            attrs = results[0].get("attributes", {})
            return {
                "zone_name": attrs.get("label") or attrs.get("ART_TXT") or "unbekannt",
                "zone_code": attrs.get("ART") or attrs.get("ZONE_CODE") or "",
                "gemeinde": attrs.get("GEMEINDE") or attrs.get("GDE_NAME") or "",
                "found": True,
            }
        return {"zone_name": "keine Zone gefunden", "found": False}
    except Exception as e:
        return {"error": str(e), "found": False}


def get_parcel_grundbuch_link(lat: float, lng: float, gemeinde: str) -> dict:
    """Erstellt Link zum kantonalen Grundbuch Kanton Bern für manuelle Eigentümer-Abfrage."""
    url = f"{SWISSTOPO_BASE}/api/MapServer/identify"
    params = {
        "geometry": f"{lng},{lat}",
        "geometryType": "esriGeometryPoint",
        "imageDisplay": "1,1,96",
        "mapExtent": f"{lng-0.001},{lat-0.001},{lng+0.001},{lat+0.001}",
        "tolerance": 10,
        "layers": "all:ch.swisstopo-vd.amtliche-vermessung",
        "lang": "de",
        "sr": 4326,
    }
    parcel_nr = "unbekannt"
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.ok:
            results = resp.json().get("results", [])
            if results:
                attrs = results[0].get("attributes", {})
                parcel_nr = attrs.get("nummer") or attrs.get("NUMMER") or attrs.get("egrid") or "unbekannt"
    except Exception:
        pass

    grundbuch_link = f"https://www.grundbuch.apps.be.ch/grundbuch/search?searchType=egrid&term={parcel_nr}"
    map_link = f"https://www.map.apps.be.ch/?lang=de&topic=oereb&X={lat}&Y={lng}&zoom=10"

    return {
        "parcel_number": parcel_nr,
        "grundbuch_be_link": grundbuch_link,
        "kanton_bern_map_link": map_link,
        "note": "Eigentümerabfrage erfordert manuelle Anmeldung im Grundbuch BE",
    }


def analyze_parcel(lat: float, lng: float, gemeinde: str, address: str, baujahr: int) -> dict:
    """
    Vollständige Analyse einer Parzelle: Fläche, Umgebung, Hangneigung, Erschliessung, Zone.
    Gibt Gesamt-Qualifizierungsstatus zurück.
    """
    time.sleep(0.5)  # Rate-Limiting für APIs

    parcel = get_parcel_area(lat, lng)
    surroundings = analyze_surroundings(lat, lng)
    slope = calculate_slope_percent(lat, lng)
    road = check_road_access(lat, lng)
    zone = get_zone_info(lat, lng)

    parcel_sqm = parcel.get("parcel_sqm")
    size_ok = (
        parcel_sqm is not None
        and 900 <= parcel_sqm <= 2000
    )

    qualifies = (
        (size_ok or parcel_sqm is None)  # wenn Fläche unbekannt: weiterführen
        and surroundings.get("qualifies", False)
        and (slope < 15 or slope == -1.0)
        and road.get("qualifies", False)
    )

    return {
        "address": address,
        "gemeinde": gemeinde,
        "baujahr": baujahr,
        "lat": lat,
        "lng": lng,
        "parcel_sqm": parcel_sqm,
        "size_ok": size_ok,
        "surroundings": surroundings,
        "slope_percent": slope,
        "road_access": road,
        "zone": zone,
        "qualifies": qualifies,
    }
