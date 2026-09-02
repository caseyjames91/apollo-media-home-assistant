from datetime import datetime, timezone
from html import escape

from fastapi import Request
from fastapi.responses import HTMLResponse


def ingress_url(request: Request, path: str = "") -> str:
    base = request.headers.get("x-ingress-path", "").rstrip("/")
    suffix = path.lstrip("/")
    if base:
        return f"{base}/{suffix}" if suffix else f"{base}/"
    return f"/{suffix}" if suffix else "/"


def local_time_html(value: datetime | None) -> str:
    """Render a UTC timestamp for browser-local display without changing storage."""
    if value is None:
        return "Never"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    iso = value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return f'<time data-local datetime="{escape(iso)}">{escape(iso)}</time>'


def page(body: str) -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html>
<html>
<head>
<title>Apollo Media Server</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{{--bg:#111;--card:#1b1b1b;--border:#333;--muted:#aaa;--ok:#65d98b;--bad:#ff7c7c;--link:#54a8ff}}
*{{box-sizing:border-box}}
body{{font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:#eee;margin:0;padding:28px}}
main{{max-width:980px;margin:auto}}h1,h2,h3{{margin-bottom:.4rem}}a{{color:var(--link)}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px;margin:18px 0}}
label{{display:block;margin-top:12px;margin-bottom:5px;color:#bbb}}
input{{width:100%;padding:11px;border-radius:8px;border:1px solid #444;background:#101010;color:#fff}}
button,.button{{display:inline-block;margin-top:12px;padding:10px 16px;border:0;border-radius:8px;font-weight:700;background:#eee;color:#111;text-decoration:none;cursor:pointer}}
.ok{{color:var(--ok)}}.bad{{color:var(--bad)}}.muted{{color:var(--muted)}}
code{{background:#222;padding:3px 6px;border-radius:5px;overflow-wrap:anywhere}}
.nav{{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0}}.nav a{{background:#222;border:1px solid #3a3a3a;padding:8px 12px;border-radius:9px;text-decoration:none}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:14px}}
.media{{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden}}
.poster{{width:100%;aspect-ratio:2/3;object-fit:cover;background:#222;display:block}}
.media-body{{padding:12px}}.media h3{{font-size:1rem;margin:0 0 6px}}.meta{{font-size:.82rem;color:#bbb;line-height:1.5;overflow-wrap:anywhere}}
.progress{{height:5px;background:#333;border-radius:99px;overflow:hidden;margin:9px 0}}.progress span{{display:block;height:100%;background:#eee}}
.pager{{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:18px 0}}
</style>
</head><body><main>{body}</main>
<script>
for (const el of document.querySelectorAll('time[data-local]')) {{
  const d = new Date(el.getAttribute('datetime'));
  if (!Number.isNaN(d.getTime())) {{
    el.textContent = d.toLocaleString([], {{dateStyle:'medium', timeStyle:'medium'}});
    el.title = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Local time';
  }}
}}
</script>
</body></html>""")
