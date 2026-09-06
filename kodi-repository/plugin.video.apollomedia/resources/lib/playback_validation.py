MIN_FALLBACK_DURATION_SECONDS = 60.0
MIN_EXPECTED_RATIO = 0.50
MAX_EXPECTED_RATIO = 1.75


def duration_valid(actual_duration, expected_duration=0):
    """
    Return:
      None  - Kodi has not exposed a usable duration yet.
      True  - duration is plausible for this media.
      False - duration is clearly invalid for this media.

    When AMS has a canonical runtime, mirror the AMS progress contract.
    When no expected runtime is available, reject only obviously-short
    playback as a conservative fallback.
    """
    actual = max(0.0, float(actual_duration or 0))
    expected = max(0.0, float(expected_duration or 0))

    if actual <= 0:
        return None

    if expected > 0:
        ratio = actual / expected
        return MIN_EXPECTED_RATIO <= ratio <= MAX_EXPECTED_RATIO

    return actual >= MIN_FALLBACK_DURATION_SECONDS
