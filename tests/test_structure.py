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


if __name__ == "__main__":
    unittest.main()
