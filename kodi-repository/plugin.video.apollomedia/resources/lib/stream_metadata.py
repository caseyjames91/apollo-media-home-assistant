import re
from dataclasses import dataclass


@dataclass(frozen=True)
class StreamMetadata:
    resolution: int = 0
    source: str = ""
    dynamic_range: str = "sdr"
    video_codec: str = ""
    audio_codec: str = ""
    atmos: bool = False
    channels: str = ""
    languages: tuple = ()
    low_quality_capture: bool = False


LANGUAGE_PATTERNS = (
    ("english", (r"\benglish\b", r"\beng\b")),
    ("spanish", (r"\bspanish\b", r"\bspa\b", r"\blatino\b")),
    ("french", (r"\bfrench\b", r"\bfre\b", r"\bfra\b")),
    ("german", (r"\bgerman\b", r"\bger\b", r"\bdeu\b")),
    ("italian", (r"\bitalian\b", r"\bita\b")),
    ("japanese", (r"\bjapanese\b", r"\bjpn\b")),
    ("korean", (r"\bkorean\b", r"\bkor\b")),
    ("hindi", (r"\bhindi\b", r"\bhin\b")),
    ("portuguese", (r"\bportuguese\b", r"\bpor\b", r"\bpt-br\b")),
    ("russian", (r"\brussian\b", r"\brus\b")),
)
LANGUAGE_NAMES = (
    r"(?:english|eng|spanish|spa|latino|french|fre|fra|german|ger|deu|"
    r"italian|ita|japanese|jpn|korean|kor|hindi|hin|portuguese|por|pt-br|"
    r"russian|rus)"
)


def stream_text(stream):
    return f" {getattr(stream, 'title', '')} {getattr(stream, 'description', '')} ".lower()


def csv_values(value):
    return tuple(x.strip().lower() for x in str(value or "").split(",") if x.strip())


def _token(text, expression):
    return re.search(rf"(?<![a-z0-9])(?:{expression})(?![a-z0-9])", text, re.I) is not None


def resolution(text):
    if _token(text, r"2160p?|4k|uhd"):
        return 2160
    if _token(text, r"1080p?"):
        return 1080
    if _token(text, r"720p?"):
        return 720
    if _token(text, r"480p?|sd"):
        return 480
    return 0


def languages(text):
    # A phrase ending in Subs/Subtitles describes subtitle availability, not
    # necessarily the audio track. Remove it before language classification.
    audio_text = re.sub(
        rf"(?<![a-z0-9]){LANGUAGE_NAMES}"
        rf"(?:[._ -]+{LANGUAGE_NAMES})*[._ -]+subs?(?:titles?)?(?![a-z0-9])",
        " ",
        text,
        flags=re.I,
    )
    return tuple(
        lang
        for lang, patterns in LANGUAGE_PATTERNS
        if any(re.search(pattern, audio_text, re.I) for pattern in patterns)
    )


def parse(stream):
    text = stream_text(stream)
    res = resolution(text)

    if "remux" in text:
        source = "remux"
    elif re.search(r"blu[ ._-]?ray", text, re.I):
        source = "bluray"
    elif re.search(r"web[ ._-]?dl", text, re.I):
        source = "web-dl"
    elif re.search(r"web[ ._-]?rip", text, re.I):
        source = "webrip"
    else:
        source = ""

    if re.search(r"(?<![a-z0-9])(?:dolby[ ._-]?vision|dovi|dv)(?![a-z0-9])", text, re.I):
        dynamic_range = "dolby_vision"
    elif "hdr10+" in text or "hdr10plus" in text:
        dynamic_range = "hdr10plus"
    elif _token(text, r"hlg"):
        dynamic_range = "hlg"
    elif _token(text, r"hdr10|hdr"):
        dynamic_range = "hdr10"
    else:
        dynamic_range = "sdr"

    if re.search(r"(?<![a-z0-9])(?:av1|av01)(?![a-z0-9])", text, re.I):
        video_codec = "av1"
    elif re.search(r"(?<![a-z0-9])(?:hevc|h[ .]?265|x265)(?![a-z0-9])", text, re.I):
        video_codec = "hevc"
    elif re.search(r"(?<![a-z0-9])(?:h[ .]?264|x264|avc)(?![a-z0-9])", text, re.I):
        video_codec = "h264"
    elif re.search(r"(?<![a-z0-9])(?:mpeg[ ._-]?2)(?![a-z0-9])", text, re.I):
        video_codec = "mpeg2"
    elif re.search(r"(?<![a-z0-9])(?:vc[ ._-]?1)(?![a-z0-9])", text, re.I):
        video_codec = "vc1"
    else:
        video_codec = ""

    if "truehd" in text:
        audio_codec = "truehd"
    elif re.search(r"(?<![a-z0-9])(?:dts[ ._-]?hd|dtshd|dts:x|dtsx)(?![a-z0-9])", text, re.I):
        audio_codec = "dtshd"
    elif re.search(r"(?<![a-z0-9])(?:eac3|e-ac-3|ddp|dd\+)(?![a-z0-9])", text, re.I):
        audio_codec = "eac3"
    elif re.search(r"(?<![a-z0-9])(?:ac3|ac-3)(?![a-z0-9])", text, re.I):
        audio_codec = "ac3"
    elif _token(text, r"aac"):
        audio_codec = "aac"
    elif _token(text, r"dts"):
        audio_codec = "dts"
    else:
        audio_codec = ""

    channel_match = re.search(r"(?<!\d)([257])\s*[.]\s*1(?!\d)", text)
    channels = f"{channel_match.group(1)}.1" if channel_match else ""

    low_quality = bool(
        re.search(
            r"(?<![a-z0-9])(?:hdcam|camrip|cam|telesync|telecine|ts)(?![a-z0-9])",
            text,
            re.I,
        )
    )

    return StreamMetadata(
        resolution=res,
        source=source,
        dynamic_range=dynamic_range,
        video_codec=video_codec,
        audio_codec=audio_codec,
        atmos="atmos" in text,
        channels=channels,
        languages=languages(text),
        low_quality_capture=low_quality,
    )


def filter_reason(stream, profile=None):
    profile = profile or {}
    meta = parse(stream)

    if meta.low_quality_capture:
        return "cam_or_telesync"

    resolution_setting = {
        2160: "allow_2160p",
        1080: "allow_1080p",
        720: "allow_720p",
        480: "allow_480p",
    }.get(meta.resolution)
    if resolution_setting and profile.get(resolution_setting) is False:
        return resolution_setting

    dynamic_settings = {
        "dolby_vision": "allow_dolby_vision",
        "hdr10plus": "allow_hdr10plus",
        "hlg": "allow_hlg",
        "hdr10": "allow_hdr10",
        "sdr": "allow_sdr",
    }
    setting = dynamic_settings.get(meta.dynamic_range)
    if setting and profile.get(setting) is False:
        return setting

    codec_settings = {
        "av1": "allow_av1",
        "hevc": "allow_hevc",
        "h264": "allow_h264",
        "mpeg2": "allow_mpeg2",
        "vc1": "allow_vc1",
    }
    setting = codec_settings.get(meta.video_codec)
    if setting and profile.get(setting) is False:
        return setting

    audio_settings = {
        "truehd": "allow_truehd",
        "dtshd": "allow_dtshd",
        "eac3": "allow_eac3",
        "ac3": "allow_ac3",
        "aac": "allow_aac",
    }
    setting = audio_settings.get(meta.audio_codec)
    if setting and profile.get(setting) is False:
        return setting

    detected = bool(
        meta.resolution
        or meta.video_codec
        or meta.audio_codec
        or meta.source
        or meta.dynamic_range != "sdr"
    )
    if not detected and profile.get("allow_unknown") is False:
        return "allow_unknown"

    stream_languages = set(meta.languages)
    excluded = set(csv_values(profile.get("excluded_languages")))
    if stream_languages & excluded:
        return "excluded_language"

    allowed = set(csv_values(profile.get("allowed_languages")))
    if allowed and stream_languages and not (stream_languages & allowed):
        return "language_not_allowed"

    return None


def ranking_key(stream, profile=None):
    profile = profile or {}
    meta = parse(stream)

    resolution_rank = {2160: 4, 1080: 3, 720: 2, 480: 1, 0: 0}[meta.resolution]
    source_rank = {"remux": 4, "bluray": 3, "web-dl": 2, "webrip": 1}.get(meta.source, 0)

    preferred = csv_values(profile.get("preferred_languages"))
    hits = [preferred.index(lang) for lang in meta.languages if lang in preferred]
    language_rank = len(preferred) - min(hits) if hits else 0

    priority = csv_values(profile.get("provider_priority")) or ("debridio", "torrentio", "comet")
    provider = str(getattr(stream, "provider", "") or "").lower()
    provider_rank = len(priority) - priority.index(provider) if provider in priority else 0

    dynamic_rank = 1 if meta.dynamic_range != "sdr" else 0
    audio_rank = 1 if meta.audio_codec in ("truehd", "dtshd") or meta.atmos else 0

    # Meaningful quality differences dominate language/provider preferences.
    return (
        resolution_rank,
        source_rank,
        language_rank,
        provider_rank,
        dynamic_rank,
        audio_rank,
    )


def score(stream, profile=None):
    if filter_reason(stream, profile):
        return -1
    return sum(
        value * weight
        for value, weight in zip(
            ranking_key(stream, profile),
            (100000, 10000, 1000, 100, 10, 1),
        )
    )


def rank_streams(streams, profile=None):
    eligible = [stream for stream in streams if filter_reason(stream, profile) is None]
    eligible.sort(
        key=lambda stream: (
            str(getattr(stream, "provider", "") or "").lower(),
            str(getattr(stream, "title", "") or "").casefold(),
            str(getattr(stream, "url", "") or ""),
        )
    )
    eligible.sort(key=lambda stream: ranking_key(stream, profile), reverse=True)
    return eligible


def technical_info(title="", description=""):
    class _Stream:
        pass

    stream = _Stream()
    stream.title = title
    stream.description = description
    meta = parse(stream)

    quality = {
        2160: "4K / 2160p",
        1080: "1080p",
        720: "720p",
        480: "SD / 480p",
    }.get(meta.resolution, "Other")

    video_bits = [quality]
    dynamic_labels = {
        "dolby_vision": "Dolby Vision",
        "hdr10plus": "HDR10+",
        "hdr10": "HDR",
        "hlg": "HLG",
    }
    if meta.dynamic_range in dynamic_labels:
        video_bits.append(dynamic_labels[meta.dynamic_range])

    codec_labels = {
        "hevc": "HEVC",
        "av1": "AV1",
        "h264": "H.264",
        "mpeg2": "MPEG-2",
        "vc1": "VC-1",
    }
    if meta.video_codec in codec_labels:
        video_bits.append(codec_labels[meta.video_codec])

    audio_labels = {
        "truehd": "TrueHD",
        "dtshd": "DTS-HD",
        "eac3": "Dolby Digital Plus",
        "ac3": "Dolby Digital",
        "aac": "AAC",
        "dts": "DTS",
    }
    audio = audio_labels.get(meta.audio_codec, "")
    if meta.atmos:
        audio = f"{audio} · Atmos" if audio else "Atmos"
    if meta.channels:
        audio = f"{audio} · {meta.channels}" if audio else meta.channels

    return {
        "quality": quality,
        "video": " · ".join(dict.fromkeys(video_bits)),
        "audio": audio or "Unknown audio",
    }
