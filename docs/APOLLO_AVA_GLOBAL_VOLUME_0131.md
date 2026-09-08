# AVA Bridge 0.13.1 — held-button OS volume suppression

AVA firmware can still alter Android media volume during a long press even when
Apollo consumes the global key event.

0.13.1 captures the AVA's current media volume when a hardware volume button is
first pressed, pins that Android media volume while the button is held, and
restores it once more shortly after release. Apollo continues sending the
configured `volume_up` / `volume_down` commands during the hold.
