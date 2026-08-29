from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class MediaIds:
    imdb: str = ""
    tmdb: str = ""
    trakt: str = ""
    jellyfin: str = ""

    def canonical(self) -> str:
        return self.imdb or self.tmdb or self.trakt or self.jellyfin


@dataclass
class MediaArt:
    poster: str = ""
    thumb: str = ""
    fanart: str = ""


@dataclass
class ResumeState:
    position: float = 0.0
    duration: float = 0.0

    @property
    def resumable(self) -> bool:
        return self.position > 0 and self.duration > 0


@dataclass
class MediaItem:
    media_type: str
    title: str
    year: int = 0
    plot: str = ""
    show_title: str = ""
    season: int = 0
    episode: int = 0
    ids: MediaIds = field(default_factory=MediaIds)
    art: MediaArt = field(default_factory=MediaArt)
    resume: ResumeState = field(default_factory=ResumeState)
    in_library: bool = False
    is_folder: bool = False
    local: bool = False
    playback: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def identity(self) -> str:
        base = self.ids.imdb or self.ids.tmdb or self.ids.jellyfin
        if not base:
            return ""
        if self.media_type == "episode":
            return f"{base}:{int(self.season)}:{int(self.episode)}"
        return str(base)

    def with_library(self, jellyfin_id: str = ""):
        self.in_library = True
        self.local = True
        if jellyfin_id:
            self.ids.jellyfin = jellyfin_id
        return self
