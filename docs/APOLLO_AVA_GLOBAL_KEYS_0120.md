# AVA Bridge 0.12.0 — global volume key diagnostic

Adds an Android AccessibilityService that requests
`FLAG_REQUEST_FILTER_KEY_EVENTS` to test whether AVA firmware exposes its
physical volume buttons globally to Apollo.

Observed keys:
- KEYCODE_VOLUME_UP
- KEYCODE_VOLUME_DOWN
- KEYCODE_VOLUME_MUTE

The diagnostic stores the last key locally and logs under `ApolloGlobalKeys`.
It returns `false` from `onKeyEvent`, so it does not consume buttons or transmit
IR yet.

## Test
1. Install 0.12.0.
2. Open Apollo Remote.
3. Under **Global volume keys**, open Accessibility settings.
4. Enable **AVA IR Bridge**.
5. Leave Apollo and open another app.
6. Press Volume Up and Volume Down.
7. Return to Apollo and inspect the last received key.

Optional:
`adb logcat -s ApolloGlobalKeys`
