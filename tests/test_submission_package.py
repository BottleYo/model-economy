import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "model-economy"
sys.path.insert(0, str(ROOT / "scripts"))

from build_submission_package import build_package, submission_manifest  # noqa: E402


class SubmissionPackageTests(unittest.TestCase):
    def build(self, directory: Path, name: str = "submission.zip") -> Path:
        output = directory / name
        build_package(PLUGIN_ROOT, output)
        return output

    def test_package_has_one_root_and_strips_directory_only_screenshots(self):
        with tempfile.TemporaryDirectory() as directory:
            output = self.build(Path(directory))
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
                self.assertTrue(names)
                self.assertTrue(all(name.startswith("model-economy/") for name in names))
                self.assertFalse(any("assets/screenshots/" in name for name in names))
                self.assertFalse(any(name.endswith((".app.json", ".mcp.json")) for name in names))
                manifest = json.loads(
                    archive.read("model-economy/.codex-plugin/plugin.json").decode("utf-8")
                )
                self.assertNotIn("screenshots", manifest["interface"])
                self.assertNotIn("apps", manifest)
                self.assertNotIn("mcpServers", manifest)

    def test_package_keeps_the_final_skill_tree_and_local_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            output = self.build(Path(directory))
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
            for required in (
                "model-economy/skills/cost-aware-development/SKILL.md",
                "model-economy/skills/cost-aware-development/references/routing-policy.json",
                "model-economy/skills/domain-context/SKILL.md",
                "model-economy/skills/module-design/SKILL.md",
                "model-economy/skills/disposable-prototype/SKILL.md",
                "model-economy/scripts/model_economy.py",
                "model-economy/assets/brand/logo-512.png",
            ):
                with self.subTest(required=required):
                    self.assertIn(required, names)

    def test_package_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            first = self.build(temporary, "first.zip")
            second = self.build(temporary, "second.zip")
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_package_meets_directory_listing_and_size_limits(self):
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        interface = manifest["interface"]
        self.assertLessEqual(len(manifest["name"]), 64)
        self.assertLessEqual(len(manifest["version"]), 64)
        self.assertLessEqual(len(interface["displayName"]), 30)
        self.assertLessEqual(len(interface["shortDescription"]), 30)
        self.assertLessEqual(len(interface["longDescription"]), 4_000)
        self.assertLessEqual(len(interface["developerName"]), 80)
        self.assertLessEqual(len(interface["capabilities"]), 20)
        self.assertLessEqual(len(interface["defaultPrompt"]), 3)
        self.assertEqual(len(interface["defaultPrompt"]), len(set(interface["defaultPrompt"])))
        for prompt in interface["defaultPrompt"]:
            self.assertTrue(prompt)
            self.assertNotIn("\n", prompt)
            self.assertNotIn("@", prompt)
            self.assertLessEqual(len(prompt), 128)

        with tempfile.TemporaryDirectory() as directory:
            output = self.build(Path(directory))
            self.assertLess(output.stat().st_size, 100 * 1024 * 1024)

    def test_skills_only_manifest_rejects_app_or_mcp_components(self):
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        for field in ("apps", "mcpServers"):
            with self.subTest(field=field):
                changed = dict(manifest)
                changed[field] = "./unsupported.json"
                with self.assertRaisesRegex(ValueError, field):
                    submission_manifest(changed)


if __name__ == "__main__":
    unittest.main()
