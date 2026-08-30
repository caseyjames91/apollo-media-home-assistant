# Changelog

## 0.2.7
- Make `POST /path-mappings` idempotent for an existing `device_key` + `source_prefix`; reposting a mapping now updates its name and Kodi prefix instead of failing the database uniqueness constraint with HTTP 500.
- Add `DELETE /path-mappings/{mapping_id}` so obsolete or incorrect mappings can be removed cleanly.
- Preserve the 0.2.6 device-aware playback resolver and Arr availability behavior unchanged.

## 0.2.6
- Add device-aware playback resolution without changing Radarr/Sonarr availability semantics.
- Translate Arr container source paths into Kodi-playable paths only at playback-resolution time using existing path mappings.
- Add `GET /path-mappings/resolve` for direct mapping validation.
- Add `GET /media/{media_id}/playback-resolution?device_key=...` to select a mapped local source when possible and explicitly fall back to remote playback when the local path cannot be resolved.
- Keep mappings direct from the provider-visible container prefix (for example `/movies`) to the target Kodi-visible prefix (for example `smb://server/share/Movies`); no fake NAS host path needs to be stored in Arr data.
- Preserve device-specific mappings with wildcard fallback and longest-prefix matching.

## 0.2.5
- Keep Radarr/Sonarr narrowly scoped to local availability and filesystem source location; they do not enrich Apollo titles, artwork, overviews, or other catalog metadata.
- Remove Sonarr title/year fallback matching. Sonarr series now match Apollo records only by TVDB, TMDB, or IMDb identity.
- Continue resolving Sonarr episodes by season/episode number only after a strict series-ID match.
- Expose Arr reconciliation details on media responses through `local_sources`, including provider, provider item ID, availability, source path, quality, and update time.
- Return Arr filesystem source paths only while the corresponding file is available; clear stale source paths and quality when a provider match disappears.
- Preserve `local_playback_path` as a separate Kodi-routing field rather than treating an Arr filesystem path as directly playable.
