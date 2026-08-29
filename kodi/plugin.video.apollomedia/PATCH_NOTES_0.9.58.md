# Apollo Media 0.9.58 — Canonical Details + Truly Headless CW Removal

- Detail type is now driven by canonical media identity, not the browse route used to reach it.
- Show, Season, Episode and Movie detail surfaces share one global routing model; origin only affects Back history.
- Episode → Season and Show → Season now resolve the same exact season route.
- Local episode season targets include Jellyfin SeasonId; missing SeasonId falls back to exact discovery-season filtering instead of an unfiltered local-series episode query.
- Season detail links back to the parent Show and never inherits the originating episode plot/progress.
- Season episode children are defensively filtered to the selected season.
- Library Movies forces DOM reconciliation from the authoritative HA sensor even when the in-memory item model already matches.
- Card Continue Watching removal now calls a dedicated JSON-RPC Files.GetDirectory action with canonical identity fields. It does not use Addons.ExecuteAddon, Container.Refresh, Container.Update or PlayMedia.
- Continue Watching sorting logic is unchanged.
