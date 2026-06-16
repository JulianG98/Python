"""
Higgsfield REST API Client für AI-gestützte Content-Generierung.
Dokumentation: https://higgsfield.ai (API-Key in .env erforderlich)
"""

import os
import time
import requests

HIGGSFIELD_BASE = "https://api.higgsfield.ai/v1"
POLL_INTERVAL = 5
MAX_POLL_ATTEMPTS = 60  # max 5 Minuten warten


def _get_headers() -> dict:
    api_key = os.environ.get("HIGGSFIELD_API_KEY", "")
    if not api_key:
        raise ValueError("HIGGSFIELD_API_KEY nicht gesetzt (siehe .env)")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def generate_image(prompt: str, width: int = 1080, height: int = 1080) -> dict:
    """
    Generiert ein Bild via Higgsfield API.
    Gibt job_id und output_url zurück (wartet auf Fertigstellung).
    """
    headers = _get_headers()
    payload = {
        "prompt": prompt,
        "width": width,
        "height": height,
    }
    resp = requests.post(
        f"{HIGGSFIELD_BASE}/generations/image",
        json=payload,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    job = resp.json()
    job_id = job.get("id") or job.get("job_id")

    if not job_id:
        return job  # Direkte Antwort ohne Job-Polling

    return _poll_job(job_id)


def generate_video(
    prompt: str,
    duration_sec: int = 5,
    aspect_ratio: str = "9:16",
) -> dict:
    """
    Generiert ein Video via Higgsfield API (async, wartet auf Ergebnis).
    aspect_ratio: '9:16' für Instagram Reels, '1:1' für Feed-Posts.
    """
    headers = _get_headers()
    payload = {
        "prompt": prompt,
        "duration": duration_sec,
        "aspect_ratio": aspect_ratio,
    }
    resp = requests.post(
        f"{HIGGSFIELD_BASE}/generations/video",
        json=payload,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    job = resp.json()
    job_id = job.get("id") or job.get("job_id")

    if not job_id:
        return job

    return _poll_job(job_id)


def _poll_job(job_id: str) -> dict:
    """Pollt Job-Status bis 'completed' oder 'failed'."""
    headers = _get_headers()
    for attempt in range(MAX_POLL_ATTEMPTS):
        time.sleep(POLL_INTERVAL)
        resp = requests.get(
            f"{HIGGSFIELD_BASE}/generations/{job_id}",
            headers=headers,
            timeout=15,
        )
        if not resp.ok:
            continue
        data = resp.json()
        status = data.get("status", "")

        if status == "completed":
            output_url = (
                data.get("output_url")
                or data.get("url")
                or data.get("result", {}).get("url")
            )
            return {
                "job_id": job_id,
                "status": "completed",
                "output_url": output_url,
                "data": data,
            }
        if status == "failed":
            return {"job_id": job_id, "status": "failed", "error": data.get("error")}

    return {"job_id": job_id, "status": "timeout", "error": "Job nach 5 Minuten nicht abgeschlossen"}


def list_recent_generations(limit: int = 10) -> dict:
    """Listet letzte Generierungen im Higgsfield-Account."""
    headers = _get_headers()
    resp = requests.get(
        f"{HIGGSFIELD_BASE}/generations",
        params={"limit": limit},
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
