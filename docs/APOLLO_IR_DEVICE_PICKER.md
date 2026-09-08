# AVA device picker

AVA Bridge 0.9.2 keeps the device dropdown limited to actual Apollo-registered
devices and makes the empty state explicit.

If the Apollo IR registry contains no devices, the app now shows:

`No Apollo devices yet. Create your first device below.`

Commands learned before Apollo IR Server 0.3.0 are not automatically indexed
because the earlier server did not persist Apollo device metadata and Apollo
does not scrape Home Assistant private BroadLink storage.

The separate **Create new device** button remains below the dropdown.

All primary and secondary buttons now use Android ripple feedback plus a subtle
press-scale animation so taps are visually obvious on the AVA display.
