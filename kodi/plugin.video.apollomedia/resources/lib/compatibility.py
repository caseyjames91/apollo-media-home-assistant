import json
import re

import xbmc


def _setting_value(setting_id, default=False):
    request = json.dumps({
        "jsonrpc": "2.0",
        "method": "Settings.GetSettingValue",
        "params": {"setting": setting_id},
        "id": 1,
    })
    try:
        response = json.loads(xbmc.executeJSONRPC(request))
        return bool((response.get("result") or {}).get("value", default))
    except Exception:
        return default


def _parse_resolution(text):
    """
    Parse a Kodi display-mode string such as:
      3840x2160 @ 60.00 - Full Screen
      1920 x 1080
    Returns (width, height) or (0, 0).
    """
    match = re.search(r"(\d{3,5})\s*[x×]\s*(\d{3,5})", str(text or ""), re.IGNORECASE)
    if not match:
        return 0, 0
    try:
        return int(match.group(1)), int(match.group(2))
    except Exception:
        return 0, 0


def _display_resolution():
    """
    Prefer Kodi's active display mode over GUI render/window dimensions.

    System.ScreenWidth/Height can represent the current Kodi window size,
    which is not a device capability and must not disable 4K playback.
    """
    candidates = (
        ("System.ScreenMode", xbmc.getInfoLabel("System.ScreenMode") or ""),
        ("System.ScreenResolution", xbmc.getInfoLabel("System.ScreenResolution") or ""),
    )
    for source, value in candidates:
        width, height = _parse_resolution(value)
        if width and height:
            return width, height, source, value

    # Useful for diagnostics only. Do not treat this as max capability.
    gui_width = int(xbmc.getInfoLabel("System.ScreenWidth") or 0)
    gui_height = int(xbmc.getInfoLabel("System.ScreenHeight") or 0)
    return 0, 0, "GUI window", f"{gui_width}×{gui_height}" if gui_width and gui_height else "unknown"



def detect(addon):
    """
    Return proposed auto-detected compatibility values without changing
    addon settings. Resolution is intentionally excluded and chosen manually
    by the compatibility wizard.
    """
    hdr_text = (xbmc.getInfoLabel("System.SupportedHDRTypes") or "").lower()

    platform = "Unknown"
    for condition, name in (
        ("System.Platform.Android", "Android"),
        ("System.Platform.Linux", "Linux"),
        ("System.Platform.Windows", "Windows"),
        ("System.Platform.OSX", "macOS"),
        ("System.Platform.IOS", "iOS"),
    ):
        if xbmc.getCondVisibility(condition):
            platform = name
            break

    values = {
        "allow_sdr": True,
        "allow_hdr10": "hdr10" in hdr_text or ("hdr" in hdr_text and "dolby" not in hdr_text),
        "allow_hdr10plus": "hdr10+" in hdr_text or "hdr10plus" in hdr_text,
        "allow_dolby_vision": "dolby vision" in hdr_text or "dolbyvision" in hdr_text,
        "allow_hlg": "hlg" in hdr_text,
        "allow_h264": True,
        "allow_hevc": True,
        "allow_av1": False,
        "allow_mpeg2": True,
        "allow_vc1": True,
        "allow_aac": True,
        "allow_ac3": _setting_value("audiooutput.ac3passthrough", True),
        "allow_eac3": _setting_value("audiooutput.eac3passthrough", True),
        "allow_dts": _setting_value("audiooutput.dtspassthrough", True),
        "allow_dtshd": _setting_value("audiooutput.dtshdpassthrough", False),
        "allow_truehd": _setting_value("audiooutput.truehdpassthrough", False),
        "allow_unknown": True,
    }

    description = f"{platform} • HDR: {hdr_text or 'none reported'}"
    return description, values


def profile(addon):
    keys = (
        "allow_2160p", "allow_1080p", "allow_720p", "allow_480p",
        "allow_sdr", "allow_hdr10", "allow_hdr10plus", "allow_dolby_vision", "allow_hlg",
        "allow_h264", "allow_hevc", "allow_av1", "allow_mpeg2", "allow_vc1",
        "allow_aac", "allow_ac3", "allow_eac3", "allow_dts", "allow_dtshd", "allow_truehd",
        "allow_unknown",
    )
    return {key: addon.getSettingBool(key) for key in keys}
