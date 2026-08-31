
const APOLLO_DEFAULT_MEDIA_ROWS = [
  {
    id: "continue",
    title: "Continue Watching",
    kind: "mixed",
    items: [
      { title: "21 Jump Street", subtitle: "42 min left", progress: 58, poster: "poster-one", watched: false },
      { title: "The Last of Us", subtitle: "S2 · E3", progress: 34, poster: "poster-two", watched: false },
      { title: "Dune", subtitle: "1h 12m left", progress: 67, poster: "poster-three", watched: false }
    ]
  },
  { id: "up_next", title: "Up Next", kind: "episodes", items: [] },
  { id: "trending_shows", title: "Trending Shows", kind: "shows", items: [] },
  { id: "trending_movies", title: "Trending Movies", kind: "movies", items: [] },
  {
    id: "popular_shows",
    title: "Popular Shows",
    kind: "discovery",
    items: [
      { title: "Thunderbolts*", subtitle: "2025", poster: "poster-fourteen", watched: false },
      { title: "Andor", subtitle: "2025", poster: "poster-fifteen", watched: false },
      { title: "The Studio", subtitle: "2025", poster: "poster-sixteen", watched: false }
    ]
  },
  {
    id: "popular_movies",
    title: "Popular Movies",
    kind: "discovery",
    items: [
      { title: "Fantastic Four", subtitle: "2025", poster: "poster-eleven", watched: false },
      { title: "Alien: Earth", subtitle: "2025", poster: "poster-twelve", watched: false },
      { title: "Weapons", subtitle: "2025", poster: "poster-thirteen", watched: false }
    ]
  }
];

const APOLLO_DEFAULT_LIBRARY = {
  movies: [
    { title: "21 Jump Street", subtitle: "2012", poster: "poster-one", watched: true },
    { title: "The Batman", subtitle: "2022", poster: "poster-four", watched: true },
    { title: "Dune", subtitle: "2021", poster: "poster-three", watched: true },
    { title: "Sinners", subtitle: "2025", poster: "poster-five", watched: false },
    { title: "Interstellar", subtitle: "2014", poster: "poster-eight", watched: true },
    { title: "Fantastic Four", subtitle: "2025", poster: "poster-eleven", watched: false }
  ],
  shows: [
    { title: "The Last of Us", subtitle: "2 Seasons", poster: "poster-two", watched: false },
    { title: "Severance", subtitle: "2 Seasons", poster: "poster-six", watched: false },
    { title: "Dark Matter", subtitle: "1 Season", poster: "poster-seven", watched: true },
    { title: "Shōgun", subtitle: "1 Season", poster: "poster-nine", watched: true },
    { title: "The Penguin", subtitle: "1 Season", poster: "poster-ten", watched: false },
    { title: "Andor", subtitle: "2 Seasons", poster: "poster-fifteen", watched: false }
  ]
};

const APOLLO_DEFAULT_LIBRARY_HOME_ROWS = [
  { id: "recently_released_episodes", title: "Recently Released Episodes", kind: "episodes", items: [] },
  { id: "recently_added_shows", title: "Recently Added Shows", kind: "shows", items: [] },
  { id: "recently_released_movies", title: "Recently Released Movies", kind: "movies", items: [] },
  { id: "recently_added_movies", title: "Recently Added Movies", kind: "movies", items: [] }
];

// Matches Apollo's existing addon completion behavior in service.py.
const APOLLO_CARD_VERSION = "0.9.83";
const APOLLO_COMPLETION_RATIO = 0.90;
const APOLLO_CONTINUE_POLL_MS = 10000;
const APOLLO_CONTINUE_PERSIST_MS = 1500;

class ApolloMediaCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("apollo-media-card-editor");
  }

  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    const hadConfig = Boolean(this.config);
    const previousPlayerEntity = this.configuredPlayerEntity();
    this.config = {
      catalog_entity: "sensor.apollo_movie_catalog",
      continue_entity: "sensor.apollo_continue_watching",
      library_movies_entity: "sensor.apollo_library_movies",
      library_shows_entity: "sensor.apollo_library_shows",
      recently_released_episodes_entity: "sensor.apollo_recently_released_episodes",
      recently_added_shows_entity: "sensor.apollo_recently_added_shows",
      recently_released_movies_entity: "sensor.apollo_recently_released_movies",
      recently_added_movies_entity: "sensor.apollo_recently_added_movies",
      popular_movies_entity: "sensor.apollo_popular_movies",
      trending_movies_entity: "sensor.apollo_trending_movies",
      popular_shows_entity: "sensor.apollo_popular_shows",
      trending_shows_entity: "sensor.apollo_trending_shows",
      up_next_entity: "sensor.apollo_up_next",
      sources_entity: "sensor.apollo_streams",
      play_script: "script.apollo_play",
      load_streams_script: "script.apollo_load_streams",
      play_stream_script: "script.apollo_play_stream",
      switch_remote_script: "script.apollo_switch_remote",
      switch_local_script: "script.apollo_switch_local",
      try_next_script: "script.apollo_try_next",
      flag_script: "script.apollo_flag_stream",
      show_script: "script.apollo_show_on_tv",
      browse_entity: "sensor.apollo_browser_items",
      browse_script: "script.apollo_browse_title",
      refresh_script: "script.apollo_refresh_media_home",
      progress_refresh_script: "script.apollo_refresh_continue_watching",
      remove_continue_script: "script.apollo_remove_continue",
      library_movies_refresh_script: "script.apollo_refresh_library_movies",
      active_entity: "sensor.apollo_active_playback",
      active_refresh_script: "script.apollo_refresh_active_playback",
      ams_enabled: true,
      ams_addon_slug: "",
      ams_profile: "",
      ams_profile_id: "",
      ...(config || {})
    };

    const nextPlayerEntity = this.configuredPlayerEntity();
    if (hadConfig) {
      if (previousPlayerEntity !== nextPlayerEntity) {
        this.resetKodiTargetState();
        if (this._hass && nextPlayerEntity) {
          this.scheduleContinueWatchingRefresh(0, true);
        }
      }
      if (this._rendered) this.renderPreservingState();
      return;
    }

    // Display sizing is global by default. The context maps remain only as
    // compatibility plumbing for the current CSS. A future override feature
    // can selectively replace them without making repeated tuning the default.
    const configuredPosterSize = Number(this.config.poster_size ?? 118);
    const displayContexts = ["home", "media-home", "media-library-home", "media-library-movies", "media-library-shows"];

    let savedPosterSize = null;
    let savedTextScale = null;
    let savedCardSpacing = null;
    try {
      savedPosterSize = Number(localStorage.getItem("apollo-media.poster-size"));
      if (!Number.isFinite(savedPosterSize) || savedPosterSize < 90 || savedPosterSize > 150) {
        savedPosterSize = null;
      }

      savedTextScale = Number(localStorage.getItem("apollo-media.text-scale"));
      if (!Number.isFinite(savedTextScale) || savedTextScale < 80 || savedTextScale > 130) {
        savedTextScale = null;
      }

      savedCardSpacing = Number(localStorage.getItem("apollo-media.card-spacing"));
      if (!Number.isFinite(savedCardSpacing) || savedCardSpacing < 6 || savedCardSpacing > 28) {
        savedCardSpacing = null;
      }

      // One-time compatibility migration from the older per-view settings.
      if (savedPosterSize === null) {
        for (const context of displayContexts) {
          const legacyPosterSize = Number(localStorage.getItem(`apollo-media.poster-size.${context}`));
          if (Number.isFinite(legacyPosterSize) && legacyPosterSize >= 90 && legacyPosterSize <= 150) {
            savedPosterSize = legacyPosterSize;
            break;
          }
        }
      }

      if (savedTextScale === null) {
        for (const context of displayContexts) {
          const legacyTextScale = Number(localStorage.getItem(`apollo-media.text-scale.${context}`));
          if (Number.isFinite(legacyTextScale) && legacyTextScale >= 80 && legacyTextScale <= 130) {
            savedTextScale = legacyTextScale;
            break;
          }
        }
      }
    } catch (_) {
      savedPosterSize = null;
      savedTextScale = null;
      savedCardSpacing = null;
    }

    this.posterSize = Math.min(150, Math.max(90, savedPosterSize ?? configuredPosterSize));
    this.textScale = Math.min(130, Math.max(80, savedTextScale ?? 100));
    this.cardSpacing = Math.min(28, Math.max(6, savedCardSpacing ?? 14));
    this.posterSizes = {};
    this.textScales = {};
    this.sortModes = {};

    displayContexts.forEach(context => {
      this.posterSizes[context] = this.posterSize;
      this.textScales[context] = this.textScale;
      try {
        this.sortModes[context] = localStorage.getItem(`apollo-media.sort.${context}`) || "default";
      } catch (_) {
        this.sortModes[context] = "default";
      }
    });

    this.mediaRows =
      this.config?.media?.home_rows && Array.isArray(this.config.media.home_rows)
        ? [...this.config.media.home_rows]
        : [...APOLLO_DEFAULT_MEDIA_ROWS];

    let savedRowOrder = [];
    try {
      savedRowOrder =
        JSON.parse(localStorage.getItem("apollo-media.media-row-order") || "[]") || [];
    } catch (_) {
      savedRowOrder = [];
    }

    if (Array.isArray(savedRowOrder) && savedRowOrder.length) {
      const orderMap = new Map(savedRowOrder.map((id, index) => [id, index]));

      this.mediaRows.sort((a, b) => {
        const aIndex = orderMap.has(a.id) ? orderMap.get(a.id) : Number.MAX_SAFE_INTEGER;
        const bIndex = orderMap.has(b.id) ? orderMap.get(b.id) : Number.MAX_SAFE_INTEGER;
        return aIndex - bIndex;
      });
    }

    let savedRowVisibility = {};
    try {
      savedRowVisibility =
        JSON.parse(localStorage.getItem("apollo-media.media-row-visibility") || "{}") || {};
    } catch (_) {
      savedRowVisibility = {};
    }

    const configuredRowVisibility = this.config?.media?.row_visibility || {};

    this.mediaRowVisibility = {};
    this.mediaRows.forEach(row => {
      if (Object.prototype.hasOwnProperty.call(savedRowVisibility, row.id)) {
        this.mediaRowVisibility[row.id] = Boolean(savedRowVisibility[row.id]);
      } else if (Object.prototype.hasOwnProperty.call(configuredRowVisibility, row.id)) {
        this.mediaRowVisibility[row.id] = Boolean(configuredRowVisibility[row.id]);
      } else {
        this.mediaRowVisibility[row.id] = true;
      }
    });

    this.library =
      this.config?.media?.library || APOLLO_DEFAULT_LIBRARY;

    // Sample content is design-time fallback only. Live cards start empty and
    // are filled from Apollo sensors so placeholder titles never masquerade as media.
    this.mediaRows.forEach(row => { row.items = []; });
    this.library = { movies: [], shows: [] };
    this.libraryRenderLimits = { shows: 60, movies: 60 };
    this.libraryHomeRows = APOLLO_DEFAULT_LIBRARY_HOME_ROWS.map(row => ({ ...row, items: [] }));
    this.catalogItems = [];
    this.browserItems = [];
    this._nowPlayingSeeking = false;
    this._nowPlayingScrubPosition = null;
    this._nowPlayingPlayer = null;
    this._streamPickerOpen = false;
    this._streamPickerTarget = "";
    this._streamPickerContext = null;
    this._streamPickerLoading = false;
    this._streamPickerPendingPath = "";
    this._flagMenuOpen = false;
    this._activeContextNotBefore = 0;
    this._expectedPlaybackSource = "";
    this._posterSizePopupOpen = false;
    this._posterSizePopupContext = "";
    this._textSizePopupOpen = false;
    this._textSizePopupContext = "";
    this._paddingPopupOpen = false;

    // Media refresh is a card-wide transaction, not page-local UI state.
    // Home Assistant's refresh script entity is authoritative for running/
    // complete status, so this survives Apollo navigation and full rerenders.
    this._refreshScriptState = null;
    this._refreshRequested = false;
    this._refreshRequestedTimer = null;
    this._refreshSuccessUntil = 0;
    this._refreshSuccessTimer = null;
    this._amsContinueItems = [];
    this._amsContinueReady = false;
    this._amsContinueLoading = false;
    this._amsContinueQueued = false;
    this._amsIngressBase = "";
    this._amsAddonSlug = "";
    this._amsProfileId = "";
    this._amsLastContinueLoad = 0;
    this._amsArtworkUrls = new Map();
  }

  set hass(hass) {
    this._hass = hass;
    if (this.config?.ams_enabled !== false) this.scheduleAmsContinueWatchingLoad();
    if (this.config?.ams_enabled === false) this.observeMediaRefreshState(hass);
    const playerEntity = this.configuredPlayerEntity();
    const player = playerEntity ? hass.states[playerEntity] : undefined;
    this._nowPlayingPlayer = player || null;

    const feedIds = [
      this.config.continue_entity, this.config.library_movies_entity,
      this.config.library_shows_entity,
      this.config.recently_released_episodes_entity, this.config.recently_added_shows_entity,
      this.config.recently_released_movies_entity, this.config.recently_added_movies_entity,
      this.config.popular_movies_entity,
      this.config.trending_movies_entity, this.config.popular_shows_entity,
      this.config.trending_shows_entity, this.config.up_next_entity, this.config.browse_entity,
      this.config.catalog_entity, this.config.sources_entity
    ];
    const feedStamps = Object.fromEntries(
      feedIds.map(id => [id, hass.states[id]?.last_updated || ""])
    );
    const changedFeedIds = this._feedStamps
      ? feedIds.filter(id => feedStamps[id] !== this._feedStamps[id])
      : feedIds;
    const optimisticPatched = playerEntity
      ? this.observeApolloPlayback(player)
      : false;
    if (playerEntity) {
      this.observeKodiPlayer(player);
      this.requestActiveApolloContext(player);
    } else {
      this.resetKodiTargetState();
    }

    const targetedContinueUpdate =
      changedFeedIds.length === 1 &&
      changedFeedIds[0] === this.config.continue_entity;
    const reconciliationIdentity = targetedContinueUpdate
      ? this._pendingPlaybackReconciliation
      : null;
    const beforeContinueItems = targetedContinueUpdate
      ? [...(this.mediaRows.find(row => row.id === "continue")?.items || [])]
      : [];
    const beforeContinueSignature = targetedContinueUpdate
      ? this.continueWatchingRenderSignature(reconciliationIdentity)
      : "";

    if (changedFeedIds.length) {
      this.applyApolloFeeds(changedFeedIds);
    }
    const continueFeedChanged = targetedContinueUpdate
      ? beforeContinueSignature !==
        this.continueWatchingRenderSignature(reconciliationIdentity)
      : changedFeedIds.length > 0;
    const afterContinueItems = targetedContinueUpdate
      ? [...(this.mediaRows.find(row => row.id === "continue")?.items || [])]
      : [];
    const continueStructureChanged = targetedContinueUpdate &&
      this.continueWatchingStructureSignature(beforeContinueItems) !==
        this.continueWatchingStructureSignature(afterContinueItems);
    this._feedStamps = feedStamps;

    if (!this._rendered) {
      this.render();
      this._rendered = true;
      this.bindEvents();
      this.showScreen("home");
      this.showMediaSection("home");
      this.showLibraryTab("home");
    } else if (targetedContinueUpdate && continueFeedChanged && !continueStructureChanged && !optimisticPatched) {
      this.patchContinueWatchingDom();
    } else if (
      (targetedContinueUpdate && continueFeedChanged) ||
      (optimisticPatched && (changedFeedIds.length === 0 || targetedContinueUpdate))
    ) {
      this.replaceContinueWatchingRail();
    } else if (continueFeedChanged || optimisticPatched) {
      this.renderPreservingState();
    }
    this.updateNowPlaying(player);
    this.updateRefreshControl();
    if (this._streamPickerOpen && changedFeedIds.includes(this.config.sources_entity)) {
      this._streamPickerLoading = false;
      this.renderStreamPicker();
    }
  }

  disconnectedCallback() {
    this.resetKodiTargetState();
    if (this._refreshRequestedTimer) window.clearTimeout(this._refreshRequestedTimer);
    if (this._refreshSuccessTimer) window.clearTimeout(this._refreshSuccessTimer);
    for (const url of this._amsArtworkUrls?.values?.() || []) {
      try { URL.revokeObjectURL(url); } catch (_) {}
    }
    this._amsArtworkUrls?.clear?.();
  }

  getCardSize() {
    return 12;
  }

  asArray(value) {
    if (Array.isArray(value)) return value;
    if (typeof value === "string") {
      try { const parsed = JSON.parse(value); return Array.isArray(parsed) ? parsed : []; }
      catch (_) { return []; }
    }
    return [];
  }

  artworkUrl(value) {
    if (!value) return "";
    let url = String(value);
    if (url.startsWith("image://")) {
      url = url.slice(8).replace(/\/$/, "");
      try { url = decodeURIComponent(url); } catch (_) {}
    }
    return url;
  }

  fileParams(file) {
    try { return Object.fromEntries(new URLSearchParams(String(file || "").split("?", 2)[1] || "")); }
    catch (_) { return {}; }
  }

  apolloPluginUrl(action, params = {}) {
    const query = new URLSearchParams();
    query.set("action", String(action || ""));
    Object.entries(params || {}).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") return;
      query.set(key, String(value));
    });
    return `plugin://plugin.video.apollomedia/?${query.toString()}`;
  }

  async ensureAmsIngressBase() {
    if (this._amsIngressBase) return this._amsIngressBase;
    if (!this._hass?.callWS) throw new Error("Home Assistant WebSocket API is unavailable");

    const sessionResult = await this._hass.callWS({
      type: "supervisor/api",
      endpoint: "/ingress/session",
      method: "post"
    });
    const session = String(sessionResult?.session || sessionResult?.data?.session || "");
    if (!session) throw new Error("Home Assistant did not create an ingress session");
    document.cookie = `ingress_session=${session};path=/api/hassio_ingress/;SameSite=Strict${location.protocol === "https:" ? ";Secure" : ""}`;

    let slug = String(this.config?.ams_addon_slug || "").trim();
    if (!slug) {
      const panelResult = await this._hass.callWS({
        type: "supervisor/api",
        endpoint: "/ingress/panels",
        method: "get"
      });
      const panels = panelResult?.panels || panelResult?.data?.panels || {};
      slug = Object.keys(panels).find(key =>
        key === "apollo_media_server" ||
        key.endsWith("_apollo_media_server") ||
        /apollo media/i.test(String(panels[key]?.title || ""))
      ) || "";
    }
    if (!slug) throw new Error("Apollo Media Server ingress panel was not found");

    const addon = await this._hass.callWS({
      type: "supervisor/api",
      endpoint: `/addons/${slug}/info`,
      method: "get"
    });
    const ingressUrl = String(addon?.ingress_url || addon?.data?.ingress_url || "").trim();
    if (!ingressUrl) throw new Error("Apollo Media Server does not expose an ingress URL");

    this._amsAddonSlug = slug;
    this._amsIngressBase = ingressUrl.endsWith("/") ? ingressUrl : `${ingressUrl}/`;
    return this._amsIngressBase;
  }

  async amsFetch(path, options = {}, retryAuth = true) {
    const base = await this.ensureAmsIngressBase();
    const response = await fetch(`${base}${String(path || "").replace(/^\/+/, "")}`, {
      credentials: "same-origin",
      cache: "no-store",
      ...options,
      headers: {
        Accept: "application/json",
        ...(options.headers || {})
      }
    });
    if (response.status === 401 && retryAuth) {
      this._amsIngressBase = "";
      this._amsAddonSlug = "";
      await this.ensureAmsIngressBase();
      return this.amsFetch(path, options, false);
    }
    if (!response.ok) throw new Error(`AMS ${response.status}: ${await response.text()}`);
    const contentType = String(response.headers.get("content-type") || "");
    return contentType.includes("application/json") ? response.json() : response.text();
  }

  async resolveAmsProfileId() {
    const configuredId = String(this.config?.ams_profile_id || "").trim();
    if (configuredId) return configuredId;
    if (this._amsProfileId) return this._amsProfileId;

    const profiles = await this.amsFetch("profiles");
    if (!Array.isArray(profiles) || profiles.length === 0) throw new Error("AMS has no profiles");
    const configuredName = String(this.config?.ams_profile || "").trim().toLowerCase();
    let profile = configuredName
      ? profiles.find(item => String(item?.name || "").trim().toLowerCase() === configuredName)
      : null;
    if (!profile && profiles.length === 1) profile = profiles[0];
    if (!profile) throw new Error("AMS has multiple profiles; configure ams_profile or ams_profile_id");
    this._amsProfileId = String(profile.id || "");
    if (!this._amsProfileId) throw new Error("AMS profile has no ID");
    return this._amsProfileId;
  }

  amsContinueItem(item) {
    const mediaType = String(item?.media_type || "movie").toLowerCase();
    const isEpisode = mediaType === "episode";
    const season = Number(item?.season || 0);
    const episode = Number(item?.episode || 0);
    const episodeTitle = String(item?.title || "Unknown");
    const seriesTitle = String(item?.series_title || "").trim();
    const displayTitle = isEpisode ? (seriesTitle || episodeTitle) : episodeTitle;
    const imdb = String(item?.imdb_id || "");
    const tmdb = String(item?.tmdb_id || "");
    const jellyfinId = String(item?.jellyfin_item_id || "");
    const posterUrl = this.artworkUrl(item?.poster_url || "");
    const backdropUrl = this.artworkUrl(item?.backdrop_url || "");
    const overview = String(item?.overview || "");
    const year = Number(item?.year || 0);
    const remoteMediaType = isEpisode ? "series" : "movie";
    const commonRemote = {
      imdb,
      media_type: remoteMediaType,
      season,
      episode,
      title: episodeTitle,
      resume_item_id: jellyfinId
    };
    const showTarget = isEpisode && imdb
      ? this.apolloPluginUrl("discovery_seasons", { imdb, title: seriesTitle || displayTitle, native_local: "1" })
      : "";
    const seasonTarget = isEpisode && imdb
      ? this.apolloPluginUrl("discovery_episodes", {
          imdb,
          season,
          title: seriesTitle || displayTitle,
          native_local: "1",
          apollo_media_type: "season",
          presentation_context: "browse",
          in_library: "1",
          show_title: seriesTitle || displayTitle,
          show_target: showTarget
        })
      : "";
    const playTarget = imdb
      ? this.apolloPluginUrl("play_resolved", {
          source: "ams",
          imdb,
          media_type: remoteMediaType,
          season,
          episode,
          title: episodeTitle
        })
      : (jellyfinId
          ? this.apolloPluginUrl("play_resolved", {
              source: "jellyfin",
              item_id: jellyfinId,
              title: episodeTitle
            })
          : "");
    return {
      title: displayTitle,
      series_title: isEpisode ? (seriesTitle || displayTitle) : "",
      episode_title: isEpisode ? episodeTitle : "",
      subtitle: isEpisode ? `S${season} E${episode}${episodeTitle ? ` · ${episodeTitle}` : ""}` : "",
      poster: posterUrl,
      ams_artwork_id: "",
      fanart: backdropUrl,
      plot: overview,
      year,
      media_type: isEpisode ? "episode" : "movie",
      season: isEpisode ? season : 0,
      episode: isEpisode ? episode : 0,
      progress: Number(item?.progress_fraction || 0) * 100,
      resume_position: Number(item?.position_seconds || 0),
      resume_duration: Number(item?.duration_seconds || 0),
      imdb,
      tmdb,
      jellyfin_item_id: jellyfinId,
      browseTarget: showTarget,
      seasonTarget,
      removeTarget: this.apolloPluginUrl("remove_continue", {
        source: "jellyfin",
        item_id: jellyfinId,
        imdb,
        season,
        episode
      }),
      remoteAutoTarget: imdb ? this.apolloPluginUrl("play_external", commonRemote) : "",
      remoteChooseTarget: imdb ? this.apolloPluginUrl("remote_stream_list", commonRemote) : "",
      playTarget,
      file: playTarget,
      is_folder: false,
      in_library: Boolean(item?.available_locally),
      watched: false,
      presentation_context: "continue",
      ams_media_id: String(item?.media_id || ""),
      ams_updated_at: String(item?.updated_at || "")
    };
  }

  async amsArtworkBlobUrl(itemId, retryAuth = true) {
    const key = String(itemId || "").trim();
    if (!key) return "";
    if (this._amsArtworkUrls.has(key)) return this._amsArtworkUrls.get(key);
    const base = await this.ensureAmsIngressBase();
    const response = await fetch(`${base}jellyfin/image/${encodeURIComponent(key)}`, {
      credentials: "same-origin",
      cache: "force-cache"
    });
    if (response.status === 401 && retryAuth) {
      this._amsIngressBase = "";
      this._amsAddonSlug = "";
      await this.ensureAmsIngressBase();
      return this.amsArtworkBlobUrl(key, false);
    }
    if (!response.ok) throw new Error(`AMS artwork ${response.status}`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    this._amsArtworkUrls.set(key, url);
    return url;
  }

  async hydrateAmsArtwork(items) {
    const ids = [...new Set((items || []).map(item => String(item?.ams_artwork_id || "")).filter(Boolean))];
    await Promise.all(ids.map(async id => {
      try { await this.amsArtworkBlobUrl(id); } catch (error) {
        console.warn("Apollo AMS artwork unavailable", id, error);
      }
    }));
    return (items || []).map(item => {
      const id = String(item?.ams_artwork_id || "");
      return id && this._amsArtworkUrls.has(id)
        ? { ...item, poster: this._amsArtworkUrls.get(id) }
        : item;
    });
  }

  async loadAmsContinueWatching({ sync = false } = {}) {
    if (this.config?.ams_enabled === false) return false;
    if (this._amsContinueLoading) {
      this._amsContinueQueued = this._amsContinueQueued || sync;
      return { success: true, changed: false, queued: true };
    }
    this._amsContinueLoading = true;
    try {
      if (sync) {
        await this.amsFetch("jellyfin/sync", { method: "POST" });
      }
      const profileId = await this.resolveAmsProfileId();
      const rows = await this.amsFetch(`profiles/${encodeURIComponent(profileId)}/continue-watching`);
      if (!Array.isArray(rows)) throw new Error("AMS Continue Watching response is not a list");
      const mapped = this.dedupeApolloItems(rows.map(item => this.amsContinueItem(item)));
      const hydrated = await this.hydrateAmsArtwork(mapped);
      const previousSignature = JSON.stringify((this._amsContinueItems || []).map(item => [
        item.ams_media_id, item.ams_updated_at, item.progress, item.poster
      ]));
      const nextSignature = JSON.stringify(hydrated.map(item => [
        item.ams_media_id, item.ams_updated_at, item.progress, item.poster
      ]));
      const changed = !this._amsContinueReady || previousSignature !== nextSignature;
      this._amsContinueItems = hydrated;
      this._amsContinueReady = true;
      this._amsLastContinueLoad = Date.now();
      const continueRow = this.mediaRows?.find(row => row.id === "continue");
      if (continueRow) continueRow.items = [...this._amsContinueItems];
      this._continueRefreshErrorLogged = false;
      if (changed && this._rendered) this.replaceContinueWatchingRail();
      return { success: true, changed };
    } catch (error) {
      // Keep the legacy HA feed as a safe fallback until AMS is reachable.
      if (!this._amsContinueReady && !this._amsContinueErrorLogged) {
        console.warn("Apollo AMS Continue Watching unavailable; using Home Assistant fallback", error);
        this._amsContinueErrorLogged = true;
      }
      return { success: false, changed: false, error };
    } finally {
      this._amsContinueLoading = false;
      if (this._amsContinueQueued) {
        const queuedSync = this._amsContinueQueued;
        this._amsContinueQueued = false;
        window.setTimeout(() => this.loadAmsContinueWatching({ sync: Boolean(queuedSync) }), 100);
      }
    }
  }

  scheduleAmsContinueWatchingLoad(force = false) {
    if (this.config?.ams_enabled === false || this._amsContinueLoading) return;
    const age = Date.now() - Number(this._amsLastContinueLoad || 0);
    if (!force && this._amsContinueReady && age < APOLLO_CONTINUE_POLL_MS) return;
    Promise.resolve().then(() => this.loadAmsContinueWatching()).catch(() => {});
  }

  apolloItems(entityId) {
    const entity = this._hass?.states?.[entityId];
    const files = this.asArray(entity?.attributes?.movies);
    return files.map(file => {
      const params = this.fileParams(file.file);
      const label = String(file.label || "");
      const cleanLabel = label.replace(/\[\/?COLOR(?: [^\]]+)?\]/gi, "").replace(/\s*[•·]\s*$/, "").trim();
      const action = params.action || "";
      const showFolder = ["discovery_seasons", "seasons"].includes(action);
      const fileSeason = Number(file.season);
      const fileEpisode = Number(file.episode);
      const paramSeason = Number(params.season);
      const paramEpisode = Number(params.episode);
      const rawSeason = Number.isFinite(fileSeason) && fileSeason >= 0 ? fileSeason : paramSeason;
      const rawEpisode = Number.isFinite(fileEpisode) && fileEpisode >= 0 ? fileEpisode : paramEpisode;
      const season = Number.isFinite(rawSeason) && rawSeason >= 0 ? rawSeason : 0;
      const episode = Number.isFinite(rawEpisode) && rawEpisode > 0 ? rawEpisode : 0;
      const canonicalType = String(params.apollo_media_type || "").trim() ||
        (episode ? "episode" : (showFolder ? "show" : (params.media_type === "series" ? "show" : (params.media_type || "movie"))));
      const episodeTitle = canonicalType === "episode"
        ? String(params.title || file.title || cleanLabel || "").trim()
        : "";
      const showTitle = canonicalType === "episode"
        ? String(params.show_title || file.showtitle || "").trim()
        : (canonicalType === "show"
            ? String(file.title || cleanLabel || params.title || "").trim()
            : (canonicalType === "season" ? String(params.show_title || file.showtitle || "").trim() : ""));
      const releaseDate = String(params.release_date || "").trim();
      const dateAdded = String(params.date_added || file.dateadded || "").trim();
      const lastEpisodeAdded = String(params.last_episode_added || "").trim();
      return {
        title: canonicalType === "episode" ? (showTitle || episodeTitle) : (file.title || cleanLabel || params.title || "Unknown"),
        series_title: canonicalType === "episode" || canonicalType === "season"
          ? showTitle
          : (canonicalType === "show" ? (file.title || cleanLabel || params.title || "") : ""),
        episode_title: canonicalType === "episode" ? episodeTitle : "",
        subtitle: canonicalType === "episode"
          ? `S${season} E${episode}${episodeTitle ? ` · ${episodeTitle}` : ""}`
          : (canonicalType === "show"
              ? (releaseDate ? String(releaseDate).slice(0, 4) : String(file.year || ""))
              : String(file.year || "")),
        poster: this.artworkUrl(file.thumbnail || file.art?.poster || ""),
        fanart: this.artworkUrl(file.fanart || file.art?.fanart || ""),
        plot: file.plot || "",
        dateadded: dateAdded,
        release_date: releaseDate,
        last_episode_added: lastEpisodeAdded,
        presentation_context: params.presentation_context || "",
        year: Number(file.year || 0),
        media_type: canonicalType,
        season: canonicalType === "episode" || canonicalType === "season" ? season : 0,
        episode: canonicalType === "episode" ? episode : 0,
        progress: (() => {
          const resume = file.resume || {};
          const position = Number(resume.position ?? resume.Position ?? 0);
          const total = Number(resume.total ?? resume.Total ?? 0);
          return total > 0 && position > 0
            ? Math.min(100, Math.max(0, (position / total) * 100))
            : undefined;
        })(),
        resume_position: Number((file.resume || {}).position ?? (file.resume || {}).Position ?? 0),
        resume_duration: Number((file.resume || {}).total ?? (file.resume || {}).Total ?? 0),
        imdb: params.imdb || file.imdbnumber || "",
        tmdb: params.tmdb || "",
        jellyfin_item_id: params.jellyfin_item_id || "",
        browseTarget: params.show_target || (canonicalType === "show" ? (file.file || "") : ""),
        seasonTarget: params.season_target || (canonicalType === "season" ? (file.file || "") : ""),
        removeTarget: params.remove_target || "",
        remoteAutoTarget: params.remote_auto_target || "",
        remoteChooseTarget: params.remote_choose_target || "",
        playTarget: params.card_play_target || file.file || "",
        file: file.file || "",
        is_folder: canonicalType === "show" || canonicalType === "season" || ["discovery_seasons", "seasons", "discovery_episodes", "episodes"].includes(params.action || ""),
        in_library: params.in_library === "1" || label.includes("IN LIBRARY"),
        watched: params.watched === "1" || Number(file.playcount || 0) > 0
      };
    });
  }

  applyApolloFeeds(changedEntityIds = null) {
    const changed = changedEntityIds ? new Set(changedEntityIds) : null;
    const shouldApply = entityId => !changed || changed.has(entityId);
    const assign = (rowId, entityId) => {
      if (!shouldApply(entityId)) return;
      const row = this.mediaRows.find(item => item.id === rowId);
      if (row) row.items = this.apolloItems(entityId);
    };
    if (shouldApply(this.config.continue_entity)) {
      const continueRow = this.mediaRows.find(item => item.id === "continue");
      if (continueRow) {
        continueRow.items = this._amsContinueReady
          ? [...this._amsContinueItems]
          : this.dedupeApolloItems(this.apolloItems(this.config.continue_entity));
      }
    }
    assign("popular_movies", this.config.popular_movies_entity);
    assign("popular_shows", this.config.popular_shows_entity);
    assign("trending_movies", this.config.trending_movies_entity);
    assign("trending_shows", this.config.trending_shows_entity);
    assign("up_next", this.config.up_next_entity);
    const assignLibraryHome = (rowId, entityId) => {
      if (!shouldApply(entityId)) return;
      const row = this.libraryHomeRows.find(item => item.id === rowId);
      if (row) row.items = this.apolloItems(entityId);
    };
    assignLibraryHome("recently_released_episodes", this.config.recently_released_episodes_entity);
    assignLibraryHome("recently_added_shows", this.config.recently_added_shows_entity);
    assignLibraryHome("recently_released_movies", this.config.recently_released_movies_entity);
    assignLibraryHome("recently_added_movies", this.config.recently_added_movies_entity);
    if (shouldApply(this.config.library_movies_entity)) {
      this.library.movies = this.apolloItems(this.config.library_movies_entity);
    }
    if (shouldApply(this.config.library_shows_entity)) {
      this.library.shows = this.apolloItems(this.config.library_shows_entity);
    }
    if (shouldApply(this.config.catalog_entity)) {
      this.catalogItems = this.apolloItems(this.config.catalog_entity);
    }
    if (shouldApply(this.config.browse_entity)) {
      this.browserItems = this.apolloItems(this.config.browse_entity);
    }

    // Continue Watching deliberately uses series artwork for episodes. Episode
    // stills can be introduced later as an explicit display choice.
    const showPosters = new Map(
      this.library.shows
        .filter(show => show.title && show.poster)
        .map(show => [String(show.title).trim().toLowerCase(), show.poster])
    );
    const continueRow = this.mediaRows.find(row => row.id === "continue");
    if (continueRow) {
      continueRow.items = (continueRow.items || []).map(item => {
        if (item.media_type !== "episode" || item.ams_media_id) return item;
        const showPoster = showPosters.get(String(item.title || "").trim().toLowerCase());
        return showPoster ? { ...item, poster: showPoster } : item;
      });
    }

    if (this._pendingPlaybackReconciliation) {
      if (shouldApply(this.config.continue_entity)) {
        this.reconcilePlaybackProgress(this._pendingPlaybackReconciliation);
      } else {
        this.applyOptimisticProgress(this._pendingPlaybackReconciliation, false);
      }
    }
  }

  refreshScriptEntity(hass = this._hass) {
    return hass?.states?.[this.config?.refresh_script] || null;
  }

  refreshScriptRunning(hass = this._hass) {
    return String(this.refreshScriptEntity(hass)?.state || "").toLowerCase() === "on";
  }

  refreshVisualState() {
    const sharedRunning = this.config?.ams_enabled === false && this.refreshScriptRunning();
    if (this._refreshRequested || sharedRunning) return "running";
    if (Date.now() < Number(this._refreshSuccessUntil || 0)) return "success";
    return "idle";
  }

  observeMediaRefreshState(hass) {
    const current = String(this.refreshScriptEntity(hass)?.state || "off").toLowerCase();
    const previous = this._refreshScriptState;
    this._refreshScriptState = current;

    if (current === "on") {
      this._refreshRequested = false;
      if (this._refreshRequestedTimer) {
        window.clearTimeout(this._refreshRequestedTimer);
        this._refreshRequestedTimer = null;
      }
      // A new refresh supersedes any old success indicator.
      this._refreshSuccessUntil = 0;
      if (this._refreshSuccessTimer) {
        window.clearTimeout(this._refreshSuccessTimer);
        this._refreshSuccessTimer = null;
      }
      return;
    }

    // Only an observed HA on -> off transition means the entire script
    // transaction completed. Initial "off" must never produce a false check.
    if (previous === "on" && current !== "on") {
      this._refreshRequested = false;
      this._refreshSuccessUntil = Date.now() + 2800;
      if (this._refreshSuccessTimer) window.clearTimeout(this._refreshSuccessTimer);
      this._refreshSuccessTimer = window.setTimeout(() => {
        this._refreshSuccessTimer = null;
        this._refreshSuccessUntil = 0;
        this.updateRefreshControl();
      }, 2850);
    }
  }

  updateRefreshControl() {
    const button = this.querySelector(".refresh-action");
    if (!button) return;

    const icon = button.querySelector("ha-icon");
    const state = this.refreshVisualState();
    const running = state === "running";
    const success = state === "success";

    button.classList.toggle("refreshing", running);
    button.classList.toggle("refresh-success", success);
    button.disabled = running;
    button.setAttribute("aria-busy", running ? "true" : "false");
    button.setAttribute(
      "aria-label",
      running ? "Refreshing media" : (success ? "Media refresh complete" : "Refresh media home")
    );
    button.title = running ? "Refreshing media…" : (success ? "Media refresh complete" : "Refresh media home");

    if (icon) {
      const desired = success ? "mdi:check" : "mdi:refresh";
      if (icon.getAttribute("icon") !== desired) icon.setAttribute("icon", desired);
    }
  }

  beginMediaRefresh() {
    if (this.refreshVisualState() === "running") return false;

    // With AMS enabled, refresh is intentionally card-local. AMS profile data
    // is shared, but another card must not inherit this card's refresh UI or
    // trigger a Kodi-backed HA feed transaction.
    if (this.config?.ams_enabled !== false) {
      this._refreshRequested = true;
      this._refreshSuccessUntil = 0;
      this.updateRefreshControl();
      Promise.resolve(this.loadAmsContinueWatching({ sync: true }))
        .then(result => {
          this._refreshRequested = false;
          if (!result?.success) throw new Error("AMS refresh failed");
          this._refreshSuccessUntil = Date.now() + 2800;
          if (this._refreshSuccessTimer) window.clearTimeout(this._refreshSuccessTimer);
          this._refreshSuccessTimer = window.setTimeout(() => {
            this._refreshSuccessTimer = null;
            this._refreshSuccessUntil = 0;
            this.updateRefreshControl();
          }, 2850);
          this.updateRefreshControl();
        })
        .catch(error => {
          this._refreshRequested = false;
          this.updateRefreshControl();
          console.error("Apollo AMS refresh failed", error);
          this.notifyApolloError("Apollo Media Server refresh failed.");
        });
      return true;
    }

    const playerEntity = this.requirePlayerEntity();
    if (!playerEntity) return false;
    this._refreshRequested = true;
    this._refreshSuccessUntil = 0;
    this.updateRefreshControl();

    if (this._refreshRequestedTimer) window.clearTimeout(this._refreshRequestedTimer);
    this._refreshRequestedTimer = window.setTimeout(() => {
      this._refreshRequestedTimer = null;
      if (!this.refreshScriptRunning()) {
        this._refreshRequested = false;
        this.updateRefreshControl();
      }
    }, 1800);

    Promise.resolve(
      this.callApolloScript(this.config.refresh_script, { player_entity: playerEntity })
    ).catch(error => {
      this._refreshRequested = false;
      if (this._refreshRequestedTimer) {
        window.clearTimeout(this._refreshRequestedTimer);
        this._refreshRequestedTimer = null;
      }
      this.updateRefreshControl();
      console.error("Apollo media refresh failed", error);
      this.notifyApolloError("Apollo media refresh could not be started.");
    });
    return true;
  }

  callApolloScript(entityId, variables = {}) {
    const parts = String(entityId || "").split(".");
    if (parts.length !== 2) return Promise.resolve();
    return this._hass.callService(parts[0], parts[1], variables);
  }

  configuredPlayerEntity() {
    const playerEntity = String(this.config?.player_entity || "").trim();
    return playerEntity.startsWith("media_player.") ? playerEntity : "";
  }

  configuredAudioEntity() {
    // Deliberately independent from Kodi: room volume is optional and may be
    // supplied by any HA media-player-compatible audio endpoint.
    const audioEntity = String(this.config?.audio_entity || "").trim();
    return audioEntity.includes(".") ? audioEntity : "";
  }

  notifyApolloError(message) {
    this.dispatchEvent(new CustomEvent("hass-notification", {
      detail: { message },
      bubbles: true,
      composed: true
    }));
  }

  isApolloRemotePlaybackActive(player) {
    const state = String(player?.state || "unknown").toLowerCase();
    if (state !== "playing" && state !== "paused") return false;

    // After a source transition is requested, the expected source type wins
    // until a fresh Apollo Active Playback context confirms the handoff.
    // This prevents the original card playback path (for example play_external)
    // from keeping Now Playing in remote mode after Kodi has switched local.
    const expected = String(this._expectedPlaybackSource || "");
    if (expected === "local") return false;
    if (expected === "remote") return true;

    const active = this.activeApolloContext(player);
    if (active) return Boolean(active.remote);

    // Only fall back to the original card-started path before any canonical
    // active context/source transition has been established.
    const action = this.fileParams(this._apolloPlayback?.path || "").action || "";
    return Boolean(this._apolloPlayback?.started) && action.startsWith("play_external");
  }

  invalidateActiveApolloContext(expectedSource = "") {
    this._expectedPlaybackSource = String(expectedSource || "");
    this._activeContextNotBefore = Date.now();
    this._nowPlayingIdentity = null;
    window.clearTimeout(this._activeApolloRefreshTimer);
    this._activeApolloRefreshTimer = null;
    this._activeApolloRequestKey = null;
    this._activeApolloRequestAttempts = 0;
  }

  activeApolloContext(player) {
    const entity = this._hass?.states?.[this.config?.active_entity];
    const updatedAt = Date.parse(entity?.last_updated || "");
    if (
      Number(this._activeContextNotBefore || 0) > 0 &&
      Number.isFinite(updatedAt) &&
      updatedAt < Number(this._activeContextNotBefore || 0)
    ) {
      return null;
    }

    const activeItems = this.asArray(entity?.attributes?.movies);
    const activeItem = activeItems[0] || null;
    const file = activeItem?.file || "";
    const params = this.fileParams(file);
    if (params.action !== "apollo_active_media") return null;

    const activeTitle = this.usefulNowPlayingText(params.title || activeItem?.title || activeItem?.label);

    const rawSeason = Number(params.season ?? activeItem?.season);
    const rawEpisode = Number(params.episode ?? activeItem?.episode);
    const season = Number.isFinite(rawSeason) && rawSeason > 0 ? rawSeason : 0;
    const episode = Number.isFinite(rawEpisode) && rawEpisode > 0 ? rawEpisode : 0;

    const playerSeason = Number(player?.attributes?.media_season || 0);
    const playerEpisode = Number(player?.attributes?.media_episode || 0);
    if (episode > 0 && playerEpisode > 0) {
      if (episode !== playerEpisode || (season > 0 && playerSeason > 0 && season !== playerSeason)) {
        return null;
      }
    }

    const remote = params.apollo_remote === "1";
    const expected = String(this._expectedPlaybackSource || "");
    if ((expected === "remote" && !remote) || (expected === "local" && remote)) {
      return null;
    }

    if (expected) {
      this._expectedPlaybackSource = "";
      this._activeContextNotBefore = 0;
    }

    return {
      remote,
      identity: params.apollo_identity || "",
      imdb: params.imdb || activeItem?.imdbnumber || "",
      mediaType: params.apollo_media_type || (episode ? "episode" : (params.media_type || "movie")),
      title: activeTitle,
      seriesTitle: this.usefulNowPlayingText(params.show_title || activeItem?.showtitle),
      season,
      episode,
      year: Number(activeItem?.year || 0) || 0,
      plot: this.usefulNowPlayingText(activeItem?.plot),
      showTarget: params.show_target || "",
      seasonTarget: params.season_target || "",
      remoteAutoTarget: params.remote_auto_target || "",
      remoteChooseTarget: params.remote_choose_target || "",
      provider: this.usefulNowPlayingText(params.apollo_provider),
      streamIndex: Number(params.apollo_stream_index ?? -1),
      streamCount: Number(params.apollo_stream_count || 0),
      streamFlagged: params.apollo_stream_flagged === "1",
      localTarget: params.apollo_local_target || "",
      quality: this.usefulNowPlayingText(params.apollo_quality),
      videoInfo: this.usefulNowPlayingText(params.apollo_video_info),
      audioInfo: this.usefulNowPlayingText(params.apollo_audio_info),
      poster: this.artworkUrl(activeItem?.thumbnail || activeItem?.art?.poster || ""),
      fanart: this.artworkUrl(activeItem?.fanart || activeItem?.art?.fanart || "")
    };
  }

  requestActiveApolloContext(player) {
    if (!this.nowPlayingActive(player)) {
      window.clearTimeout(this._activeApolloRefreshTimer);
      this._activeApolloRefreshTimer = null;
      this._activeApolloRequestKey = null;
      this._activeApolloRequestAttempts = 0;
      return;
    }

    const key = this.nowPlayingMediaIdentity(player);
    const active = this.activeApolloContext(player);
    if (active) {
      window.clearTimeout(this._activeApolloRefreshTimer);
      this._activeApolloRefreshTimer = null;
      this._activeApolloRequestKey = key;
      this._activeApolloRequestAttempts = 0;
      return;
    }

    if (this._activeApolloRequestKey !== key) {
      window.clearTimeout(this._activeApolloRefreshTimer);
      this._activeApolloRefreshTimer = null;
      this._activeApolloRequestKey = key;
      this._activeApolloRequestAttempts = 0;
    }

    if (this._activeApolloRefreshInFlight || this._activeApolloRefreshTimer) return;
    if (Number(this._activeApolloRequestAttempts || 0) >= 5) return;

    const playerEntity = this.configuredPlayerEntity();
    if (!playerEntity) return;

    this._activeApolloRequestAttempts = Number(this._activeApolloRequestAttempts || 0) + 1;
    this._activeApolloRefreshInFlight = true;

    Promise.resolve(
      this.callApolloScript(this.config.active_refresh_script, { player_entity: playerEntity })
    ).catch(error => {
      console.debug("Apollo active playback refresh failed", error);
    }).finally(() => {
      this._activeApolloRefreshInFlight = false;
      const retryDelay = Math.min(1800, 350 + (this._activeApolloRequestAttempts * 250));
      this._activeApolloRefreshTimer = window.setTimeout(() => {
        this._activeApolloRefreshTimer = null;
        const current = this._hass?.states?.[this.configuredPlayerEntity()];
        if (
          this.nowPlayingActive(current) &&
          this.nowPlayingMediaIdentity(current) === key &&
          !this.activeApolloContext(current)
        ) {
          this.requestActiveApolloContext(current);
        }
      }, retryDelay);
    });
  }

  async tryNextApolloStream() {
    if (this._tryNextPending) {
      return false;
    }
    const playerEntity = this.requirePlayerEntity();
    const player = playerEntity ? this._hass?.states?.[playerEntity] : null;
    if (!playerEntity || !this.isApolloRemotePlaybackActive(player)) return false;

    this._tryNextPending = true;
    this.invalidateActiveApolloContext("remote");
    this.updateNowPlayingDynamic(player);
    try {
      await this.callApolloScript(this.config.try_next_script, {
        player_entity: playerEntity
      });
      return true;
    } catch (error) {
      console.error("Apollo Try Next failed", error);
      this.notifyApolloError("Apollo could not try the next stream.");
      return false;
    } finally {
      this._tryNextPending = false;
      this.updateNowPlayingDynamic();
    }
  }

  nowPlayingActive(player) {
    const state = String(player?.state || "unknown").toLowerCase();
    return state === "playing" || state === "paused";
  }

  usefulNowPlayingText(value) {
    const text = String(value || "").trim();
    return text && text !== "-1" ? text : "";
  }

  usefulNowPlayingNumber(value) {
    const numeric = Number(value);
    return Number.isFinite(numeric) && numeric > 0 ? numeric : 0;
  }

  nowPlayingContextKey() {
    const playerEntity = this.configuredPlayerEntity();
    return playerEntity ? `apollo_now_playing_context:${playerEntity}` : "";
  }

  nowPlayingKodiFingerprint(player) {
    const attributes = player?.attributes || {};
    return {
      contentId: this.usefulNowPlayingText(attributes.media_content_id || attributes.media_channel),
      title: this.usefulNowPlayingText(attributes.media_title),
      duration: Math.max(0, Number(attributes.media_duration || 0))
    };
  }

  compatibleNowPlayingContext(context, player) {
    const saved = context?.kodi || {};
    const active = this.nowPlayingKodiFingerprint(player);
    if (saved.contentId || active.contentId) {
      return Boolean(saved.contentId && active.contentId && saved.contentId === active.contentId);
    }
    // Kodi does not consistently expose a content ID. A matching title plus a
    // near-identical duration is conservative enough for a reload restore.
    return Boolean(
      saved.title && active.title && saved.title === active.title &&
      saved.duration > 0 && active.duration > 0 && Math.abs(saved.duration - active.duration) <= 5
    );
  }

  safeNowPlayingPresentation(item, player) {
    if (!item) return null;
    const season = this.usefulNowPlayingNumber(item.season);
    const episode = this.usefulNowPlayingNumber(item.episode);
    const seriesTitle = this.usefulNowPlayingText(item.series_title || (episode ? item.title : ""));
    const episodeTitle = this.usefulNowPlayingText(item.episode_title || (episode ? "" : item.title));
    return {
      kodi: this.nowPlayingKodiFingerprint(player),
      identity: this.apolloItemIdentityKey(item),
      mediaType: this.usefulNowPlayingText(item.media_type),
      title: this.usefulNowPlayingText(item.title),
      seriesTitle,
      episodeTitle,
      season,
      episode,
      year: Number(item.year || 0) || 0,
      plot: this.usefulNowPlayingText(item.plot),
      poster: this.usefulNowPlayingText(item.poster),
      fanart: this.usefulNowPlayingText(item.fanart),
      imdb: this.usefulNowPlayingText(item.imdb),
      // Only existing Apollo directory targets are retained. Playback/provider
      // URLs are deliberately excluded from the persistent presentation model.
      browseTarget: this.usefulNowPlayingText(item.browseTarget) ||
        (item.is_folder ? this.usefulNowPlayingText(item.file) : ""),
      seasonTarget: this.usefulNowPlayingText(item.seasonTarget)
    };
  }

  persistNowPlayingPresentation(context) {
    const key = this.nowPlayingContextKey();
    if (!key || !context) return;
    try { localStorage.setItem(key, JSON.stringify(context)); } catch (_) {}
  }

  clearNowPlayingPresentation() {
    const key = this.nowPlayingContextKey();
    if (key) {
      try { localStorage.removeItem(key); } catch (_) {}
    }
    this._nowPlayingPresentationContext = null;
  }

  currentNowPlayingPresentation(player) {
    const launchItem = this._apolloPlayback?.cardInitiated ? this._apolloPlayback.sourceItem : null;
    const launch = launchItem ? this.safeNowPlayingPresentation(launchItem, player) : null;
    const active = this.activeApolloContext(player);

    let saved = this._nowPlayingPresentationContext;
    if (!saved || !this.compatibleNowPlayingContext(saved, player)) {
      const key = this.nowPlayingContextKey();
      if (key) {
        try {
          const candidate = JSON.parse(localStorage.getItem(key) || "null");
          saved = candidate && this.compatibleNowPlayingContext(candidate, player)
            ? candidate
            : null;
        } catch (_) {
          saved = null;
        }
      }
    }

    if (active || launch) {
      // Merge rather than returning the launch context early. The launch item
      // supplies immediate artwork/metadata; the active sensor later adds the
      // authoritative Apollo remote capability plus safe show/season targets.
      const context = {
        ...(saved || {}),
        ...(launch || {}),
        kodi: this.nowPlayingKodiFingerprint(player),
        identity: active?.identity || launch?.identity || saved?.identity || "",
        remote: Boolean(active?.remote || launch?.remote || saved?.remote),
        mediaType: active?.mediaType || launch?.mediaType || saved?.mediaType || "movie",
        title: active?.title || launch?.title || saved?.title || "",
        seriesTitle: active?.seriesTitle || launch?.seriesTitle || saved?.seriesTitle || "",
        episodeTitle: active?.title || launch?.episodeTitle || saved?.episodeTitle || "",
        season: Number(active?.season || launch?.season || saved?.season || 0),
        episode: Number(active?.episode || launch?.episode || saved?.episode || 0),
        year: Number(active?.year || launch?.year || saved?.year || 0),
        plot: active?.plot || launch?.plot || saved?.plot || "",
        poster: active?.poster || launch?.poster || saved?.poster || "",
        fanart: active?.fanart || launch?.fanart || saved?.fanart || "",
        imdb: active?.imdb || launch?.imdb || saved?.imdb || "",
        browseTarget: active?.showTarget || launch?.browseTarget || saved?.browseTarget || "",
        seasonTarget: active?.seasonTarget || launch?.seasonTarget || saved?.seasonTarget || ""
      };
      const changed = JSON.stringify(context) !== JSON.stringify(this._nowPlayingPresentationContext);
      this._nowPlayingPresentationContext = context;
      if (changed) this.persistNowPlayingPresentation(context);
      return context;
    }

    if (saved && this.compatibleNowPlayingContext(saved, player)) {
      this._nowPlayingPresentationContext = saved;
      return saved;
    }

    // A stored context that cannot be tied to the current live item is stale.
    this.clearNowPlayingPresentation();
    return null;
  }

  nowPlayingMediaIdentity(player) {
    const attributes = player?.attributes || {};
    const contentId = String(attributes.media_content_id || attributes.media_channel || "").trim();
    if (contentId) return `content:${contentId}`;
    const series = String(attributes.media_series_title || attributes.media_album_name || "").trim();
    const title = String(attributes.media_title || attributes.friendly_name || "Now Playing").trim();
    const season = Number(attributes.media_season || 0);
    const episode = Number(attributes.media_episode || 0);
    return JSON.stringify([series, title, season, episode]);
  }

  nowPlayingArtwork(player, presentation = null) {
    const mediaIdentity = this.nowPlayingMediaIdentity(player);
    if (this._nowPlayingArtworkIdentity !== mediaIdentity) {
      this._nowPlayingArtworkIdentity = mediaIdentity;
      this._nowPlayingArtwork = "";
    }
    const attributes = player?.attributes || {};
    const candidate = String(
      attributes.media_image_url || attributes.entity_picture ||
      presentation?.fanart || presentation?.poster || ""
    ).trim();
    // HA media attributes are sometimes temporarily absent between updates.
    // Keep the last valid value until the active media identity changes.
    if (candidate) this._nowPlayingArtwork = candidate;
    return this._nowPlayingArtwork || "";
  }

  nowPlayingMetadata(player) {
    const attributes = player?.attributes || {};
    const presentation = this.currentNowPlayingPresentation(player);
    const mediaType = this.usefulNowPlayingText(presentation?.mediaType) ||
      (this.usefulNowPlayingNumber(attributes.media_episode) ? "episode" : "movie");
    const isSeries = mediaType === "series" || mediaType === "episode";

    const series = isSeries
      ? (this.usefulNowPlayingText(attributes.media_series_title || attributes.media_album_name) ||
        presentation?.seriesTitle || "")
      : "";
    const kodiTitle = this.usefulNowPlayingText(attributes.media_title);
    const season = isSeries
      ? (this.usefulNowPlayingNumber(attributes.media_season) || Number(presentation?.season || 0))
      : 0;
    const episode = isSeries
      ? (this.usefulNowPlayingNumber(attributes.media_episode) || Number(presentation?.episode || 0))
      : 0;
    const title = kodiTitle || presentation?.episodeTitle || presentation?.title ||
      String(attributes.friendly_name || "Now Playing").trim();
    const episodeCode = episode ? `S${season} E${episode}` : "";
    const context = series
      ? [episodeCode, title].filter(Boolean).join(" · ")
      : "";

    return {
      title,
      seriesTitle: series,
      season,
      episode,
      mediaType,
      context,
      mediaTitle: title,
      year: Number(presentation?.year || 0),
      plot: presentation?.plot || "",
      poster: presentation?.poster || "",
      fanart: presentation?.fanart || "",
      imdb: presentation?.imdb || "",
      artwork: this.nowPlayingArtwork(player, presentation),
      duration: Math.max(0, Number(attributes.media_duration || 0)),
      state: String(player?.state || "unknown").toLowerCase(),
      contentId: String(attributes.media_content_id || attributes.media_channel || ""),
      browseTarget: isSeries ? (presentation?.browseTarget || "") : "",
      seasonTarget: isSeries ? (presentation?.seasonTarget || "") : "",
      presentation
    };
  }

  nowPlayingAudioMetadata() {
    const audioEntity = this.configuredAudioEntity();
    const audio = audioEntity ? this._hass?.states?.[audioEntity] : null;
    const attributes = audio?.attributes || {};
    const volume = Number(attributes.volume_level);
    return {
      available: Boolean(audio),
      volume,
      muted: attributes.is_volume_muted
    };
  }

  nowPlayingIdentity(player) {
    const metadata = this.nowPlayingMetadata(player);
    return JSON.stringify([
      metadata.contentId, metadata.title, metadata.context,
      metadata.mediaTitle, metadata.artwork,
      metadata.browseTarget, metadata.seasonTarget,
      this.configuredAudioEntity(),
      this.isApolloRemotePlaybackActive(player),
      this.activeApolloContext(player)?.provider || "",
      this.activeApolloContext(player)?.streamIndex ?? -1,
      this.activeApolloContext(player)?.streamCount || 0
    ]);
  }

  nowPlayingPosition(player, now = Date.now()) {
    if (now < Number(this._nowPlayingOptimisticUntil || 0)) {
      return Math.max(0, Number(this._nowPlayingOptimisticPosition || 0));
    }
    return this.playbackPosition(player, now).position;
  }

  apolloStreamItems() {
    const entity = this._hass?.states?.[this.config?.sources_entity];
    const sources = this.asArray(entity?.attributes?.sources);
    return sources.map(file => {
      const params = this.fileParams(file.file || "");
      return {
        title: String(file.title || file.label || "Stream"),
        description: String(file.plot || ""),
        provider: String(params.apollo_provider || ""),
        index: Number(params.apollo_stream_index || 0),
        count: Number(params.apollo_stream_count || 0),
        flagged: params.apollo_flagged === "1",
        current: params.apollo_current === "1",
        quality: String(params.apollo_quality || "Other"),
        videoInfo: String(params.apollo_video_info || ""),
        audioInfo: String(params.apollo_audio_info || ""),
        file: String(file.file || "")
      };
    });
  }

  currentPlaybackSnapshot() {
    const player = this._hass?.states?.[this.configuredPlayerEntity()] || this._nowPlayingPlayer;
    const sample = this.playbackPosition(player);
    return {
      position: Math.max(0, Number(sample.position || 0)),
      duration: Math.max(0, Number(sample.duration || 0))
    };
  }

  async openStreamPicker(path, context = null) {
    const target = String(path || "").trim();
    const playerEntity = this.requirePlayerEntity();
    if (!target || !playerEntity) return false;

    this._streamPickerOpen = true;
    this._streamPickerTarget = target;
    this._streamPickerContext = context || null;
    this._streamPickerLoading = true;
    this.renderStreamPicker();

    try {
      await this.callApolloScript(this.config.load_streams_script, {
        player_entity: playerEntity,
        path: target
      });
      return true;
    } catch (error) {
      console.error("Apollo stream picker load failed", error);
      this.notifyApolloError("Apollo could not load streams.");
      return false;
    } finally {
      this._streamPickerLoading = false;
      this.renderStreamPicker();
    }
  }

  closeStreamPicker() {
    this._streamPickerOpen = false;
    this._streamPickerPendingPath = "";
    this.querySelector(".stream-picker-overlay")?.remove();
  }

  renderStreamPicker() {
    this.querySelector(".stream-picker-overlay")?.remove();
    if (!this._streamPickerOpen) return;

    const streams = this.apolloStreamItems();
    const qualityOrder = ["4K / 2160p", "1080p", "720p", "SD / 480p", "Other"];
    const grouped = qualityOrder
      .map(quality => [quality, streams.filter(stream => stream.quality === quality)])
      .filter(([, items]) => items.length);
    const rows = this._streamPickerLoading && !streams.length
      ? `<div class="stream-picker-empty"><ha-icon icon="mdi:loading"></ha-icon> Loading streams…</div>`
      : (streams.length
          ? grouped.map(([quality, items]) => `
            <div class="stream-quality-group">
              <div class="stream-quality-separator"><span>${quality}</span><small>${items.length}</small></div>
              ${items.map(stream => `
                <button class="stream-picker-row${stream.current ? " current" : ""}${stream.flagged ? " flagged" : ""}" type="button"
                  data-stream-play="${encodeURIComponent(stream.file)}" ${this._streamPickerPendingPath ? "disabled" : ""}>
                  <span class="stream-picker-main">
                    <strong>${stream.title}</strong>
                    <small>${[stream.provider, stream.videoInfo, stream.audioInfo, stream.current ? "Current" : "", stream.flagged ? "Flagged" : ""].filter(Boolean).join(" · ")}</small>
                    ${stream.description ? `<em>${stream.description}</em>` : ""}
                  </span>
                  <ha-icon icon="${stream.current ? "mdi:play-circle" : "mdi:chevron-right"}"></ha-icon>
                </button>`).join("")}
            </div>`).join("")
          : `<div class="stream-picker-empty">No compatible streams found.</div>`);

    const overlay = document.createElement("div");
    overlay.className = "stream-picker-overlay open";
    overlay.innerHTML = `
      <section class="stream-picker-sheet">
        <div class="sheet-handle"></div>
        <div class="stream-picker-header">
          <div><div class="screen-kicker">REMOTE</div><h2>Choose Stream</h2></div>
          <button class="stream-picker-close" type="button" aria-label="Close"><ha-icon icon="mdi:close"></ha-icon></button>
        </div>
        <div class="stream-picker-list">${rows}</div>
      </section>`;
    this.querySelector(".app")?.appendChild(overlay);

    overlay.querySelector(".stream-picker-close")?.addEventListener("click", () => this.closeStreamPicker());
    overlay.addEventListener("click", event => {
      if (event.target === overlay) this.closeStreamPicker();
    });
    overlay.querySelectorAll("[data-stream-play]").forEach(button => {
      button.addEventListener("click", async event => {
        const path = decodeURIComponent(event.currentTarget.dataset.streamPlay || "");
        await this.playPickedStream(path);
      });
    });
  }

  async playPickedStream(path) {
    const playerEntity = this.requirePlayerEntity();
    const target = String(path || "").trim();
    if (!playerEntity || !target || this._streamPickerPendingPath) return false;
    this._streamPickerPendingPath = target;
    this.renderStreamPicker();

    const player = this._hass?.states?.[playerEntity] || this._nowPlayingPlayer;
    const active = this.nowPlayingActive(player);
    const context = this._streamPickerContext || {};
    try {
      if (active) {
        const sample = this.currentPlaybackSnapshot();
        await this.callApolloScript(this.config.play_stream_script, {
          player_entity: playerEntity,
          path: target,
          position: sample.position,
          duration: sample.duration
        });
      } else {
        const resumable = Number(context.resume_position || 0) > 0 || Number(context.progress || 0) > 0;
        await this.callApolloScript(this.config.play_script, {
          player_entity: playerEntity,
          path: target,
          ...(resumable ? { resume: true } : {})
        });
      }
      this.closeStreamPicker();
      return true;
    } catch (error) {
      console.error("Apollo stream selection failed", error);
      this.notifyApolloError("Apollo could not switch streams.");
      this._streamPickerPendingPath = "";
      this.renderStreamPicker();
      return false;
    }
  }

  async switchNowPlayingToRemote() {
    const playerEntity = this.requirePlayerEntity();
    const player = this._hass?.states?.[playerEntity] || this._nowPlayingPlayer;
    const active = this.activeApolloContext(player);
    const path = String(active?.remoteAutoTarget || "").trim();
    if (!playerEntity || !path || active?.remote) return false;
    const sample = this.currentPlaybackSnapshot();
    this.invalidateActiveApolloContext("remote");
    try {
      await this.callApolloScript(this.config.switch_remote_script, {
        player_entity: playerEntity,
        path,
        position: sample.position,
        duration: sample.duration
      });
      if (this._nowPlayingOpen) this.rebuildNowPlayingModal(this._nowPlayingPlayer);
      return true;
    } catch (error) {
      console.error("Apollo remote switch failed", error);
      this.notifyApolloError("Apollo could not switch this playback to a remote stream.");
      return false;
    }
  }

  async switchNowPlayingToLocal() {
    const playerEntity = this.requirePlayerEntity();
    const player = this._hass?.states?.[playerEntity] || this._nowPlayingPlayer;
    const active = this.activeApolloContext(player);
    const path = String(active?.localTarget || "").trim();
    if (!playerEntity || !path || !active?.remote) return false;
    const sample = this.currentPlaybackSnapshot();
    this.invalidateActiveApolloContext("local");
    try {
      await this.callApolloScript(this.config.switch_local_script, {
        player_entity: playerEntity,
        path,
        position: sample.position,
        duration: sample.duration
      });
      if (this._nowPlayingOpen) this.rebuildNowPlayingModal(this._nowPlayingPlayer);
      return true;
    } catch (error) {
      console.error("Apollo local switch failed", error);
      this.notifyApolloError("Apollo could not switch this playback to the local library copy.");
      return false;
    }
  }

  openFlagMenu() {
    this._flagMenuOpen = true;
    this.renderFlagMenu();
  }

  closeFlagMenu() {
    this._flagMenuOpen = false;
    this.querySelector(".stream-flag-overlay")?.remove();
  }

  renderFlagMenu() {
    this.querySelector(".stream-flag-overlay")?.remove();
    if (!this._flagMenuOpen) return;
    const reasons = [
      ["bad_colors", "Bad colors / HDR"],
      ["no_audio", "No audio"],
      ["unsupported_codec", "Unsupported codec"],
      ["buffering", "Buffering"],
      ["wrong_content", "Wrong content"],
      ["wrong_language", "Wrong language"]
    ];
    const overlay = document.createElement("div");
    overlay.className = "stream-flag-overlay open";
    overlay.innerHTML = `
      <section class="stream-flag-sheet">
        <div class="sheet-handle"></div>
        <div class="stream-picker-header">
          <div><div class="screen-kicker">REMOTE</div><h2>Flag Stream</h2></div>
          <button class="stream-flag-close" type="button" aria-label="Close"><ha-icon icon="mdi:close"></ha-icon></button>
        </div>
        <div class="stream-flag-list">
          ${reasons.map(([reason, label]) => `<button type="button" data-stream-flag="${reason}">${label}</button>`).join("")}
        </div>
      </section>`;
    this.querySelector(".app")?.appendChild(overlay);
    overlay.querySelector(".stream-flag-close")?.addEventListener("click", () => this.closeFlagMenu());
    overlay.addEventListener("click", event => {
      if (event.target === overlay) this.closeFlagMenu();
    });
    overlay.querySelectorAll("[data-stream-flag]").forEach(button => {
      button.addEventListener("click", async event => {
        const reason = event.currentTarget.dataset.streamFlag || "";
        const playerEntity = this.requirePlayerEntity();
        if (!playerEntity || !reason) return;
        try {
          this.invalidateActiveApolloContext("remote");
          await this.callApolloScript(this.config.flag_script, { player_entity: playerEntity, reason });
          this.closeFlagMenu();
        } catch (error) {
          console.error("Apollo flag stream failed", error);
          this.notifyApolloError("Apollo could not flag this stream.");
        }
      });
    });
  }

  renderNowPlayingContent(player) {
    const metadata = this.nowPlayingMetadata(player);
    const duration = metadata.duration;
    const position = Math.min(duration || Number.MAX_SAFE_INTEGER, this.nowPlayingPosition(player));
    const remaining = duration > 0 ? Math.max(0, duration - position) : 0;
    const audio = this.nowPlayingAudioMetadata();
    const hasVolume = audio.available && Number.isFinite(audio.volume) && audio.volume >= 0;
    const hasMute = audio.available && typeof audio.muted === "boolean";
    const remoteApollo = this.isApolloRemotePlaybackActive(player);
    const activeApollo = this.activeApolloContext(player);
    const sourceLabel = !remoteApollo && activeApollo ? "LOCAL" : "";
    const technicalMarkup = activeApollo && (activeApollo.quality || activeApollo.videoInfo || activeApollo.audioInfo)
      ? `<div class="now-playing-technical">
          <span><small>VIDEO</small><strong>${activeApollo.videoInfo || activeApollo.quality || "Unknown"}</strong></span>
          <span><small>AUDIO</small><strong>${activeApollo.audioInfo || "Unknown"}</strong></span>
        </div>`
      : "";
    const artworkStyle = metadata.artwork
      ? `background-image:linear-gradient(to bottom,rgba(8,9,11,.18),#0c0d10),url('${metadata.artwork.replaceAll("'", "%27")}')`
      : "";
    const episodeMeta = metadata.episode
      ? `${metadata.seasonTarget ? `<button class="now-playing-season-link" type="button" data-now-playing-browse-level="season" data-now-playing-browse="${encodeURIComponent(metadata.seasonTarget)}">Season ${metadata.season || 0}</button>` : `Season ${metadata.season || 0}`} · Episode ${metadata.episode}`
      : "";
    const showMarkup = metadata.seriesTitle
      ? (metadata.browseTarget
          ? `<button class="now-playing-series-link" type="button" data-now-playing-browse-level="show" data-now-playing-browse="${encodeURIComponent(metadata.browseTarget)}">${metadata.seriesTitle}</button>`
          : `<div class="now-playing-series">${metadata.seriesTitle}</div>`)
      : "";
    return `
      <div data-now-playing-content>
        ${metadata.artwork ? `<div class="now-playing-hero" style="${artworkStyle}">
          <button class="now-playing-close" type="button" aria-label="Close"><ha-icon icon="mdi:close"></ha-icon></button>
        </div>` : `<div class="now-playing-header"><button class="now-playing-close" type="button" aria-label="Close"><ha-icon icon="mdi:close"></ha-icon></button></div>`}
        <div class="now-playing-content">
          <div class="screen-kicker" data-now-playing-state>${metadata.state === "paused" ? "PAUSED" : "NOW PLAYING"}</div>
          ${sourceLabel ? `<div class="now-playing-source${remoteApollo ? " remote" : " local"}">${sourceLabel}</div>` : ""}
          <h2>${metadata.title}</h2>
          ${showMarkup}
          ${episodeMeta ? `<div class="now-playing-context">${episodeMeta}</div>` : ""}
          ${technicalMarkup}
          <div class="now-playing-times">
            <span data-now-playing-position>${this.formatMediaTime(position)}</span>
            <span data-now-playing-duration>${duration > 0 ? this.formatMediaTime(duration) : "--:--"}</span>
          </div>
          <input class="now-playing-seek" data-now-playing-seek type="range" min="0" max="${duration || 0}" step="1" value="${position}" ${duration > 0 ? "" : "disabled"} aria-label="Playback position" />
          <div class="now-playing-remaining" data-now-playing-remaining>${duration > 0 ? `${this.formatMediaTime(remaining)} remaining` : ""}</div>
          <div class="now-playing-controls">
            <button type="button" data-now-playing-control data-now-playing-back aria-label="Seek back 10 seconds"><ha-icon icon="mdi:rewind-10"></ha-icon><span>10s</span></button>
            <button class="now-playing-primary" type="button" data-now-playing-control data-now-playing-toggle aria-label="Play or pause"><ha-icon icon="${metadata.state === "paused" ? "mdi:play" : "mdi:pause"}"></ha-icon></button>
            <button type="button" data-now-playing-control data-now-playing-forward aria-label="Seek forward 30 seconds"><ha-icon icon="mdi:fast-forward-30"></ha-icon><span>30s</span></button>
            <button type="button" data-now-playing-control data-now-playing-stop aria-label="Stop"><ha-icon icon="mdi:stop"></ha-icon></button>
          </div>
          ${hasVolume || hasMute ? `
            <div class="now-playing-volume">
              ${hasMute ? `<button type="button" data-now-playing-control data-now-playing-mute aria-label="Mute or unmute"><ha-icon icon="${audio.muted ? "mdi:volume-off" : "mdi:volume-high"}"></ha-icon></button>` : ""}
              ${hasVolume ? `<input data-now-playing-volume type="range" min="0" max="1" step="0.01" value="${Math.min(1, audio.volume)}" aria-label="Volume" />` : ""}
            </div>` : ""}
          ${remoteApollo ? `
            <div class="now-playing-source-actions">
              ${activeApollo?.remoteChooseTarget ? `<button type="button" data-now-playing-stream-picker><ha-icon icon="mdi:format-list-bulleted"></ha-icon> Stream Picker</button>` : ""}
              <button type="button" data-now-playing-try-next><ha-icon icon="mdi:skip-next"></ha-icon> Next Stream</button>
              <button type="button" data-now-playing-flag><ha-icon icon="mdi:flag-outline"></ha-icon> Flag Stream</button>
              ${activeApollo?.localTarget ? `<button type="button" data-now-playing-switch-local><ha-icon icon="mdi:harddisk"></ha-icon> Play Locally</button>` : ""}
            </div>`
            : (activeApollo?.remoteAutoTarget ? `
              <div class="now-playing-source-actions">
                <button type="button" data-now-playing-switch-remote><ha-icon icon="mdi:cloud-play-outline"></ha-icon> Stream Remotely</button>
                ${activeApollo?.remoteChooseTarget ? `<button type="button" data-now-playing-stream-picker><ha-icon icon="mdi:format-list-bulleted"></ha-icon> Choose Remote Stream</button>` : ""}
              </div>` : "")}
        </div>
      </div>`;
  }

  rebuildNowPlayingModal(player) {
    const sheet = this.querySelector(".now-playing-sheet");
    if (!sheet) return;
    const scrollTop = sheet.scrollTop || 0;
    sheet.innerHTML = this.renderNowPlayingContent(player);
    this.bindNowPlayingEvents();
    sheet.scrollTop = scrollTop;
  }

  updateNowPlaying(player = null) {
    const currentPlayer = player || this._hass?.states?.[this.configuredPlayerEntity()];
    this._nowPlayingPlayer = currentPlayer || null;
    const active = this.nowPlayingActive(currentPlayer);
    const affordance = this.querySelector("[data-now-playing-affordance]");
    const app = this.querySelector(".app");
    if (!active) {
      if (affordance) affordance.hidden = true;
      app?.classList.remove("has-mini-player");
      this.closeNowPlaying();
      this._nowPlayingArtwork = "";
      this._nowPlayingArtworkIdentity = null;
      this.clearNowPlayingPresentation();
      window.clearInterval(this._nowPlayingTicker);
      this._nowPlayingTicker = null;
      return;
    }

    const identity = this.nowPlayingIdentity(currentPlayer);
    const structureChanged = identity !== this._nowPlayingIdentity;
    this._nowPlayingIdentity = identity;
    if (affordance) affordance.hidden = this._nowPlayingOpen;
    app?.classList.toggle("has-mini-player", !this._nowPlayingOpen);
    if (this._nowPlayingOpen && (structureChanged || !this.querySelector("[data-now-playing-content]"))) {
      this.rebuildNowPlayingModal(currentPlayer);
    }
    this.updateNowPlayingDynamic(currentPlayer);
    if (!this._nowPlayingTicker) {
      this._nowPlayingTicker = window.setInterval(() => {
        this.updateNowPlayingDynamic(this._nowPlayingPlayer);
      }, 1000);
    }
  }

  updateNowPlayingDynamic(player = null) {
    const currentPlayer = player || this._nowPlayingPlayer;
    if (!this.nowPlayingActive(currentPlayer)) return;
    const metadata = this.nowPlayingMetadata(currentPlayer);
    const duration = metadata.duration;
    const authoritativePosition = Math.min(duration || Number.MAX_SAFE_INTEGER, this.nowPlayingPosition(currentPlayer));
    const scrubPosition = Number(this._nowPlayingScrubPosition);
    const position = this._nowPlayingSeeking && Number.isFinite(scrubPosition)
      ? Math.min(duration || Number.MAX_SAFE_INTEGER, Math.max(0, scrubPosition))
      : authoritativePosition;
    const remaining = duration > 0 ? Math.max(0, duration - position) : 0;
    const setText = (selector, value) => {
      const element = this.querySelector(selector);
      if (element) element.textContent = value;
    };
    setText("[data-now-playing-affordance-title]", metadata.title);
    setText(
      "[data-now-playing-affordance-context]",
      [metadata.seriesTitle || metadata.context, metadata.state === "paused" ? "Paused" : "Playing"].filter(Boolean).join(" · ")
    );
    setText("[data-now-playing-state]", metadata.state === "paused" ? "PAUSED" : "NOW PLAYING");
    setText("[data-now-playing-position]", this.formatMediaTime(position));
    setText("[data-now-playing-duration]", duration > 0 ? this.formatMediaTime(duration) : "--:--");
    setText("[data-now-playing-remaining]", duration > 0 ? `${this.formatMediaTime(remaining)} remaining` : "");

    const affordanceArt = this.querySelector("[data-now-playing-affordance-art]");
    if (affordanceArt) affordanceArt.style.backgroundImage = metadata.artwork ? `url('${metadata.artwork.replaceAll("'", "%27")}')` : "";

    const miniProgress = this.querySelector("[data-now-playing-mini-progress]");
    if (miniProgress) {
      const progressPercent = duration > 0
        ? Math.min(100, Math.max(0, (position / duration) * 100))
        : 0;
      miniProgress.style.width = `${progressPercent}%`;
    }

    const seek = this.querySelector("[data-now-playing-seek]");
    if (seek && !this._nowPlayingSeeking) {
      seek.max = String(duration || 0);
      seek.value = String(position);
      seek.disabled = !(duration > 0);
    }
    const toggleIcon = this.querySelector("[data-now-playing-toggle] ha-icon");
    if (toggleIcon) toggleIcon.setAttribute("icon", metadata.state === "paused" ? "mdi:play" : "mdi:pause");
    const miniToggleIcon = this.querySelector("[data-now-playing-mini-toggle] ha-icon");
    if (miniToggleIcon) miniToggleIcon.setAttribute("icon", metadata.state === "paused" ? "mdi:play" : "mdi:pause");
    const audio = this.nowPlayingAudioMetadata();
    const volume = this.querySelector("[data-now-playing-volume]");
    if (volume && Number.isFinite(audio.volume)) volume.value = String(Math.min(1, Math.max(0, audio.volume)));
    const muteIcon = this.querySelector("[data-now-playing-mute] ha-icon");
    if (muteIcon && typeof audio.muted === "boolean") muteIcon.setAttribute("icon", audio.muted ? "mdi:volume-off" : "mdi:volume-high");
    const tryNext = this.querySelector("[data-now-playing-try-next]");
    if (tryNext) tryNext.disabled = Boolean(this._tryNextPending);
  }

  openNowPlaying() {
    const player = this._hass?.states?.[this.configuredPlayerEntity()];
    if (!this.nowPlayingActive(player)) return;
    this._nowPlayingOpen = true;
    this.rebuildNowPlayingModal(player);
    this.querySelector(".now-playing-overlay")?.classList.add("open");
    const affordance = this.querySelector("[data-now-playing-affordance]");
    if (affordance) affordance.hidden = true;
    this.querySelector(".app")?.classList.remove("has-mini-player");
    this.updateNowPlayingDynamic(player);
  }

  closeNowPlaying() {
    this._nowPlayingOpen = false;
    this._nowPlayingSeeking = false;
    this._nowPlayingScrubPosition = null;
    this.querySelector(".now-playing-overlay")?.classList.remove("open");
    const player = this._hass?.states?.[this.configuredPlayerEntity()];
    const affordance = this.querySelector("[data-now-playing-affordance]");
    const active = this.nowPlayingActive(player);
    if (affordance) affordance.hidden = !active;
    this.querySelector(".app")?.classList.toggle("has-mini-player", active);
  }

  transitionCardPlaybackToNowPlaying(context) {
    if (!context?.cardInitiated || context.nowPlayingTransitioned) return;
    context.nowPlayingTransitioned = true;
    // Do not redraw the card here: this is an actual playback transition, not
    // a navigation action, and removing the detail layer preserves its scroll.
    this.selectedTitle = null;
    this.detailState = { open: false, entryPoint: null };
    this.detailPath = "";
    this.detailHistory = [];
    this.detailTitleHistory = [];
    this.querySelector(".title-overlay")?.remove();
    this.openNowPlaying();
  }

  async callNowPlayingService(service, data = {}) {
    const playerEntity = this.requirePlayerEntity();
    if (!playerEntity || !this._hass?.states?.[playerEntity]) {
      if (playerEntity) this.notifyApolloError("Configured Kodi player is unavailable.");
      return false;
    }
    try {
      await this._hass.callService("media_player", service, {
        entity_id: playerEntity,
        ...data
      });
      return true;
    } catch (error) {
      console.error(`Apollo Now Playing ${service} failed`, error);
      this.notifyApolloError("Apollo could not update Kodi playback.");
      return false;
    }
  }

  async callAudioService(service, data = {}) {
    const audioEntity = this.configuredAudioEntity();
    if (!audioEntity || !this._hass?.states?.[audioEntity]) return false;
    try {
      await this._hass.callService("media_player", service, {
        entity_id: audioEntity,
        ...data
      });
      return true;
    } catch (error) {
      console.error(`Apollo audio ${service} failed`, error);
      this.notifyApolloError("Apollo could not update room audio.");
      return false;
    }
  }

  async runNowPlayingControl(service, data = {}) {
    if (this._nowPlayingControlPending) return false;
    this._nowPlayingControlPending = true;
    this.querySelectorAll("[data-now-playing-control]").forEach(button => { button.disabled = true; });
    try {
      return await this.callNowPlayingService(service, data);
    } finally {
      this._nowPlayingControlPending = false;
      this.querySelectorAll("[data-now-playing-control]").forEach(button => { button.disabled = false; });
    }
  }

  async toggleNowPlayingPlayback() {
    const player = this._hass?.states?.[this.configuredPlayerEntity()] || this._nowPlayingPlayer;
    const state = String(player?.state || "").toLowerCase();
    if (state === "playing") return this.runNowPlayingControl("media_pause");
    if (state === "paused") return this.runNowPlayingControl("media_play");
    return false;
  }

  async runAudioControl(service, data = {}) {
    if (this._nowPlayingAudioPending) return false;
    this._nowPlayingAudioPending = true;
    this.querySelectorAll("[data-now-playing-mute], [data-now-playing-volume]").forEach(control => { control.disabled = true; });
    try {
      return await this.callAudioService(service, data);
    } finally {
      this._nowPlayingAudioPending = false;
      this.querySelectorAll("[data-now-playing-mute], [data-now-playing-volume]").forEach(control => { control.disabled = false; });
    }
  }

  async seekNowPlaying(position) {
    const player = this._hass?.states?.[this.configuredPlayerEntity()];
    if (!this.nowPlayingActive(player)) return false;
    const duration = Math.max(0, Number(player?.attributes?.media_duration || 0));
    const numeric = Number(position);
    if (!Number.isFinite(numeric)) return false;
    const target = Math.min(duration || Number.MAX_SAFE_INTEGER, Math.max(0, numeric));
    this._nowPlayingOptimisticPosition = target;
    this._nowPlayingOptimisticUntil = Date.now() + 2000;
    this.updateNowPlayingDynamic(player);
    return this.runNowPlayingControl("media_seek", { seek_position: target });
  }

  async seekNowPlayingRelative(offset) {
    const player = this._hass?.states?.[this.configuredPlayerEntity()];
    const current = this.nowPlayingPosition(player);
    return this.seekNowPlaying(current + Number(offset || 0));
  }

  openNowPlayingBrowse(path, level = "show") {
    if (!path) return false;
    const player = this._hass?.states?.[this.configuredPlayerEntity()];
    const metadata = this.nowPlayingMetadata(player);
    const presentation = metadata.presentation || {};
    const showTitle = metadata.seriesTitle || presentation.seriesTitle || "Show";
    const showTarget = presentation.browseTarget || metadata.browseTarget || "";
    const seasonTarget = presentation.seasonTarget || metadata.seasonTarget || "";

    const showItem = {
      title: showTitle,
      series_title: showTitle,
      episode_title: "",
      subtitle: metadata.year ? String(metadata.year) : "",
      poster: presentation.poster || "",
      fanart: presentation.fanart || metadata.artwork || "",
      plot: presentation.plot || "",
      year: Number(metadata.year || 0),
      media_type: "show",
      season: 0,
      episode: 0,
      imdb: presentation.imdb || metadata.imdb || "",
      file: showTarget || path,
      is_folder: true,
      watched: false
    };

    this.closeNowPlaying();
    this.selectedTitle = showItem;
    this.detailState = { open: true, entryPoint: "now-playing" };
    this.detailHistory = [];
    this.detailTitleHistory = [];

    if (level === "season") {
      this.detailPath = seasonTarget || path;
      if (showTarget && showTarget !== this.detailPath) {
        this.detailHistory = [showTarget];
        this.detailTitleHistory = [showItem];
      }
    } else {
      this.detailPath = showTarget || path;
    }

    this.redraw();
    if (this.detailPath) this.loadDetailPath(this.detailPath, false);
    return true;
  }

  bindNowPlayingEvents() {
    this.querySelector(".now-playing-close")?.addEventListener("click", () => this.closeNowPlaying());
    const overlay = this.querySelector(".now-playing-overlay");
    overlay?.addEventListener("click", event => {
      if (event.target === overlay) this.closeNowPlaying();
    });
    this.querySelector("[data-now-playing-toggle]")?.addEventListener("click", () => {
      this.toggleNowPlayingPlayback();
    });
    this.querySelector("[data-now-playing-stop]")?.addEventListener("click", () => {
      this.runNowPlayingControl("media_stop");
    });
    this.querySelector("[data-now-playing-back]")?.addEventListener("click", () => {
      this.seekNowPlayingRelative(-10);
    });
    this.querySelector("[data-now-playing-forward]")?.addEventListener("click", () => {
      this.seekNowPlayingRelative(30);
    });
    const seek = this.querySelector("[data-now-playing-seek]");
    seek?.addEventListener("input", event => {
      this._nowPlayingSeeking = true;
      this._nowPlayingScrubPosition = Number(event.target.value || 0);
      this.updateNowPlayingDynamic(this._nowPlayingPlayer);
    });
    seek?.addEventListener("change", event => {
      const target = Number(event.target.value || 0);
      this._nowPlayingSeeking = false;
      this._nowPlayingScrubPosition = null;
      this.seekNowPlaying(target);
    });
    this.querySelector("[data-now-playing-volume]")?.addEventListener("change", event => {
      const level = Math.min(1, Math.max(0, Number(event.target.value || 0)));
      this.runAudioControl("volume_set", { volume_level: level });
    });
    this.querySelector("[data-now-playing-mute]")?.addEventListener("click", () => {
      const audio = this.nowPlayingAudioMetadata();
      const muted = audio.muted;
      if (typeof muted === "boolean") {
        this.runAudioControl("volume_mute", { is_volume_muted: !muted });
      }
    });
    this.querySelector("[data-now-playing-try-next]")?.addEventListener("click", () => {
      this.tryNextApolloStream();
    });
    this.querySelector("[data-now-playing-stream-picker]")?.addEventListener("click", () => {
      const active = this.activeApolloContext(this._nowPlayingPlayer);
      if (active?.remoteChooseTarget) this.openStreamPicker(active.remoteChooseTarget, active);
    });
    this.querySelector("[data-now-playing-switch-remote]")?.addEventListener("click", () => {
      this.switchNowPlayingToRemote();
    });
    this.querySelector("[data-now-playing-switch-local]")?.addEventListener("click", () => {
      this.switchNowPlayingToLocal();
    });
    this.querySelector("[data-now-playing-flag]")?.addEventListener("click", () => {
      this.openFlagMenu();
    });
    this.querySelectorAll("[data-now-playing-browse]").forEach(button => button.addEventListener("click", event => {
      const path = decodeURIComponent(event.currentTarget.dataset.nowPlayingBrowse || "");
      const level = event.currentTarget.dataset.nowPlayingBrowseLevel || "show";
      if (!path) return;
      this.openNowPlayingBrowse(path, level);
    }));
  }

  requirePlayerEntity() {
    const playerEntity = this.configuredPlayerEntity();
    if (!playerEntity) {
      this.notifyApolloError("Select a Kodi Player in the Apollo Media card configuration.");
    }
    return playerEntity;
  }

  resetKodiTargetState() {
    window.clearInterval(this._continuePollTimer);
    window.clearInterval(this._nowPlayingTicker);
    window.clearTimeout(this._continueRefreshTimer);
    window.clearTimeout(this._activeApolloRefreshTimer);
    this._continuePollTimer = null;
    this._nowPlayingTicker = null;
    this._continueRefreshTimer = null;
    this._continueRefreshDue = null;
    this._continueRefreshQueued = false;
    this._activeApolloRefreshTimer = null;
    this._activeApolloRefreshInFlight = false;
    this._activeApolloRequestKey = null;
    this._activeApolloRequestAttempts = 0;
    this._kodiPlaybackSessionActive = false;
    this._apolloPlayback = null;
    this._pendingPlaybackReconciliation = null;
    this._nowPlayingPlayer = null;
    this._nowPlayingIdentity = null;
    this._nowPlayingArtwork = "";
    this._nowPlayingArtworkIdentity = null;
    this._activeContextNotBefore = 0;
    this._expectedPlaybackSource = "";
    this.closeNowPlaying();
    this.closeStreamPicker();
    this.closeFlagMenu();
  }

  sameApolloIdentity(left, right) {
    const leftImdb = String(left?.imdb || "").trim().toLowerCase();
    const rightImdb = String(right?.imdb || "").trim().toLowerCase();
    return Boolean(leftImdb && rightImdb) &&
      leftImdb === rightImdb &&
      Number(left?.season || 0) === Number(right?.season || 0) &&
      Number(left?.episode || 0) === Number(right?.episode || 0);
  }

  dedupeApolloItems(items) {
    const deduped = [];
    (items || []).forEach(item => {
      const duplicate = deduped.some(existing =>
        this.sameApolloIdentity(existing, item)
      );
      if (!duplicate) deduped.push(item);
    });
    return deduped;
  }

  playbackPosition(player, now = Date.now()) {
    const attributes = player?.attributes || {};
    let position = Number(attributes.media_position);
    const duration = Number(attributes.media_duration);
    if (!Number.isFinite(position) || position < 0) position = 0;

    if (String(player?.state || "").toLowerCase() === "playing") {
      const updatedAt = Date.parse(attributes.media_position_updated_at || "");
      if (Number.isFinite(updatedAt)) {
        position += Math.max(0, (now - updatedAt) / 1000);
      }
    }

    if (Number.isFinite(duration) && duration > 0) {
      position = Math.min(position, duration);
    }
    return {
      position,
      duration: Number.isFinite(duration) && duration > 0 ? duration : 0
    };
  }

  observeApolloPlayback(player) {
    const context = this._apolloPlayback;
    if (!context) return false;

    const state = String(player?.state || "unknown").toLowerCase();
    if (state === "playing" || state === "paused") {
      context.started = true;
      context.lastPlayablePlayer = player;
      const sample = this.playbackPosition(player);
      if (sample.position >= 0) context.position = sample.position;
      if (sample.duration > 0) context.duration = sample.duration;
      if (context.imdb && sample.duration > 0) {
        const liveProgress = Math.min(100, Math.max(0, (sample.position / sample.duration) * 100));
        this.patchApolloIdentity(context, {
          progress: liveProgress,
          resume_position: sample.position,
          resume_duration: sample.duration
        });
        const block = this.querySelector("[data-title-progress]");
        if (block && this.sameApolloIdentity(this.selectedTitle, context)) {
          block.querySelector("[data-title-progress-watched]")?.replaceChildren(
            document.createTextNode(`${this.formatMediaTime(sample.position)} watched`)
          );
          block.querySelector("[data-title-progress-remaining]")?.replaceChildren(
            document.createTextNode(`${this.formatMediaTime(Math.max(0, sample.duration - sample.position))} remaining`)
          );
          const fill = block.querySelector("[data-title-progress-fill]");
          if (fill) fill.style.width = `${liveProgress}%`;
        }
      }
      if (state === "playing") this.transitionCardPlaybackToNowPlaying(context);
    }

    const stopped = ["idle", "off", "stopped"].includes(state);
    if (!context.started || !stopped) return false;

    if (context.lastPlayablePlayer) {
      const finalSample = this.playbackPosition(context.lastPlayablePlayer);
      if (finalSample.position >= 0) context.position = finalSample.position;
      if (finalSample.duration > 0) context.duration = finalSample.duration;
    }

    this._apolloPlayback = null;
    this._pendingPlaybackReconciliation = context;
    this.applyOptimisticProgress(context, true);
    this.schedulePlaybackReconciliation(context);
    return true;
  }

  observeKodiPlayer(player) {
    const state = String(player?.state || "unknown").toLowerCase();
    const active = state === "playing" || state === "paused";
    const terminal = ["idle", "off", "stopped"].includes(state);

    if (active) {
      this._kodiPlaybackSessionActive = true;
      if (!this._continuePollTimer) {
        this._continuePollTimer = window.setInterval(() => {
          this.scheduleContinueWatchingRefresh(0);
        }, APOLLO_CONTINUE_POLL_MS);
      }
      return;
    }

    if (this._continuePollTimer) {
      window.clearInterval(this._continuePollTimer);
      this._continuePollTimer = null;
    }

    if (terminal && this._kodiPlaybackSessionActive) {
      this._kodiPlaybackSessionActive = false;
      this.scheduleContinueWatchingRefresh(APOLLO_CONTINUE_PERSIST_MS, true);
    }
  }

  continueWatchingRenderSignature(identity = null) {
    const continueRow = this.mediaRows.find(row => row.id === "continue");
    const identityCopies = [];
    const collect = (name, items) => {
      if (!identity?.imdb) return;
      (items || []).forEach(item => {
        if (this.sameApolloIdentity(item, identity)) {
          identityCopies.push([
            name,
            item.file || "",
            item.progress,
            item.resume_position,
            item.resume_duration
          ]);
        }
      });
    };

    this.mediaRows.forEach(row => {
      if (row.id !== "continue") collect(`row:${row.id}`, row.items);
    });
    collect("library:movies", this.library.movies);
    collect("library:shows", this.library.shows);
    collect("catalog", this.catalogItems);
    collect("browser", this.browserItems);
    collect("selected", this.selectedTitle ? [this.selectedTitle] : []);
    collect("detail-history", this.detailTitleHistory);

    return JSON.stringify({
      continueItems: continueRow?.items || [],
      identityCopies
    });
  }

  apolloItemIdentityKey(item) {
    const imdb = String(item?.imdb || "").trim().toLowerCase();
    if (imdb) {
      return `${imdb}:${Number(item?.season || 0)}:${Number(item?.episode || 0)}`;
    }
    return `file:${String(item?.file || "")}`;
  }

  continueWatchingStructureSignature(items) {
    return JSON.stringify((items || []).map(item => [
      this.apolloItemIdentityKey(item),
      item.file || "",
      item.title || "",
      item.subtitle || "",
      item.poster || "",
      item.fanart || "",
      item.plot || "",
      item.year || 0,
      Boolean(item.watched)
    ]));
  }

  progressPercent(item) {
    const position = Math.max(0, Number(item?.resume_position || 0));
    const duration = Math.max(0, Number(item?.resume_duration || 0));
    if (duration > 0) {
      return Math.min(100, Math.max(0, (position / duration) * 100));
    }
    const progress = Number(item?.progress);
    return Number.isFinite(progress) ? Math.min(100, Math.max(0, progress)) : null;
  }

  formatMediaTime(value) {
    const numeric = Number(value);
    const totalSeconds = Number.isFinite(numeric)
      ? Math.max(0, Math.floor(numeric))
      : 0;
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    return hours > 0
      ? `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`
      : `${minutes}:${String(seconds).padStart(2, "0")}`;
  }

  patchPosterProgress(button, item) {
    const poster = button?.querySelector?.(".poster");
    if (!poster) return;
    const progress = this.progressPercent(item);
    let track = poster.querySelector(".poster-progress");
    if (progress === null) {
      track?.remove();
      return;
    }
    if (!track) {
      track = document.createElement("div");
      track.className = "poster-progress";
      track.innerHTML = '<div class="poster-progress-fill"></div>';
      poster.appendChild(track);
    }
    const fill = track.querySelector(".poster-progress-fill");
    if (fill) fill.style.width = `${progress}%`;
  }

  patchContinueWatchingDom() {
    const items = this.mediaRows.find(row => row.id === "continue")?.items || [];
    const buttons = this.querySelectorAll(
      '.media-home-row[data-row-id="continue"] [data-apollo-row="continue"]'
    );
    buttons.forEach((button, index) => this.patchPosterProgress(button, items[index]));

    if (this.detailState?.entryPoint !== "continue" || !this.selectedTitle) return;
    const authoritative = items.find(item =>
      this.sameApolloIdentity(item, this.selectedTitle) ||
      this.apolloItemIdentityKey(item) === this.apolloItemIdentityKey(this.selectedTitle)
    );
    if (!authoritative) return;
    this.selectedTitle = { ...this.selectedTitle, ...authoritative };

    const block = this.querySelector("[data-title-progress]");
    if (!block) return;
    const position = Math.max(0, Number(authoritative.resume_position || 0));
    const duration = Math.max(0, Number(authoritative.resume_duration || 0));
    const progress = this.progressPercent(authoritative) || 0;
    const watched = block.querySelector("[data-title-progress-watched]");
    const remaining = block.querySelector("[data-title-progress-remaining]");
    const fill = block.querySelector("[data-title-progress-fill]");
    if (watched) watched.textContent = position > 0
      ? `${this.formatMediaTime(position)} watched`
      : "In progress";
    if (remaining) remaining.textContent = duration > 0
      ? `${this.formatMediaTime(Math.max(0, duration - position))} remaining`
      : `${Math.round(progress)}%`;
    if (fill) fill.style.width = `${progress}%`;
  }

  normalizeRailScrollLeft(value) {
    const numeric = Math.max(0, Number(value) || 0);
    // Values this close to the leading edge are layout/scroll-anchoring noise.
    // Snapping them to zero preserves the rail's visible 17px left inset.
    return numeric <= 24 ? 0 : numeric;
  }

  captureApolloScrollState() {
    const railScroll = new Map(
      [...this.querySelectorAll(".media-home-row[data-row-id]")].map(row => [
        row.dataset.rowId,
        this.normalizeRailScrollLeft(row.querySelector(".horizontal-row")?.scrollLeft || 0)
      ])
    );
    const ancestorScroll = [];
    for (let node = this.parentElement; node; node = node.parentElement) {
      if (node.scrollTop || node.scrollLeft) {
        ancestorScroll.push([node, node.scrollTop, node.scrollLeft]);
      }
    }
    return {
      contentScroll: this.querySelector(".content")?.scrollTop || 0,
      railScroll,
      titleScroll: this.querySelector(".title-sheet")?.scrollTop || 0,
      ancestorScroll,
      windowScroll: [Number(window.scrollX || 0), Number(window.scrollY || 0)]
    };
  }

  restoreApolloScrollState(state, settle = false) {
    if (!state) return;
    const restore = () => {
      const content = this.querySelector(".content");
      if (content) content.scrollTop = state.contentScroll;
      state.railScroll.forEach((scrollLeft, rowId) => {
        const rail = this.querySelector(
          `.media-home-row[data-row-id="${rowId}"] .horizontal-row`
        );
        if (rail) rail.scrollLeft = this.normalizeRailScrollLeft(scrollLeft);
      });
      const titleSheet = this.querySelector(".title-sheet");
      if (titleSheet) titleSheet.scrollTop = state.titleScroll;
      state.ancestorScroll.forEach(([node, scrollTop, scrollLeft]) => {
        node.scrollTop = scrollTop;
        node.scrollLeft = scrollLeft;
      });
      if (typeof window.scrollTo === "function") {
        window.scrollTo(state.windowScroll[0], state.windowScroll[1]);
      }
    };

    restore();
    if (!settle) return;
    const afterMicrotask = () => {
      restore();
      if (typeof window.requestAnimationFrame === "function") {
        window.requestAnimationFrame(() => {
          restore();
          window.requestAnimationFrame(restore);
        });
      }
    };
    if (typeof queueMicrotask === "function") queueMicrotask(afterMicrotask);
    else Promise.resolve().then(afterMicrotask);
  }

  replaceContinueWatchingRail() {
    const row = this.mediaRows.find(item => item.id === "continue");
    const rail = this.querySelector(
      '.media-home-row[data-row-id="continue"] .horizontal-row'
    );
    if (!row || !rail) {
      this.patchContinueWatchingDom();
      return;
    }

    const scrollState = this.captureApolloScrollState();
    rail.innerHTML = this.renderRailItems(row);
    this.bindApolloItemButtons(rail);
    this.patchContinueWatchingDom();
    this.restoreApolloScrollState(scrollState, true);
  }

  patchApolloIdentity(identity, patch) {
    const patchItems = items => (items || []).map(item =>
      this.sameApolloIdentity(item, identity) ? { ...item, ...patch } : item
    );

    this.mediaRows.forEach(row => { row.items = patchItems(row.items); });
    this.library.movies = patchItems(this.library.movies);
    this.library.shows = patchItems(this.library.shows);
    this.catalogItems = patchItems(this.catalogItems);
    this.browserItems = patchItems(this.browserItems);
    if (this.sameApolloIdentity(this.selectedTitle, identity)) {
      this.selectedTitle = { ...this.selectedTitle, ...patch };
    }
    this.detailTitleHistory = patchItems(this.detailTitleHistory);
  }

  applyOptimisticProgress(context, updateContinue = true) {
    if (!context?.imdb) return;
    const position = Math.max(0, Number(context.position || 0));
    const duration = Math.max(0, Number(context.duration || 0));
    const progress = duration > 0
      ? Math.min(100, Math.max(0, (position / duration) * 100))
      : undefined;
    const completed = duration > 0 && position / duration >= APOLLO_COMPLETION_RATIO;

    this.patchApolloIdentity(context, {
      progress,
      resume_position: position,
      resume_duration: duration
    });

    if (!updateContinue) return;
    const continueRow = this.mediaRows.find(row => row.id === "continue");
    if (!continueRow) return;

    const matches = (continueRow.items || []).filter(item =>
      this.sameApolloIdentity(item, context)
    );
    const withoutMatches = (continueRow.items || []).filter(item =>
      !this.sameApolloIdentity(item, context)
    );

    if (position > 0 && !completed) {
      const base = matches[0] || context.sourceItem;
      continueRow.items = [{
        ...base,
        progress,
        resume_position: position,
        resume_duration: duration
      }, ...withoutMatches];
    } else if (completed) {
      continueRow.items = withoutMatches;
    }
  }

  reconcilePlaybackProgress(context) {
    if (this._pendingPlaybackReconciliation !== context) return;
    const continueRow = this.mediaRows.find(row => row.id === "continue");
    const authoritative = (continueRow?.items || []).find(item =>
      this.sameApolloIdentity(item, context)
    );

    if (authoritative) {
      this.patchApolloIdentity(context, {
        progress: authoritative.progress,
        resume_position: authoritative.resume_position,
        resume_duration: authoritative.resume_duration
      });
    } else {
      this.patchApolloIdentity(context, {
        progress: undefined,
        resume_position: undefined,
        resume_duration: undefined
      });
    }

    window.clearTimeout(this._continueRefreshTimer);
    this._continueRefreshTimer = null;
    this._continueRefreshDue = null;
    this._pendingPlaybackReconciliation = null;
  }

  schedulePlaybackReconciliation(context) {
    if (this._pendingPlaybackReconciliation !== context) return;
    this.scheduleContinueWatchingRefresh(APOLLO_CONTINUE_PERSIST_MS, true);
  }

  scheduleContinueWatchingRefresh(delay = 0, replacePending = false) {
    const safeDelay = Math.max(0, Number(delay || 0));
    const due = Date.now() + safeDelay;
    if (this._continueRefreshTimer) {
      const sameWindow = Math.abs(this._continueRefreshDue - due) < 250;
      if (sameWindow || (!replacePending && this._continueRefreshDue <= due)) return;
    }

    window.clearTimeout(this._continueRefreshTimer);
    this._continueRefreshDue = due;
    this._continueRefreshTimer = window.setTimeout(() => {
      this._continueRefreshTimer = null;
      this._continueRefreshDue = null;
      // Polling is best-effort and may be skipped while another reconciliation
      // is running. Stop/config changes must queue behind the active request.
      this.refreshContinueWatching(replacePending);
    }, safeDelay);
  }

  async refreshContinueWatching(queueIfBusy = true) {
    const playerEntity = this.configuredPlayerEntity();
    if (!playerEntity) return false;
    if (this._continueRefreshInFlight) {
      if (queueIfBusy) this._continueRefreshQueued = true;
      return false;
    }

    this._continueRefreshInFlight = true;
    try {
      if (this.config?.ams_enabled !== false) {
        // AMS clients reconcile directly against profile state. Do not touch
        // the legacy shared HA Continue Watching sensor, which would wake and
        // rerender every Apollo card in the dashboard.
        await this.loadAmsContinueWatching({ sync: true });
      } else {
        await this.callApolloScript(this.config.progress_refresh_script, {
          player_entity: playerEntity
        });
      }
      this._continueRefreshErrorLogged = false;
    } catch (error) {
      if (!this._continueRefreshErrorLogged) {
        console.error("Apollo Continue Watching reconciliation failed", error);
        this._continueRefreshErrorLogged = true;
      }
    } finally {
      this._continueRefreshInFlight = false;
      if (this._continueRefreshQueued) {
        this._continueRefreshQueued = false;
        this.scheduleContinueWatchingRefresh(250, true);
      }
    }
  }

  async playApolloItem(item, playbackAction = null, sourcePreference = "default") {
    if (this._playbackPending) return false;

    const notifyError = message => this.notifyApolloError(message);

    if (!item) {
      notifyError("Apollo playback item is unavailable.");
      return false;
    }
    if (item.is_folder) {
      notifyError("Open this item before playing it.");
      return false;
    }

    const localPath = String(item.playTarget || item.file || item.path || "");
    const remotePath = String(item.remoteAutoTarget || "");
    const useRemoteDefault = sourcePreference !== "local" && Boolean(remotePath);
    const path = useRemoteDefault ? remotePath : localPath;
    if (!path) {
      notifyError("Apollo playback path is unavailable.");
      return false;
    }
    if (!path.startsWith("plugin://plugin.video.apollomedia/")) {
      notifyError("Apollo refused an unsupported playback path.");
      return false;
    }
    const playerEntity = this.requirePlayerEntity();
    if (!playerEntity) return false;

    const playButtons = [...this.querySelectorAll("[data-title-play-action], [data-title-play]")];
    const buttonStates = playButtons.map(button => Boolean(button.disabled));
    const routeParams = this.fileParams(path);
    this._playbackPending = true;
    playButtons.forEach(button => {
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
    });

    try {
      this.invalidateActiveApolloContext(useRemoteDefault ? "remote" : "local");
      this._apolloPlayback = {
        path,
        imdb: item.imdb || routeParams.imdb || "",
        media_type: item.media_type || routeParams.media_type || "movie",
        season: Number(item.season || routeParams.season || 0),
        episode: Number(item.episode || routeParams.episode || 0),
        title: item.title || "",
        sourceItem: {
          ...item,
          file: path
        },
        cardInitiated: true,
        nowPlayingTransitioned: false,
        started: false,
        position: 0,
        duration: 0,
        lastPlayablePlayer: null
      };
      const variables = {
        path,
        player_entity: playerEntity
      };
      if (playbackAction === "resume" || playbackAction === "start_over") {
        variables.resume = playbackAction === "resume";
      }
      await this.callApolloScript(this.config.play_script, variables);
      return true;
    } catch (error) {
      this._apolloPlayback = null;
      console.error("Apollo playback dispatch failed", error);
      notifyError("Apollo could not start playback.");
      return false;
    } finally {
      this._playbackPending = false;
      playButtons.forEach((button, index) => {
        if (!button.isConnected) return;
        button.disabled = buttonStates[index];
        button.removeAttribute("aria-busy");
      });
    }
  }

  itemForFile(file) {
    for (const row of this.mediaRows || []) {
      const found = (row.items || []).find(item => item.file === file);
      if (found) return found;
    }
    for (const row of this.libraryHomeRows || []) {
      const found = (row.items || []).find(item => item.file === file);
      if (found) return found;
    }
    return [...(this.library?.movies || []), ...(this.library?.shows || []), ...(this.browserItems || [])]
      .find(item => item.file === file);
  }

  redraw() {
    const screen = this.currentScreen || "home";
    const section = this.currentMediaSection || "home";
    const tab = this.currentLibraryTab || "home";
    this.render();
    this.bindEvents();
    this.showScreen(screen);
    this.showMediaSection(section);
    this.showLibraryTab(tab);
    this.updateNowPlaying(this._nowPlayingPlayer);
  }

  renderPreservingState() {
    const screen = this.currentScreen || "home";
    const section = this.currentMediaSection || "home";
    const tab = this.currentLibraryTab || "home";
    const scrollState = this.captureApolloScrollState();

    this.render();
    this.bindEvents();
    this.showScreen(screen);
    this.showMediaSection(section);
    this.showLibraryTab(tab);

    this.restoreApolloScrollState(scrollState, true);
  }

  canonicalDetailType(item) {
    const type = String(item?.media_type || "").trim().toLowerCase();
    if (type === "series" || type === "tvshow") return "show";
    if (["movie", "show", "season", "episode"].includes(type)) return type;
    if (Number(item?.episode || 0) > 0) return "episode";
    if (Number(item?.season || 0) > 0 && item?.is_folder) return "season";
    return item?.is_folder ? "show" : "movie";
  }

  detailChildrenTarget(item) {
    const type = this.canonicalDetailType(item);
    if (type === "show") return item?.browseTarget || item?.file || "";
    if (type === "season") return item?.seasonTarget || item?.file || "";
    return "";
  }

  makeParentShowDetail(item, path = "") {
    const target = path || item?.browseTarget || "";
    const params = this.fileParams(target);
    const title = String(item?.series_title || params.show_title || item?.title || "Show").trim();
    return {
      ...item,
      title,
      series_title: title,
      episode_title: "",
      media_type: "show",
      season: 0,
      episode: 0,
      file: target,
      browseTarget: target,
      seasonTarget: "",
      is_folder: true,
      // Episode plot/progress must never leak into a parent Show detail.
      plot: this.canonicalDetailType(item) === "show" ? (item?.plot || "") : "",
      progress: undefined,
      resume_position: 0,
      resume_duration: 0
    };
  }

  makeParentSeasonDetail(item, path = "") {
    const target = path || item?.seasonTarget || "";
    const params = this.fileParams(target);
    const season = Number(params.season || item?.season || 0);
    const showTitle = String(item?.series_title || params.show_title || item?.title || "Show").trim();
    const showTarget = String(params.show_target || item?.browseTarget || "");
    return {
      ...item,
      title: season === 0 ? "Specials" : `Season ${season}`,
      series_title: showTitle,
      episode_title: "",
      media_type: "season",
      season,
      episode: 0,
      file: target,
      seasonTarget: target,
      browseTarget: showTarget,
      is_folder: true,
      // Do not display the originating episode synopsis as season metadata.
      plot: this.canonicalDetailType(item) === "season" ? (item?.plot || "") : "",
      progress: undefined,
      resume_position: 0,
      resume_duration: 0
    };
  }

  openTitle(item, detailState = {}) {
    if (!item) return;
    const type = this.canonicalDetailType(item);
    this.selectedTitle = { ...item, media_type: type };
    this.detailState = {
      open: true,
      entryPoint: detailState.entryPoint || "item"
    };
    this.detailHistory = [];
    this.detailTitleHistory = [];
    this.detailPath = this.detailChildrenTarget(this.selectedTitle);
    this.redraw();
    if (this.detailPath) this.loadDetailPath(this.detailPath, false);
  }

  loadDetailPath(path, remember = true) {
    if (!path) return;
    if (remember && this.detailPath && this.detailPath !== path) {
      this.detailHistory = [...(this.detailHistory || []), this.detailPath];
    }
    this.detailPath = path;
    const playerEntity = this.requirePlayerEntity();
    if (playerEntity) {
      this.callApolloScript(this.config.browse_script, { path, player_entity: playerEntity });
    }
    this.redraw();
  }

  seasonDisplayLabel(item) {
    const params = this.fileParams(item?.file || "");
    const itemSeason = Number(item?.season);
    const paramSeason = Number(params.season);
    const season = Number.isFinite(itemSeason) && itemSeason >= 0 ? itemSeason : paramSeason;
    if (Number.isFinite(season)) return season === 0 ? "Specials" : `Season ${season}`;
    const title = String(item?.title || "").trim();
    return /^specials$/i.test(title) ? "Specials" : title;
  }

  renderTitleModal() {
    if (!this.selectedTitle) return "";
    const item = this.selectedTitle;
    const browser = this._hass?.states?.[this.config.browse_entity];
    const loadedPath = String(browser?.attributes?.directory || "");
    const pathParams = this.fileParams(this.detailPath);
    const detailType = this.canonicalDetailType(item);
    const browsingSeasons = detailType === "show";
    const browsingEpisodes = detailType === "season";
    const browsing = (browsingSeasons || browsingEpisodes) && Boolean(this.detailPath);
    const rawChildren = loadedPath === this.detailPath ? this.browserItems : [];
    const expectedSeason = Number(item.season || pathParams.season || 0);
    const children = browsingEpisodes && expectedSeason >= 0
      ? rawChildren.filter(child => {
          const childParams = this.fileParams(child?.file || "");
          const childSeason = Number(child?.season || childParams.season || 0);
          return childSeason === expectedSeason;
        }).sort((left, right) => Number(left?.episode || 0) - Number(right?.episode || 0))
      : rawChildren;
    const continueDetail = this.detailState?.entryPoint === "continue";
    const heroArtwork = item.fanart || item.poster || "";
    const position = Math.max(0, Number(item.resume_position || 0));
    const duration = Math.max(0, Number(item.resume_duration || 0));
    const progress = duration > 0
      ? Math.min(100, Math.max(0, (position / duration) * 100))
      : Number(item.progress || 0);
    const resumable = position > 0 || progress > 0;
    const seasonNumber = Number(pathParams.season || item.season || 0);
    const showTitle = String(item.series_title || pathParams.show_title || (detailType === "show" ? item.title : "") || "").trim();

    const progressMarkup = resumable && (detailType === "movie" || detailType === "episode")
      ? `<div class="title-progress-block" data-title-progress>
          <div class="title-progress-copy">
            <span data-title-progress-watched>${position > 0 ? `${this.formatMediaTime(position)} watched` : "In progress"}</span>
            <span data-title-progress-remaining>${duration > 0 ? `${this.formatMediaTime(Math.max(0, duration - position))} remaining` : `${Math.round(progress)}%`}</span>
          </div>
          <div class="title-progress-track"><span data-title-progress-fill style="width:${progress}%"></span></div>
        </div>`
      : "";

    const childMarkup = browsing
      ? (children.length
          ? children.map(child => {
              const childTitle = browsingSeasons
                ? this.seasonDisplayLabel(child)
                : (child.episode_title || child.title || "Untitled");
              const episodeCode = browsingEpisodes
                ? `S${Number(child.season || expectedSeason || 0)} E${Number(child.episode || 0)}`
                : "";
              const childProgress = browsingEpisodes
                ? (child.watched ? 100 : this.progressPercent(child))
                : null;
              const childPoster = browsingEpisodes
                ? { ...child, progress: undefined, resume_position: 0, resume_duration: 0 }
                : child;
              return `
              <button class="title-child${browsingEpisodes ? " episode-row" : ""}" type="button" data-detail-child="${encodeURIComponent(child.file || "")}" data-detail-folder="${child.is_folder ? "true" : "false"}">
                ${this.posterMarkup(childPoster, "title-child-poster")}
                <span>
                  <strong>${childTitle}</strong>
                  ${browsingEpisodes
                    ? `<span class="episode-inline-meta">
                        <small>${episodeCode}</small>
                        ${Number.isFinite(childProgress) && childProgress > 0
                          ? `<span class="episode-inline-progress" aria-label="${Math.round(childProgress)} percent watched"><i style="width:${childProgress}%"></i></span>`
                          : ""}
                      </span>`
                    : ""}
                  ${browsingEpisodes && child.plot ? `<em>${child.plot}</em>` : ""}
                </span>
                <ha-icon icon="mdi:chevron-right"></ha-icon>
              </button>`;
            }).join("")
          : `<div class="title-loading"><ha-icon icon="mdi:loading"></ha-icon> Loading…</div>`)
      : "";

    let heading = item.title || "Untitled";
    let meta = item.subtitle || "";
    let breadcrumbs = "";
    let sectionLabel = "";

    if (detailType === "show") {
      heading = item.title || showTitle || "Untitled";
      meta = item.subtitle || (item.year ? String(item.year) : "");
      sectionLabel = "Seasons";
    } else if (detailType === "season") {
      heading = showTitle || item.series_title || "Untitled";
      meta = seasonNumber === 0 ? "Specials" : `Season ${seasonNumber}`;
      sectionLabel = seasonNumber === 0 ? "Specials" : `Season ${seasonNumber}`;
      if (item.browseTarget) {
        breadcrumbs = `<button class="season-show-link detail-link" type="button" data-detail-browse-level="show" data-detail-browse="${encodeURIComponent(item.browseTarget)}">${heading}</button>`;
        heading = "";
      }
    } else if (detailType === "episode") {
      heading = item.episode_title || item.title || "Untitled";
      meta = `Episode ${Number(item.episode || 0)}${duration > 0 ? ` · ${this.formatMediaTime(duration)}` : ""}`;
      if (item.series_title) {
        breadcrumbs += item.browseTarget
          ? `<button class="episode-breadcrumb detail-link" type="button" data-detail-browse-level="show" data-detail-browse="${encodeURIComponent(item.browseTarget)}">${item.series_title}</button>`
          : `<div class="episode-breadcrumb">${item.series_title}</div>`;
      }
      if (item.season) {
        breadcrumbs += item.seasonTarget
          ? `<button class="episode-season detail-link" type="button" data-detail-browse-level="season" data-detail-browse="${encodeURIComponent(item.seasonTarget)}">Season ${item.season}</button>`
          : `<div class="episode-season">Season ${item.season}</div>`;
      }
    } else {
      meta = item.subtitle || (item.year ? String(item.year) : "");
    }

    const showActions = detailType === "movie" || detailType === "episode";
    const playbackActions = showActions
      ? `<div class="title-actions${resumable ? " continue-actions" : ""}">
          ${resumable
            ? `<button class="title-primary" type="button" data-title-play-action="resume"><ha-icon icon="mdi:play"></ha-icon> Resume</button>
               <button class="title-secondary" type="button" data-title-play-action="start_over"><ha-icon icon="mdi:restart"></ha-icon> Start Over</button>`
            : `<button class="title-primary" type="button" data-title-play="${encodeURIComponent(item.file || "")}"><ha-icon icon="mdi:play"></ha-icon> Play</button>`}
          ${item.in_library && item.remoteAutoTarget ? `<button class="title-secondary" type="button" data-title-play-local><ha-icon icon="mdi:harddisk"></ha-icon> ${resumable ? "Resume Locally" : "Play Locally"}</button>` : ""}
          ${item.remoteChooseTarget ? `<button class="title-secondary" type="button" data-title-stream-picker="${encodeURIComponent(item.remoteChooseTarget)}"><ha-icon icon="mdi:format-list-bulleted"></ha-icon> Choose Stream</button>` : ""}
          <button class="title-secondary" type="button" data-title-tv="${encodeURIComponent(item.file || "")}"><ha-icon icon="mdi:television"></ha-icon> Show on TV</button>
          ${continueDetail && item.removeTarget ? `<button class="title-secondary title-remove" type="button" data-title-remove-continue="${encodeURIComponent(item.removeTarget)}"><ha-icon icon="mdi:playlist-remove"></ha-icon> Remove from Continue Watching</button>` : ""}
        </div>`
      : `<div class="title-actions browse-actions">
          <button class="title-secondary" type="button" data-title-tv="${encodeURIComponent(this.detailPath || item.file || "")}"><ha-icon icon="mdi:television"></ha-icon> Show on TV</button>
        </div>`;

    return `
      <div class="title-overlay open browse-detail" data-detail-type="${detailType}">
        <section class="title-sheet browse-detail-sheet">
          <div class="title-hero${!item.fanart && item.poster ? " poster-fallback" : ""}" style="${heroArtwork ? `background-image:linear-gradient(to bottom,rgba(8,9,11,.18),#08090b),url('${String(heroArtwork).replaceAll("'", "%27")}')` : ""}">
            <button class="title-close" type="button" aria-label="Close"><ha-icon icon="mdi:close"></ha-icon></button>
            ${(this.detailHistory || []).length ? `<button class="title-back" type="button" aria-label="Back"><ha-icon icon="mdi:arrow-left"></ha-icon></button>` : ""}
          </div>
          <div class="title-content">
            ${breadcrumbs}
            ${heading ? `<h2>${heading}</h2>` : ""}
            ${meta ? `<div class="title-meta">${meta}</div>` : ""}
            ${detailType !== "episode" && duration > 0 ? `<div class="title-runtime">${this.formatMediaTime(duration)}</div>` : ""}
            ${item.plot ? `<p>${item.plot}</p>` : ""}
            ${progressMarkup}
            ${playbackActions}
            ${sectionLabel ? `<div class="title-section-label">${sectionLabel}</div>` : ""}
            <div class="title-children">${childMarkup}</div>
          </div>
        </section>
      </div>`;
  }


  posterMarkup(item, extraClass = "") {
    const progress =
      typeof item.progress === "number"
        ? `
          <div class="poster-progress">
            <div class="poster-progress-fill" style="width:${item.progress}%"></div>
          </div>
        `
        : "";

    const watched = item.watched
      ? `
        <div class="watched-badge" aria-label="Watched">
          <ha-icon icon="mdi:check"></ha-icon>
        </div>
      `
      : "";
    const inLibrary = item.in_library
      ? `<div class="library-badge" aria-label="In library" title="In library"><ha-icon icon="mdi:bookshelf"></ha-icon></div>`
      : "";

    const posterUrl = /^(?:https?:\/\/|blob:)/i.test(String(item.poster || "")) ? item.poster : "";
    const posterStyle = posterUrl
      ? ` style="background-image:url('${String(posterUrl).replaceAll("'", "%27")}');background-size:cover;background-position:center"`
      : "";

    return `
      <div class="poster ${extraClass} ${posterUrl ? "apollo-poster" : (item.poster || "poster-one")}"${posterStyle}>
        ${watched}
        ${inLibrary}
        ${progress}
      </div>
    `;
  }

  sortDateValue(value) {
    const parsed = Date.parse(String(value || ""));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  sortedItems(items, context) {
    const mode = this.sortModes[context] || "default";
    const result = [...(items || [])];
    const title = item => String(item?.title || "").localeCompare;
    const compareTitle = (a, b) => String(a.title || "").localeCompare(String(b.title || ""));
    const date = (item, field) => this.sortDateValue(item?.[field]);
    if (mode === "title" || mode === "title_asc") result.sort(compareTitle);
    if (mode === "title_desc") result.sort((a, b) => compareTitle(b, a));
    if (mode === "year" || mode === "release_date_desc") result.sort((a, b) => (date(b, "release_date") || Number(b.year || 0)) - (date(a, "release_date") || Number(a.year || 0)));
    if (mode === "release_date_asc") result.sort((a, b) => (date(a, "release_date") || Number(a.year || 0)) - (date(b, "release_date") || Number(b.year || 0)));
    if (mode === "added" || mode === "date_added_desc") result.sort((a, b) => date(b, "dateadded") - date(a, "dateadded"));
    if (mode === "date_added_asc") result.sort((a, b) => date(a, "dateadded") - date(b, "dateadded"));
    if (mode === "last_episode_added_desc") result.sort((a, b) => date(b, "last_episode_added") - date(a, "last_episode_added"));
    if (mode === "last_episode_added_asc") result.sort((a, b) => date(a, "last_episode_added") - date(b, "last_episode_added"));
    return result;
  }

  sortOptionsForContext(context) {
    if (context === "media-library-shows") return [
      ["default", "Default"], ["title_asc", "Title A–Z"], ["title_desc", "Title Z–A"],
      ["release_date_desc", "Release date ↓"], ["release_date_asc", "Release date ↑"],
      ["date_added_desc", "Date added ↓"], ["date_added_asc", "Date added ↑"],
      ["last_episode_added_desc", "Last episode added ↓"], ["last_episode_added_asc", "Last episode added ↑"]
    ];
    if (context === "media-library-movies") return [
      ["default", "Default"], ["title_asc", "Title A–Z"], ["title_desc", "Title Z–A"],
      ["release_date_desc", "Release date ↓"], ["release_date_asc", "Release date ↑"],
      ["date_added_desc", "Date added ↓"], ["date_added_asc", "Date added ↑"]
    ];
    return [["default", "Default"]];
  }

  setSortMode(mode, persist = true) {
    const context = this.getOptionsContext();
    this.sortModes[context] = mode || "default";
    if (persist) {
      try { localStorage.setItem(`apollo-media.sort.${context}`, this.sortModes[context]); } catch (_) {}
    }
    const screen = this.currentScreen || "home";
    const section = this.currentMediaSection || "home";
    const tab = this.currentLibraryTab || "home";
    this.render(); this.bindEvents(); this.showScreen(screen); this.showMediaSection(section); this.showLibraryTab(tab);
    this.openOptions();
  }

  railSubtitle(item) {
    const season = Number(item?.season || 0);
    const episode = Number(item?.episode || 0);
    const subtitle = String(item?.subtitle || "");
    if (!episode) return subtitle;
    const episodeTitle = subtitle.replace(/^S\d+\s*E\d+\s*[•·]\s*/i, "").trim();
    const code = `S${season} E${episode}`;
    return episodeTitle ? `${code} · ${episodeTitle}` : code;
  }

  renderRailItems(row) {
    const displayItems = [...(row.items || [])];
    return displayItems.map((item, index) => `
      <button class="poster-item rail-poster-item" data-apollo-row="${row.id}" data-apollo-index="${index}" data-apollo-file="${encodeURIComponent(item.file || "")}" data-apollo-folder="${item.is_folder ? "true" : "false"}" type="button">
        ${this.posterMarkup(item, row.id === "continue" ? "continue-poster" : "")}
        <div class="poster-title">${item.title || ""}</div>
        <div class="poster-sub">${this.railSubtitle(item)}</div>
      </button>
    `).join("");
  }

  renderRail(row) {
    const items = this.renderRailItems(row);

    const hiddenClass = this.isMediaRowVisible(row.id) ? "" : " row-hidden";

    return `
      <section class="media-section media-home-row${hiddenClass}" data-row-id="${row.id}">
        <div class="section-header">
          <h2>${row.title}</h2>
          <button class="see-all" type="button">See All</button>
        </div>

        <div class="horizontal-row">
          ${items}
        </div>
      </section>
    `;
  }

  renderLibraryGrid(items, tab) {
    return this.sortedItems(items, `media-library-${tab}`).map((item, index) => `
      <button class="poster-grid-item" data-apollo-library="${index}" data-apollo-file="${encodeURIComponent(item.file || "")}" data-apollo-folder="${item.is_folder ? "true" : "false"}" type="button">
        ${this.posterMarkup(item, "grid-poster")}
        <div class="poster-title">${item.title || ""}</div>
        <div class="poster-sub">${this.railSubtitle(item)}</div>
      </button>
    `).join("");
  }

  isMediaRowVisible(rowId) {
    return this.mediaRowVisibility?.[rowId] !== false;
  }

  renderMediaRowOptions() {
    return this.mediaRows.map(row => `
      <div class="row-toggle-item" data-row-option="${row.id}">
        <button
          class="row-drag-handle"
          type="button"
          aria-label="Drag ${row.title} to reorder"
          title="Drag to reorder"
        >
          <ha-icon icon="mdi:drag"></ha-icon>
        </button>

        <div class="row-toggle-copy">
          <div class="option-title">${row.title}</div>
          <div class="option-subtitle">Show this row on Media Home</div>
        </div>

        <label class="row-toggle-control">
          <input
            class="media-row-toggle"
            type="checkbox"
            data-row-toggle="${row.id}"
            ${this.isMediaRowVisible(row.id) ? "checked" : ""}
          />
          <span class="toggle-switch" aria-hidden="true"></span>
        </label>
      </div>
    `).join("");
  }

  renderMediaHome() {
    return this.mediaRows.map(row => this.renderRail(row)).join("");
  }


  renderLibraryHome() {
    return (this.libraryHomeRows || []).map(row => this.renderRail(row)).join("");
  }

  renderMediaLibrary() {
    return `
      <div class="library-toolbar">
        <div class="library-segmented">
          <button class="library-tab active" data-library-tab="home" type="button">Home</button>
          <button class="library-tab" data-library-tab="shows" type="button">Shows</button>
          <button class="library-tab" data-library-tab="movies" type="button">Movies</button>
        </div>
        <div class="library-actions">
          <button class="tiny-action" type="button" aria-label="Search library"><ha-icon icon="mdi:magnify"></ha-icon></button>
          <button class="tiny-action" data-library-sort type="button" aria-label="Sort library"><ha-icon icon="mdi:sort"></ha-icon></button>
        </div>
      </div>

      <div class="library-panel active" data-library-panel="home">
        ${this.renderLibraryHome()}
      </div>
      <div class="library-panel" data-library-panel="shows">
        <div class="poster-grid" data-library-grid="shows"></div>
        <button class="library-load-more" data-library-load-more="shows" type="button" hidden>Load more</button>
      </div>
      <div class="library-panel" data-library-panel="movies">
        <div class="poster-grid" data-library-grid="movies"></div>
        <button class="library-load-more" data-library-load-more="movies" type="button" hidden>Load more</button>
      </div>
    `;
  }

  bindApolloItemButtons(root = this) {
    root.querySelectorAll("[data-apollo-row]").forEach(button => {
      button.addEventListener("click", () => {
        const file = decodeURIComponent(button.dataset.apolloFile || "");
        this.openTitle(this.itemForFile(file), { entryPoint: button.dataset.apolloRow });
      });
    });
  }

  bindLibraryItemButtons(root = this) {
    root.querySelectorAll("[data-apollo-library]").forEach(button => {
      button.addEventListener("click", () => {
        const file = decodeURIComponent(button.dataset.apolloFile || "");
        this.openTitle(this.itemForFile(file));
      });
    });
  }

  renderFullLibraryTab(tab, reset = false) {
    if (tab !== "movies" && tab !== "shows") return false;
    const entityId = tab === "movies" ? this.config.library_movies_entity : this.config.library_shows_entity;
    const entity = this._hass?.states?.[entityId];
    if (!entity) return false;
    const liveItems = this.apolloItems(entityId);
    const expectedCount = Math.max(0, Number(entity.state || 0));
    this.library[tab] = liveItems;
    const panel = this.querySelector(`.library-panel[data-library-panel="${tab}"]`);
    const grid = panel?.querySelector(`[data-library-grid="${tab}"]`);
    const more = panel?.querySelector(`[data-library-load-more="${tab}"]`);
    if (!grid) return false;
    if (reset) this.libraryRenderLimits[tab] = 60;
    const limit = Math.max(60, Number(this.libraryRenderLimits?.[tab] || 60));
    const visibleItems = liveItems.slice(0, limit);
    grid.innerHTML = this.renderLibraryGrid(visibleItems, tab);
    this.bindLibraryItemButtons(grid);
    if (more) { const remaining = Math.max(0, liveItems.length - visibleItems.length); more.hidden = remaining <= 0; more.textContent = remaining > 0 ? `Load more (${remaining} remaining)` : "Load more"; }
    if (!liveItems.length && expectedCount > 0) { grid.innerHTML = `<div class="empty-state">Apollo library page is not available yet. Run Refresh and reopen this tab.</div>`; console.error(`Apollo ${tab}: state=${expectedCount}, parsed=0`, entity.attributes); }
    return true;
  }

  syncLibraryTabFromHass(tab) { return this.renderFullLibraryTab(tab, false); }

  bindEvents() {
    this.bindApolloItemButtons(this);
    this.bindLibraryItemButtons(this);
    this.querySelectorAll("[data-library-load-more]").forEach(button => button.addEventListener("click", () => { const tab = button.dataset.libraryLoadMore; if (tab !== "movies" && tab !== "shows") return; this.libraryRenderLimits[tab] = Number(this.libraryRenderLimits?.[tab] || 60) + 60; this.renderFullLibraryTab(tab, false); }));

    this.querySelector(".title-close")?.addEventListener("click", () => {
      this.selectedTitle = null;
      this.detailState = { open: false, entryPoint: null };
      this.detailPath = "";
      this.detailHistory = [];
      this.detailTitleHistory = [];
      this.redraw();
    });
    this.querySelector(".title-back")?.addEventListener("click", () => {
      const history = [...(this.detailHistory || [])];
      const path = history.pop() || "";
      this.detailHistory = history;
      const titles = [...(this.detailTitleHistory || [])];
      this.selectedTitle = titles.pop() || this.selectedTitle;
      this.detailTitleHistory = titles;
      if (path === "__item__") {
        this.detailPath = "";
        this.redraw();
      } else if (path) {
        this.loadDetailPath(path, false);
      }
    });
    this.querySelectorAll("[data-detail-child]").forEach(button => {
      button.addEventListener("click", () => {
        const file = decodeURIComponent(button.dataset.detailChild || "");
        const child = this.browserItems.find(entry => entry.file === file);
        if (!child) return;
        if (child.is_folder) {
          const parent = this.selectedTitle;
          const childType = this.canonicalDetailType(child);
          const base = {
            ...child,
            media_type: childType,
            series_title: child.series_title || parent?.series_title || parent?.title || "",
            browseTarget: child.browseTarget || parent?.browseTarget || parent?.file || "",
            seasonTarget: child.seasonTarget || (childType === "season" ? (child.file || "") : "")
          };
          const next = childType === "season" ? this.makeParentSeasonDetail(base, child.file || "") : base;
          this.detailHistory = [...(this.detailHistory || []), this.detailPath || "__item__"];
          this.detailTitleHistory = [...(this.detailTitleHistory || []), parent];
          this.selectedTitle = next;
          this.detailPath = this.detailChildrenTarget(next);
          this.redraw();
          if (this.detailPath) this.loadDetailPath(this.detailPath, false);
        } else {
          this.detailHistory = [...(this.detailHistory || []), this.detailPath || "__item__"];
          this.detailTitleHistory = [...(this.detailTitleHistory || []), this.selectedTitle];
          this.selectedTitle = child;
          this.detailPath = "";
          this.redraw();
        }
      });
    });
    this.querySelectorAll("[data-detail-browse]").forEach(button => {
      button.addEventListener("click", () => {
        const path = decodeURIComponent(button.dataset.detailBrowse || "");
        if (!path) return;
        const level = button.dataset.detailBrowseLevel || "show";
        const origin = this.selectedTitle;
        const next = level === "season"
          ? this.makeParentSeasonDetail(origin, path)
          : this.makeParentShowDetail(origin, path);

        this.detailHistory = [...(this.detailHistory || []), this.detailPath || "__item__"];
        this.detailTitleHistory = [...(this.detailTitleHistory || []), origin];
        this.selectedTitle = next;
        this.detailState = { open: true, entryPoint: "detail-link" };
        this.detailPath = this.detailChildrenTarget(next);
        this.redraw();
        if (this.detailPath) this.loadDetailPath(this.detailPath, false);
      });
    });
    this.querySelector("[data-title-play]")?.addEventListener("click", async () => {
      await this.playApolloItem(this.selectedTitle);
    });
    this.querySelectorAll("[data-title-play-action]").forEach(button => {
      button.addEventListener("click", async () => {
        await this.playApolloItem(this.selectedTitle, button.dataset.titlePlayAction);
      });
    });
    this.querySelector("[data-title-play-local]")?.addEventListener("click", async () => {
      const resumable = Number(this.selectedTitle?.resume_position || 0) > 0 || Number(this.selectedTitle?.progress || 0) > 0;
      await this.playApolloItem(this.selectedTitle, resumable ? "resume" : null, "local");
    });
    this.querySelector("[data-title-stream-picker]")?.addEventListener("click", event => {
      const path = decodeURIComponent(event.currentTarget.dataset.titleStreamPicker || "");
      if (path) this.openStreamPicker(path, this.selectedTitle);
    });
    this.querySelector("[data-title-tv]")?.addEventListener("click", event => {
      const path = decodeURIComponent(event.currentTarget.dataset.titleTv || "");
      const playerEntity = this.requirePlayerEntity();
      if (path && playerEntity) {
        this.callApolloScript(this.config.show_script, { path, player_entity: playerEntity });
      }
    });
    this.querySelector("[data-title-remove-continue]")?.addEventListener("click", async event => {
      const playerEntity = this.requirePlayerEntity();
      if (!playerEntity || this._removeContinuePending) return;
      const removedItem = this.selectedTitle ? { ...this.selectedTitle } : null;
      if (!removedItem) return;
      const removeParams = this.fileParams(removedItem.removeTarget || "");
      const source = String(removeParams.source || (removedItem.in_library ? "jellyfin" : "apollo"));
      this._removeContinuePending = true;
      event.currentTarget.disabled = true;
      try {
        await this.callApolloScript(this.config.remove_continue_script, {
          player_entity: playerEntity,
          source,
          item_id: String(removeParams.item_id || removedItem.jellyfin_item_id || ""),
          imdb: String(removeParams.imdb || removedItem.imdb || ""),
          season: Number(removeParams.season || removedItem.season || 0),
          episode: Number(removeParams.episode || removedItem.episode || 0)
        });

        const continueRow = this.mediaRows.find(row => row.id === "continue");
        if (continueRow && removedItem) {
          continueRow.items = (continueRow.items || []).filter(item =>
            !(this.sameApolloIdentity(item, removedItem) ||
              this.apolloItemIdentityKey(item) === this.apolloItemIdentityKey(removedItem))
          );
        }

        this.selectedTitle = null;
        this.detailState = { open: false, entryPoint: null };
        this.detailPath = "";
        this.detailHistory = [];
        this.detailTitleHistory = [];
        this.querySelector(".title-overlay")?.remove();
        this.replaceContinueWatchingRail();
        this.scheduleContinueWatchingRefresh(250, true);
      } catch (error) {
        console.error("Apollo Remove from Continue Watching failed", error);
        this.notifyApolloError("Apollo could not remove this item from Continue Watching.");
      } finally {
        this._removeContinuePending = false;
      }
    });

    this.querySelector("[data-now-playing-open]")?.addEventListener("click", () => {
      this.openNowPlaying();
    });
    this.querySelector("[data-now-playing-mini-toggle]")?.addEventListener("click", event => {
      event.stopPropagation();
      this.toggleNowPlayingPlayback();
    });
    this.bindNowPlayingEvents();

    this.querySelectorAll(".nav-item[data-screen]").forEach(btn => {
      btn.addEventListener("click", () => this.showScreen(btn.dataset.screen));
    });

    this.querySelector("[data-library-sort]")?.addEventListener("click", () => {
      if ((this.currentLibraryTab || "home") !== "home") this.openOptions();
    });

    const optionsBtn = this.querySelector(".options-action");
    if (optionsBtn) {
      optionsBtn.addEventListener("click", () => this.openOptions());
    }

    const refreshBtn = this.querySelector(".refresh-action");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => this.beginMediaRefresh());
      this.updateRefreshControl();
    }

    const optionsClose = this.querySelector(".options-close");
    if (optionsClose) {
      optionsClose.addEventListener("click", () => this.closeOptions());
    }

    const optionsOverlay = this.querySelector(".options-overlay");
    if (optionsOverlay) {
      optionsOverlay.addEventListener("click", event => {
        if (event.target === optionsOverlay) this.closeOptions();
      });
    }

    this.querySelector(".poster-size-open")?.addEventListener("click", () => {
      this.openPosterSizePopup();
    });

    this.querySelector(".poster-size-close")?.addEventListener("click", () => {
      this.closePosterSizePopup();
    });

    const posterSizeOverlay = this.querySelector(".poster-size-overlay");
    posterSizeOverlay?.addEventListener("click", event => {
      if (event.target === posterSizeOverlay) this.closePosterSizePopup();
    });

    const posterSlider = this.querySelector(".poster-size-popup-slider");
    if (posterSlider) {
      posterSlider.addEventListener("input", event => {
        this.setPosterSize(Number(event.target.value), false);
      });

      posterSlider.addEventListener("change", event => {
        this.setPosterSize(Number(event.target.value), true);
      });
    }

    this.querySelector(".text-size-open")?.addEventListener("click", () => this.openTextSizePopup());
    this.querySelector(".text-size-close")?.addEventListener("click", () => this.closeTextSizePopup());

    const textSizeOverlay = this.querySelector(".text-size-overlay");
    textSizeOverlay?.addEventListener("click", event => {
      if (event.target === textSizeOverlay) this.closeTextSizePopup();
    });

    const textSizeSlider = this.querySelector(".text-size-popup-slider");
    if (textSizeSlider) {
      textSizeSlider.addEventListener("input", event => {
        this.setTextScale(Number(event.target.value), false);
      });
      textSizeSlider.addEventListener("change", event => {
        this.setTextScale(Number(event.target.value), true);
      });
    }

    this.querySelector(".padding-size-open")?.addEventListener("click", () => this.openPaddingPopup());
    this.querySelector(".padding-close")?.addEventListener("click", () => this.closePaddingPopup());

    const paddingOverlay = this.querySelector(".padding-overlay");
    paddingOverlay?.addEventListener("click", event => {
      if (event.target === paddingOverlay) this.closePaddingPopup();
    });

    const paddingSlider = this.querySelector(".padding-popup-slider");
    if (paddingSlider) {
      paddingSlider.addEventListener("input", event => {
        this.setCardSpacing(Number(event.target.value), false);
      });
      paddingSlider.addEventListener("change", event => {
        this.setCardSpacing(Number(event.target.value), true);
      });
    }

    const sortSelect = this.querySelector(".media-sort-select");
    if (sortSelect) {
      sortSelect.addEventListener("change", event => this.setSortMode(event.target.value, true));
    }

    this.querySelectorAll(".media-row-toggle").forEach(toggle => {
      toggle.addEventListener("change", event => {
        this.setMediaRowVisibility(
          event.target.dataset.rowToggle,
          event.target.checked,
          true
        );
      });
    });

    this.bindMediaRowDrag();

    const resetOptions = this.querySelector(".reset-display-options");
    if (resetOptions) {
      resetOptions.addEventListener("click", () => {
        const context = this.getOptionsContext();

        if (context === "home" || context === "media-home" || context.startsWith("media-library-")) {
          this.setPosterSize(118, true);
          this.setTextScale(100, true);
          this.setCardSpacing(14, true);

          const slider = this.querySelector(".poster-size-popup-slider");
          if (slider) slider.value = "118";
          const textSlider = this.querySelector(".text-size-popup-slider");
          if (textSlider) textSlider.value = "100";
          const paddingSlider = this.querySelector(".padding-popup-slider");
          if (paddingSlider) paddingSlider.value = "14";

          try {
            ["home", "media-home", "media-library-home", "media-library-movies", "media-library-shows"].forEach(displayContext => {
              localStorage.removeItem(`apollo-media.poster-size.${displayContext}`);
              localStorage.removeItem(`apollo-media.text-scale.${displayContext}`);
            });
            localStorage.removeItem(`apollo-media.sort.${context}`);
          } catch (_) {}
          this.sortModes[context] = "default";
        }

        if (context === "media-home") {
          this.mediaRows.forEach(row => {
            this.mediaRowVisibility[row.id] = true;

            const section = this.querySelector(`.media-home-row[data-row-id="${row.id}"]`);
            if (section) section.classList.remove("row-hidden");

            const toggle = this.querySelector(`.media-row-toggle[data-row-toggle="${row.id}"]`);
            if (toggle) toggle.checked = true;
          });

          const defaultOrder = APOLLO_DEFAULT_MEDIA_ROWS.map(row => row.id);
          this.setMediaRowOrder(defaultOrder, false);

          const optionsContainer = this.querySelector(".media-row-options");
          if (optionsContainer) {
            defaultOrder.forEach(id => {
              const option = optionsContainer.querySelector(`[data-row-option="${id}"]`);
              if (option) optionsContainer.appendChild(option);
            });
          }

          try {
            localStorage.removeItem("apollo-media.media-row-visibility");
            localStorage.removeItem("apollo-media.media-row-order");
          } catch (_) {}
        }
      });
    }

    const remoteBtn = this.querySelector(".nav-item.remote-action");
    if (remoteBtn) {
      remoteBtn.addEventListener("click", () => this.openRemote());
    }

    const inlineRemote = this.querySelector(".remote-inline");
    if (inlineRemote) {
      inlineRemote.addEventListener("click", () => this.openRemote());
    }

    const closeRemote = this.querySelector(".remote-close");
    if (closeRemote) {
      closeRemote.addEventListener("click", () => this.closeRemote());
    }

    const overlay = this.querySelector(".remote-overlay");
    if (overlay) {
      overlay.addEventListener("click", event => {
        if (event.target === overlay) this.closeRemote();
      });
    }

    this.querySelectorAll(".segment").forEach(btn => {
      btn.addEventListener("click", () => {
        const group = btn.closest(".segmented-control");
        if (!group) return;

        group.querySelectorAll(".segment").forEach(el => el.classList.remove("active"));
        btn.classList.add("active");

        const value = btn.dataset.value;
        this.currentTvSection = value;

        this.querySelectorAll('.segment-panel[data-group="tv"]').forEach(panel => {
          panel.classList.toggle("active", panel.dataset.value === value);
        });
      });
    });

    this.querySelectorAll(".media-section-tab").forEach(btn => {
      btn.addEventListener("click", () => this.showMediaSection(btn.dataset.mediaSection));
    });

    this.querySelectorAll(".library-tab").forEach(btn => {
      btn.addEventListener("click", () => this.showLibraryTab(btn.dataset.libraryTab));
    });
  }

  showScreen(screen) {
    this.currentScreen = screen;

    this.querySelectorAll(".screen").forEach(el => {
      el.classList.toggle("active", el.dataset.screen === screen);
    });

    this.querySelectorAll(".nav-item[data-screen]").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.screen === screen);
    });

    const content = this.querySelector(".content");
    if (content) content.scrollTop = 0;
    this.applyTextScaleContext();
  }

  showMediaSection(section) {
    this.currentMediaSection = section;

    this.querySelectorAll(".media-section-tab").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.mediaSection === section);
    });

    this.querySelectorAll(".media-main-panel").forEach(panel => {
      panel.classList.toggle("active", panel.dataset.mediaPanel === section);
    });

    const content = this.querySelector(".content");
    if (content) content.scrollTop = 0;
    this.applyTextScaleContext();
  }

  showLibraryTab(tab) {
    this.currentLibraryTab = tab;

    this.querySelectorAll(".library-tab").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.libraryTab === tab);
    });

    this.querySelectorAll(".library-panel").forEach(panel => {
      panel.classList.toggle("active", panel.dataset.libraryPanel === tab);
    });

    // Re-read the authoritative HA sensor when entering a full library tab.
    // This repairs a missed in-memory feed transition without a card redraw.
    if (tab === "movies" || tab === "shows") {
      this.renderFullLibraryTab(tab, false);
    }

    if (tab === "movies" && !(this.library?.movies || []).length && !this._libraryMoviesRefreshInFlight) {
      const playerEntity = this.configuredPlayerEntity();
      if (playerEntity) {
        this._libraryMoviesRefreshInFlight = true;
        Promise.resolve(this.callApolloScript(this.config.library_movies_refresh_script, { player_entity: playerEntity }))
          .catch(error => console.debug("Apollo Library Movies refresh failed", error))
          .finally(() => { this._libraryMoviesRefreshInFlight = false; });
      }
    }

    this.applyTextScaleContext();
  }

  bindMediaRowDrag() {
    const container = this.querySelector(".media-row-options");
    if (!container) return;

    container.querySelectorAll(".row-drag-handle").forEach(handle => {
      handle.addEventListener("pointerdown", event => {
        if (event.button !== undefined && event.button !== 0) return;

        const item = handle.closest(".row-toggle-item");
        if (!item) return;

        event.preventDefault();

        const pointerId = event.pointerId;
        item.classList.add("dragging");
        handle.classList.add("dragging-handle");

        const move = moveEvent => {
          if (moveEvent.pointerId !== pointerId) return;
          moveEvent.preventDefault();

          const siblings = [
            ...container.querySelectorAll(".row-toggle-item:not(.dragging)")
          ];

          const beforeItem = siblings.find(sibling => {
            const rect = sibling.getBoundingClientRect();
            return moveEvent.clientY < rect.top + rect.height / 2;
          });

          if (beforeItem) {
            container.insertBefore(item, beforeItem);
          } else {
            container.appendChild(item);
          }

          const sheet = this.querySelector(".options-sheet");
          if (sheet) {
            const sheetRect = sheet.getBoundingClientRect();
            const edge = 48;

            if (moveEvent.clientY < sheetRect.top + edge) {
              sheet.scrollTop -= 8;
            } else if (moveEvent.clientY > sheetRect.bottom - edge) {
              sheet.scrollTop += 8;
            }
          }
        };

        const finish = finishEvent => {
          if (finishEvent.pointerId !== pointerId) return;

          item.classList.remove("dragging");
          handle.classList.remove("dragging-handle");

          window.removeEventListener("pointermove", move);
          window.removeEventListener("pointerup", finish);
          window.removeEventListener("pointercancel", finish);

          const order = [...container.querySelectorAll(".row-toggle-item")]
            .map(el => el.dataset.rowOption)
            .filter(Boolean);

          this.setMediaRowOrder(order, true);
        };

        window.addEventListener("pointermove", move, { passive: false });
        window.addEventListener("pointerup", finish);
        window.addEventListener("pointercancel", finish);
      });
    });
  }

  setMediaRowOrder(order, persist = true) {
    if (!Array.isArray(order) || !order.length) return;

    const orderMap = new Map(order.map((id, index) => [id, index]));

    this.mediaRows.sort((a, b) => {
      const aIndex = orderMap.has(a.id) ? orderMap.get(a.id) : Number.MAX_SAFE_INTEGER;
      const bIndex = orderMap.has(b.id) ? orderMap.get(b.id) : Number.MAX_SAFE_INTEGER;
      return aIndex - bIndex;
    });

    const homePanel = this.querySelector('.media-main-panel[data-media-panel="home"]');
    if (homePanel) {
      order.forEach(id => {
        const row = homePanel.querySelector(`.media-home-row[data-row-id="${id}"]`);
        if (row) homePanel.appendChild(row);
      });
    }

    if (persist) {
      try {
        localStorage.setItem(
          "apollo-media.media-row-order",
          JSON.stringify(this.mediaRows.map(row => row.id))
        );
      } catch (_) {}
    }
  }

  setMediaRowVisibility(rowId, visible, persist = true) {
    if (!rowId) return;

    this.mediaRowVisibility[rowId] = Boolean(visible);

    const section = this.querySelector(`.media-home-row[data-row-id="${rowId}"]`);
    if (section) {
      section.classList.toggle("row-hidden", !visible);
    }

    if (persist) {
      try {
        localStorage.setItem(
          "apollo-media.media-row-visibility",
          JSON.stringify(this.mediaRowVisibility)
        );
      } catch (_) {}
    }
  }

  setPosterSize(size, persist = true) {
    const safeSize = Math.min(150, Math.max(90, Number(size) || 118));
    this.posterSize = safeSize;

    Object.keys(this.posterSizes || {}).forEach(context => {
      this.posterSizes[context] = safeSize;
    });

    const app = this.querySelector(".app");
    if (app) {
      ["home", "media-home", "media-library-home", "media-library-movies", "media-library-shows"].forEach(context => {
        app.style.setProperty(`--apollo-poster-width-${context}`, `${safeSize}px`);
      });
      app.style.setProperty("--apollo-poster-width", `${safeSize}px`);
    }

    this.querySelectorAll(".poster-size-value").forEach(value => {
      value.textContent = `${safeSize}px`;
    });
    const popupSlider = this.querySelector(".poster-size-popup-slider");
    if (popupSlider) popupSlider.value = String(safeSize);

    if (persist) {
      try {
        localStorage.setItem("apollo-media.poster-size", String(safeSize));
      } catch (_) {}
    }
  }

  setTextScale(percent, persist = true) {
    const safePercent = Math.min(130, Math.max(80, Number(percent) || 100));
    this.textScale = safePercent;

    Object.keys(this.textScales || {}).forEach(context => {
      this.textScales[context] = safePercent;
    });

    this.applyTextScaleContext();

    this.querySelectorAll(".text-size-value").forEach(value => {
      value.textContent = `${safePercent}%`;
    });

    const slider = this.querySelector(".text-size-popup-slider");
    if (slider) slider.value = String(safePercent);

    if (persist) {
      try {
        localStorage.setItem("apollo-media.text-scale", String(safePercent));
      } catch (_) {}
    }
  }

  applyTextScaleContext() {
    const percent = Number(this.textScale || 100);
    const app = this.querySelector(".app");
    if (app) app.style.setProperty("--apollo-text-scale", String(percent / 100));
  }

  setCardSpacing(size, persist = true) {
    const safeSize = Math.min(28, Math.max(6, Number(size) || 14));
    this.cardSpacing = safeSize;

    const app = this.querySelector(".app");
    if (app) app.style.setProperty("--apollo-card-gap", `${safeSize}px`);

    this.querySelectorAll(".padding-size-value").forEach(value => {
      value.textContent = `${safeSize}px`;
    });

    const slider = this.querySelector(".padding-popup-slider");
    if (slider) slider.value = String(safeSize);

    if (persist) {
      try {
        localStorage.setItem("apollo-media.card-spacing", String(safeSize));
      } catch (_) {}
    }
  }

  getOptionsContext() {
    if (this.currentScreen === "media") {
      return this.currentMediaSection === "library"
        ? `media-library-${this.currentLibraryTab || "home"}`
        : "media-home";
    }

    if (this.currentScreen === "tv") {
      return "tv";
    }

    return "home";
  }

  updateOptionsContext() {
    const context = this.getOptionsContext();
    const title = this.querySelector(".options-title");
    const kicker = this.querySelector(".options-kicker");
    const posterGroup = this.querySelector(".poster-size-option");
    const textGroup = this.querySelector(".text-size-option");
    const paddingGroup = this.querySelector(".padding-size-option");
    const sortGroup = this.querySelector(".sort-option");
    const mediaLabel = this.querySelector(".media-home-options-label");
    const mediaRows = this.querySelector(".media-row-options");
    const empty = this.querySelector(".options-empty");
    const reset = this.querySelector(".reset-display-options");

    const showPoster = context === "home" ||
                       context === "media-home" ||
                       context.startsWith("media-library-");
    const showSort = context === "media-library-shows" || context === "media-library-movies";
    const showMediaRows = context === "media-home";

    if (posterGroup) posterGroup.classList.toggle("context-hidden", !showPoster);
    if (textGroup) textGroup.classList.toggle("context-hidden", !showPoster);
    if (paddingGroup) paddingGroup.classList.toggle("context-hidden", !showPoster);
    if (sortGroup) sortGroup.classList.toggle("context-hidden", !showSort);
    if (mediaLabel) mediaLabel.classList.toggle("context-hidden", !showMediaRows);
    if (mediaRows) mediaRows.classList.toggle("context-hidden", !showMediaRows);
    if (empty) empty.classList.toggle("context-hidden", context !== "tv");
    if (reset) reset.classList.toggle("context-hidden", context === "tv");

    if (kicker) {
      kicker.textContent =
        context === "media-home" || context.startsWith("media-library-")
          ? "MEDIA"
          : context === "tv"
            ? "TV"
            : "HOME";
    }

    if (title) {
      title.textContent =
        context === "media-home"
          ? "Media Home Options"
          : context === "media-library-home"
            ? "Library Home Options"
          : context === "media-library-movies"
            ? "Movie Library Options"
            : context === "media-library-shows"
              ? "Show Library Options"
            : context === "tv"
              ? "TV Options"
              : "Home Options";
    }

    const contextSize = this.posterSize || 118;
    this.querySelectorAll(".poster-size-value").forEach(value => {
      value.textContent = `${contextSize}px`;
    });

    const contextTextScale = this.textScale || 100;
    this.querySelectorAll(".text-size-value").forEach(value => {
      value.textContent = `${contextTextScale}%`;
    });
    this.applyTextScaleContext();

    const spacing = this.cardSpacing || 14;
    this.querySelectorAll(".padding-size-value").forEach(value => {
      value.textContent = `${spacing}px`;
    });

    const sortSelect = this.querySelector(".media-sort-select");
    if (sortSelect) {
      const options = this.sortOptionsForContext(context);
      sortSelect.innerHTML = options.map(([value, label]) => `<option value="${value}">${label}</option>`).join("");
      sortSelect.value = this.sortModes[context] || "default";
    }
  }

  openOptions() {
    this.updateOptionsContext();

    const overlay = this.querySelector(".options-overlay");
    if (overlay) overlay.classList.add("open");
  }

  closeOptions() {
    const overlay = this.querySelector(".options-overlay");
    if (overlay) overlay.classList.remove("open");
  }

  openPosterSizePopup() {
    const context = this.getOptionsContext();
    this._posterSizePopupContext = context;
    this._posterSizePopupOpen = true;
    this.closeOptions();

    const size = this.posterSize || 118;
    const overlay = this.querySelector(".poster-size-overlay");
    const slider = this.querySelector(".poster-size-popup-slider");
    const value = this.querySelector(".poster-size-popup .poster-size-value");
    if (slider) slider.value = String(size);
    if (value) value.textContent = `${size}px`;
    if (overlay) overlay.classList.add("open");
  }

  closePosterSizePopup() {
    this._posterSizePopupOpen = false;
    this._posterSizePopupContext = "";
    const overlay = this.querySelector(".poster-size-overlay");
    if (overlay) overlay.classList.remove("open");
  }

  openTextSizePopup() {
    const context = this.getOptionsContext();
    this._textSizePopupContext = context;
    this._textSizePopupOpen = true;
    this.closeOptions();

    const scale = this.textScale || 100;
    const overlay = this.querySelector(".text-size-overlay");
    const slider = this.querySelector(".text-size-popup-slider");
    const value = this.querySelector(".text-size-popup .text-size-value");
    if (slider) slider.value = String(scale);
    if (value) value.textContent = `${scale}%`;
    if (overlay) overlay.classList.add("open");
  }

  closeTextSizePopup() {
    this._textSizePopupOpen = false;
    this._textSizePopupContext = "";
    const overlay = this.querySelector(".text-size-overlay");
    if (overlay) overlay.classList.remove("open");
  }

  openPaddingPopup() {
    this._paddingPopupOpen = true;
    this.closeOptions();

    const spacing = this.cardSpacing || 14;
    const overlay = this.querySelector(".padding-overlay");
    const slider = this.querySelector(".padding-popup-slider");
    const value = this.querySelector(".padding-popup .padding-size-value");
    if (slider) slider.value = String(spacing);
    if (value) value.textContent = `${spacing}px`;
    if (overlay) overlay.classList.add("open");
  }

  closePaddingPopup() {
    this._paddingPopupOpen = false;
    const overlay = this.querySelector(".padding-overlay");
    if (overlay) overlay.classList.remove("open");
  }

  openRemote() {
    const overlay = this.querySelector(".remote-overlay");
    if (overlay) overlay.classList.add("open");
  }

  closeRemote() {
    const overlay = this.querySelector(".remote-overlay");
    if (overlay) overlay.classList.remove("open");
  }

  render() {
    const kioskMode = (() => {
      try {
        return new URLSearchParams(window.location.search || "").has("kiosk");
      } catch (_) {
        return false;
      }
    })();

    this.innerHTML = `
      <ha-card class="apollo-shell">
        <div class="app" data-kiosk="${kioskMode ? "true" : "false"}">

          <header class="topbar">
            <div class="brand">Apollo</div>

            <div class="topbar-actions">
              <button class="icon-button" type="button" aria-label="Search">
                <ha-icon icon="mdi:magnify"></ha-icon>
              </button>

              <button
                class="icon-button refresh-action ${this.refreshVisualState() === "running" ? "refreshing" : (this.refreshVisualState() === "success" ? "refresh-success" : "")}"
                type="button"
                aria-label="${this.refreshVisualState() === "running" ? "Refreshing media" : (this.refreshVisualState() === "success" ? "Media refresh complete" : "Refresh media home")}"
                aria-busy="${this.refreshVisualState() === "running" ? "true" : "false"}"
                title="${this.refreshVisualState() === "running" ? "Refreshing media…" : (this.refreshVisualState() === "success" ? "Media refresh complete" : "Refresh media home")}"
                ${this.refreshVisualState() === "running" ? "disabled" : ""}
              >
                <ha-icon icon="${this.refreshVisualState() === "success" ? "mdi:check" : "mdi:refresh"}"></ha-icon>
              </button>

              <button class="icon-button options-action" type="button" aria-label="Apollo options">
                <ha-icon icon="mdi:tune-variant"></ha-icon>
              </button>
            </div>
          </header>

          ${this.configuredPlayerEntity() ? "" : `
            <div class="config-warning" role="alert">
              Select a Kodi Player in the Apollo Media card configuration to enable playback and refreshes.
            </div>`}

          <main class="content">

            <!-- HOME -->
            <section class="screen active" data-screen="home">

              <section class="hero">
                <div class="hero-bg"></div>
                <div class="hero-gradient"></div>

                <div class="hero-content">
                  <div class="hero-label">NOW PLAYING</div>
                  <div class="hero-title">21 Jump Street</div>
                  <div class="hero-meta">2012 · 1h 49m</div>

                  <div class="progress">
                    <div class="progress-fill"></div>
                  </div>

                  <div class="hero-actions">
                    <button class="primary-button" type="button">
                      <ha-icon icon="mdi:play"></ha-icon>
                      Resume
                    </button>

                    <button class="round-button remote-inline" type="button">
                      <ha-icon icon="mdi:remote"></ha-icon>
                    </button>
                  </div>
                </div>
              </section>

              <section class="media-section continue-section">
                <div class="section-header">
                  <h2>Continue Watching</h2>
                  <button class="see-all" type="button">See All</button>
                </div>

                <div class="horizontal-row">
                  <button class="poster-item rail-poster-item" type="button">
                    ${this.posterMarkup({title:"21 Jump Street", subtitle:"42 min left", progress:58, poster:"poster-one"}, "continue-poster")}
                    <div class="poster-title">21 Jump Street</div>
                    <div class="poster-sub">42 min left</div>
                  </button>

                  <button class="poster-item rail-poster-item" type="button">
                    ${this.posterMarkup({title:"The Last of Us", subtitle:"S2 · E3", progress:34, poster:"poster-two"}, "continue-poster")}
                    <div class="poster-title">The Last of Us</div>
                    <div class="poster-sub">S2 · E3</div>
                  </button>

                  <button class="poster-item rail-poster-item" type="button">
                    ${this.posterMarkup({title:"Dune", subtitle:"1h 12m left", progress:67, poster:"poster-three"}, "continue-poster")}
                    <div class="poster-title">Dune</div>
                    <div class="poster-sub">1h 12m left</div>
                  </button>
                </div>
              </section>

              <section class="media-section">
                <div class="section-header">
                  <h2>Live Now</h2>
                  <button class="see-all" type="button">TV Guide</button>
                </div>

                <div class="live-row">
                  <button class="live-card" type="button">
                    <div class="channel-logo">FOX</div>
                    <div class="live-info">
                      <div class="live-badge">LIVE</div>
                      <div class="live-title">Local News</div>
                      <div class="live-sub">FOX · 10:00 PM</div>
                    </div>
                  </button>

                  <button class="live-card" type="button">
                    <div class="channel-logo">ESPN</div>
                    <div class="live-info">
                      <div class="live-badge">LIVE</div>
                      <div class="live-title">SportsCenter</div>
                      <div class="live-sub">ESPN</div>
                    </div>
                  </button>
                </div>
              </section>

              <section class="media-section">
                <div class="section-header">
                  <h2>Recently Added</h2>
                  <button class="see-all" type="button">See All</button>
                </div>

                <div class="horizontal-row">
                  <button class="poster-item rail-poster-item" type="button">
                    ${this.posterMarkup({title:"The Batman", subtitle:"2022", poster:"poster-four", watched:true})}
                    <div class="poster-title">The Batman</div>
                    <div class="poster-sub">2022</div>
                  </button>

                  <button class="poster-item rail-poster-item" type="button">
                    ${this.posterMarkup({title:"Sinners", subtitle:"2025", poster:"poster-five"})}
                    <div class="poster-title">Sinners</div>
                    <div class="poster-sub">2025</div>
                  </button>

                  <button class="poster-item rail-poster-item" type="button">
                    ${this.posterMarkup({title:"Severance", subtitle:"2025", poster:"poster-six"})}
                    <div class="poster-title">Severance</div>
                    <div class="poster-sub">2025</div>
                  </button>
                </div>
              </section>

            </section>

            <!-- TV -->
            <section class="screen" data-screen="tv">

              <div class="screen-heading">
                <div>
                  <div class="screen-kicker">WATCH</div>
                  <h1>TV</h1>
                </div>

                <button class="small-action" type="button">
                  <ha-icon icon="mdi:star-outline"></ha-icon>
                </button>
              </div>

              <div class="segmented-control">
                <button class="segment active" data-value="live" type="button">Live</button>
                <button class="segment" data-value="guide" type="button">Guide</button>
                <button class="segment" data-value="sports" type="button">Sports</button>
              </div>

              <div class="segment-panel active" data-group="tv" data-value="live">
                <div class="section-header screen-section-header">
                  <h2>Favorites</h2>
                  <button class="see-all" type="button">Edit</button>
                </div>

                <div class="channel-chip-row">
                  <button class="channel-chip" type="button">FOX</button>
                  <button class="channel-chip" type="button">ESPN</button>
                  <button class="channel-chip" type="button">AMC</button>
                  <button class="channel-chip" type="button">TNT</button>
                </div>

                <div class="section-header screen-section-header">
                  <h2>On Now</h2>
                </div>

                <div class="tv-list">
                  <button class="tv-program" type="button">
                    <div class="channel-logo small">FOX</div>
                    <div class="tv-program-main">
                      <div class="tv-program-top">
                        <span>Local News</span>
                        <span class="live-badge">LIVE</span>
                      </div>
                      <div class="tv-program-sub">FOX · 10:00–10:30 PM</div>
                      <div class="tv-progress"><span style="width:62%"></span></div>
                    </div>
                  </button>

                  <button class="tv-program" type="button">
                    <div class="channel-logo small">ESPN</div>
                    <div class="tv-program-main">
                      <div class="tv-program-top">
                        <span>SportsCenter</span>
                        <span class="live-badge">LIVE</span>
                      </div>
                      <div class="tv-program-sub">ESPN · 10:00–11:00 PM</div>
                      <div class="tv-progress"><span style="width:36%"></span></div>
                    </div>
                  </button>

                  <button class="tv-program" type="button">
                    <div class="channel-logo small">AMC</div>
                    <div class="tv-program-main">
                      <div class="tv-program-top">
                        <span>Movie Night</span>
                      </div>
                      <div class="tv-program-sub">AMC · 9:30–11:45 PM</div>
                      <div class="tv-progress"><span style="width:48%"></span></div>
                    </div>
                  </button>
                </div>
              </div>

              <div class="segment-panel" data-group="tv" data-value="guide">
                <div class="guide-placeholder">
                  <ha-icon icon="mdi:view-list-outline"></ha-icon>
                  <h2>TV Guide</h2>
                  <p>Timeline guide will live here.</p>
                </div>
              </div>

              <div class="segment-panel" data-group="tv" data-value="sports">
                <div class="sports-stack">
                  <div class="section-header screen-section-header">
                    <h2>Live Sports</h2>
                  </div>

                  <button class="sport-card" type="button">
                    <div class="sport-league">NFL</div>
                    <div class="sport-main">
                      <strong>Saints vs Falcons</strong>
                      <span>FOX · Live</span>
                    </div>
                    <ha-icon icon="mdi:chevron-right"></ha-icon>
                  </button>

                  <button class="sport-card" type="button">
                    <div class="sport-league">MLB</div>
                    <div class="sport-main">
                      <strong>Astros vs Rangers</strong>
                      <span>ESPN · 7:10 PM</span>
                    </div>
                    <ha-icon icon="mdi:chevron-right"></ha-icon>
                  </button>
                </div>
              </div>

            </section>

            <!-- MEDIA -->
            <section class="screen" data-screen="media">

              <div class="screen-heading media-heading">
                <div>
                  <div class="screen-kicker">WATCH</div>
                  <h1>Media</h1>
                </div>
              </div>

              <div class="media-section-tabs">
                <button class="media-section-tab active" data-media-section="home" type="button">Home</button>
                <button class="media-section-tab" data-media-section="library" type="button">Library</button>
              </div>

              <div class="media-main-panel active" data-media-panel="home">
                ${this.renderMediaHome()}
              </div>

              <div class="media-main-panel" data-media-panel="library">
                ${this.renderMediaLibrary()}
              </div>

            </section>

          </main>

          <div class="now-playing-affordance" data-now-playing-affordance hidden>
            <span class="now-playing-affordance-art" data-now-playing-affordance-art></span>
            <button class="now-playing-affordance-copy" data-now-playing-open type="button" aria-label="Open Now Playing">
              <strong data-now-playing-affordance-title>Now Playing</strong>
              <small data-now-playing-affordance-context></small>
            </button>
            <button class="now-playing-mini-toggle" data-now-playing-mini-toggle type="button" aria-label="Play or pause"><ha-icon icon="mdi:pause"></ha-icon></button>
            <div class="now-playing-mini-progress" aria-hidden="true">
              <span data-now-playing-mini-progress></span>
            </div>
          </div>

          <!-- BOTTOM NAV -->
          <nav class="bottom-nav">
            <button class="nav-item active" data-screen="home" type="button">
              <ha-icon icon="mdi:home"></ha-icon>
              <span>Home</span>
            </button>

            <button class="nav-item" data-screen="tv" type="button">
              <ha-icon icon="mdi:television"></ha-icon>
              <span>TV</span>
            </button>

            <button class="nav-item" data-screen="media" type="button">
              <ha-icon icon="mdi:movie-open"></ha-icon>
              <span>Media</span>
            </button>

            <button class="nav-item remote-action" type="button">
              <ha-icon icon="mdi:remote"></ha-icon>
              <span>Remote</span>
            </button>
          </nav>

          <!-- OPTIONS POPUP -->
          ${this.renderTitleModal()}

          <div class="now-playing-overlay${this._nowPlayingOpen ? " open" : ""}">
            <section class="now-playing-sheet">
              ${this._nowPlayingOpen && this._nowPlayingPlayer ? this.renderNowPlayingContent(this._nowPlayingPlayer) : ""}
            </section>
          </div>

          <!-- OPTIONS POPUP -->
          <div class="options-overlay">
            <div class="options-sheet">
              <div class="sheet-handle"></div>

              <div class="options-sheet-header">
                <div>
                  <div class="screen-kicker options-kicker">HOME</div>
                  <h2 class="options-title">Home Options</h2>
                </div>

                <button class="options-close" type="button" aria-label="Close options">
                  <ha-icon icon="mdi:close"></ha-icon>
                </button>
              </div>

              <div class="option-group poster-size-option">
                <button class="poster-size-open" type="button">
                  <span>
                    <span class="option-title">Change Poster Size</span>
                    <span class="option-subtitle">Applies across all media views</span>
                  </span>
                  <span class="option-value poster-size-value">${this.posterSize}px</span>
                  <ha-icon icon="mdi:chevron-right"></ha-icon>
                </button>
              </div>

              <div class="option-group text-size-option">
                <button class="text-size-open" type="button">
                  <span>
                    <span class="option-title">Change Text Size</span>
                    <span class="option-subtitle">Applies across the whole card</span>
                  </span>
                  <span class="option-value text-size-value">${this.textScale || 100}%</span>
                  <ha-icon icon="mdi:chevron-right"></ha-icon>
                </button>
              </div>

              <div class="option-group padding-size-option">
                <button class="padding-size-open" type="button">
                  <span>
                    <span class="option-title">Change Padding</span>
                    <span class="option-subtitle">Adjust spacing between poster cards</span>
                  </span>
                  <span class="option-value padding-size-value">${this.cardSpacing || 14}px</span>
                  <ha-icon icon="mdi:chevron-right"></ha-icon>
                </button>
              </div>

              <div class="option-group sort-option">
                <div class="option-row">
                  <div>
                    <div class="option-title">Sort</div>
                    <div class="option-subtitle">Saved separately for this tab</div>
                  </div>
                  <select class="media-sort-select" aria-label="Media sorting">
                    <option value="default">Default</option>
                    <option value="title">Title A–Z</option>
                    <option value="year">Newest year</option>
                    <option value="added">Recently added</option>
                  </select>
                </div>
              </div>

              <div class="options-section-label media-home-options-label">
                MEDIA HOME · DRAG TO REORDER
              </div>

              <div class="option-group media-row-options">
                ${this.renderMediaRowOptions()}
              </div>

              <div class="options-empty context-hidden">
                <ha-icon icon="mdi:tune-variant"></ha-icon>
                <div class="option-title">No TV options yet</div>
                <div class="option-subtitle">
                  TV-specific controls will appear here as we add them.
                </div>
              </div>

              <button class="reset-display-options" type="button">
                Reset display settings
              </button>
            </div>
          </div>

          <!-- POSTER SIZE POPUP -->
          <div class="poster-size-overlay">
            <section class="poster-size-popup">
              <div class="sheet-handle"></div>
              <div class="poster-size-popup-header">
                <div>
                  <div class="screen-kicker">DISPLAY</div>
                  <h2>Poster Size</h2>
                </div>
                <button class="poster-size-close" type="button" aria-label="Close poster size">
                  <ha-icon icon="mdi:close"></ha-icon>
                </button>
              </div>

              <div class="poster-size-popup-value">
                <span>Size</span>
                <strong class="poster-size-value">${this.posterSize}px</strong>
              </div>

              <input
                class="poster-size-popup-slider"
                type="range"
                min="90"
                max="150"
                step="1"
                value="${this.posterSize}"
                aria-label="Poster size"
              />

              <div class="slider-scale">
                <span>Smaller</span>
                <span>Larger</span>
              </div>
            </section>
          </div>

          <!-- TEXT SIZE POPUP -->
          <div class="text-size-overlay">
            <section class="text-size-popup">
              <div class="sheet-handle"></div>
              <div class="text-size-popup-header">
                <div>
                  <div class="screen-kicker">DISPLAY</div>
                  <h2>Text Size</h2>
                </div>
                <button class="text-size-close" type="button" aria-label="Close text size">
                  <ha-icon icon="mdi:close"></ha-icon>
                </button>
              </div>

              <div class="text-size-popup-value">
                <span>Scale</span>
                <strong class="text-size-value">${this.textScale || 100}%</strong>
              </div>

              <input
                class="text-size-popup-slider"
                type="range"
                min="80"
                max="130"
                step="1"
                value="${this.textScale || 100}"
                aria-label="Text size"
              />

              <div class="slider-scale">
                <span>Smaller</span>
                <span>Larger</span>
              </div>
            </section>
          </div>

          <!-- PADDING POPUP -->
          <div class="padding-overlay">
            <section class="padding-popup">
              <div class="sheet-handle"></div>
              <div class="padding-popup-header">
                <div>
                  <div class="screen-kicker">DISPLAY</div>
                  <h2>Card Padding</h2>
                </div>
                <button class="padding-close" type="button" aria-label="Close padding">
                  <ha-icon icon="mdi:close"></ha-icon>
                </button>
              </div>

              <div class="padding-popup-value">
                <span>Spacing</span>
                <strong class="padding-size-value">${this.cardSpacing || 14}px</strong>
              </div>

              <input
                class="padding-popup-slider"
                type="range"
                min="6"
                max="28"
                step="1"
                value="${this.cardSpacing || 14}"
                aria-label="Poster card spacing"
              />

              <div class="slider-scale">
                <span>Tighter</span>
                <span>Wider</span>
              </div>
            </section>
          </div>

          <!-- REMOTE POPUP -->
          <div class="remote-overlay">
            <div class="remote-sheet">
              <div class="sheet-handle"></div>

              <div class="remote-sheet-header">
                <div>
                  <div class="screen-kicker">CONTROL</div>
                  <h2>Remote</h2>
                </div>

                <button class="remote-close" type="button" aria-label="Close remote">
                  <ha-icon icon="mdi:close"></ha-icon>
                </button>
              </div>

              <div class="remote-placeholder">
                <ha-icon icon="mdi:remote"></ha-icon>
                <strong>Universal Remote Card</strong>
                <span>Your existing remote card will be embedded here later.</span>
              </div>
            </div>
          </div>

        </div>
      </ha-card>

      <style>
        :host {
          display: block;
        }

        .apollo-shell {
          background: #08090b;
          color: #fff;
          overflow: hidden;
          border-radius: 0;
        }

        .app {
          --apollo-poster-width-home: ${this.posterSizes.home}px;
          --apollo-poster-width-media-home: ${this.posterSizes["media-home"]}px;
          --apollo-poster-width-media-library-home: ${this.posterSizes["media-library-home"]}px;
          --apollo-poster-width-media-library-movies: ${this.posterSizes["media-library-movies"]}px;
          --apollo-poster-width-media-library-shows: ${this.posterSizes["media-library-shows"]}px;
          --apollo-text-scale: ${(this.textScale || 100) / 100};
          --apollo-card-gap: ${this.cardSpacing || 14}px;
          --apollo-poster-width: var(--apollo-poster-width-home);
          --apollo-view-offset: 56px;
          --apollo-bottom-nav-height: calc(76px + env(safe-area-inset-bottom,0px));
          --apollo-mini-player-height: 72px;
          position: relative;
          height: calc(100dvh - var(--apollo-view-offset));
          min-height: 0;
          max-height: none;
          display: flex;
          flex-direction: column;
          background:
            radial-gradient(circle at 90% 0%, rgba(74,90,120,.18), transparent 35%),
            #08090b;
        }

        .app[data-kiosk="true"] {
          --apollo-view-offset: 0px;
        }

        .topbar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding:
            calc(env(safe-area-inset-top,0px) + 12px)
            18px
            10px;
          flex-shrink: 0;
        }

        .brand {
          font-size: calc(27px * var(--apollo-text-scale, 1));
          line-height: 1;
          font-weight: 700;
          letter-spacing: -.7px;
        }

        .topbar-actions {
          display: flex;
          align-items: center;
          gap: 7px;
        }

        .icon-button,
        .round-button,
        .small-action,
        .remote-close,
        .options-close,
        .tiny-action {
          width: 44px;
          height: 44px;
          border-radius: 50%;
          border: 0;
          background: rgba(255,255,255,.09);
          color: #fff;
          display: grid;
          place-items: center;
          cursor: pointer;
        }

        .refresh-action.refreshing ha-icon {
          animation: apollo-refresh-spin .8s linear infinite;
        }

        .refresh-action.refresh-success {
          color: #4ade80;
        }

        .refresh-action:disabled {
          cursor: default;
          opacity: .82;
        }

        @keyframes apollo-refresh-spin {
          to { transform: rotate(360deg); }
        }

        .now-playing-source {
          display: inline-flex;
          align-items: center;
          width: fit-content;
          margin: 4px 0 8px;
          padding: 6px 9px;
          border-radius: 999px;
          font-size: calc(10px * var(--apollo-text-scale, 1));
          font-weight: 800;
          letter-spacing: .7px;
          background: rgba(255,255,255,.08);
          color: #c8ccd4;
        }

        .now-playing-source.remote {
          background: rgba(65, 126, 255, .16);
          color: #a9c5ff;
        }

        .now-playing-technical {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
          margin: 12px 0 4px;
        }

        .now-playing-technical span {
          min-width: 0;
          display: grid;
          gap: 3px;
          padding: 9px 10px;
          border-radius: 11px;
          background: rgba(255,255,255,.055);
        }

        .now-playing-technical small {
          color: #858b96;
          font-size: calc(9px * var(--apollo-text-scale, 1));
          font-weight: 800;
          letter-spacing: .8px;
        }

        .now-playing-technical strong {
          overflow: hidden;
          text-overflow: ellipsis;
          color: #dfe3e9;
          font-size: calc(11px * var(--apollo-text-scale, 1));
          white-space: nowrap;
        }

        .now-playing-source-actions {
          display: grid;
          grid-template-columns: repeat(auto-fit,minmax(130px,1fr));
          gap: 9px;
          margin-top: 16px;
        }

        .now-playing-source-actions button,
        .stream-flag-list button {
          min-height: 44px;
          border: 0;
          border-radius: 12px;
          background: rgba(255,255,255,.09);
          color: #fff;
          font-weight: 700;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          cursor: pointer;
        }

        .stream-picker-overlay,
        .stream-flag-overlay {
          position: absolute;
          inset: 0 0 var(--apollo-bottom-nav-height) 0;
          z-index: 95;
          display: flex;
          align-items: flex-end;
          background: rgba(0,0,0,.62);
        }

        .stream-picker-sheet,
        .stream-flag-sheet {
          width: 100%;
          max-height: 88%;
          overflow: hidden;
          overscroll-behavior: contain;
          border-radius: 22px 22px 0 0;
          display: flex;
          flex-direction: column;
          background: #111318;
          padding: 10px 14px calc(18px + env(safe-area-inset-bottom,0px));
          box-shadow: 0 -18px 55px rgba(0,0,0,.42);
        }

        .stream-picker-header {
          display: flex;
          align-items: center;
          flex: 0 0 auto;
          position: relative;
          z-index: 4;
          background: #111318;
          justify-content: space-between;
          gap: 16px;
          padding: 6px 2px 12px;
        }

        .stream-picker-header h2 {
          margin: 2px 0 0;
          font-size: calc(24px * var(--apollo-text-scale, 1));
        }

        .stream-picker-close,
        .stream-flag-close {
          width: 40px;
          height: 40px;
          border: 0;
          border-radius: 50%;
          background: rgba(255,255,255,.09);
          color: #fff;
          display: grid;
          place-items: center;
        }

        .stream-picker-list,
        .stream-flag-list {
          display: grid;
          gap: 8px;
          min-height: 0;
          overflow-y: auto;
          overscroll-behavior: contain;
          padding-bottom: 2px;
        }

        .stream-quality-group {
          display: grid;
          gap: 8px;
        }

        .stream-quality-separator {
          position: sticky;
          top: 0;
          z-index: 2;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 10px 4px 5px;
          background: #111318;
          color: #c8ccd4;
          font-size: calc(11px * var(--apollo-text-scale, 1));
          font-weight: 800;
          letter-spacing: .75px;
          text-transform: uppercase;
        }

        .stream-quality-separator small {
          color: #737985;
          font-size: calc(10px * var(--apollo-text-scale, 1));
          font-weight: 700;
        }

        .stream-picker-row {
          width: 100%;
          border: 1px solid transparent;
          border-radius: 14px;
          background: rgba(255,255,255,.06);
          color: #fff;
          display: flex;
          align-items: center;
          gap: 12px;
          text-align: left;
          padding: 12px;
        }

        .stream-picker-row.current {
          border-color: rgba(92,145,255,.62);
          background: rgba(64,116,223,.14);
        }

        .stream-picker-row.flagged {
          opacity: .58;
        }

        .stream-picker-main {
          min-width: 0;
          flex: 1;
          display: grid;
          gap: 3px;
        }

        .stream-picker-main strong,
        .stream-picker-main small,
        .stream-picker-main em {
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .stream-picker-main small {
          color: #9da3ae;
          font-size: calc(11px * var(--apollo-text-scale, 1));
        }

        .stream-picker-main em {
          color: #777e8a;
          font-size: calc(11px * var(--apollo-text-scale, 1));
          font-style: normal;
          white-space: nowrap;
        }

        .stream-picker-empty {
          min-height: 100px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          color: #999faa;
        }

        .tiny-action {
          width: 38px;
          height: 38px;
        }

        .content {
          flex: 1;
          overflow-y: auto;
          overflow-x: hidden;
          scrollbar-width: none;
          padding-bottom: 20px;
        }

        .app.has-mini-player .content {
          padding-bottom: 20px;
        }

        .config-warning {
          margin: 0 16px 12px;
          padding: 10px 12px;
          border: 1px solid rgba(255, 184, 77, .45);
          border-radius: 10px;
          color: #ffd28a;
          background: rgba(113, 69, 0, .22);
          font-size: calc(12px * var(--apollo-text-scale, 1));
          line-height: 1.4;
        }

        .content::-webkit-scrollbar,
        .horizontal-row::-webkit-scrollbar,
        .live-row::-webkit-scrollbar,
        .channel-chip-row::-webkit-scrollbar,
        .library-filter-row::-webkit-scrollbar {
          display: none;
        }

        .screen {
          display: none;
          animation: screenIn .18s ease;
        }

        .screen.active {
          display: block;
        }

        @keyframes screenIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .screen-heading {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 20px 14px;
        }

        .screen-heading h1,
        .remote-sheet-header h2 {
          margin: 2px 0 0;
          font-size: calc(28px * var(--apollo-text-scale, 1));
          letter-spacing: -.7px;
        }

        .screen-kicker {
          font-size: calc(10px * var(--apollo-text-scale, 1));
          letter-spacing: 1.5px;
          font-weight: 750;
          color: #8f949e;
        }

        .hero {
          position: relative;
          margin: 4px 16px 22px;
          height: 245px;
          overflow: hidden;
          border-radius: 22px;
          background: #181a1f;
        }

        .hero-bg {
          position: absolute;
          inset: 0;
          background:
            radial-gradient(circle at 70% 25%, #665b47 0, #29303b 32%, #171b21 67%, #101216 100%);
        }

        .hero-gradient {
          position: absolute;
          inset: 0;
          background:
            linear-gradient(to top, rgba(8,9,11,.97) 4%, rgba(8,9,11,.45) 55%, rgba(8,9,11,.05) 100%);
        }

        .hero-content {
          position: absolute;
          left: 18px;
          right: 18px;
          bottom: 18px;
        }

        .hero-label {
          font-size: calc(10px * var(--apollo-text-scale, 1));
          letter-spacing: 1.5px;
          font-weight: 700;
          color: #aeb2bb;
          margin-bottom: 6px;
        }

        .hero-title {
          font-size: calc(27px * var(--apollo-text-scale, 1));
          font-weight: 750;
          line-height: 1.05;
          letter-spacing: -.5px;
        }

        .hero-meta {
          margin-top: 6px;
          color: #bbbfc7;
          font-size: calc(13px * var(--apollo-text-scale, 1));
        }

        .progress {
          margin-top: 14px;
          height: 3px;
          border-radius: 10px;
          overflow: hidden;
          background: rgba(255,255,255,.2);
        }

        .progress-fill {
          height: 100%;
          width: 58%;
          background: white;
        }

        .hero-actions {
          margin-top: 14px;
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .primary-button {
          height: 46px;
          padding: 0 19px;
          border: 0;
          border-radius: 24px;
          background: #fff;
          color: #090a0c;
          font-weight: 700;
          font-size: calc(14px * var(--apollo-text-scale, 1));
          display: flex;
          align-items: center;
          gap: 7px;
          cursor: pointer;
        }

        .media-section {
          margin-bottom: 28px;
        }

        .continue-section {
          margin-bottom: 20px;
        }

        .section-header {
          padding: 0 17px 11px;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .screen-section-header {
          padding-top: 14px;
        }

        .section-header h2 {
          margin: 0;
          font-size: calc(19px * var(--apollo-text-scale, 1));
          font-weight: 700;
          letter-spacing: -.3px;
        }

        .see-all {
          border: 0;
          background: transparent;
          color: #9c9fa6;
          min-height: 44px;
          padding: 0 2px 0 12px;
          font-size: calc(12px * var(--apollo-text-scale, 1));
          cursor: pointer;
        }

        .horizontal-row {
          display: flex;
          align-items: flex-start;
          overflow-x: auto;
          gap: var(--apollo-card-gap);
          padding: 0 17px;
          scroll-padding-inline: 17px;
          overflow-anchor: none;
          scrollbar-width: none;
          scroll-snap-type: x proximity;
        }

        .poster-item,
        .poster-grid-item {
          padding: 0;
          border: 0;
          background: transparent;
          color: inherit;
          text-align: left;
          cursor: pointer;
        }

        .poster-grid-item {
          width: var(--apollo-poster-width);
        }

        .poster-item {
          flex: 0 0 var(--apollo-poster-width);
          width: var(--apollo-poster-width);
          align-self: flex-start;
          scroll-snap-align: start;
        }

        .poster {
          position: relative;
          width: var(--apollo-poster-width);
          aspect-ratio: 2 / 3;
          border-radius: 13px;
          background: #292c32;
          box-shadow: 0 8px 22px rgba(0,0,0,.22);
          overflow: hidden;
        }

        .grid-poster {
          width: var(--apollo-poster-width);
        }

        .poster-progress {
          position: absolute;
          left: 0;
          right: 0;
          bottom: 0;
          height: 4px;
          background: rgba(255,255,255,.24);
        }

        .poster-progress-fill {
          height: 100%;
          background: #fff;
        }

        .watched-badge {
          position: absolute;
          top: 7px;
          right: 7px;
          z-index: 2;
          width: 23px;
          height: 23px;
          border-radius: 50%;
          background: rgba(7,8,10,.72);
          border: 1px solid rgba(255,255,255,.16);
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          display: grid;
          place-items: center;
        }

        .watched-badge ha-icon {
          --mdc-icon-size: 15px;
          color: #fff;
        }

        .library-badge {
          position: absolute;
          left: 7px;
          bottom: 8px;
          z-index: 2;
          width: 23px;
          height: 23px;
          border-radius: 7px;
          background: rgba(7,8,10,.76);
          border: 1px solid rgba(255,255,255,.14);
          display: grid;
          place-items: center;
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
        }
        .library-badge ha-icon { --mdc-icon-size: 14px; color: #fff; }

        .poster-one { background: linear-gradient(145deg,#46647f,#b26b42); }
        .poster-two { background: linear-gradient(145deg,#354134,#846344); }
        .poster-three { background: linear-gradient(145deg,#846f52,#23292f); }
        .poster-four { background: linear-gradient(145deg,#202b37,#554452); }
        .poster-five { background: linear-gradient(145deg,#7a332a,#201718); }
        .poster-six { background: linear-gradient(145deg,#244d52,#e3b48a); }
        .poster-seven { background: linear-gradient(145deg,#4f394f,#1d2530); }
        .poster-eight { background: linear-gradient(145deg,#b28b5f,#26313b); }
        .poster-nine { background: linear-gradient(145deg,#6d3e28,#161c20); }
        .poster-ten { background: linear-gradient(145deg,#342b38,#7b5d51); }
        .poster-eleven { background: linear-gradient(145deg,#385273,#9b8060); }
        .poster-twelve { background: linear-gradient(145deg,#313d32,#7a6b3c); }
        .poster-thirteen { background: linear-gradient(145deg,#722b2d,#21181b); }
        .poster-fourteen { background: linear-gradient(145deg,#4f555a,#8d493d); }
        .poster-fifteen { background: linear-gradient(145deg,#263642,#876957); }
        .poster-sixteen { background: linear-gradient(145deg,#5c4638,#20282e); }

        .poster-title {
          margin-top: 8px;
          font-size: calc(13px * var(--apollo-text-scale, 1));
          font-weight: 650;
          line-height: 1.2;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .rail-poster-item .poster-title {
          display: -webkit-box;
          height: 2.4em;
          min-height: 2.4em;
          white-space: normal;
          overflow: hidden;
          text-overflow: ellipsis;
          -webkit-box-orient: vertical;
          -webkit-line-clamp: 2;
        }

        .poster-sub {
          margin-top: 3px;
          font-size: calc(11px * var(--apollo-text-scale, 1));
          color: #858990;
        }

        .poster-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, var(--apollo-poster-width));
          column-gap: var(--apollo-card-gap);
          row-gap: 18px;
          padding: 0 17px 28px;
          justify-content: start;
          align-items: start;
        }

        .live-row {
          display: flex;
          gap: 11px;
          overflow-x: auto;
          padding: 0 17px;
          scrollbar-width: none;
        }

        .live-card {
          flex: 0 0 285px;
          height: 105px;
          border: 0;
          border-radius: 16px;
          background: #15171b;
          color: #fff;
          display: flex;
          align-items: center;
          gap: 14px;
          padding: 13px;
          text-align: left;
          cursor: pointer;
        }

        .channel-logo {
          flex: 0 0 68px;
          width: 68px;
          height: 68px;
          border-radius: 13px;
          background: #25282e;
          display: grid;
          place-items: center;
          font-size: calc(13px * var(--apollo-text-scale, 1));
          font-weight: 800;
        }

        .channel-logo.small {
          flex-basis: 58px;
          width: 58px;
          height: 58px;
          border-radius: 12px;
        }

        .live-info {
          min-width: 0;
        }

        .live-badge {
          display: inline-block;
          font-size: calc(9px * var(--apollo-text-scale, 1));
          font-weight: 800;
          letter-spacing: .7px;
          padding: 3px 6px;
          border-radius: 5px;
          background: #d64040;
          margin-bottom: 6px;
        }

        .live-title {
          font-size: calc(15px * var(--apollo-text-scale, 1));
          font-weight: 700;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .live-sub {
          margin-top: 4px;
          color: #8f9299;
          font-size: calc(11px * var(--apollo-text-scale, 1));
        }

        .segmented-control {
          display: grid;
          grid-template-columns: repeat(3,1fr);
          gap: 4px;
          padding: 4px;
          margin: 0 17px 14px;
          border-radius: 14px;
          background: #14161a;
        }

        .segment {
          min-height: 42px;
          border: 0;
          border-radius: 11px;
          background: transparent;
          color: #8f949c;
          font-weight: 650;
          font-family: inherit;
          cursor: pointer;
        }

        .segment.active {
          background: #26292f;
          color: #fff;
        }

        .segment-panel,
        .media-main-panel,
        .library-panel {
          display: none;
        }

        .segment-panel.active,
        .media-main-panel.active,
        .library-panel.active {
          display: block;
          animation: screenIn .16s ease;
        }

        .channel-chip-row {
          display: flex;
          gap: 10px;
          overflow-x: auto;
          scrollbar-width: none;
          padding: 0 17px 8px;
        }

        .channel-chip {
          flex: 0 0 72px;
          width: 72px;
          height: 58px;
          border: 0;
          border-radius: 14px;
          background: #17191e;
          color: #fff;
          font-weight: 800;
          font-family: inherit;
          cursor: pointer;
        }

        .tv-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
          padding: 0 17px 24px;
        }

        .tv-program {
          width: 100%;
          min-height: 86px;
          border: 0;
          border-radius: 16px;
          background: #15171b;
          color: #fff;
          padding: 13px;
          display: flex;
          gap: 13px;
          align-items: center;
          text-align: left;
          font-family: inherit;
          cursor: pointer;
        }

        .tv-program-main {
          min-width: 0;
          flex: 1;
        }

        .tv-program-top {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          font-size: calc(15px * var(--apollo-text-scale, 1));
          font-weight: 700;
        }

        .tv-program-top .live-badge {
          margin: 0;
          flex: 0 0 auto;
        }

        .tv-program-sub {
          margin-top: 5px;
          color: #8f9299;
          font-size: calc(11px * var(--apollo-text-scale, 1));
        }

        .tv-progress {
          height: 3px;
          background: rgba(255,255,255,.12);
          border-radius: 999px;
          overflow: hidden;
          margin-top: 10px;
        }

        .tv-progress span {
          display: block;
          height: 100%;
          background: rgba(255,255,255,.85);
        }

        .guide-placeholder {
          min-height: 360px;
          margin: 0 17px 24px;
          border-radius: 20px;
          border: 1px solid rgba(255,255,255,.06);
          background: #111318;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          text-align: center;
          color: #8f949d;
          padding: 24px;
        }

        .guide-placeholder ha-icon {
          --mdc-icon-size: 38px;
          margin-bottom: 8px;
        }

        .guide-placeholder h2 {
          color: #fff;
          margin: 6px 0;
        }

        .guide-placeholder p {
          margin: 0;
          font-size: calc(13px * var(--apollo-text-scale, 1));
        }

        .sports-stack {
          padding-bottom: 24px;
        }

        .sport-card {
          width: calc(100% - 34px);
          min-height: 76px;
          margin: 0 17px 10px;
          border: 0;
          border-radius: 16px;
          background: #15171b;
          color: #fff;
          padding: 13px;
          display: flex;
          align-items: center;
          gap: 12px;
          text-align: left;
          font-family: inherit;
          cursor: pointer;
        }

        .sport-league {
          width: 50px;
          height: 50px;
          border-radius: 13px;
          background: #25282e;
          display: grid;
          place-items: center;
          font-size: calc(11px * var(--apollo-text-scale, 1));
          font-weight: 800;
        }

        .sport-main {
          flex: 1;
          display: flex;
          flex-direction: column;
          min-width: 0;
        }

        .sport-main strong {
          font-size: calc(14px * var(--apollo-text-scale, 1));
        }

        .sport-main span {
          margin-top: 4px;
          font-size: calc(11px * var(--apollo-text-scale, 1));
          color: #8f9299;
        }

        .media-heading {
          padding-bottom: 6px;
        }

        .media-section-tabs {
          display: flex;
          gap: 24px;
          padding: 0 20px 16px;
        }

        .media-section-tab {
          position: relative;
          min-height: 44px;
          border: 0;
          background: transparent;
          color: #7f848d;
          font-size: calc(16px * var(--apollo-text-scale, 1));
          font-weight: 700;
          font-family: inherit;
          padding: 0;
          cursor: pointer;
        }

        .media-section-tab.active {
          color: #fff;
        }

        .media-section-tab.active::after {
          content: "";
          position: absolute;
          left: 0;
          right: 0;
          bottom: 2px;
          height: 2px;
          border-radius: 999px;
          background: #fff;
        }

        .media-home-row {
          margin-bottom: 27px;
        }

        .media-home-row.row-hidden {
          display: none;
        }

        .library-toolbar {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 0 17px 10px;
        }

        .library-segmented {
          flex: 1;
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 4px;
          padding: 4px;
          min-height: 46px;
          border-radius: 14px;
          background: #14161a;
        }

        .library-tab {
          min-height: 38px;
          border: 0;
          border-radius: 10px;
          background: transparent;
          color: #858a93;
          font-size: calc(14px * var(--apollo-text-scale, 1));
          font-weight: 700;
          font-family: inherit;
          cursor: pointer;
          transition:
            background .16s ease,
            color .16s ease;
        }

        .library-tab.active {
          background: #272a30;
          color: #fff;
          box-shadow: inset 0 0 0 1px rgba(255,255,255,.035);
        }

        .library-actions {
          flex: 0 0 auto;
          display: flex;
          gap: 7px;
        }

        .library-filter-row {
          display: flex;
          gap: 8px;
          overflow-x: auto;
          scrollbar-width: none;
          padding: 4px 17px 16px;
        }

        .filter-chip {
          flex: 0 0 auto;
          height: 34px;
          padding: 0 13px;
          border: 1px solid rgba(255,255,255,.08);
          border-radius: 999px;
          background: #13151a;
          color: #8f949c;
          font-size: calc(11px * var(--apollo-text-scale, 1));
          font-weight: 650;
          font-family: inherit;
          cursor: pointer;
        }

        .filter-chip.active {
          background: #fff;
          color: #090a0c;
          border-color: #fff;
        }

        .bottom-nav {
          height: var(--apollo-bottom-nav-height);
          box-sizing: border-box;
          padding:
            4px
            8px
            calc(env(safe-area-inset-bottom,0px) + 6px);
          background: rgba(9,10,12,.94);
          border-top: 1px solid rgba(255,255,255,.045);
          display: grid;
          grid-template-columns: repeat(4,1fr);
          gap: 4px;
          flex-shrink: 0;
          position: relative;
          z-index: 90;
          backdrop-filter: blur(20px) saturate(130%);
          -webkit-backdrop-filter: blur(20px) saturate(130%);
        }

        .nav-item {
          position: relative;
          min-height: 54px;
          border: 0;
          background: transparent;
          color: #7f848d;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          gap: 4px;
          font-size: calc(10px * var(--apollo-text-scale, 1));
          font-family: inherit;
          cursor: pointer;
        }

        .nav-item ha-icon {
          --mdc-icon-size: 23px;
        }

        .nav-item span {
          line-height: 1;
        }

        .nav-item.active {
          color: #fff;
          font-weight: 650;
        }

        .nav-item.active::after {
          content: "";
          position: absolute;
          bottom: 1px;
          width: 20px;
          height: 2px;
          border-radius: 999px;
          background: rgba(255,255,255,.92);
        }

        .now-playing-affordance {
          position: relative;
          z-index: 65;
          width: 100%;
          height: var(--apollo-mini-player-height);
          min-height: var(--apollo-mini-player-height);
          box-sizing: border-box;
          padding: 7px 12px;
          border: 0;
          border-top: 1px solid rgba(255,255,255,.08);
          border-radius: 0;
          background: rgba(25,27,32,.98);
          box-shadow: none;
          color: #fff;
          display: grid;
          grid-template-columns: 44px minmax(0, 1fr) 42px;
          align-items: center;
          gap: 10px;
          flex: 0 0 var(--apollo-mini-player-height);
          backdrop-filter: blur(20px) saturate(130%);
          -webkit-backdrop-filter: blur(20px) saturate(130%);
        }
        .now-playing-affordance[hidden] { display: none; }
        .now-playing-affordance-art {
          width: 44px;
          height: 44px;
          border-radius: 9px;
          background: #30343a center / cover no-repeat;
        }
        .now-playing-affordance-copy {
          min-width: 0;
          padding: 0;
          border: 0;
          background: transparent;
          color: inherit;
          font: inherit;
          text-align: left;
        }
        .now-playing-affordance-copy strong,
        .now-playing-affordance-copy small {
          display: block;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .now-playing-affordance-copy strong { font-size: calc(13px * var(--apollo-text-scale, 1)); }
        .now-playing-affordance-copy small { margin-top: 3px; color: #92969e; font-size: calc(11px * var(--apollo-text-scale, 1)); }
        .now-playing-mini-toggle {
          width: 38px;
          height: 38px;
          padding: 0;
          border: 0;
          border-radius: 50%;
          background: #fff;
          color: #090a0c;
          display: grid;
          place-items: center;
        }

        .now-playing-mini-progress {
          position: absolute;
          left: 0;
          right: 0;
          bottom: 0;
          height: 3px;
          overflow: hidden;
          background: rgba(255,255,255,.14);
        }

        .now-playing-mini-progress span {
          display: block;
          width: 0;
          height: 100%;
          background: #fff;
          transition: width .3s linear;
        }

        .now-playing-overlay {
          position: absolute;
          inset: 0 0 var(--apollo-bottom-nav-height);
          z-index: 70;
          display: block;
          background: rgba(0,0,0,.72);
          backdrop-filter: blur(8px);
          opacity: 0;
          visibility: hidden;
          pointer-events: none;
        }
        .now-playing-overlay.open { opacity: 1; visibility: visible; pointer-events: auto; }
        .now-playing-sheet {
          width: 100%;
          height: 100%;
          display: flex;
          flex-direction: column;
          overflow-y: auto;
          border-radius: 0;
          background: #0c0d10;
          box-shadow: none;
        }
        .now-playing-hero {
          position: relative;
          height: clamp(190px, 36vh, 340px);
          flex: 0 0 auto;
          background: #1c1f24 center / cover no-repeat;
        }
        .now-playing-header {
          position: relative;
          height: 14px;
        }
        .now-playing-close {
          position: absolute;
          top: 14px;
          right: 14px;
          width: 42px;
          height: 42px;
          border: 0;
          border-radius: 50%;
          background: rgba(8,9,11,.78);
          color: #fff;
        }
        [data-now-playing-content] { min-height: 100%; display: flex; flex-direction: column; }
        .now-playing-content { flex: 1; display: flex; flex-direction: column; padding: 18px 20px calc(env(safe-area-inset-bottom,0px) + 28px); }
        .now-playing-content h2 { margin: 4px 0 5px; font-size: calc(27px * var(--apollo-text-scale, 1)); }
        .now-playing-series, .now-playing-series-link { color: #e7e9ed; font-size: calc(15px * var(--apollo-text-scale, 1)); font-weight: 700; }
        .now-playing-series-link, .now-playing-season-link {
          width: fit-content;
          padding: 0;
          border: 0;
          background: transparent;
          color: inherit;
          font: inherit;
          font-weight: 700;
          text-align: left;
          text-decoration: none;
          cursor: pointer;
        }
        .now-playing-series-link:hover,
        .now-playing-season-link:hover,
        .now-playing-series-link:focus-visible,
        .now-playing-season-link:focus-visible {
          color: #fff;
        }
        .now-playing-context { color: #a7abb2; font-size: calc(13px * var(--apollo-text-scale, 1)); }
        .now-playing-times { display: flex; justify-content: space-between; margin-top: 22px; font-size: calc(12px * var(--apollo-text-scale, 1)); font-variant-numeric: tabular-nums; }
        .now-playing-seek, .now-playing-volume input { width: 100%; accent-color: #fff; }
        .now-playing-remaining { margin-top: 5px; color: #8f949c; font-size: calc(11px * var(--apollo-text-scale, 1)); text-align: right; font-variant-numeric: tabular-nums; }
        .now-playing-controls { display: flex; align-items: center; justify-content: center; gap: 13px; margin: auto 0 18px; }
        .now-playing-controls button,
        .now-playing-volume button {
          width: 48px;
          height: 48px;
          border: 0;
          border-radius: 50%;
          background: #25282e;
          color: #fff;
          display: grid;
          place-items: center;
        }
        .now-playing-controls button span { font-size: calc(9px * var(--apollo-text-scale, 1)); }
        .now-playing-controls .now-playing-primary { width: 62px; height: 62px; background: #fff; color: #090a0c; }
        .now-playing-volume { display: flex; align-items: center; gap: 12px; margin-top: 12px; }
        .now-playing-volume button { flex: 0 0 44px; width: 44px; height: 44px; }
        .now-playing-try-next {
          width: 100%;
          min-height: 46px;
          margin-top: 12px;
          border: 0;
          border-radius: 12px;
          background: #25282e;
          color: #fff;
          font: 700 13px inherit;
        }

        .title-overlay {
          position: absolute;
          inset: 0 0 var(--apollo-bottom-nav-height);
          z-index: 60;
          display: flex;
          align-items: stretch;
          background: #08090b;
          backdrop-filter: none;
        }

        .app.has-mini-player .title-overlay {
          bottom: calc(var(--apollo-bottom-nav-height) + var(--apollo-mini-player-height));
        }

        .title-sheet {
          width: 100%;
          height: 100%;
          max-height: 100%;
          overflow-y: auto;
          border-radius: 0;
          background: #08090b;
          box-shadow: none;
        }

        .title-overlay.browse-detail {
          align-items: stretch;
          background: #08090b;
          backdrop-filter: none;
        }

        .title-sheet.browse-detail-sheet {
          height: 100%;
          max-height: 100%;
          border-radius: 0;
          box-shadow: none;
        }

        .title-hero {
          position: relative;
          height: clamp(190px, 32vh, 310px);
          background-size: cover;
          background-position: center;
          background-repeat: no-repeat;
          background-color: #15171b;
        }

        .title-hero.poster-fallback {
          background-size: cover;
          background-position: center 28%;
        }

        .title-close, .title-back {
          position: absolute;
          top: 14px;
          width: 40px;
          height: 40px;
          border: 0;
          border-radius: 50%;
          background: rgba(8,9,11,.78);
          color: #fff;
        }

        .title-close { right: 14px; }
        .title-back { left: 14px; }
        .title-content { padding: 0 18px 28px; }
        .app.has-mini-player .title-content {
          padding-bottom: 28px;
        }
        .title-content h2 { margin: 0 0 5px; font-size: calc(25px * var(--apollo-text-scale, 1)); }
        .episode-breadcrumb {
          display: block;
          width: fit-content;
          margin: 0 0 2px;
          color: #fff;
          font-size: calc(18px * var(--apollo-text-scale, 1));
          line-height: 1.2;
          font-weight: 800;
          letter-spacing: -.2px;
        }
        .episode-season {
          display: block;
          width: fit-content;
          margin: 0 0 10px;
          color: #8f949c;
          font-size: calc(12px * var(--apollo-text-scale, 1));
          line-height: 1.25;
          font-weight: 650;
        }
        .season-show-link {
          display: block;
          width: fit-content;
          margin: 0 0 4px;
          padding: 0;
          border: 0;
          background: transparent;
          color: #fff;
          font: inherit;
          font-size: calc(28px * var(--apollo-text-scale, 1));
          line-height: 1.12;
          font-weight: 800;
          letter-spacing: -.45px;
          text-align: left;
          cursor: pointer;
        }
        .detail-link { padding: 0; border: 0; background: transparent; color: inherit; font: inherit; font-weight: inherit; text-align: left; cursor: pointer; text-decoration: none; }
        .title-meta { color: #a7abb2; font-size: calc(13px * var(--apollo-text-scale, 1)); }
        .title-runtime { margin-top: 5px; color: #8f949c; font-size: calc(12px * var(--apollo-text-scale, 1)); }
        .title-content p { color: #c5c8cd; font-size: calc(13px * var(--apollo-text-scale, 1)); line-height: 1.55; }
        .title-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 9px; margin: 18px 0; }
        .title-actions.continue-actions { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .title-actions.continue-actions [data-title-tv] { grid-column: 1 / -1; }
        .title-actions [data-title-remove-continue] { grid-column: 1 / -1; }
        .title-progress-block { margin-top: 16px; }
        .title-progress-copy { display: flex; justify-content: space-between; gap: 12px; color: #a7abb2; font-size: calc(11px * var(--apollo-text-scale, 1)); }
        .title-progress-track { height: 5px; margin-top: 8px; overflow: hidden; border-radius: 999px; background: rgba(255,255,255,.13); }
        .title-progress-track span { display: block; height: 100%; border-radius: inherit; background: #fff; }
        .title-primary, .title-secondary {
          min-height: 46px;
          border: 0;
          border-radius: 12px;
          font: 700 13px inherit;
        }
        .title-primary { background: #fff; color: #090a0c; }
        .title-secondary { background: #24272d; color: #fff; }
        .title-primary ha-icon, .title-secondary ha-icon { vertical-align: middle; --mdc-icon-size: 19px; }
        .title-section-label {
          margin-top: 22px;
          color: #8f949e;
          font-size: calc(10px * var(--apollo-text-scale, 1));
          font-weight: 800;
          letter-spacing: 1.4px;
          text-transform: uppercase;
        }
        .title-children { display: grid; gap: 7px; margin-top: 10px; }
        .title-child {
          display: grid;
          grid-template-columns: 54px 1fr 24px;
          align-items: center;
          gap: 11px;
          min-height: 72px;
          padding: 8px;
          border: 0;
          border-radius: 12px;
          background: #15171b;
          color: #fff;
          text-align: left;
        }
        .title-child .poster { width: 54px; height: 72px; border-radius: 7px; }
        .title-child span { min-width: 0; }
        .title-child strong, .title-child small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .title-child small { margin-top: 4px; color: #8f949c; }
        .episode-inline-meta {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-top: 4px;
          min-width: 0;
        }

        .episode-inline-meta small {
          flex: 0 0 auto;
          margin-top: 0;
        }

        .episode-inline-progress {
          flex: 1 1 auto;
          max-width: 96px;
          min-width: 44px;
          height: 4px;
          overflow: hidden;
          border-radius: 999px;
          background: rgba(255,255,255,.14);
        }

        .episode-inline-progress i {
          display: block;
          height: 100%;
          border-radius: inherit;
          background: rgba(255,255,255,.92);
        }

        .title-child em {
          display: -webkit-box;
          margin-top: 5px;
          overflow: hidden;
          color: #aeb2b9;
          font-size: calc(11px * var(--apollo-text-scale, 1));
          font-style: normal;
          line-height: 1.35;
          -webkit-box-orient: vertical;
          -webkit-line-clamp: 2;
        }
        .title-child.episode-row {
          min-height: 88px;
          align-items: start;
        }
        .title-child.episode-row .poster {
          height: 72px;
        }
        .title-loading { padding: 28px; color: #9da1a8; text-align: center; }
        .title-loading ha-icon { --mdc-icon-size: 20px; }

        .options-overlay {
          position: absolute;
          inset: 0 0 var(--apollo-bottom-nav-height);
          z-index: 55;
          background: rgba(0,0,0,.58);
          opacity: 0;
          visibility: hidden;
          pointer-events: none;
          display: flex;
          align-items: flex-end;
          transition: opacity .18s ease, visibility .18s ease;
        }

        .app.has-mini-player .options-overlay,
        .app.has-mini-player .remote-overlay {
          bottom: calc(var(--apollo-bottom-nav-height) + var(--apollo-mini-player-height));
        }

        .options-overlay.open {
          opacity: 1;
          visibility: visible;
          pointer-events: auto;
        }

        .options-sheet {
          width: 100%;
          max-height: 82%;
          overflow-y: auto;
          background: #111318;
          border-radius: 24px 24px 0 0;
          border-top: 1px solid rgba(255,255,255,.08);
          box-shadow: 0 -20px 60px rgba(0,0,0,.38);
          padding:
            8px
            17px
            calc(env(safe-area-inset-bottom,0px) + 22px);
          transform: translateY(100%);
          transition: transform .24s cubic-bezier(.2,.75,.25,1);
        }

        .options-overlay.open .options-sheet {
          transform: translateY(0);
        }

        .options-sheet-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 18px;
        }

        .options-sheet-header h2 {
          margin: 2px 0 0;
          font-size: calc(25px * var(--apollo-text-scale, 1));
          letter-spacing: -.5px;
        }

        .option-group {
          padding: 16px;
          border-radius: 18px;
          background: #17191e;
        }

        .option-row {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 18px;
        }

        .option-title {
          font-size: calc(15px * var(--apollo-text-scale, 1));
          font-weight: 700;
        }

        .option-subtitle {
          margin-top: 4px;
          color: #8f949d;
          font-size: calc(11px * var(--apollo-text-scale, 1));
          line-height: 1.35;
        }

        .option-value {
          flex: 0 0 auto;
          color: #fff;
          font-size: calc(13px * var(--apollo-text-scale, 1));
          font-weight: 700;
          padding-top: 1px;
        }

        .sort-option {
          margin-top: 12px;
        }

        .media-sort-select {
          min-width: 132px;
          height: 38px;
          padding: 0 10px;
          border: 1px solid rgba(255,255,255,.1);
          border-radius: 10px;
          background: #24272d;
          color: #fff;
          font: inherit;
        }

        .poster-size-open,
        .text-size-open,
        .padding-size-open {
          width: 100%;
          min-height: 54px;
          padding: 0;
          border: 0;
          background: transparent;
          color: #fff;
          display: grid;
          grid-template-columns: 1fr auto 24px;
          align-items: center;
          gap: 10px;
          text-align: left;
          cursor: pointer;
        }

        .poster-size-open > span:first-child,
        .text-size-open > span:first-child,
        .padding-size-open > span:first-child {
          min-width: 0;
        }

        .text-size-option,
        .padding-size-option {
          margin-top: 12px;
        }

        .poster-size-overlay,
        .text-size-overlay,
        .padding-overlay {
          position: absolute;
          inset: 0 0 var(--apollo-bottom-nav-height);
          z-index: 72;
          display: flex;
          align-items: flex-end;
          background: rgba(0,0,0,.26);
          opacity: 0;
          visibility: hidden;
          pointer-events: none;
          transition: opacity .16s ease, visibility .16s ease;
        }

        .poster-size-overlay.open,
        .text-size-overlay.open,
        .padding-overlay.open {
          opacity: 1;
          visibility: visible;
          pointer-events: auto;
        }

        .poster-size-popup,
        .text-size-popup,
        .padding-popup {
          width: 100%;
          margin: 0 14px 14px;
          padding: 9px 16px 16px;
          border: 1px solid rgba(255,255,255,.08);
          border-radius: 20px;
          background: rgba(17,19,24,.96);
          box-shadow: 0 18px 50px rgba(0,0,0,.42);
          backdrop-filter: blur(18px);
        }

        .poster-size-popup-header,
        .text-size-popup-header,
        .padding-popup-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 14px;
          margin-bottom: 12px;
        }

        .poster-size-popup-header h2,
        .text-size-popup-header h2,
        .padding-popup-header h2 {
          margin: 2px 0 0;
          font-size: calc(21px * var(--apollo-text-scale, 1));
        }

        .poster-size-close,
        .text-size-close,
        .padding-close {
          width: 38px;
          height: 38px;
          border: 0;
          border-radius: 50%;
          background: rgba(255,255,255,.08);
          color: #fff;
          display: grid;
          place-items: center;
        }

        .poster-size-popup-value,
        .text-size-popup-value,
        .padding-popup-value {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 8px;
          color: #8f949d;
          font-size: calc(11px * var(--apollo-text-scale, 1));
        }

        .poster-size-popup-value strong,
        .text-size-popup-value strong,
        .padding-popup-value strong {
          color: #fff;
          font-size: calc(13px * var(--apollo-text-scale, 1));
        }

        .poster-size-popup-slider,
        .text-size-popup-slider,
        .padding-popup-slider {
          width: 100%;
          margin: 8px 0 6px;
          accent-color: #fff;
          cursor: pointer;
        }

        .slider-scale {
          display: flex;
          justify-content: space-between;
          color: #737881;
          font-size: calc(10px * var(--apollo-text-scale, 1));
        }

        .context-hidden {
          display: none !important;
        }

        .options-empty {
          min-height: 150px;
          border-radius: 18px;
          background: #17191e;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          text-align: center;
          padding: 24px;
        }

        .options-empty ha-icon {
          --mdc-icon-size: 34px;
          margin-bottom: 10px;
          color: #8d929b;
        }

        .options-empty .option-subtitle {
          max-width: 250px;
          margin-top: 6px;
        }

        .options-section-label {
          margin: 20px 4px 9px;
          color: #777c85;
          font-size: calc(10px * var(--apollo-text-scale, 1));
          font-weight: 800;
          letter-spacing: 1.35px;
        }

        .media-row-options {
          padding: 4px 16px;
        }

        .row-toggle-item {
          position: relative;
          min-height: 64px;
          display: flex;
          align-items: center;
          gap: 12px;
          border-bottom: 1px solid rgba(255,255,255,.055);
          transition:
            background .12s ease,
            transform .12s ease,
            opacity .12s ease;
        }

        .row-toggle-item:last-child {
          border-bottom: 0;
        }

        .row-toggle-item.dragging {
          z-index: 5;
          background: rgba(255,255,255,.055);
          border-radius: 12px;
          opacity: .9;
          transform: scale(1.015);
          box-shadow: 0 8px 24px rgba(0,0,0,.24);
        }

        .row-drag-handle {
          flex: 0 0 34px;
          width: 34px;
          height: 44px;
          border: 0;
          border-radius: 10px;
          background: transparent;
          color: #70757e;
          display: grid;
          place-items: center;
          cursor: grab;
          touch-action: none;
          -webkit-user-select: none;
          user-select: none;
        }

        .row-drag-handle:active,
        .row-drag-handle.dragging-handle {
          cursor: grabbing;
          color: #d9dce1;
          background: rgba(255,255,255,.055);
          transform: none;
        }

        .row-drag-handle ha-icon {
          --mdc-icon-size: 23px;
        }

        .row-toggle-copy {
          flex: 1;
          min-width: 0;
        }

        .row-toggle-control {
          position: relative;
          flex: 0 0 46px;
          width: 46px;
          height: 44px;
          display: flex;
          align-items: center;
          cursor: pointer;
        }

        .media-row-toggle {
          position: absolute;
          opacity: 0;
          pointer-events: none;
        }

        .toggle-switch {
          position: relative;
          display: block;
          flex: 0 0 46px;
          width: 46px;
          height: 28px;
          border-radius: 999px;
          background: #343840;
          transition: background .16s ease;
        }

        .toggle-switch::after {
          content: "";
          position: absolute;
          top: 3px;
          left: 3px;
          width: 22px;
          height: 22px;
          border-radius: 50%;
          background: #fff;
          box-shadow: 0 2px 7px rgba(0,0,0,.32);
          transition: transform .16s ease;
        }

        .media-row-toggle:checked + .toggle-switch {
          background: #f2f2f2;
        }

        .media-row-toggle:checked + .toggle-switch::after {
          transform: translateX(18px);
          background: #111318;
        }

        .reset-display-options {
          width: 100%;
          min-height: 46px;
          margin-top: 12px;
          border: 0;
          border-radius: 14px;
          background: rgba(255,255,255,.06);
          color: #b9bdc4;
          font-size: calc(12px * var(--apollo-text-scale, 1));
          font-weight: 650;
          font-family: inherit;
          cursor: pointer;
        }

        .remote-overlay {
          position: absolute;
          inset: 0 0 var(--apollo-bottom-nav-height);
          z-index: 50;
          background: rgba(0,0,0,.62);
          opacity: 0;
          visibility: hidden;
          pointer-events: none;
          display: flex;
          align-items: flex-end;
          transition: opacity .18s ease, visibility .18s ease;
        }

        .remote-overlay.open {
          opacity: 1;
          visibility: visible;
          pointer-events: auto;
        }

        .remote-sheet {
          width: 100%;
          min-height: 470px;
          max-height: 82%;
          overflow-y: auto;
          background: #111318;
          border-radius: 24px 24px 0 0;
          border-top: 1px solid rgba(255,255,255,.08);
          box-shadow: 0 -20px 60px rgba(0,0,0,.38);
          padding:
            8px
            17px
            calc(env(safe-area-inset-bottom,0px) + 22px);
          transform: translateY(100%);
          transition: transform .24s cubic-bezier(.2,.75,.25,1);
        }

        .remote-overlay.open .remote-sheet {
          transform: translateY(0);
        }

        .sheet-handle {
          width: 42px;
          height: 5px;
          border-radius: 999px;
          background: rgba(255,255,255,.2);
          margin: 0 auto 10px;
        }

        .remote-sheet-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 18px;
        }

        .remote-placeholder {
          min-height: 320px;
          border-radius: 20px;
          border: 1px dashed rgba(255,255,255,.12);
          background: #0d0f13;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
          padding: 28px;
          color: #8f949d;
        }

        .remote-placeholder ha-icon {
          --mdc-icon-size: 44px;
          color: #fff;
          margin-bottom: 14px;
        }

        .remote-placeholder strong {
          color: #fff;
          font-size: calc(17px * var(--apollo-text-scale, 1));
        }

        .remote-placeholder span {
          max-width: 260px;
          margin-top: 7px;
          font-size: calc(12px * var(--apollo-text-scale, 1));
          line-height: 1.45;
        }

        /* Each original display tab owns its poster size independently. */
        .screen[data-screen="home"] .poster-item,
        .screen[data-screen="home"] .poster {
          flex-basis: var(--apollo-poster-width-home);
          width: var(--apollo-poster-width-home);
        }

        .media-main-panel[data-media-panel="home"] .poster-item,
        .media-main-panel[data-media-panel="home"] .poster {
          flex-basis: var(--apollo-poster-width-media-home);
          width: var(--apollo-poster-width-media-home);
        }

        .library-panel[data-library-panel="home"] .poster-item,
        .library-panel[data-library-panel="home"] .poster {
          flex-basis: var(--apollo-poster-width-media-library-home);
          width: var(--apollo-poster-width-media-library-home);
        }

        .library-panel[data-library-panel="movies"] .poster-grid {
          grid-template-columns: repeat(auto-fill, var(--apollo-poster-width-media-library-movies));
        }

        .library-panel[data-library-panel="movies"] .poster-grid-item,
        .library-panel[data-library-panel="movies"] .poster {
          width: var(--apollo-poster-width-media-library-movies);
        }

        .library-panel[data-library-panel="shows"] .poster-grid {
          grid-template-columns: repeat(auto-fill, var(--apollo-poster-width-media-library-shows));
        }

        .library-panel[data-library-panel="shows"] .poster-grid-item,
        .library-panel[data-library-panel="shows"] .poster {
          width: var(--apollo-poster-width-media-library-shows);
        }

        button {
          -webkit-tap-highlight-color: transparent;
        }

        button:active {
          transform: scale(.97);
        }

        @supports not (height: 100dvh) {
          .app {
            height: calc(100vh - var(--apollo-view-offset));
          }
        }

        @media (min-width: 600px) {
          .app {
            max-width: 430px;
            margin: auto;
          }
        }
      </style>
    `;
  }
}

class ApolloMediaCardEditor extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (this._picker) this._picker.hass = hass;
    if (this._audioPicker) this._audioPicker.hass = hass;
  }

  setConfig(config) {
    this._config = { ...(config || {}) };
    this.render();
  }

  connectedCallback() {
    this.render();
  }

  render() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const playerEntity = String(this._config?.player_entity || "").trim();
    const audioEntity = String(this._config?.audio_entity || "").trim();
    const hasPlayerEntity = playerEntity.startsWith("media_player.");
    this.shadowRoot.innerHTML = `
      <div class="editor">
        <div class="entity-field"><ha-entity-picker data-player-picker></ha-entity-picker></div>
        <div class="entity-field"><ha-entity-picker data-audio-picker></ha-entity-picker></div>
        ${hasPlayerEntity ? "" : `
          <div class="warning" role="status">
            Select a Kodi media player to enable Apollo playback and refreshes.
          </div>`}
      </div>
      <style>
        .editor { display: grid; gap: 14px; padding: 12px 0; }
        .entity-field, .entity-field ha-entity-picker { display: block; width: 100%; }
        .warning {
          margin-top: 8px;
          color: var(--warning-color, #f0b429);
          font-size: 12px;
          line-height: 1.4;
        }
      </style>
    `;

    const picker = this.shadowRoot.querySelector("[data-player-picker]");
    const audioPicker = this.shadowRoot.querySelector("[data-audio-picker]");
    this._picker = picker;
    this._audioPicker = audioPicker;
    [picker, audioPicker].forEach(entityPicker => {
      entityPicker.hass = this._hass;
      entityPicker.includeDomains = ["media_player"];
      entityPicker.allowCustomEntity = true;
    });
    picker.value = playerEntity;
    picker.label = "Kodi Player";
    audioPicker.value = audioEntity;
    audioPicker.label = "Audio / Volume Entity";
    picker.addEventListener("value-changed", event => {
      const value = String(event.detail?.value ?? event.target?.value ?? "").trim();
      const config = { ...(this._config || {}) };
      if (value) config.player_entity = value;
      else delete config.player_entity;
      this._config = config;
      this.dispatchEvent(new CustomEvent("config-changed", {
        detail: { config: { ...config } },
        bubbles: true,
        composed: true
      }));
      this.render();
    });
    audioPicker.addEventListener("value-changed", event => {
      const value = String(event.detail?.value ?? event.target?.value ?? "").trim();
      const config = { ...(this._config || {}) };
      if (value) config.audio_entity = value;
      else delete config.audio_entity;
      this._config = config;
      this.dispatchEvent(new CustomEvent("config-changed", {
        detail: { config: { ...config } },
        bubbles: true,
        composed: true
      }));
      this.render();
    });
  }
}

if (!customElements.get("apollo-media-card-editor")) {
  customElements.define("apollo-media-card-editor", ApolloMediaCardEditor);
}

if (!customElements.get("apollo-media-card")) {
  customElements.define("apollo-media-card", ApolloMediaCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some(card => card.type === "apollo-media-card")) {
  window.customCards.push({
    type: "apollo-media-card",
    name: "Apollo Media",
    description: "Apollo media center interface"
  });
}
