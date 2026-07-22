import importlib.util
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins/model-economy"
PLUGIN_MANIFEST = PLUGIN_ROOT / ".codex-plugin/plugin.json"
SVG_ASSETS = (
    "assets/model-economy-flow-en.svg",
    "assets/model-economy-flow-zh-CN.svg",
    "assets/social-preview.svg",
)
PNG_ASSET = ROOT / "assets/social-preview.png"
RENDER_SCRIPT = ROOT / "scripts/render_social_preview.py"
SVG_NAMESPACE = {"svg": "http://www.w3.org/2000/svg"}
X_PROMOTION_SVGS = (
    "assets/promotion/x/builder-workbench.svg",
    "assets/promotion/x/project-01.svg",
    "assets/promotion/x/route-by-risk.svg",
    "assets/promotion/x/claim-boundaries.svg",
    "assets/promotion/x/real-task-wanted.svg",
)
X_PROMOTION_PNGS = {
    "assets/promotion/x/builder-workbench.png": (1600, 900),
    "assets/promotion/x/project-01.png": (1600, 900),
    "assets/promotion/x/route-by-risk.png": (1600, 900),
    "assets/promotion/x/claim-boundaries.png": (1600, 900),
    "assets/promotion/x/model-economy-flow-en.png": (1440, 760),
    "assets/promotion/x/real-task-wanted.png": (1600, 900),
}
XIAOHONGSHU_PNGS = tuple(
    f"assets/promotion/xiaohongshu-{number:02d}.png" for number in range(1, 7)
)
X_CONTENT_PLAN = ROOT / "docs/promotion/x-first-week.md"


def estimated_text_width(text: str, font_size: float) -> float:
    units = 0.0
    for character in text:
        if "\u4e00" <= character <= "\u9fff":
            units += 1.0
        elif character == " ":
            units += 0.35
        elif character.isupper():
            units += 0.72
        else:
            units += 0.56
    return units * font_size


def load_renderer():
    spec = importlib.util.spec_from_file_location("render_social_preview", RENDER_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class VisualAssetTests(unittest.TestCase):
    def test_plugin_manifest_declares_self_contained_brand_assets(self):
        import json

        manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
        interface = manifest["interface"]
        expected_assets = {
            "composerIcon": "./assets/brand/composer-icon.svg",
            "logo": "./assets/brand/logo.svg",
            "logoDark": "./assets/brand/logo-dark.svg",
        }

        self.assertEqual(interface["brandColor"], "#1F6F6A")
        for field, relative_path in expected_assets.items():
            with self.subTest(field=field):
                self.assertEqual(interface[field], relative_path)
                path = PLUGIN_ROOT / relative_path.removeprefix("./")
                self.assertTrue(path.is_file(), f"missing plugin brand asset: {relative_path}")
                source = path.read_text(encoding="utf-8")
                root = ET.fromstring(source)
                self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
                self.assertTrue(root.attrib.get("viewBox"))
                for prohibited in (
                    "linearGradient",
                    "radialGradient",
                    "<image",
                    "<script",
                    "href=",
                    "<text",
                ):
                    self.assertNotIn(prohibited, source)

    def test_svg_assets_are_parseable_and_self_contained(self):
        prohibited = ("linearGradient", "radialGradient", "filter")

        for relative_path in SVG_ASSETS:
            with self.subTest(path=relative_path):
                path = ROOT / relative_path
                self.assertTrue(path.is_file())
                source = path.read_text(encoding="utf-8")
                ET.fromstring(source)
                self.assertFalse(any(token in source for token in prohibited))
                self.assertNotIn("href=", source)

    def test_x_promotion_assets_are_platform_ready(self):
        for relative_path in X_PROMOTION_SVGS:
            with self.subTest(path=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8")
                root = ET.fromstring(source)
                self.assertEqual(root.attrib.get("width"), "1600")
                self.assertEqual(root.attrib.get("height"), "900")
                self.assertNotIn("href=", source)
                self.assertNotIn("<script", source)

        for relative_path, expected_size in X_PROMOTION_PNGS.items():
            with self.subTest(path=relative_path):
                path = ROOT / relative_path
                self.assertTrue(path.is_file())
                with Image.open(path) as image:
                    self.assertEqual(image.format, "PNG")
                    self.assertEqual(image.size, expected_size)

    def test_xiaohongshu_cards_have_uploadable_png_copies(self):
        for relative_path in XIAOHONGSHU_PNGS:
            with self.subTest(path=relative_path):
                path = ROOT / relative_path
                self.assertTrue(path.is_file())
                with Image.open(path) as image:
                    self.assertEqual(image.format, "PNG")
                    self.assertEqual(image.size, (1080, 1440))

    def test_x_content_plan_references_existing_upload_assets(self):
        source = X_CONTENT_PLAN.read_text(encoding="utf-8")
        referenced_assets = set()
        for line in source.splitlines():
            for fragment in line.split("`")[1::2]:
                if fragment.endswith((".png", ".svg")):
                    referenced_assets.add(fragment)

        self.assertTrue(referenced_assets)
        for relative_path in referenced_assets:
            with self.subTest(path=relative_path):
                path = ROOT / relative_path
                if not path.is_file():
                    path = ROOT / "assets/promotion" / relative_path
                self.assertTrue(path.is_file(), f"missing promotion asset: {relative_path}")

    def test_flow_assets_show_all_classification_routes(self):
        expected_routes = {"simple", "standard", "large-high-risk", "mechanical"}

        for relative_path in SVG_ASSETS[:2]:
            with self.subTest(path=relative_path):
                root = ET.parse(ROOT / relative_path).getroot()
                routes = {
                    element.attrib["data-route"]
                    for element in root.findall(".//*[@data-route]", SVG_NAMESPACE)
                }
                self.assertEqual(routes, expected_routes)

    def test_standard_route_states_the_exact_strong_escalation_gate(self):
        english = (ROOT / SVG_ASSETS[0]).read_text(encoding="utf-8")
        chinese = (ROOT / SVG_ASSETS[1]).read_text(encoding="utf-8")

        self.assertIn("AFTER 2 FAILURES · DIAGNOSTIC ×1", english)
        self.assertIn("两次失败后 · 仅诊断 1 次", chinese)

    def test_flow_card_labels_stay_inside_declared_bounds(self):
        required_labels = {"ARCHITECT", "IMPLEMENT"}

        for relative_path in SVG_ASSETS:
            with self.subTest(path=relative_path):
                root = ET.parse(ROOT / relative_path).getroot()
                cards = {
                    element.attrib["id"]: element
                    for element in root.findall(".//svg:rect[@id]", SVG_NAMESPACE)
                }
                fitted_labels = set()
                for label in root.findall(".//svg:text[@data-fit]", SVG_NAMESPACE):
                    card = cards[label.attrib["data-fit"]]
                    text = "".join(label.itertext()).strip()
                    fitted_labels.add(text)
                    left = float(label.attrib["x"])
                    right = float(card.attrib["x"]) + float(card.attrib["width"]) - 16
                    width = estimated_text_width(text, float(label.attrib["font-size"]))
                    self.assertLessEqual(left + width, right, text)

                self.assertTrue(fitted_labels)
                if relative_path.endswith("-en.svg"):
                    self.assertTrue(required_labels <= fitted_labels)

    def test_social_preview_is_a_compact_1280_by_640_png(self):
        self.assertTrue(PNG_ASSET.is_file())
        self.assertLess(PNG_ASSET.stat().st_size, 1_000_000)

        with Image.open(PNG_ASSET) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (1280, 640))

    def test_social_preview_renderer_matches_committed_png(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "social-preview.png"
            command = [sys.executable, str(RENDER_SCRIPT), "--output", str(output)]
            subprocess.run(command, check=True, cwd=ROOT)
            self.assertEqual(output.read_bytes(), PNG_ASSET.read_bytes())

    def test_renderer_does_not_depend_on_system_fonts(self):
        source = RENDER_SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("/System/Library/Fonts", source)
        self.assertNotIn("/Library/Fonts", source)
        self.assertNotIn("ImageFont.truetype", source)

    def test_renderer_uses_repo_defined_bitmap_glyphs(self):
        source = RENDER_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("BITMAP_FONT", source)
        self.assertNotIn("ImageFont", source)

    def test_social_preview_states_the_product_constraints(self):
        sources = (
            RENDER_SCRIPT.read_text(encoding="utf-8"),
            (ROOT / "assets/social-preview.svg").read_text(encoding="utf-8"),
        )

        for source in sources:
            self.assertIn("Rigor scales with risk.", source)
            self.assertIn("Policy caps. One orchestrator.", source)
            self.assertIn("STRONG 0/1/2", source)
            self.assertIn("SUBAGENTS 3 MAX", source)

    def test_public_asset_renderers_are_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            preview = temporary / "social-preview.png"
            subprocess.run(
                [sys.executable, str(RENDER_SCRIPT), "--output", str(preview)],
                check=True,
                cwd=ROOT,
            )
            self.assertEqual(preview.read_bytes(), PNG_ASSET.read_bytes())

            plugin_output = temporary / "plugin"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/render_plugin_screenshots.py"),
                    "--output-dir",
                    str(plugin_output),
                ],
                check=True,
                cwd=ROOT,
            )
            generated_plugin = list(plugin_output.glob("*.png"))
            self.assertEqual(len(generated_plugin), 2)
            for generated in generated_plugin:
                committed = PLUGIN_ROOT / "assets/screenshots" / generated.name
                self.assertEqual(generated.read_bytes(), committed.read_bytes())

            promotion_output = temporary / "promotion"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/render_xiaohongshu_cards.py"),
                    "--output-dir",
                    str(promotion_output),
                ],
                check=True,
                cwd=ROOT,
            )
            generated_promotion = list(promotion_output.glob("*.svg"))
            self.assertEqual(len(generated_promotion), 6)
            for generated in generated_promotion:
                committed = ROOT / "assets/promotion" / generated.name
                self.assertEqual(generated.read_bytes(), committed.read_bytes())

            submission_logo = temporary / "logo-512.png"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/render_submission_logo.py"),
                    "--output",
                    str(submission_logo),
                ],
                check=True,
                cwd=ROOT,
            )
            committed_logo = PLUGIN_ROOT / "assets/brand/logo-512.png"
            self.assertEqual(submission_logo.read_bytes(), committed_logo.read_bytes())

    def test_social_preview_badge_labels_fit_their_bounds(self):
        renderer = load_renderer()
        badges = getattr(renderer, "PREVIEW_BADGES", ())
        self.assertTrue(badges)
        for bounds, label, scale in badges:
            with self.subTest(label=label):
                left, _, right, _ = bounds
                width = renderer.bitmap_text_width(label, scale)
                self.assertLessEqual(width, right - left - 24)

    def test_ci_installs_declared_visual_test_dependencies(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        self.assertIn("[dependency-groups]", pyproject)
        self.assertIn('Pillow==', pyproject)
        self.assertIn("python -m pip install --group test", workflow)


if __name__ == "__main__":
    unittest.main()
