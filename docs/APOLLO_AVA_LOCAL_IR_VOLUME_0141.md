# AVA Bridge 0.14.1 — faster local hardware-volume repeat

Tunes the local AVA IR hardware-volume timing for a more natural remote feel.

Changes:
- initial held-button repeat delay: 280 ms -> 220 ms
- repeat interval while held: 105 ms -> 70 ms

Local IR remains the primary path:
AVA hardware button -> AccessibilityService -> ConsumerIrManager -> TV.
