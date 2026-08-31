import math
import uuid
from html import escape

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.integration import Integration
from app.models.media import Media
from app.models.profile import Profile
from app.models.progress import Progress
from app.ui import ingress_url, local_time_html, page

router = APIRouter(tags=["debug"])
PAGE_SIZE = 80


def _hms(seconds: float) -> str:
    seconds = max(0, int(seconds or 0))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _media_card(request: Request, media: Media, progress: Progress | None = None) -> str:
    title = escape(media.title or "Untitled")
    poster_url = str(media.poster_url or "").strip()
    if poster_url:
        src = escape(poster_url)
        image = f'<img class="poster" src="{src}" alt="" loading="lazy">'
    else:
        image = '<div class="poster"></div>'

    episode = ""
    if media.media_type == "episode":
        episode = f"S{media.season or 0} E{media.episode or 0} · "

    progress_html = ""
    if progress:
        duration = max(0.0, progress.duration_seconds or 0)
        fraction = min(1.0, max(0.0, (progress.position_seconds or 0) / duration)) if duration else 0
        progress_html = (
            f'<div class="progress"><span style="width:{fraction*100:.1f}%"></span></div>'
            f'<div class="meta">{_hms(progress.position_seconds)} / {_hms(duration)} · {fraction*100:.1f}%</div>'
            f'<div class="meta">Updated {local_time_html(progress.updated_at)}</div>'
        )

    ids = [f"Canonical: {escape(media.canonical_id)}"]
    if media.imdb_id:
        ids.append(f"IMDb: {escape(media.imdb_id)}")
    if media.tmdb_id:
        ids.append(f"TMDB: {escape(media.tmdb_id)}")

    return f'''<article class="media">{image}<div class="media-body">
      <h3>{episode}{title}</h3>
      <div class="meta">Type: {escape(media.media_type)}</div>
      {progress_html}
      <div class="meta">{'<br>'.join(ids)}</div>
    </div></article>'''


@router.get("/browser")
def browser(
    request: Request,
    view: str = Query("movies", pattern="^(movies|shows|continue)$"),
    profile_id: uuid.UUID | None = None,
    page_num: int = Query(1, alias="page", ge=1),
    db: Session = Depends(get_db),
):
    profiles = list(db.scalars(select(Profile).order_by(Profile.name)))
    profile = db.get(Profile, profile_id) if profile_id else (profiles[0] if profiles else None)

    nav = '<div class="nav">' + ''.join([
        f'<a href="{escape(ingress_url(request, "browser?view=movies"))}">Movies</a>',
        f'<a href="{escape(ingress_url(request, "browser?view=shows"))}">Shows</a>',
        f'<a href="{escape(ingress_url(request, "browser?view=continue"))}">Continue Watching</a>',
        f'<a href="{escape(ingress_url(request))}">Server</a>',
    ]) + '</div>'

    offset = (page_num - 1) * PAGE_SIZE
    cards: list[str] = []
    total = 0
    heading = view.replace("continue", "Continue Watching").title()

    if view in {"movies", "shows"}:
        media_type = "movie" if view == "movies" else "show"
        total = db.scalar(select(func.count()).select_from(Media).where(Media.media_type == media_type)) or 0
        rows = list(db.scalars(
            select(Media).where(Media.media_type == media_type).order_by(Media.title).offset(offset).limit(PAGE_SIZE)
        ))
        cards = [_media_card(request, row) for row in rows]
    else:
        if profile is None:
            return page(f'<h1>Apollo Cache Browser</h1>{nav}<div class="card"><p class="muted">No profile exists yet.</p></div>')
        base = (
            select(Progress, Media)
            .join(Media, Media.id == Progress.media_id)
            .where(Progress.profile_id == profile.id)
            .order_by(Progress.updated_at.desc())
        )
        all_rows = db.execute(base).all()
        filtered = []
        for progress, media in all_rows:
            duration = max(0.0, progress.duration_seconds or 0)
            fraction = (progress.position_seconds or 0) / duration if duration > 0 else 0
            if (progress.position_seconds or 0) > 0 and fraction < 0.90:
                filtered.append((progress, media))
        total = len(filtered)
        rows = filtered[offset:offset + PAGE_SIZE]
        cards = [_media_card(request, media, progress) for progress, media in rows]
        heading += f" · {escape(profile.name)}"

    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    def page_link(n: int, label: str) -> str:
        if n < 1 or n > total_pages:
            return '<span></span>'
        suffix = f"browser?view={view}&page={n}"
        if view == "continue" and profile:
            suffix += f"&profile_id={profile.id}"
        return f'<a class="button" href="{escape(ingress_url(request, suffix))}">{label}</a>'

    pager = f'<div class="pager">{page_link(page_num-1,"Previous")}<span class="muted">Page {page_num} of {total_pages} · {total} items</span>{page_link(page_num+1,"Next")}</div>'
    body = ''.join(cards) or '<div class="card"><p class="muted">No cached items in this view.</p></div>'
    return page(f'<h1>Apollo Cache Browser</h1>{nav}<h2>{heading}</h2>{pager}<div class="grid">{body}</div>{pager}')
