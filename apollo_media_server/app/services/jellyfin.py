from dataclasses import dataclass
from datetime import datetime, timezone
import httpx

CLIENT_NAME = "Apollo Media Server"
CLIENT_VERSION = "0.1.5"
DEVICE_NAME = "Home Assistant Add-on"
DEVICE_ID = "apollo-media-server"
TICKS_PER_SECOND = 10_000_000


def _auth_header(token: str | None = None) -> str:
    parts = [
        f'Client="{CLIENT_NAME}"',
        f'Device="{DEVICE_NAME}"',
        f'DeviceId="{DEVICE_ID}"',
        f'Version="{CLIENT_VERSION}"',
    ]
    if token:
        parts.append(f'Token="{token}"')
    return "MediaBrowser " + ", ".join(parts)


def auth_headers(token: str | None = None) -> dict[str, str]:
    """Headers for authenticated Jellyfin requests made by Apollo."""
    return {"Authorization": _auth_header(token)}


@dataclass
class JellyfinConnectionResult:
    server_name: str
    user_id: str
    access_token: str
    username: str


@dataclass
class JellyfinSyncPayload:
    catalog_items: list[dict]
    resume_items: list[dict]


async def authenticate(base_url: str, username: str, password: str) -> JellyfinConnectionResult:
    base_url = base_url.rstrip("/")
    headers = auth_headers()
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        server_resp = await client.get(f"{base_url}/System/Info/Public")
        server_resp.raise_for_status()
        server_info = server_resp.json()

        auth_resp = await client.post(
            f"{base_url}/Users/AuthenticateByName",
            headers=headers,
            json={"Username": username, "Pw": password},
        )
        auth_resp.raise_for_status()
        payload = auth_resp.json()

    return JellyfinConnectionResult(
        server_name=server_info.get("ServerName") or "Jellyfin",
        user_id=payload["User"]["Id"],
        access_token=payload["AccessToken"],
        username=payload["User"].get("Name") or username,
    )


async def validate_token(base_url: str, token: str) -> dict:
    base_url = base_url.rstrip("/")
    headers = auth_headers(token)
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        resp = await client.get(f"{base_url}/System/Info", headers=headers)
        resp.raise_for_status()
        return resp.json()


async def fetch_sync_payload(base_url: str, user_id: str, token: str) -> JellyfinSyncPayload:
    """Fetch all remote data before touching Apollo's cache.

    If either Jellyfin request fails, the caller receives an exception and can
    leave the last-known-good SQLite cache untouched.
    """
    base_url = base_url.rstrip("/")
    headers = auth_headers(token)
    common_fields = "ProviderIds,UserData,SeriesId,SeriesName,ParentIndexNumber,IndexNumber"
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        catalog_resp = await client.get(
            f"{base_url}/Users/{user_id}/Items",
            headers=headers,
            params={
                "Recursive": "true",
                "IncludeItemTypes": "Movie,Series",
                "Fields": common_fields,
                "SortBy": "SortName",
                "SortOrder": "Ascending",
            },
        )
        catalog_resp.raise_for_status()

        resume_resp = await client.get(
            f"{base_url}/Users/{user_id}/Items/Resume",
            headers=headers,
            params={
                "Recursive": "true",
                "MediaTypes": "Video",
                "Fields": common_fields,
                "Limit": "200",
            },
        )
        resume_resp.raise_for_status()

    return JellyfinSyncPayload(
        catalog_items=(catalog_resp.json() or {}).get("Items", []),
        resume_items=(resume_resp.json() or {}).get("Items", []),
    )


def ticks_to_seconds(value) -> float:
    try:
        return max(0.0, float(value or 0) / TICKS_PER_SECOND)
    except (TypeError, ValueError):
        return 0.0


def parse_jellyfin_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)
