import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StructureTests(unittest.TestCase):
    def test_manifest_and_marketplace_agree(self):
        manifest = json.loads((ROOT / "plugins/model-economy/.codex-plugin/plugin.json").read_text())
        marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
        self.assertEqual(manifest["name"], "model-economy")
        self.assertEqual(marketplace["name"], "model-economy-public")
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], manifest["name"])
        self.assertEqual(entry["source"]["path"], "./plugins/model-economy")

    def test_ci_checkout_fetches_full_history(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        checkout = "      - uses: actions/checkout@v4\n"
        self.assertIn(checkout + "        with:\n          fetch-depth: 0\n", workflow)

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
