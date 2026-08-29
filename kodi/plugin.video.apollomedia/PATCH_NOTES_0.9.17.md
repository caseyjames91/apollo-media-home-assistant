# Apollo Media 0.9.17

- Fixes remote playback overrides for local items not updating Jellyfin progress.
- Remote source sessions now retain the originating Jellyfin item id.
- For a local item played through a remote source, Jellyfin remains the progress authority.
- Pause, seek, periodic progress, stop and completion events are reported back to Jellyfin.
- Apollo does not create a competing remote-progress record for that local item.
- Remote-only media continues to use Apollo's progress database.
