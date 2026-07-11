import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "model-economy" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from model_economy_lib.global_routing import (  # noqa: E402
    END_MARKER,
    GlobalRoutingConflict,
    START_MARKER,
    disable_text,
    enable_text,
)


class GlobalRoutingTextTests(unittest.TestCase):
    def test_missing_file_round_trip_returns_to_missing(self):
        enabled = enable_text(None)

        self.assertIn(START_MARKER, enabled)
        self.assertIn("origin=missing", enabled)
        self.assertIsNone(disable_text(enabled))

    def test_existing_content_round_trips_byte_for_byte(self):
        originals = (
            "",
            "现有规则",
            "现有规则\n",
            "现有规则\n\n",
            "现有规则\r\n",
            "现有规则\r\n\r\n",
        )

        for original in originals:
            with self.subTest(original=repr(original)):
                enabled = enable_text(original)
                self.assertIn("origin=existing", enabled)
                self.assertEqual(disable_text(enabled), original)

    def test_enable_is_idempotent(self):
        enabled = enable_text("现有规则")

        self.assertEqual(enable_text(enabled), enabled)

    def test_enable_replaces_managed_body_and_preserves_restore_metadata(self):
        enabled = enable_text("现有规则")
        stale = enabled.replace("## 默认开发路由", "## 旧规则")

        refreshed = enable_text(stale)

        self.assertIn("## 默认开发路由", refreshed)
        self.assertNotIn("## 旧规则", refreshed)
        self.assertEqual(disable_text(refreshed), "现有规则")

    def test_disable_without_markers_is_idempotent(self):
        self.assertEqual(disable_text("现有规则"), "现有规则")
        self.assertIsNone(disable_text(None))

    def test_malformed_or_repeated_markers_fail_closed(self):
        cases = (
            START_MARKER,
            END_MARKER,
            END_MARKER + "\n" + START_MARKER,
            START_MARKER + "\n" + START_MARKER + "\n" + END_MARKER,
            START_MARKER + "\n" + END_MARKER + "\n" + END_MARKER,
        )

        for text in cases:
            with self.subTest(text=text), self.assertRaises(GlobalRoutingConflict):
                enable_text(text)
            with self.subTest(text=text), self.assertRaises(GlobalRoutingConflict):
                disable_text(text)


if __name__ == "__main__":
    unittest.main()
