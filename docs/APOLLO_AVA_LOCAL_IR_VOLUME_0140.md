# AVA Bridge 0.14.0 — local hardware volume IR

This release removes Home Assistant and BroadLink from the normal AVA hardware
volume path.

Setup still uses Apollo IR Server once:

1. Select the BroadLink learner.
2. Select a device containing `volume_up` and `volume_down`.
3. Tap **Import selected device for local volume**.
4. Apollo IR Server returns the BroadLink raw IR payloads.
5. AVA validates and stores both payloads in its own app preferences.

After import:

- physical Volume Up/Down are caught globally by AccessibilityService
- AVA calls its own `ConsumerIrManager` directly
- no Home Assistant call is made for a successful local transmission
- hold repeat is generated locally every ~105 ms after an initial ~280 ms delay
- network/HA remains only as a fallback if local IR transmission fails

This is intentionally generic: any Apollo IR device with `volume_up` and
`volume_down` can be imported onto an AVA.
