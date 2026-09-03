import ast
from pathlib import Path
import unittest


MAIN = Path(__file__).resolve().parents[1] / "main.py"


class FutureAiringLabelContract(unittest.TestCase):
    def test_future_airing_label_is_explicit_and_colored(self):
        source = MAIN.read_text()
        self.assertIn('"[COLOR gold]Airing on "', source)
        self.assertIn('"[/COLOR]"', source)
        self.assertNotIn('return "Airs " + target.strftime', source)

    def test_airing_indicator_remains_in_episode_row_label(self):
        source = MAIN.read_text()
        self.assertIn('air_label=_episode_air_label(row.get("air_date"))', source)
        self.assertIn('label=f"{episode}. {ep_title}" + (f"  •  {air_label}" if air_label else "")', source)

    def test_airing_parser_uses_kodi_safe_iso_date_path(self):
        source = MAIN.read_text()
        self.assertIn('date.fromisoformat(value[:10])', source)
        self.assertNotIn('datetime.strptime(value[:10]', source)

    def test_main_still_parses(self):
        ast.parse(MAIN.read_text())


if __name__ == "__main__":
    unittest.main()
