# AVA Bridge 0.13.0 — global hardware volume routing

AVA's two physical volume buttons can now control a selected Apollo IR device
globally through the existing Apollo IR Server / Home Assistant / BroadLink path.

The selected device must contain commands named exactly:

- `volume_up`
- `volume_down`

In Apollo Remote:
1. Select the BroadLink learner.
2. Select the TV/soundbar device.
3. Under **Global volume keys**, tap **Use selected device for volume**.
4. Keep the AVA IR Bridge accessibility service enabled.

Once configured, AVA consumes the physical volume key events so Android media
volume does not change in parallel. Holding a button uses Android key-repeat
events to send repeated commands.

This release uses the supported Apollo/HA/BroadLink command path. It does not
yet replay BroadLink-learned raw payloads through AVA's local IR LED because
Home Assistant's supported BroadLink API does not expose those raw payloads.
