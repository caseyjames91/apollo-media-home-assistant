import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text()
AMS = (ROOT / "resources" / "lib" / "ams.py").read_text()

class PaginationRegressionTests(unittest.TestCase):
    def test_ams_page_parameter(self):
        self.assertIn('def discovery(addon, mode, media_type, query="", page=1):', AMS)
        self.assertIn('params = {"page": max(1, int(page or 1))}', AMS)

    def test_discovery_pagination(self):
        self.assertIn("def discovery_list(mode, media_type, page=1):", MAIN)
        self.assertIn("page=page + 1", MAIN)

    def test_search_pagination_preserves_query(self):
        self.assertIn('def search(media_type, query="", page=1):', MAIN)
        self.assertIn('url("search", media_type=media_type, query=query, page=page + 1)', MAIN)

if __name__ == "__main__":
    unittest.main()
