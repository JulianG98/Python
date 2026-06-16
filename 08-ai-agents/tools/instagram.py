"""
Instagram Meta Graph API Client.
Voraussetzung: Instagram Business/Creator Account + Meta Graph API Access Token.
Dokumentation: https://developers.facebook.com/docs/instagram-api
"""

import os
import time
import requests

GRAPH_BASE = "https://graph.facebook.com/v19.0"


def _get_credentials() -> tuple[str, str]:
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    account_id = os.environ.get("INSTAGRAM_ACCOUNT_ID", "")
    if not token or not account_id:
        raise ValueError("INSTAGRAM_ACCESS_TOKEN und INSTAGRAM_ACCOUNT_ID müssen in .env gesetzt sein")
    return token, account_id


def create_media_container(
    media_url: str,
    caption: str,
    media_type: str = "IMAGE",
) -> dict:
    """
    Schritt 1: Media-Container erstellen.
    media_type: 'IMAGE', 'VIDEO', 'REELS'
    Gibt container_id zurück.
    """
    token, account_id = _get_credentials()
    payload = {
        "access_token": token,
        "caption": caption,
    }
    if media_type == "VIDEO" or media_type == "REELS":
        payload["media_type"] = "REELS"
        payload["video_url"] = media_url
    else:
        payload["image_url"] = media_url

    resp = requests.post(
        f"{GRAPH_BASE}/{account_id}/media",
        data=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    container_id = data.get("id")
    if not container_id:
        return {"error": "Kein Container-ID erhalten", "response": data}

    # Auf Container-Verarbeitung warten (besonders bei Videos)
    if media_type in ("VIDEO", "REELS"):
        _wait_for_container(container_id, token)

    return {"container_id": container_id, "status": "ready"}


def _wait_for_container(container_id: str, token: str, max_wait: int = 120):
    """Wartet bis der Media-Container verarbeitet ist."""
    for _ in range(max_wait // 5):
        time.sleep(5)
        resp = requests.get(
            f"{GRAPH_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=15,
        )
        if resp.ok:
            status = resp.json().get("status_code", "")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise RuntimeError(f"Media-Container Fehler: {resp.json()}")


def publish_post(container_id: str) -> dict:
    """
    Schritt 2: Container auf Instagram veröffentlichen.
    Gibt post_id zurück.
    """
    token, account_id = _get_credentials()
    resp = requests.post(
        f"{GRAPH_BASE}/{account_id}/media_publish",
        data={"creation_id": container_id, "access_token": token},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    post_id = data.get("id")
    return {
        "post_id": post_id,
        "status": "published",
        "instagram_url": f"https://www.instagram.com/p/{post_id}/" if post_id else None,
    }


def post_image(image_url: str, caption: str) -> dict:
    """Kombiniert create_media_container + publish_post für Bilder."""
    container = create_media_container(image_url, caption, "IMAGE")
    if "error" in container:
        return container
    return publish_post(container["container_id"])


def post_video(video_url: str, caption: str) -> dict:
    """Kombiniert create_media_container + publish_post für Videos (Reels)."""
    container = create_media_container(video_url, caption, "REELS")
    if "error" in container:
        return container
    return publish_post(container["container_id"])


def get_account_insights() -> dict:
    """Holt Account-Insights: Follower, Reichweite, Impressionen."""
    token, account_id = _get_credentials()
    resp = requests.get(
        f"{GRAPH_BASE}/{account_id}",
        params={
            "fields": "followers_count,media_count,name,username,biography",
            "access_token": token,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def get_recent_posts(limit: int = 10) -> dict:
    """Listet die letzten Posts des Instagram-Accounts."""
    token, account_id = _get_credentials()
    resp = requests.get(
        f"{GRAPH_BASE}/{account_id}/media",
        params={
            "fields": "id,caption,media_type,timestamp,like_count,comments_count,permalink",
            "limit": limit,
            "access_token": token,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
