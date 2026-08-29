from datetime import datetime

from .models import MediaItem, MediaIds, MediaArt, ResumeState
from .discovery import (
    popular_movies,
    popular_series,
    search_movies,
    search_series,
    series_details,
    movie_catalog,
    series_catalog,
    progress_metadata,
)


class MediaService:
    """
    Normalizes provider data before Kodi sees it.

    Source adapters remain responsible for fetching.
    This service is responsible for identity, presentation metadata,
    local-library overlay and stable Apollo media objects.
    """

    def __init__(self, jellyfin_client):
        self.jf = jellyfin_client


    @staticmethod
    def _imdb_id(value):
        return str(value or "").strip()

    def _movie_from_discovery(self, movie):
        imdb_id = self._imdb_id(movie.get("imdb_id") or movie.get("id"))
        title = movie.get("name") or movie.get("title") or "Unknown"
        year = movie.get("releaseInfo") or movie.get("year") or 0
        try:
            year = int(str(year)[:4]) if year else 0
        except Exception:
            year = 0

        return MediaItem(
            media_type="movie",
            title=title,
            year=year,
            plot=movie.get("description") or "",
            ids=MediaIds(imdb=imdb_id),
            art=MediaArt(
                poster=movie.get("poster") or "",
                fanart=movie.get("background") or "",
            ),
            source="discovery",
            raw=movie,
        )

    def _show_from_discovery(self, show):
        imdb_id = self._imdb_id(show.get("imdb_id") or show.get("id"))
        title = show.get("name") or show.get("title") or "Unknown"
        year = show.get("releaseInfo") or show.get("year") or 0
        try:
            year = int(str(year)[:4]) if year else 0
        except Exception:
            year = 0

        return MediaItem(
            media_type="show",
            title=title,
            year=year,
            plot=show.get("description") or "",
            ids=MediaIds(imdb=imdb_id),
            art=MediaArt(
                poster=show.get("poster") or "",
                fanart=show.get("background") or "",
            ),
            is_folder=True,
            source="discovery",
            raw=show,
        )

    def _jellyfin_series_item(self, series):
        """
        Normalize a local Jellyfin show without remote metadata lookups.

        Jellyfin is the source of truth for local library presentation,
        structure, identity, artwork and state.
        """
        provider_ids = series.get("ProviderIds") or {}
        imdb_id = provider_ids.get("Imdb") or provider_ids.get("IMDb") or ""
        item_id = series.get("Id") or ""

        return MediaItem(
            media_type="show",
            title=series.get("Name") or "Unknown",
            year=int(series.get("ProductionYear") or 0),
            plot=series.get("Overview") or "",
            ids=MediaIds(imdb=imdb_id, jellyfin=item_id),
            art=MediaArt(
                poster=self.jf.image_url(item_id),
                fanart=self.jf.image_url(item_id, "Backdrop", 1280),
            ),
            in_library=True,
            local=True,
            is_folder=True,
            source="jellyfin",
            raw=series,
        )

    def _jellyfin_movie_item(self, movie):
        provider_ids = movie.get("ProviderIds") or {}
        imdb_id = provider_ids.get("Imdb") or provider_ids.get("IMDb") or ""
        item_id = movie.get("Id") or ""
        user_data = movie.get("UserData") or {}
        position = int(user_data.get("PlaybackPositionTicks") or 0) / 10000000
        duration = int(movie.get("RunTimeTicks") or 0) / 10000000
        return MediaItem(
            media_type="movie",
            title=movie.get("Name") or "Unknown",
            year=int(movie.get("ProductionYear") or 0),
            plot=movie.get("Overview") or "",
            ids=MediaIds(imdb=imdb_id, jellyfin=item_id),
            art=MediaArt(
                poster=self.jf.image_url(item_id),
                fanart=self.jf.image_url(item_id, "Backdrop", 1280),
            ),
            resume=ResumeState(position, duration),
            in_library=True,
            local=True,
            source="jellyfin",
            raw=movie,
        )

    def library_movies(self):
        return [
            self._jellyfin_movie_item(item)
            for item in self.jf.items("Movie")
        ]

    def library_shows(self):
        items = [
            self._jellyfin_series_item(item)
            for item in self.jf.items("Series")
        ]
        items.sort(key=lambda item: item.title.casefold())
        return items

    def popular_movies(self):
        local_index = self.jf.movie_index()
        result = []
        for raw in popular_movies():
            item = self._movie_from_discovery(raw)
            local = local_index.get(item.ids.imdb.lower())
            if local:
                item.with_library(local.get("Id") or "")
            result.append(item)
        return result

    def popular_shows(self):
        local_index = self.jf.series_index()
        result = []
        for raw in popular_series():
            item = self._show_from_discovery(raw)
            local = local_index.get(item.ids.imdb.lower())
            if local:
                item.with_library(local.get("Id") or "")
            result.append(item)
        return result

    def trending_movies(self):
        local_index = self.jf.movie_index()
        result = []
        for raw in movie_catalog("imdbRating"):
            item = self._movie_from_discovery(raw)
            local = local_index.get(item.ids.imdb.lower())
            if local:
                item.with_library(local.get("Id") or "")
            result.append(item)
        return result

    def trending_shows(self):
        local_index = self.jf.series_index()
        result = []
        for raw in series_catalog("imdbRating"):
            item = self._show_from_discovery(raw)
            local = local_index.get(item.ids.imdb.lower())
            if local:
                item.with_library(local.get("Id") or "")
            result.append(item)
        return result

    def search_movies(self, query):
        local_index = self.jf.movie_index()
        result = []
        for raw in search_movies(query):
            item = self._movie_from_discovery(raw)
            local = local_index.get(item.ids.imdb.lower())
            if local:
                item.with_library(local.get("Id") or "")
            result.append(item)
        return result

    def search_shows(self, query):
        local_index = self.jf.series_index()
        result = []
        for raw in search_series(query):
            item = self._show_from_discovery(raw)
            local = local_index.get(item.ids.imdb.lower())
            if local:
                item.with_library(local.get("Id") or "")
            result.append(item)
        return result

    def local_seasons(self, series_id, imdb_id="", show_title=""):
        """
        Normalize Jellyfin season containers directly.

        No pre-filtering or metadata repair is performed here.
        """
        result = []
        for season in self.jf.seasons(series_id):
            number = int(season.get("IndexNumber") or 0)
            season_id = season.get("Id") or ""
            image_tags = season.get("ImageTags") or {}

            season_art = (
                self.jf.image_url(season_id)
                if image_tags.get("Primary") or season.get("PrimaryImageTag")
                else ""
            )

            result.append(MediaItem(
                media_type="season",
                title=season.get("Name") or ("Specials" if number == 0 else f"Season {number}"),
                show_title=show_title,
                season=number,
                plot=season.get("Overview") or "",
                ids=MediaIds(imdb=imdb_id, jellyfin=season_id),
                art=MediaArt(poster=season_art),
                in_library=True,
                local=True,
                is_folder=True,
                source="jellyfin",
                raw=season,
                playback={"series_id": series_id, "season_id": season_id},
            ))

        result.sort(key=lambda item: item.season)
        return result

    def local_episodes(self, series_id, season_id, imdb_id="", show_title=""):
        """
        Normalize Jellyfin episodes directly.

        Jellyfin is trusted for local episode title, plot, identity, artwork,
        resume state and playback target.
        """
        result = []

        for episode in self.jf.episodes(series_id, season_id):
            item_id = episode.get("Id") or ""
            season = int(episode.get("ParentIndexNumber") or 0)
            number = int(episode.get("IndexNumber") or 0)

            image_tags = episode.get("ImageTags") or {}
            episode_art = (
                self.jf.image_url(item_id)
                if image_tags.get("Primary") or episode.get("PrimaryImageTag")
                else ""
            )

            user_data = episode.get("UserData") or {}
            position = int(user_data.get("PlaybackPositionTicks") or 0) / 10000000
            duration = int(episode.get("RunTimeTicks") or 0) / 10000000

            result.append(MediaItem(
                media_type="episode",
                title=episode.get("Name") or f"Episode {number}",
                show_title=episode.get("SeriesName") or show_title,
                season=season,
                episode=number,
                plot=episode.get("Overview") or "",
                ids=MediaIds(imdb=imdb_id, jellyfin=item_id),
                art=MediaArt(
                    poster=episode_art,
                    thumb=episode_art,
                ),
                resume=ResumeState(position, duration),
                in_library=True,
                local=True,
                source="jellyfin",
                raw=episode,
                playback={"item_id": item_id},
            ))

        result.sort(key=lambda item: item.episode)
        return result

    def discovery_seasons(self, imdb_id, show_title=""):
        details = series_details(imdb_id)
        season_numbers = sorted({
            int(video.get("season") or 0)
            for video in details.get("videos", [])
        })
        show_poster = details.get("poster") or ""
        result = []
        for number in season_numbers:
            label = "Specials" if number == 0 else f"Season {number}"
            result.append(MediaItem(
                media_type="season",
                title=label,
                show_title=show_title or details.get("name") or "",
                season=number,
                ids=MediaIds(imdb=imdb_id),
                art=MediaArt(poster=show_poster),
                is_folder=True,
                source="discovery",
            ))
        return result

    def discovery_episodes(self, imdb_id, season_number):
        details = series_details(imdb_id)
        show_title = details.get("name") or details.get("title") or ""
        show_poster = details.get("poster") or ""
        result = []
        for video in details.get("videos", []):
            season = int(video.get("season") or 0)
            episode = int(video.get("episode") or 0)
            if season != int(season_number):
                continue
            metadata = progress_metadata(imdb_id, "series", season, episode)
            result.append(MediaItem(
                media_type="episode",
                title=metadata.get("title") or f"Episode {episode}",
                show_title=show_title,
                season=season,
                episode=episode,
                plot=metadata.get("plot") or "",
                ids=MediaIds(imdb=imdb_id),
                art=MediaArt(
                    poster=show_poster,
                    thumb=video.get("thumbnail") or "",
                    fanart=details.get("background") or "",
                ),
                source="discovery",
                raw=video,
            ))
        result.sort(key=lambda item: item.episode)
        return result
