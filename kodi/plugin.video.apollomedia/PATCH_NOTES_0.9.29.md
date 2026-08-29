# Apollo Media 0.9.29 — Stream Flag Management

Manual Choose Remote Stream list:
- flagged streams remain visible;
- flagged streams show a `⚠` indicator;
- flagged streams are sorted below unflagged streams;
- normal click still plays the selected source;
- context menu includes `Play`;
- clean sources include `Flag Stream`;
- flagged sources include `Unflag Stream`.

Flag behavior:
- `Wrong language` is now available in both active-stream and manual-stream
  flag dialogs.
- `Flag Current Stream` retains its existing behavior: flag the active source
  and immediately advance to the next source.
- Manual flagging does not start or advance playback.
- Flags are preserved when reopening/refeshing the source list for the same
  movie or episode.
- Automatic playback starts with the first unflagged source.
