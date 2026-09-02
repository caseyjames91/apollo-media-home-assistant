
class ApolloYouTubeTestCard extends HTMLElement {
  setConfig(config) {
    this.config = {
      api_base: "http://hass.pve.home:18100",
      device_key: "kodi-web",
      title: "Apollo YouTube",
      ...(config || {})
    };

    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }

    this.load();
  }

  set hass(hass) {
    this._hass = hass;
  }

  async api(path, options = {}) {
    const base = String(this.config.api_base || "").replace(/\/$/, "");
    const response = await fetch(`${base}${path}`, options);

    if (!response.ok) {
      let detail = `${response.status} ${response.statusText}`;
      try {
        const data = await response.json();
        if (data?.detail) detail = data.detail;
      } catch (_) {}
      throw new Error(detail);
    }

    return response.json();
  }

  async load() {
    this.loading = true;
    this.error = null;
    this.render();

    try {
      const [continueData, homeData] = await Promise.all([
        this.api("/youtube/continue-watching"),
        this.api("/youtube/home")
      ]);

      this.continueItems = continueData?.items || [];
      this.homeItems = homeData?.items || [];
    } catch (err) {
      this.error = err?.message || String(err);
    } finally {
      this.loading = false;
      this.render();
    }
  }

  async play(item, resume = false) {
    if (!item?.video_id) return;

    this.playingId = item.video_id;
    this.error = null;
    this.render();

    try {
      const startSeconds =
        resume && Number(item.start_seconds) > 0
          ? Number(item.start_seconds)
          : 0;

      await this.api("/youtube/play", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          device_key: this.config.device_key,
          video_id: item.video_id,
          start_seconds: startSeconds
        })
      });
    } catch (err) {
      this.error = err?.message || String(err);
    } finally {
      this.playingId = null;
      this.render();
    }
  }

  esc(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  thumbnail(item) {
    const thumbs = item?.thumbnails;
    if (!Array.isArray(thumbs) || !thumbs.length) return "";
    return thumbs[thumbs.length - 1]?.url || thumbs[0]?.url || "";
  }

  renderItem(item, isContinue = false) {
    const thumb = this.thumbnail(item);
    const progress = Number(item?.progress_percent);
    const hasProgress = Number.isFinite(progress) && progress > 0;
    const isPlaying = this.playingId === item?.video_id;

    return `
      <article class="video">
        <button class="thumb" data-video="${this.esc(item.video_id)}"
          data-resume="${isContinue ? "1" : "0"}">
          ${thumb
            ? `<img src="${this.esc(thumb)}" alt="">`
            : `<div class="placeholder"></div>`
          }

          ${item?.duration
            ? `<span class="duration">${this.esc(item.duration)}</span>`
            : ""
          }

          ${hasProgress
            ? `<div class="progress"><div style="width:${Math.min(100, Math.max(0, progress))}%"></div></div>`
            : ""
          }

          ${isPlaying ? `<div class="starting">Starting…</div>` : ""}
        </button>

        <div class="meta">
          <div class="video-title">${this.esc(item?.title || "Untitled")}</div>
          <div class="channel">${this.esc(item?.channel || "")}</div>
          ${isContinue && item?.start_seconds
            ? `<button class="resume" data-video="${this.esc(item.video_id)}">Resume</button>`
            : ""
          }
        </div>
      </article>
    `;
  }

  bindEvents() {
    this.shadowRoot.querySelectorAll(".thumb").forEach(el => {
      el.addEventListener("click", () => {
        const videoId = el.dataset.video;
        const resume = el.dataset.resume === "1";
        const all = [...(this.continueItems || []), ...(this.homeItems || [])];
        const item = all.find(x => x.video_id === videoId);
        this.play(item, resume);
      });
    });

    this.shadowRoot.querySelectorAll(".resume").forEach(el => {
      el.addEventListener("click", event => {
        event.stopPropagation();
        const videoId = el.dataset.video;
        const item = (this.continueItems || []).find(x => x.video_id === videoId);
        this.play(item, true);
      });
    });

    const refresh = this.shadowRoot.querySelector(".refresh");
    if (refresh) refresh.addEventListener("click", () => this.load());
  }

  render() {
    if (!this.shadowRoot) return;

    const continueItems = this.continueItems || [];
    const homeItems = this.homeItems || [];

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          font-family: var(--paper-font-body1_-_font-family, sans-serif);
          color: var(--primary-text-color);
        }

        ha-card {
          display: block;
          overflow: hidden;
          padding: 16px 0 20px;
        }

        header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 16px 8px;
        }

        h1 {
          margin: 0;
          font-size: 21px;
          font-weight: 600;
        }

        .target {
          opacity: .62;
          font-size: 12px;
          margin-top: 3px;
        }

        .refresh,
        .resume {
          border: 0;
          border-radius: 9px;
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
          padding: 7px 10px;
          cursor: pointer;
        }

        .error {
          margin: 8px 16px 14px;
          padding: 10px 12px;
          border-radius: 10px;
          background: var(--error-color);
          color: white;
          font-size: 13px;
        }

        .loading {
          padding: 30px 16px;
          opacity: .65;
        }

        section {
          margin-top: 17px;
        }

        h2 {
          font-size: 17px;
          margin: 0 16px 9px;
        }

        .rail {
          display: flex;
          gap: 12px;
          overflow-x: auto;
          padding: 0 16px 8px;
          scrollbar-width: none;
        }

        .rail::-webkit-scrollbar {
          display: none;
        }

        .video {
          flex: 0 0 260px;
          min-width: 0;
        }

        .thumb {
          width: 260px;
          aspect-ratio: 16 / 9;
          padding: 0;
          border: 0;
          border-radius: 12px;
          overflow: hidden;
          position: relative;
          background: #111;
          cursor: pointer;
          display: block;
        }

        .thumb img,
        .placeholder {
          width: 100%;
          height: 100%;
          object-fit: cover;
          display: block;
        }

        .duration {
          position: absolute;
          right: 6px;
          bottom: 6px;
          background: rgba(0,0,0,.78);
          color: white;
          padding: 2px 5px;
          border-radius: 4px;
          font-size: 11px;
        }

        .progress {
          position: absolute;
          left: 0;
          right: 0;
          bottom: 0;
          height: 4px;
          background: rgba(255,255,255,.28);
        }

        .progress > div {
          height: 100%;
          background: var(--primary-color);
        }

        .starting {
          position: absolute;
          inset: 0;
          display: grid;
          place-items: center;
          background: rgba(0,0,0,.5);
          color: white;
          font-weight: 600;
        }

        .meta {
          padding: 8px 2px 0;
        }

        .video-title {
          font-size: 14px;
          font-weight: 600;
          line-height: 1.25;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .channel {
          margin-top: 3px;
          font-size: 12px;
          opacity: .62;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .resume {
          margin-top: 7px;
          font-size: 12px;
        }

        .empty {
          padding: 0 16px;
          opacity: .6;
          font-size: 13px;
        }

        @media (max-width: 600px) {
          .video {
            flex-basis: 220px;
          }

          .thumb {
            width: 220px;
          }
        }
      </style>

      <ha-card>
        <header>
          <div>
            <h1>${this.esc(this.config?.title || "Apollo YouTube")}</h1>
            <div class="target">Playing to ${this.esc(this.config?.device_key || "")}</div>
          </div>
          <button class="refresh">Refresh</button>
        </header>

        ${this.error ? `<div class="error">${this.esc(this.error)}</div>` : ""}

        ${this.loading
          ? `<div class="loading">Loading YouTube…</div>`
          : `
            <section>
              <h2>Continue Watching</h2>
              ${continueItems.length
                ? `<div class="rail">${continueItems.map(x => this.renderItem(x, true)).join("")}</div>`
                : `<div class="empty">Nothing to resume.</div>`
              }
            </section>

            <section>
              <h2>Home</h2>
              ${homeItems.length
                ? `<div class="rail">${homeItems.map(x => this.renderItem(x, false)).join("")}</div>`
                : `<div class="empty">No recommendations returned.</div>`
              }
            </section>
          `
        }
      </ha-card>
    `;

    this.bindEvents();
  }

  getCardSize() {
    return 8;
  }
}

customElements.define("apollo-youtube-test-card", ApolloYouTubeTestCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "apollo-youtube-test-card",
  name: "Apollo YouTube Test Card",
  description: "Standalone Apollo Media Server YouTube test card"
});
