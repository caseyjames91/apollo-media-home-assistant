# Apollo IR Server 0.6.0 — one-time BroadLink raw IR import

Adds a read-only Home Assistant config mount and a narrow `GET /api/raw-code`
endpoint so Apollo can copy an already-learned BroadLink IR command into an AVA
remote.

The server scans only Home Assistant `.storage` files whose names contain
`broadlink`, looks for the exact requested device/command pair, and only returns
a value if it decodes as a BroadLink IR packet (`0x26`).

Example:

```bash
curl -sG   --data-urlencode 'device=YOUR_DEVICE'   --data-urlencode 'command=volume_up'   http://homeassistant.local:8100/api/raw-code
```

This is an import bridge, not Apollo's ongoing source of truth.
