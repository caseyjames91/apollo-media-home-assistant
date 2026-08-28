from html import escape
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
import httpx

from app.db.session import get_db
from app.models.integration import Integration
from app.models.profile import Profile
from app.services.jellyfin import authenticate, validate_token

router = APIRouter()

def ingress_url(request: Request, path: str = "") -> str:
    """Build a URL that remains inside Home Assistant ingress.

    Home Assistant supplies X-Ingress-Path for ingress requests. Direct access
    has no such header, so routes fall back to normal root-relative URLs.
    """
    base = request.headers.get("x-ingress-path", "").rstrip("/")
    suffix = path.lstrip("/")
    if base:
        return f"{base}/{suffix}" if suffix else f"{base}/"
    return f"/{suffix}" if suffix else "/"

def page(body: str) -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html>
<html>
<head>
<title>Apollo Media Server</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{{font-family:system-ui;background:#111;color:#eee;margin:0;padding:28px}}
main{{max-width:760px;margin:auto}}h1,h2{{margin-bottom:.4rem}}
.card{{background:#1b1b1b;border:1px solid #333;border-radius:14px;padding:20px;margin:18px 0}}
label{{display:block;margin-top:12px;margin-bottom:5px;color:#bbb}}
input{{width:100%;box-sizing:border-box;padding:11px;border-radius:8px;border:1px solid #444;background:#101010;color:#fff}}
button{{margin-top:16px;padding:10px 16px;border:0;border-radius:8px;font-weight:700}}
.ok{{color:#65d98b}}.bad{{color:#ff7c7c}}.muted{{color:#aaa}}
code{{background:#222;padding:3px 6px;border-radius:5px}}
</style>
</head><body><main>{body}</main></body></html>""")

@router.get("/", response_class=HTMLResponse)
def root(request: Request, db: Session = Depends(get_db)):
    jellyfin = db.scalar(select(Integration).where(Integration.kind == "jellyfin"))
    profiles = list(db.scalars(select(Profile).order_by(Profile.name)))
    if jellyfin:
        status = f'''
        <div class="card">
          <h2>Jellyfin</h2>
          <p class="ok">Connected</p>
          <p><b>Server:</b> {escape(jellyfin.server_name or "Jellyfin")}</p>
          <p><b>URL:</b> <code>{escape(jellyfin.base_url)}</code></p>
          <p><b>User:</b> {escape(jellyfin.username or "")}</p>
          <form method="post" action="{escape(ingress_url(request, 'jellyfin/test'))}"><button>Test connection</button></form>
          <form method="post" action="{escape(ingress_url(request, 'jellyfin/disconnect'))}"><button>Disconnect</button></form>
        </div>'''
    else:
        status = f'''
        <div class="card">
          <h2>Connect Jellyfin</h2>
          <p class="muted">Apollo stores the returned Jellyfin access token. The password is used only for authentication and is not stored.</p>
          <form method="post" action="{escape(ingress_url(request, 'jellyfin/connect'))}">
            <label>Jellyfin URL</label>
            <input name="base_url" placeholder="http://server:8096" required>
            <label>Username</label>
            <input name="username" required>
            <label>Password</label>
            <input name="password" type="password" required>
            <button>Connect Jellyfin</button>
          </form>
        </div>'''
    plist = "".join(f"<li>{escape(p.name)}</li>" for p in profiles) or "<li>No Apollo profiles yet</li>"
    return page(f'''
      <h1>Apollo Media Server</h1>
      <p class="ok">Server is running.</p>
      <p>Version <code>0.1.3</code></p>
      {status}
      <div class="card"><h2>Profiles</h2><ul>{plist}</ul></div>
    ''')

@router.post("/jellyfin/connect")
async def jellyfin_connect(
    request: Request,
    base_url: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        result = await authenticate(base_url, username, password)
    except httpx.HTTPStatusError as exc:
        return page(f'<h1>Jellyfin connection failed</h1><p class="bad">HTTP {exc.response.status_code}</p><p><a href="{escape(ingress_url(request))}">Back</a></p>')
    except Exception as exc:
        return page(f'<h1>Jellyfin connection failed</h1><p class="bad">{escape(str(exc))}</p><p><a href="{escape(ingress_url(request))}">Back</a></p>')

    row = db.scalar(select(Integration).where(Integration.kind == "jellyfin"))
    if row is None:
        row = Integration(kind="jellyfin", base_url=base_url.rstrip("/"))
        db.add(row)

    row.base_url = base_url.rstrip("/")
    row.username = result.username
    row.user_id = result.user_id
    row.access_token = result.access_token
    row.server_name = result.server_name
    row.enabled = True

    profile = db.scalar(select(Profile).where(Profile.name == result.username))
    if profile is None:
        profile = Profile(name=result.username, jellyfin_user_id=result.user_id)
        db.add(profile)
    else:
        profile.jellyfin_user_id = result.user_id

    db.commit()
    return RedirectResponse(url=ingress_url(request), status_code=303)

@router.post("/jellyfin/test")
async def jellyfin_test(request: Request, db: Session = Depends(get_db)):
    row = db.scalar(select(Integration).where(Integration.kind == "jellyfin"))
    if row is None or not row.access_token:
        return page(f'<h1>Jellyfin</h1><p class="bad">Not configured.</p><p><a href="{escape(ingress_url(request))}">Back</a></p>')
    try:
        info = await validate_token(row.base_url, row.access_token)
        name = escape(info.get("ServerName") or row.server_name or "Jellyfin")
        return page(f'<h1>Jellyfin</h1><p class="ok">Connection successful.</p><p>Server: {name}</p><p><a href="{escape(ingress_url(request))}">Back</a></p>')
    except Exception as exc:
        return page(f'<h1>Jellyfin</h1><p class="bad">Connection failed: {escape(str(exc))}</p><p><a href="{escape(ingress_url(request))}">Back</a></p>')

@router.post("/jellyfin/disconnect")
def jellyfin_disconnect(request: Request, db: Session = Depends(get_db)):
    row = db.scalar(select(Integration).where(Integration.kind == "jellyfin"))
    if row:
        db.delete(row)
        db.commit()
    return RedirectResponse(url=ingress_url(request), status_code=303)
