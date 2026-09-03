from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text()
SERVICE = (ROOT / "service.py").read_text()

def test_source_session_snapshots_native_resume_baseline():
    assert "resume_position, resume_duration = ams.resume(ADDON, imdb, season, episode)" in MAIN
    assert "resume_position=resume_position" in MAIN
    assert "resume_duration=resume_duration" in MAIN
    assert 'resume_mode="native"' in MAIN

def test_native_resolution_reuses_session_baseline():
    assert 'position = max(0.0, float(session.get("resume_position") or 0))' in MAIN
    assert 'duration = max(0.0, float(session.get("resume_duration") or 0))' in MAIN
    assert "if position <= 0 or duration <= 0:" in MAIN

def test_service_captures_one_user_resume_decision_for_retry_session():
    assert 'source_session.update_resume(0,0,"beginning")' in SERVICE
    assert 'source_session.update_resume(actual,float(self.getTotalTime() or 0),"fixed")' in SERVICE
    assert '_plugin_url("play_session_stream",index=index)' in SERVICE
