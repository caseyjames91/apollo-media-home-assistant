import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
CARD = (ROOT.parent / "apollo-media-card.js").read_text(encoding="utf-8")

class GlobalDisplaySettingsTests(unittest.TestCase):
    def test_global_storage_keys(self):
        self.assertIn('localStorage.setItem("apollo-media.poster-size", String(safeSize))', CARD)
        self.assertIn('localStorage.setItem("apollo-media.text-scale", String(safePercent))', CARD)

    def test_global_values_propagate_to_context_maps(self):
        self.assertIn('Object.keys(this.posterSizes || {}).forEach(context =>', CARD)
        self.assertIn('Object.keys(this.textScales || {}).forEach(context =>', CARD)

    def test_legacy_per_view_migration(self):
        self.assertIn('One-time compatibility migration from the older per-view settings.', CARD)
        self.assertIn('apollo-media.poster-size.${context}', CARD)
        self.assertIn('apollo-media.text-scale.${context}', CARD)

    def test_reset_label_is_global(self):
        self.assertIn('Reset display settings', CARD)

    def test_poster_spacing(self):
        self.assertIn('gap: var(--apollo-card-gap);', CARD)
        self.assertIn('column-gap: var(--apollo-card-gap);', CARD)

    def test_release_stamp(self):
        self.assertIn('const APOLLO_CARD_VERSION = "0.9.83";', CARD)

if __name__ == "__main__":
    unittest.main()
