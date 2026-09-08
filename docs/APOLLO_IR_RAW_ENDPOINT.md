# AVA IR Bridge raw transmission API

## Endpoint

`POST /ir/raw`

JSON payload:

```json
{
  "modulation_hz": 38000,
  "timings_us": [9000, 4500, 560, 560]
}
```

`timings_us` is an alternating mark/space duration list in microseconds.
Positive or negative input values are accepted by the bridge and normalized
to the positive-duration array required by Android `ConsumerIrManager`.

Limits:
- modulation: 10 kHz through 100 kHz
- at least two timing values
- at most 10,000 timing values
- total pattern duration must be less than two seconds

The legacy generic BroadLink endpoint remains available during migration:

`POST /ir/broadlink`

This is retained for compatibility and testing, but Home Assistant's native
infrared entity uses `/ir/raw`.
