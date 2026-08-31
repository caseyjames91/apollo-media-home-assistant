from html import escape

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.profile import Profile
from app.ui import ingress_url, page


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def root(request: Request, db: Session = Depends(get_db)):
    profiles = list(db.scalars(select(Profile).order_by(Profile.name)))
    plist = (
        "".join(f"<li>{escape(p.name)}</li>" for p in profiles)
        or "<li>No Apollo profiles yet</li>"
    )

    return page(
        f'''
      <h1>Apollo Media Server</h1>
      <p class="ok">Server is running.</p>
      <p>Version <code>{escape(settings.version)}</code></p>
      <div class="nav">
        <a href="{escape(ingress_url(request, 'browser'))}">Browse Apollo cache</a>
      </div>
      <div class="card">
        <h2>Profiles</h2>
        <ul>{plist}</ul>
      </div>
    '''
    )
