from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrationType:
    kind: str
    name: str
    description: str
    discovery: bool = False
    pairing: bool = False
    control: bool = False
    requires_base_url: bool = False
    requires_access_token: bool = False


INTEGRATION_TYPES: dict[str, IntegrationType] = {
    "android_tv": IntegrationType(
        kind="android_tv",
        name="Android TV",
        description="Android TV / Google TV devices using the Remote v2 protocol.",
        discovery=True,
        pairing=True,
        control=True,
    ),
    "jellyfin": IntegrationType(
        kind="jellyfin",
        name="Jellyfin",
        description="Jellyfin local media server integration.",
        requires_base_url=True,
        requires_access_token=True,
    ),
    "radarr": IntegrationType(
        kind="radarr",
        name="Radarr",
        description="Radarr movie library integration.",
        requires_base_url=True,
        requires_access_token=True,
    ),
    "sonarr": IntegrationType(
        kind="sonarr",
        name="Sonarr",
        description="Sonarr TV library integration.",
        requires_base_url=True,
        requires_access_token=True,
    ),
    "tmdb": IntegrationType(
        kind="tmdb",
        name="TMDB",
        description="The Movie Database metadata integration.",
        requires_access_token=True,
    ),
}


def get_integration_type(kind: str) -> IntegrationType | None:
    return INTEGRATION_TYPES.get(kind.strip().lower())
