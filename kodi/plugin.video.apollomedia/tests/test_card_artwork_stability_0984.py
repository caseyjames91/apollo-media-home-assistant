import pathlib, unittest
ROOT = pathlib.Path(__file__).resolve().parents[2]
CARD = (ROOT / 'apollo-media-card.js').read_text(encoding='utf-8')
class CardArtworkStability0984Tests(unittest.TestCase):
    def test_blob_urls_are_renderable(self):
        self.assertIn('/^(?:https?:\\/\\/|blob:)/i', CARD)
    def test_ams_artwork_is_not_replaced_by_legacy_show_poster(self):
        self.assertIn('item.media_type !== "episode" || item.ams_media_id', CARD)
    def test_unchanged_ams_poll_does_not_replace_rail(self):
        self.assertIn('const changed = !this._amsContinueReady || previousSignature !== nextSignature;', CARD)
        self.assertIn('if (changed && this._rendered) this.replaceContinueWatchingRail();', CARD)
if __name__ == '__main__': unittest.main()
