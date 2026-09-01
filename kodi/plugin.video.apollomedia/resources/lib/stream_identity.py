import re
from urllib.parse import urlsplit


def _value(stream, key, default=""):
    if isinstance(stream, dict):
        return stream.get(key, default)
    return getattr(stream, key, default)


def _normalized_title(stream):
    title = str(_value(stream, "title", "") or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "", title)


def _normalized_hash(stream):
    value = str(_value(stream, "info_hash", "") or "").strip().lower()
    value = value.replace("urn:btih:", "")
    return re.sub(r"[^a-f0-9]", "", value)


def _normalized_size(stream):
    try:
        size = int(float(_value(stream, "size", 0) or 0))
    except (TypeError, ValueError):
        return 0
    return max(size, 0)


def _url_identity(stream):
    raw = str(_value(stream, "url", "") or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlsplit(raw)
        return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path}"
    except Exception:
        return raw


def identity_aliases(stream):
    # Hash is strongest. Filename remains an alias so a provider without hash
    # can still match the same release and old Apollo flags migrate cleanly.
    aliases = []

    stored = str(_value(stream, "stream_key", "") or "").strip()
    if stored:
        aliases.append(stored)

    stored_aliases = _value(stream, "release_aliases", ()) or ()
    if isinstance(stored_aliases, str):
        stored_aliases = (stored_aliases,)
    aliases.extend(
        str(alias).strip()
        for alias in stored_aliases
        if str(alias).strip()
    )

    info_hash = _normalized_hash(stream)
    if info_hash:
        aliases.append(f"hash:{info_hash}")

    title = _normalized_title(stream)
    size = _normalized_size(stream)
    if title and size:
        aliases.append(f"name-size:{title}:{size}")
    if title:
        aliases.append(f"name:{title}")
        aliases.append(title)

    url = _url_identity(stream)
    if url:
        aliases.append(f"url:{url}")

    return tuple(dict.fromkeys(aliases))


def release_key(stream):
    aliases = identity_aliases(stream)
    for prefix in ("hash:", "name-size:", "name:", "url:"):
        match = next(
            (alias for alias in aliases if alias.startswith(prefix)),
            None,
        )
        if match:
            return match
    return aliases[0] if aliases else ""


def same_release(left, right):
    return bool(set(identity_aliases(left)) & set(identity_aliases(right)))
