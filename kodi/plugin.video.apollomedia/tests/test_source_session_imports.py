import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SOURCE = (ROOT / "resources/lib/source_session.py").read_text(encoding="utf-8")

class SourceSessionImportTests(unittest.TestCase):
    def test_regex_dependency_is_imported(self):
        self.assertIn("import re", SOURCE)
        self.assertIn("re.search(", SOURCE)

if __name__ == "__main__":
    unittest.main()
