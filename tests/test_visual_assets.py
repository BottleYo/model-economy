import importlib.util
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SVG_ASSETS = (
    "assets/model-economy-flow-en.svg",
    "assets/model-economy-flow-zh-CN.svg",
    "assets/social-preview.svg",
)
PNG_ASSET = ROOT / "assets/social-preview.png"
RENDER_SCRIPT = ROOT / "scripts/render_social_preview.py"
SVG_NAMESPACE = {"svg": "http://www.w3.org/2000/svg"}


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
