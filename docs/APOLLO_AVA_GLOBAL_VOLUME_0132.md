# AVA Bridge 0.13.2 — deterministic held-volume repeat

0.13.2 no longer relies on AVA firmware to deliver Android repeat key events.

For either physical volume button:

- first press sends one command immediately
- after 320 ms, Apollo starts its own repeat loop
- while held, Apollo sends the selected volume command every 170 ms
- release stops the repeat loop immediately

This gives held buttons normal remote-style behavior even when AVA only reports
the initial key-down.

The patch also strengthens Android media-volume suppression after key release.
AVA firmware can apply a late Volume-Up adjustment after AccessibilityService
returns, so Apollo restores the captured media volume at several short
intervals after release.
