import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs/submission/fixtures"


class SubmissionFixtureTests(unittest.TestCase):
    def run_python(self, directory: str, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *arguments],
            cwd=FIXTURES / directory,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def test_simple_fixture_starts_green(self):
        result = self.run_python("simple", "-m", "unittest", "-v")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_mechanical_fixture_has_five_valid_inputs(self):
        result = self.run_python("mechanical", "validate.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "validated 5 fixtures")

    def test_standard_fixture_contains_the_documented_reproducible_bug(self):
        result = self.run_python("standard", "-m", "unittest", "-v")
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL: test_whitespace_is_removed_before_rendering", result.stderr)

    def test_high_risk_fixture_starts_green_without_external_services(self):
        result = self.run_python("high-risk", "-m", "unittest", "-v")
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
