import json
import urllib.request

def get_json(url, timeout=30):
    req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"ApolloMedia/0.10"})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def build_url(base, path="", query=None):
    """Compatibility URL builder used by isolated provider/account-link modules."""
    from urllib.parse import urlencode
    base = str(base or "").rstrip("/")
    path = str(path or "").lstrip("/")
    target = f"{base}/{path}" if path else base
    if query:
        encoded = urlencode(
            {key: value for key, value in query.items() if value is not None},
            doseq=True,
        )
        if encoded:
            target += ("&" if "?" in target else "?") + encoded
    return target
