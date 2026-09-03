import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")


class SingleResumeOwner040(unittest.TestCase):
    def playable_block(self):
        return MAIN[MAIN.index("def playable_media("):MAIN.index("\ndef home():")]

    def remote_block(self):
        return MAIN[MAIN.index("def play_remote("):MAIN.index("\ndef go_to_season(")]

    def resolve_block(self):
        return MAIN[MAIN.index("def _resolve_remote("):MAIN.index("\ndef _save_source_session(")]

    def test_browse_row_is_command_but_keeps_progress_metadata(self):
        block = self.playable_block()
        self.assertIn('item.setProperty("IsPlayable", "false")', block)
        self.assertIn("tag.setResumePoint(position, duration)", block)

    def test_browse_row_marks_command_launch_boundary(self):
        block = self.playable_block()
        self.assertIn('"play_remote",', block)
        self.assertIn('launch="1"', block)

    def test_command_launch_hands_off_to_session_stream(self):
        block = self.remote_block()
        self.assertIn('if str(p.get("launch") or "") == "1":', block)
        self.assertIn('"PlayMedia(" + url("play_session_stream", index=index) + ")"', block)

    def test_direct_play_remote_resolver_compatibility_is_preserved(self):
        block = self.remote_block()
        self.assertIn("_resolve_remote(stream, p)", block)
        self.assertLess(
            block.index('if str(p.get("launch") or "") == "1":'),
            block.index("_resolve_remote(stream, p)")
        )

    def test_apollo_owns_explicit_resume_choice(self):
        self.assertIn('f"Resume from {resume_label}?"', MAIN)
        self.assertIn('resume_mode = "beginning"', MAIN)
        self.assertIn('resume_mode = "fixed"', MAIN)
        self.assertIn('resume_mode=resume_mode', MAIN)

    def test_resolved_remote_uses_explicit_offset_not_resume_bookmark(self):
        block = self.resolve_block()
        self.assertIn('item.setProperty("StartOffset", str(position))', block)
        self.assertNotIn("setResumePoint", block)


if __name__ == "__main__":
    unittest.main()
