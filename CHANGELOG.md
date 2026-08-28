# 0.1.3
- Fix Home Assistant ingress routing for Jellyfin Connect, Test Connection, Disconnect, redirects, and Back links.
- Build ingress-safe URLs from Home Assistant's `X-Ingress-Path` request header.
- Keep direct/non-ingress access working with normal root-relative routes.
- Update repository metadata to the public Apollo Media Home Assistant repository.

# 0.1.2
- Jellyfin connection setup UI.
- Authenticates by username/password and stores returned access token.
- Does not store the Jellyfin password.
- Creates/updates an Apollo profile mapped to the Jellyfin user.
- Adds Jellyfin connection test and disconnect.
- Adds integration persistence to Apollo's SQLite database.

# 0.1.1
- First installable Home Assistant local add-on.
- SQLite-backed Apollo Server foundation.
