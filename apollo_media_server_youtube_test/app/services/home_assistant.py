import os
import httpx

from app.core.config import settings


def _token() -> str:
    token = os.getenv("SUPERVISOR_TOKEN") or os.getenv("APOLLO_HOME_ASSISTANT_TOKEN")
    if not token:
        raise RuntimeError("Home Assistant API token is not available")
    return token


async def call_service(domain: str, service: str, data: dict) -> dict | list:
    url = f"{settings.home_assistant_api_url.rstrip('/')}/services/{domain}/{service}"
    headers = {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()


async def play_media(entity_id: str, media_content_id: str, media_content_type: str = "video"):
    return await call_service(
        "media_player",
        "play_media",
        {
            "entity_id": entity_id,
            "media_content_id": media_content_id,
            "media_content_type": media_content_type,
        },
    )


async def media_seek(entity_id: str, position: float):
    return await call_service(
        "media_player",
        "media_seek",
        {
            "entity_id": entity_id,
            "seek_position": position,
        },
    )
