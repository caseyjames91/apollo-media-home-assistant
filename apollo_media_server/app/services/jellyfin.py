from dataclasses import dataclass
import httpx

CLIENT_NAME = "Apollo Media Server"
CLIENT_VERSION = "0.1.3"
DEVICE_NAME = "Home Assistant Add-on"
DEVICE_ID = "apollo-media-server"

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

@dataclass
class JellyfinConnectionResult:
    server_name: str
    user_id: str
    access_token: str
    username: str

async def authenticate(base_url: str, username: str, password: str) -> JellyfinConnectionResult:
    base_url = base_url.rstrip("/")
    headers = {"Authorization": _auth_header()}
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
    headers = {"Authorization": _auth_header(token)}
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        resp = await client.get(f"{base_url}/System/Info", headers=headers)
        resp.raise_for_status()
        return resp.json()
