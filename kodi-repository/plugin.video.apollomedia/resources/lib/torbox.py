import json
import urllib.error
import urllib.request
import os
import threading

import xbmc
import xbmcgui

from .http import build_url, get_json


API_URL = "https://api.torbox.app/v1/api"
LINK_URL = "https://tor.box/link"


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


class TorBoxLinkDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.addon = kwargs.pop("addon")
        self.device_code = kwargs.pop("device_code")
        self.user_code = kwargs.pop("user_code")
        self.interval = kwargs.pop("interval")
        self.done = False
        self.success = False
        self._worker = None
        super().__init__(*args, **kwargs)

    def onInit(self):
        self.getControl(101).setLabel(self.user_code or "(no code returned)")
        self.getControl(102).setLabel(f"Scan the QR code or open {LINK_URL}")
        self.getControl(103).setLabel("Waiting for TorBox authorization...")
        self._worker = threading.Thread(target=self._poll, daemon=True)
        self._worker.start()

    def _poll(self):
        monitor = xbmc.Monitor()
        attempts = 300 // self.interval
        for _ in range(attempts):
            if self.done or monitor.abortRequested() or monitor.waitForAbort(self.interval):
                return
            token = extract_token(poll_device_login(self.device_code))
            if token:
                self.addon.setSettingString("torbox_token", token)
                self.success = True
                self.done = True
                try:
                    self.getControl(103).setLabel("TorBox linked successfully.")
                except Exception:
                    pass
                xbmc.sleep(700)
                self.close()
                return
        if not self.done:
            self.done = True
            try:
                self.getControl(103).setLabel("TorBox authorization timed out.")
            except Exception:
                pass

    def onClick(self, control_id):
        if control_id == 200:
            self.done = True
            self.close()

    def onAction(self, action):
        if action.getId() in (9, 10, 13, 92, 216):
            self.done = True
            self.close()


def link_account(addon):
    try:
        info = start_device_login()
    except Exception as exc:
        xbmcgui.Dialog().ok("Apollo Media", f"Could not start TorBox login:\n{exc}")
        return False

    device_code = info.get("device_code") or ""
    code = info.get("code") or info.get("user_code") or ""
    interval = max(int(info.get("interval") or 5), 2)
    if not device_code:
        xbmcgui.Dialog().ok("Apollo Media", "TorBox did not return a device code.")
        return False

    addon_path = addon.getAddonInfo("path")
    dialog = TorBoxLinkDialog(
        "TorBoxLink.xml",
        addon_path,
        "Default",
        "1080i",
        addon=addon,
        device_code=device_code,
        user_code=code,
        interval=interval,
    )
    dialog.doModal()
    success = dialog.success
    del dialog

    if success:
        xbmcgui.Dialog().notification(
            "Apollo Media", "TorBox linked", xbmcgui.NOTIFICATION_INFO, 5000
        )
        return True
    return False
