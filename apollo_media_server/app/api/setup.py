from html import escape
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
import httpx

from app.db.session import get_db
from app.models.integration import Integration
from app.models.profile import Profile
from app.models.sync_state import SyncState
from app.services.jellyfin import authenticate, validate_token
from app.services.catalog_sync import sync_jellyfin
from app.ui import ingress_url, local_time_html, page

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def root(request: Request, db: Session = Depends(get_db)):
    jellyfin = db.scalar(select(Integration).where(Integration.kind == "jellyfin"))
    profiles = list(db.scalars(select(Profile).order_by(Profile.name)))
    sync_state = db.scalar(select(SyncState).where(SyncState.integration_kind == "jellyfin"))
    if jellyfin:
        status = f'''
        <div class="card">
          <h2>Jellyfin</h2>
          <p class="ok">Connected</p>
          <p><b>Server:</b> {escape(jellyfin.server_name or "Jellyfin")}</p>
          <p><b>URL:</b> <code>{escape(jellyfin.base_url)}</code></p>
          <p><b>User:</b> {escape(jellyfin.username or "")}</p>
          <form method="post" action="{escape(ingress_url(request, 'jellyfin/test'))}"><button>Test connection</button></form>
          <form method="post" action="{escape(ingress_url(request, 'jellyfin/sync-ui'))}"><button>Sync library &amp; Continue Watching</button></form>
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
    if sync_state and sync_state.last_success_at:
        sync_html = f"<div class=\"card\"><h2>Jellyfin Cache</h2><p class=\"ok\">Last sync succeeded.</p><p><b>Catalog:</b> {sync_state.catalog_items} items</p><p><b>Continue Watching:</b> {sync_state.continue_watching_items} items</p><p><b>Last sync:</b> {local_time_html(sync_state.last_success_at)}</p></div>"
    elif sync_state and sync_state.last_error:
        sync_html = f"<div class=\"card\"><h2>Jellyfin Cache</h2><p class=\"bad\">Last sync failed.</p><p class=\"muted\">Last-known-good cache was preserved.</p><p>{escape(sync_state.last_error)}</p></div>"
    else:
        sync_html = "<div class=\"card\"><h2>Jellyfin Cache</h2><p class=\"muted\">Not synced yet.</p></div>" if jellyfin else ""
    return page(f'''
      <h1>Apollo Media Server</h1>
      <p class="ok">Server is running.</p>
      <p>Version <code>0.1.5</code></p><div class="nav"><a href="{escape(ingress_url(request, 'browser'))}">Browse Apollo cache</a></div>
      {status}
      {sync_html}
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


@router.post("/jellyfin/sync-ui")
async def jellyfin_sync_ui(request: Request, db: Session = Depends(get_db)):
    try:
        result = await sync_jellyfin(db)
        return page(f'<h1>Jellyfin Sync</h1><p class="ok">Sync successful.</p><p>Catalog: {result["catalog_items"]} items</p><p>Continue Watching: {result["continue_watching_items"]} items</p><p><a href="{escape(ingress_url(request))}">Back</a></p>')
    except Exception as exc:
        return page(f'<h1>Jellyfin Sync</h1><p class="bad">Sync failed: {escape(str(exc))}</p><p class="muted">Apollo kept the last-known-good cache.</p><p><a href="{escape(ingress_url(request))}">Back</a></p>')
