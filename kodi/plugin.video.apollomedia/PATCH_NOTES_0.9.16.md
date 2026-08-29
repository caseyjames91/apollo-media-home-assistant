# Apollo Media 0.9.16

- Local-to-remote playback overrides now inherit the current Jellyfin resume point.
- `Play from Stream` reads Jellyfin progress and starts the best-ranked remote stream there.
- `Choose Remote Stream` carries the same Jellyfin resume point into the selected remote stream.
- Reading the resume point does not clear or modify Jellyfin progress.
- Remote playback can continue to maintain Apollo's own remote-progress state normally.
- Normal local click remains Jellyfin-first.
