# Apollo Media 0.9.64 — Persistent Refresh Feedback

## Refresh transaction feedback
- The top-bar Refresh control now reflects the actual Home Assistant refresh-script transaction.
- Idle: normal refresh icon.
- Running: spinning refresh icon, button disabled to prevent overlapping refreshes.
- Complete: green check for approximately 2.8 seconds, then return to idle.

## Persistence
- Refresh status is card-wide, not tied to a particular Apollo page.
- Navigating Home / Library / Movies / Shows / detail views while a refresh runs preserves the spinner.
- Full card rerenders also reconstruct the correct state from Home Assistant.
- If the card is opened/reloaded while `script.apollo_refresh_media_home` is already running, it immediately shows the running state.

## Authority
- Home Assistant's `script.apollo_refresh_media_home` entity state is authoritative.
- The green check is shown only after an observed HA `on -> off` transition, so it means the full refresh script finished rather than merely one feed updating.
- A short local requested state provides immediate click feedback only until HA reports the script as running.
- Failed script starts return to the idle icon and show an HA notification.

## Preserved
- Apollo Media 0.9.63 playback/resume architecture is unchanged.
- No addon feed logic or playback lifecycle was modified.
