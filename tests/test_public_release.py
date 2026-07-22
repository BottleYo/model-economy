import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


class PublicReleaseTests(unittest.TestCase):
    def test_community_health_and_submission_materials_exist(self):
        required = (
            "AGENTS.md",
            "CONTRIBUTING.md",
            "SUPPORT.md",
            "CODE_OF_CONDUCT.md",
            "ROADMAP.md",
            ".github/ISSUE_TEMPLATE/bug.yml",
            ".github/ISSUE_TEMPLATE/feature.yml",
            ".github/ISSUE_TEMPLATE/installation.yml",
            ".github/ISSUE_TEMPLATE/config.yml",
            "docs/evaluation/0.6.0-pilot-protocol.md",
            "docs/evaluation/0.6.0-pilot-template.csv",
            "docs/promotion/launch-kit.md",
            "docs/promotion/x-first-week.md",
            "docs/promotion/technical-article.zh-CN.md",
            "docs/promotion/release-0.5.2.md",
            "docs/promotion/release-0.6.0-rc.1.md",
            "docs/promotion/release-0.6.0.md",
            "docs/submission/0.6.0.md",
            "docs/submission/fixtures/README.md",
            "docs/release/0.6.0-rc.1-readiness.md",
        )
        for relative in required:
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file())

    def test_manifest_has_public_urls_and_real_png_screenshots(self):
        plugin_root = ROOT / "plugins/model-economy"
        manifest = json.loads(
            (plugin_root / ".codex-plugin/plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["homepage"], "https://bottleyo.github.io/model-economy/")
        self.assertEqual(manifest["repository"], "https://github.com/BottleYo/model-economy")
        interface = manifest["interface"]
        self.assertEqual(interface["websiteURL"], manifest["homepage"])
        for field in ("privacyPolicyURL", "termsOfServiceURL"):
            self.assertTrue(interface[field].startswith("https://bottleyo.github.io/model-economy/"))
        self.assertLessEqual(len(interface["defaultPrompt"]), 3)
        for screenshot in interface["screenshots"]:
            self.assertTrue(screenshot.startswith("./assets/"))
            path = plugin_root / screenshot.removeprefix("./")
            self.assertEqual(path.suffix, ".png")
            with Image.open(path) as image:
                self.assertEqual(image.size, (1280, 800))
        with Image.open(plugin_root / "assets/brand/logo-512.png") as logo:
            self.assertEqual(logo.size, (512, 512))

    def test_pages_are_static_and_contain_no_external_tracking(self):
        sources = "\n".join(
            path.read_text(encoding="utf-8") for path in sorted((ROOT / "site").rglob("*")) if path.is_file()
        ).lower()
        for token in (
            "google-analytics",
            "googletagmanager",
            "segment.com",
            "mixpanel",
            "plausible.io",
            "fonts.googleapis.com",
            "document.cookie",
        ):
            self.assertNotIn(token, sources)
        self.assertNotIn("<script", sources)

    def test_pages_internal_links_resolve_in_source_or_deploy_bundle(self):
        site = ROOT / "site"
        for page in site.rglob("*.html"):
            source = page.read_text(encoding="utf-8")
            for target in re.findall(r'(?:href|src)="([^"]+)"', source):
                if target.startswith(("https://", "#")):
                    continue
                resolved = (page.parent / target.split("#", 1)[0]).resolve()
                if target.endswith("/"):
                    resolved /= "index.html"
                if target == "./assets/social-preview.png":
                    resolved = ROOT / "assets/social-preview.png"
                self.assertTrue(resolved.exists(), f"broken link in {page}: {target}")

    def test_six_xiaohongshu_cards_are_three_by_four_and_self_contained(self):
        cards = sorted((ROOT / "assets/promotion").glob("xiaohongshu-*.svg"))
        self.assertEqual(len(cards), 6)
        for card in cards:
            source = card.read_text(encoding="utf-8")
            root = ET.fromstring(source)
            self.assertEqual(root.attrib["width"], "1080")
            self.assertEqual(root.attrib["height"], "1440")
            self.assertNotIn("href=", source)
            self.assertNotIn("<script", source)
            fitted = [element for element in root if element.tag.endswith("text") and "textLength" in element.attrib]
            self.assertEqual(len(fitted), 3)
            for element in fitted:
                self.assertLessEqual(float(element.attrib["x"]) + float(element.attrib["textLength"]), 964)

    def test_public_copy_avoids_unverified_fixed_savings_claims(self):
        public_paths = [
            ROOT / "README.md",
            ROOT / "README.zh-CN.md",
            ROOT / "site/index.html",
            ROOT / "docs/promotion/launch-kit.md",
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in public_paths)
        self.assertNotRegex(combined, r"(?:save|节省)\s*\d+%")
        self.assertNotIn("Hard caps", combined)
        self.assertNotIn("硬上限", combined)


if __name__ == "__main__":
    unittest.main()
