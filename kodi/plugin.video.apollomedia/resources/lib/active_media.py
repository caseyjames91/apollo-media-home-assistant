"""Safe Apollo active-media record; never stores a stream or provider URL."""
import json
import os
import time
import xbmcvfs

def _path():
    directory = xbmcvfs.translatePath("special://profile/addon_data/plugin.video.apollomedia")
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, "active_media.json")

def save(data):
    payload = dict(data or {})
    payload["updated"] = time.time()
    with open(_path(), "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    return payload

def load(max_age=21600):
    try:
        with open(_path(), encoding="utf-8") as handle:
            data = json.load(handle)
        return data if time.time() - float(data.get("updated") or 0) <= max_age else {}
    except Exception:
        return {}
