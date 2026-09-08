# Custom AVA device modal

AVA Bridge 0.9.4 replaces the stock Android create-device AlertDialog with a
fully custom Apollo modal.

The modal uses:
- one consistent dark rounded surface
- white title and body text
- dark high-contrast text fields
- Apollo secondary and primary buttons
- visible ripple / press feedback
- inline validation for missing device ID
- an in-progress `Creating…` state

This avoids Android 11's default light dialog chrome and keeps the create-device
flow visually consistent with the rest of the AVA app.
