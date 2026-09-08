# AVA device picker and readable dropdowns

AVA Bridge 0.9.0 changes device selection to one dropdown containing:

- all devices already registered with Apollo IR Server
- `Create new device`
- `Add existing BroadLink device`

Creating a new device accepts a stable device ID and optional friendly name.
Registering an existing BroadLink device uses its existing device key without
altering any learned commands.

Learner and device dropdowns now use a dark, high-contrast custom adapter so
both the selected value and opened dropdown remain readable on the AVA display.
