import json
import urllib.error
import urllib.parse
import urllib.request


USER_AGENT = "ApolloMedia/0.2 Kodi"


def build_url(base, path, params=None):
    url = (base or "").rstrip("/") + "/" + path.lstrip("/")
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return url


def request_json(method, url, data=None, headers=None, timeout=15):
    request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    if headers:
        request_headers.update(headers)
    body = json.dumps(data).encode("utf-8") if data is not None else None
    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"{method} failed: {url}: {exc}")


def get_json(url, headers=None, timeout=15):
    return request_json("GET", url, headers=headers, timeout=timeout)


def post_json(url, data=None, headers=None, timeout=15):
    return request_json("POST", url, data=data or {}, headers=headers, timeout=timeout)
