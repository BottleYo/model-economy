import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StructureTests(unittest.TestCase):
    def test_manifest_and_marketplace_agree(self):
        manifest = json.loads(
            (ROOT / "plugins/model-economy/.codex-plugin/plugin.json").read_text(encoding="utf-8")
        )
        marketplace = json.loads(
            (ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "model-economy")
        self.assertEqual(marketplace["name"], "model-economy-public")
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], manifest["name"])
        self.assertEqual(entry["source"]["path"], "./plugins/model-economy")

    def test_global_routing_release_contract(self):
        manifest = json.loads(
            (ROOT / "plugins/model-economy/.codex-plugin/plugin.json").read_text(encoding="utf-8")
        )
        skill = (ROOT / "plugins/model-economy/skills/cost-aware-development/SKILL.md").read_text(
            encoding="utf-8"
        )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertEqual(manifest["version"], "0.2.0")
        self.assertIn("软件开发", skill.split("---", 2)[1])
        self.assertIn("enable-global-routing", readme)
        self.assertIn("disable-global-routing", readme)
        self.assertIn("项目自身的 `AGENTS.md` 可以覆盖", readme)

    def test_ci_checkout_fetches_full_history(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        checkout = "      - uses: actions/checkout@v4\n"
        self.assertIn(checkout + "        with:\n          fetch-depth: 0\n", workflow)

    def test_ci_forces_utf8_on_every_platform(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn('PYTHONUTF8: "1"', workflow)

    def test_readme_custom_commands_are_single_line_for_posix_and_powershell(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        custom_start = readme.index("# 3. custom")
        custom_end = readme.index("```", custom_start)
        custom = readme[custom_start:custom_end]
        self.assertNotIn("\\\n", custom)
        self.assertIn(
            "python plugins/model-economy/scripts/model_economy.py configure --strong <strong-model> --balanced <balanced-model> --economy <economy-model>",
            custom,
        )
        self.assertIn(
            "py -3.11 plugins/model-economy/scripts/model_economy.py configure --strong <strong-model> --balanced <balanced-model> --economy <economy-model>",
            custom,
        )


if __name__ == "__main__":
    unittest.main()
