import json
import urllib.error
import urllib.request

import xbmc
import xbmcgui

from .http import build_url, get_json


API_URL = "https://api.torbox.app/v1/api"


def start_device_login():
    response = get_json(build_url(API_URL, "/user/auth/device/start", {"app": "apollo-media"}))
    return response.get("data") or {}


def poll_device_login(device_code):
    request = urllib.request.Request(
        build_url(API_URL, "/user/auth/device/token"),
        data=json.dumps({"device_code": device_code}).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "ApolloMedia/0.4 Kodi"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError:
        return {"success": False}
    except Exception:
        return {"success": False}


def extract_token(response):
    data = response.get("data") or {}
    if isinstance(data, str):
        return data
    return data.get("access_token") or data.get("token") or data.get("api_key") or ""


def link_account(addon):
    try:
        info = start_device_login()
    except Exception as exc:
        xbmcgui.Dialog().ok("Apollo Media", f"Could not start TorBox login:\n{exc}")
        return False
    device_code = info.get("device_code") or ""
    code = info.get("code") or ""
    url = info.get("friendly_verification_url") or info.get("verification_url") or "https://tor.box/link"
    interval = max(int(info.get("interval") or 5), 2)
    if not device_code:
        xbmcgui.Dialog().ok("Apollo Media", "TorBox did not return a device code.")
        return False
    dialog = xbmcgui.DialogProgress()
    dialog.create("Link TorBox", f"Open [B]{url}[/B]\n\nEnter code: [B]{code}[/B]\n\nWaiting for approval...")
    monitor = xbmc.Monitor()
    attempts = 300 // interval
    for index in range(attempts):
        if dialog.iscanceled() or monitor.abortRequested() or monitor.waitForAbort(interval):
            dialog.close()
            return False
        dialog.update(int(index * 100 / attempts))
        token = extract_token(poll_device_login(device_code))
        if token:
            addon.setSettingString("torbox_token", token)
            dialog.close()
            xbmcgui.Dialog().notification("Apollo Media", "TorBox linked", xbmcgui.NOTIFICATION_INFO, 5000)
            return True
    dialog.close()
    xbmcgui.Dialog().ok("Apollo Media", "TorBox login timed out.")
    return False
