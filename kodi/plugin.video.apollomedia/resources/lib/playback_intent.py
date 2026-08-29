VALID_REMOTE_MODES = {"resume", "start_over"}


def resolve_remote_position(resume_mode, start_position, start_duration, load_saved):
    """Resolve one position authority for a new remote source session."""
    mode = str(resume_mode or "").strip().lower()
    if mode == "start_over":
        return 0.0, float(start_duration or 0), mode
    if mode == "resume":
        position, duration = load_saved()
        return float(position or 0), float(duration or 0), mode
    if start_position is None:
        position, duration = load_saved()
        return float(position or 0), float(duration or 0), "native"
    return (
        float(start_position or 0),
        float(start_duration or 0),
        "native",
    )


def should_seek_remote(same_identity, resume_position, resume_mode):
    if not same_identity:
        return False
    # Start Over is already enforced by StartOffset=0 on the resolved item.
    # Do not create a second zero seek callback that could report/reset saved
    # progress before playback has genuinely advanced.
    return float(resume_position or 0) > 0
