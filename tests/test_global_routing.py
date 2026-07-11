import os
import stat
import tempfile
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
    disable_global_routing,
    disable_text,
    enable_global_routing,
    enable_text,
)


class GlobalRoutingTextTests(unittest.TestCase):
    def test_missing_file_round_trip_returns_empty_text_without_metadata(self):
        enabled = enable_text(None)

        self.assertIn(START_MARKER, enabled)
        self.assertNotIn("origin=", enabled)
        self.assertEqual(disable_text(enabled), "")

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
                self.assertEqual(disable_text(enabled), original)

    def test_enable_is_idempotent(self):
        enabled = enable_text("现有规则")

        self.assertEqual(enable_text(enabled), enabled)

    def test_enable_replaces_managed_body(self):
        enabled = enable_text("现有规则")
        stale = enabled.replace("## 默认开发路由", "## 旧规则")

        refreshed = enable_text(stale)

        self.assertIn("## 默认开发路由", refreshed)
        self.assertNotIn("## 旧规则", refreshed)
        self.assertEqual(disable_text(refreshed), "现有规则")

    def test_disable_without_markers_is_idempotent(self):
        self.assertEqual(disable_text("现有规则"), "现有规则")
        self.assertIsNone(disable_text(None))

    def test_disable_preserves_content_added_before_and_after_managed_block(self):
        enabled = enable_text("原有规则")
        edited = "前置规则\n" + enabled + "后置规则\n"

        disabled = disable_text(edited)

        self.assertEqual(disabled, "前置规则\n原有规则\n后置规则\n")

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

    def test_file_io_round_trips_crlf_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AGENTS.md"
            original = "# Existing\r\n\r\nKeep this rule.\r\n".encode("utf-8")
            path.write_bytes(original)

            enable_global_routing(path)
            disable_global_routing(path)

            self.assertEqual(path.read_bytes(), original)

    @unittest.skipIf(os.name == "nt", "POSIX mode is not available on Windows")
    def test_file_io_preserves_posix_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AGENTS.md"
            path.write_text("existing", encoding="utf-8")
            path.chmod(0o640)

            enable_global_routing(path)

            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)

    @unittest.skipIf(os.name == "nt", "link semantics differ on Windows")
    def test_symlink_and_hardlink_targets_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.md"
            target.write_text("existing", encoding="utf-8")
            symlink = root / "symlink.md"
            symlink.symlink_to(target)
            hardlink = root / "hardlink.md"
            os.link(target, hardlink)

            for path in (symlink, hardlink):
                with self.subTest(path=path), self.assertRaises(GlobalRoutingConflict):
                    enable_global_routing(path)

            self.assertEqual(target.read_text(encoding="utf-8"), "existing")

    def test_non_utf8_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AGENTS.md"
            original = b"\xff\xfe"
            path.write_bytes(original)

            with self.assertRaises(GlobalRoutingConflict):
                enable_global_routing(path)

            self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
