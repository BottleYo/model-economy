import sys
import tempfile
import unittest
from pathlib import Path
from subprocess import DEVNULL, run


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_sensitive_content import (
    _is_public_git_email,
    format_findings,
    scan,
    scan_git,
    scan_text,
)


def _join(*parts: str) -> str:
    return "".join(parts)


def _private_key_header(prefix: str = "", suffix: str = "") -> str:
    return _join("-" * 5, "BEGIN ", prefix, "PRIVATE", " KEY", suffix, "-" * 5)


def _api_assignment(name: str) -> str:
    return _join(name, " = ", '"fixture-', 'secret"')


def _private_project_name() -> str:
    return _join("stock", "-studio")


class SensitiveContentTests(unittest.TestCase):
    def test_public_git_email_allows_only_documented_noreply_forms(self):
        self.assertTrue(_is_public_git_email("fixture@users.noreply.github.com"))
        self.assertTrue(_is_public_git_email("noreply@github.com"))

        for email in (
            "fixture@example.invalid",
            "attacker@github.com",
            "noreply+fixture@github.com",
            "noreply@github.com.example.invalid",
            "",
        ):
            with self.subTest(email=email):
                self.assertFalse(_is_public_git_email(email))

    def test_scan_text_reports_each_prohibited_content_type(self):
        cases = {
            "private_key": _private_key_header(),
            "api_key_assignment": _api_assignment(_join("OPENAI", "_API", "_KEY")),
            "macos_absolute_path": _join("/", "Users", "/fixture-user/project"),
            "windows_absolute_path": _join("C:", r"\Users\fixture-user\project"),
            "private_project": _private_project_name(),
            "persona_name": _join("N", "ORA"),
            "investment_keyword": _join("\\u4e2a", "\\u4eba", "\\u6301", "\\u4ed3").encode().decode("unicode_escape"),
        }

        for expected_rule, text in cases.items():
            with self.subTest(rule=expected_rule):
                findings = scan_text(Path("fixture.txt"), text)
                self.assertEqual([finding.rule for finding in findings], [expected_rule])

    def test_former_fixture_marker_does_not_exempt_a_match(self):
        former_marker = _join(" # ", "allow", "-sensitive", "-fixture")
        text = _join(_private_project_name(), former_marker)

        findings = scan_text(Path("fixture.txt"), text)

        self.assertEqual([(finding.line, finding.rule) for finding in findings], [(1, "private_project")])

    def test_scan_text_reports_all_supported_private_key_headers(self):
        prefixes = ("", "ENCRYPTED ", "OPENSSH ", "EC ", "RSA ", "DSA ", "PGP ")
        suffixes = ("", "", "", "", "", "", " BLOCK")

        for prefix, suffix in zip(prefixes, suffixes, strict=True):
            with self.subTest(prefix=prefix):
                findings = scan_text(Path("fixture.txt"), _private_key_header(prefix, suffix))
                self.assertEqual([finding.rule for finding in findings], ["private_key"])

    def test_scan_text_matches_case_insensitive_api_key_assignments(self):
        names = ("apiKey", "api_key", "openai_api_key", "OPENAI_API_KEY", "OpenAiApiKey")

        for name in names:
            with self.subTest(name=name):
                findings = scan_text(Path("fixture.txt"), _api_assignment(name))
                self.assertEqual([finding.rule for finding in findings], ["api_key_assignment"])

    def test_scan_text_does_not_flag_non_secret_api_key_examples(self):
        cases = (
            _join("api", "Key"),
            _join("api", "Key = ", '""'),
            _join("api", "Keys = ", '"fixture-secret"'),
        )

        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(scan_text(Path("fixture.txt"), text), [])

    def test_summary_never_includes_matching_content(self):
        secret_value = _join("fixture", "-secret")
        secret = _join("openai", "_api", "_key = ", '"', secret_value, '"')
        findings = scan_text(Path("fixture.txt"), secret)

        rendered = format_findings(findings)

        self.assertIn("fixture.txt:1: api_key_assignment", rendered)
        self.assertNotIn(secret_value, rendered)

    def test_scan_skips_ignored_directories_and_reports_relative_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".venv").mkdir()
            (root / ".venv" / "ignored.txt").write_text(_join("N", "ORA"), encoding="utf-8")
            (root / "visible.md").write_text(_join("N", "ORA"), encoding="utf-8")

            findings = scan(root)

        self.assertEqual([(finding.path, finding.line, finding.rule) for finding in findings], [
            (Path("visible.md"), 1, "persona_name"),
        ])

    def test_scan_checks_all_utf8_text_regardless_of_suffix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = [Path(".env"), Path("CONFIG"), Path("deploy.sh"), Path("script.ps1")]
            for path in expected:
                (root / path).write_text(_private_project_name(), encoding="utf-8")
            (root / "binary.bin").write_bytes(b"\x00" + _private_project_name().encode())

            findings = scan(root)

        self.assertEqual([finding.path for finding in findings], expected)

    def test_scan_does_not_report_its_own_source_or_test_fixtures(self):
        self.assertEqual(scan(ROOT), [])

    def test_scan_git_reports_author_and_committer_and_scans_history_paths_and_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run(["git", "init", "-q"], cwd=root, check=True)
            path = root / _join(_private_project_name(), ".md")
            path.write_text(_private_key_header("RSA "), encoding="utf-8")
            run(["git", "add", path.name], cwd=root, check=True)
            run(
                ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture"],
                cwd=root,
                check=True,
            )

            findings = scan_git(root)

        rules = {finding.rule for finding in findings}
        self.assertTrue({"git_author_email", "git_committer_email", "private_project", "private_key"} <= rules)

    def test_scan_git_returns_no_history_for_non_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(scan_git(Path(directory)), [])

    def test_scan_git_fails_closed_when_git_marker_is_unreadable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()

            with self.assertRaises(RuntimeError):
                scan_git(root)

    def test_scan_git_scans_annotated_tag_metadata_and_message(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run(["git", "init", "-q"], cwd=root, check=True)
            (root / "public.txt").write_text("public", encoding="utf-8")
            run(["git", "add", "public.txt"], cwd=root, check=True)
            identity = ["-c", "user.name=Fixture", "-c", "user.email=fixture@users.noreply.github.com"]
            run(["git", *identity, "commit", "-qm", "public"], cwd=root, check=True)
            run(["git", *identity, "tag", "-am", _private_project_name(), "v0.1.0"], cwd=root, check=True)

            findings = scan_git(root)

        self.assertIn("private_project", {finding.rule for finding in findings})

    def test_scan_git_scans_nested_annotated_tag_chain_without_inner_ref(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run(["git", "init", "-q"], cwd=root, check=True)
            (root / "public.txt").write_text("public", encoding="utf-8")
            run(["git", "add", "public.txt"], cwd=root, check=True)
            identity = ["-c", "user.name=Fixture", "-c", "user.email=fixture@users.noreply.github.com"]
            run(["git", *identity, "commit", "-qm", "public"], cwd=root, check=True)
            run(["git", *identity, "tag", "-am", _private_project_name(), "inner"], cwd=root, check=True)
            run(
                ["git", *identity, "tag", "-am", "public", "outer", "inner"],
                cwd=root,
                check=True,
                stderr=DEVNULL,
            )
            run(["git", "tag", "-d", "inner"], cwd=root, check=True, stdout=DEVNULL)

            findings = scan_git(root)

        self.assertIn("private_project", {finding.rule for finding in findings})

    def test_scan_git_scans_lightweight_tag_name(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run(["git", "init", "-q"], cwd=root, check=True)
            (root / "public.txt").write_text("public", encoding="utf-8")
            run(["git", "add", "public.txt"], cwd=root, check=True)
            identity = ["-c", "user.name=Fixture", "-c", "user.email=fixture@users.noreply.github.com"]
            run(["git", *identity, "commit", "-qm", "public"], cwd=root, check=True)
            run(["git", "tag", _private_project_name()], cwd=root, check=True)

            findings = scan_git(root)

        self.assertIn("private_project", {finding.rule for finding in findings})


if __name__ == "__main__":
    unittest.main()
