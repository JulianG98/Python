"""
Content-Agent – Higgsfield AI Content-Generierung + Instagram-Posting.

Generiert Videos/Bilder via Higgsfield und veröffentlicht diese auf Instagram.
"""

from .base import BaseAgent
from tools import higgsfield, instagram


SYSTEM_PROMPT = """Du bist ein Social Media Content Manager, spezialisiert auf Instagram.

Deine Aufgaben:
1. Erstelle ansprechende, kreative Prompts für die Higgsfield AI Content-Generierung
2. Generiere Videos (bevorzugt für Reels, 9:16) oder Bilder je nach Bedarf
3. Verfasse passende Instagram-Captions mit relevanten Hashtags
4. Poste Content auf Instagram oder erstelle Posting-Plans

Stil-Richtlinien:
- Professionell aber nahbar
- Fokus auf visuelle Attraktivität
- Schweizerdeutsche Brands verwenden Hochdeutsch
- Hashtags: Mix aus Nischen- und Broad-Tags (max. 25)
- Call-to-Action in jeder Caption

Antworte auf Deutsch."""

TOOLS = [
    {
        "name": "generate_video",
        "description": "Generiert ein KI-Video via Higgsfield (async, wartet auf Fertigstellung). Gibt output_url zurück.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Detaillierter Video-Prompt auf Englisch"},
                "duration_sec": {"type": "integer", "description": "Dauer in Sekunden (3-15, Standard: 5)"},
                "aspect_ratio": {"type": "string", "description": "'9:16' für Reels, '1:1' für Feed, '16:9' für Landscape"},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "generate_image",
        "description": "Generiert ein KI-Bild via Higgsfield. Gibt output_url zurück.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Detaillierter Bild-Prompt auf Englisch"},
                "width": {"type": "integer", "description": "Breite in px (Standard: 1080)"},
                "height": {"type": "integer", "description": "Höhe in px (Standard: 1080)"},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "post_image_to_instagram",
        "description": "Postet ein Bild auf Instagram. media_url muss öffentlich zugänglich sein.",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_url": {"type": "string", "description": "Öffentliche URL des Bildes"},
                "caption": {"type": "string", "description": "Instagram Caption mit Hashtags"},
            },
            "required": ["image_url", "caption"],
        },
    },
    {
        "name": "post_video_to_instagram",
        "description": "Postet ein Video als Reel auf Instagram.",
        "input_schema": {
            "type": "object",
            "properties": {
                "video_url": {"type": "string", "description": "Öffentliche URL des Videos"},
                "caption": {"type": "string", "description": "Instagram Caption mit Hashtags"},
            },
            "required": ["video_url", "caption"],
        },
    },
    {
        "name": "get_account_insights",
        "description": "Holt Instagram-Account-Statistiken: Follower, Posts, Bio.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_recent_posts",
        "description": "Listet die letzten Instagram-Posts mit Likes und Kommentaren.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Anzahl Posts (Standard: 10)"},
            },
        },
    },
]


class ContentAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            tool_handlers={
                "generate_video": lambda prompt, duration_sec=5, aspect_ratio="9:16": higgsfield.generate_video(prompt, duration_sec, aspect_ratio),
                "generate_image": lambda prompt, width=1080, height=1080: higgsfield.generate_image(prompt, width, height),
                "post_image_to_instagram": lambda image_url, caption: instagram.post_image(image_url, caption),
                "post_video_to_instagram": lambda video_url, caption: instagram.post_video(video_url, caption),
                "get_account_insights": lambda: instagram.get_account_insights(),
                "get_recent_posts": lambda limit=10: instagram.get_recent_posts(limit),
            },
        )

    def create_and_post(self, topic: str, content_type: str = "video") -> str:
        prompt = f"""Erstelle und poste Instagram-Content zum Thema: {topic}

Schritte:
1. Erstelle einen kreativen, detaillierten Higgsfield-Prompt auf Englisch für ein {content_type}
2. Generiere den Content ({content_type})
3. Verfasse eine ansprechende deutsche Instagram-Caption mit 15-25 relevanten Hashtags
4. Poste den Content auf Instagram
5. Bestätige den erfolgreichen Post mit dem Link

Content-Typ: {"Reel (9:16, 5-8 Sekunden)" if content_type == "video" else "Feed-Bild (1:1)"}"""

        return self.run(prompt)
