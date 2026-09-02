import asyncio
import httpx


async def jsonrpc(url: str, method: str, params: dict | None = None):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
    }
    if params is not None:
        payload["params"] = params

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    if "error" in data:
        raise RuntimeError(f"Kodi JSON-RPC error: {data['error']}")

    return data.get("result")


async def open_file(url: str, file: str):
    return await jsonrpc(
        url,
        "Player.Open",
        {"item": {"file": file}},
    )


async def wait_for_video_player(
    url: str,
    timeout: float = 10.0,
    interval: float = 0.5,
) -> int:
    elapsed = 0.0

    while elapsed < timeout:
        players = await jsonrpc(url, "Player.GetActivePlayers")

        for player in players or []:
            if player.get("type") == "video":
                return int(player["playerid"])

        await asyncio.sleep(interval)
        elapsed += interval

    raise RuntimeError("Kodi video player did not become ready")


async def seek(url: str, player_id: int, seconds: float):
    return await jsonrpc(
        url,
        "Player.Seek",
        {
            "playerid": player_id,
            "value": {
                "time": {
                    "hours": int(seconds // 3600),
                    "minutes": int((seconds % 3600) // 60),
                    "seconds": int(seconds % 60),
                    "milliseconds": int((seconds % 1) * 1000),
                }
            },
        },
    )
