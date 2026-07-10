import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "model-economy" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from model_economy_lib.cli import main  # noqa: E402
from model_economy_lib.doctor import DoctorReport, SmokeReport  # noqa: E402
from model_economy_lib.models import ROLES  # noqa: E402


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.home = Path(self.temporary_directory.name) / "codex-home"
        self.codex_home = Path(self.temporary_directory.name) / "environment-codex-home"
        self.default_home = Path(self.temporary_directory.name) / "must-not-be-used"
        self.original_home = os.environ.get("HOME")
        self.original_codex_home = os.environ.get("CODEX_HOME")
        os.environ["HOME"] = str(self.default_home)
        self.addCleanup(self.restore_environment)

    def restore_environment(self):
        if self.original_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self.original_home
        if self.original_codex_home is None:
            os.environ.pop("CODEX_HOME", None)
        else:
            os.environ["CODEX_HOME"] = self.original_codex_home

    def test_default_codex_home_uses_environment_without_writing_home_dot_codex(self):
        os.environ["CODEX_HOME"] = str(self.codex_home)

        code = main(["install", "--profile", "inherited"])

        self.assertEqual(code, 0)
        self.assertTrue((self.codex_home / "model-economy" / "config.toml").exists())
        self.assertFalse((self.default_home / ".codex").exists())

    def test_explicit_codex_home_overrides_environment(self):
        os.environ["CODEX_HOME"] = str(self.codex_home)

        code = main(["--codex-home", str(self.home), "install", "--profile", "inherited"])

        self.assertEqual(code, 0)
        self.assertTrue((self.home / "model-economy" / "config.toml").exists())
        self.assertFalse(self.codex_home.exists())

    def test_install_inherited(self):
        code = main(["--codex-home", str(self.home), "install", "--profile", "inherited"])
        self.assertEqual(code, 0)
        self.assertTrue((self.home / "model-economy" / "config.toml").exists())

    def test_conflict_returns_two(self):
        target = self.home / "agents" / "model-economy-architect.toml"
        target.parent.mkdir(parents=True)
        target.write_text("occupied", encoding="utf-8")
        code = main(["--codex-home", str(self.home), "install", "--profile", "inherited"])
        self.assertEqual(code, 2)

    def test_parameter_errors_return_sixty_four(self):
        code = main(["--codex-home", str(self.home), "install", "--profile", "missing"])
        self.assertEqual(code, 64)

    def test_configure_custom_models_updates_managed_agents(self):
        code = main(
            [
                "configure",
                "--codex-home",
                str(self.home),
                "--strong",
                "strong-model",
                "--balanced",
                "balanced-model",
                "--economy",
                "economy-model",
            ]
        )
        self.assertEqual(code, 0)
        rendered = (self.home / "agents" / "model-economy-explorer.toml").read_text(encoding="utf-8")
        self.assertIn('model = "economy-model"', rendered)

    def test_export_and_import_profile_use_explicit_paths(self):
        self.assertEqual(
            main(["--codex-home", str(self.home), "install", "--profile", "openai-56"]),
            0,
        )
        exported = Path(self.temporary_directory.name) / "profile.toml"
        self.assertEqual(main(["--codex-home", str(self.home), "export-profile", str(exported)]), 0)
        self.assertTrue(exported.exists())

        imported_home = Path(self.temporary_directory.name) / "imported-home"
        self.assertEqual(main(["--codex-home", str(imported_home), "import-profile", str(exported)]), 0)
        self.assertTrue((imported_home / "model-economy" / "state.json").exists())

    def test_upgrade_and_uninstall_exit_successfully_for_managed_installation(self):
        self.assertEqual(main(["--codex-home", str(self.home), "install", "--profile", "inherited"]), 0)
        self.assertEqual(main(["--codex-home", str(self.home), "upgrade"]), 0)
        self.assertEqual(main(["--codex-home", str(self.home), "uninstall", "--purge"]), 0)
        self.assertFalse((self.home / "model-economy" / "state.json").exists())

    def test_upgrade_dry_run_reports_plan_without_writing(self):
        self.assertEqual(main(["--codex-home", str(self.home), "install", "--profile", "inherited"]), 0)
        managed_paths = [
            *(self.home / "agents" / f"{role.name}.toml" for role in ROLES),
            self.home / "model-economy" / "config.toml",
            self.home / "model-economy" / "state.json",
        ]
        before = {path: path.read_bytes() for path in managed_paths}

        output = StringIO()
        with redirect_stdout(output):
            code = main(["--codex-home", str(self.home), "upgrade", "--dry-run"])

        self.assertEqual(code, 0)
        self.assertEqual(before, {path: path.read_bytes() for path in managed_paths})
        self.assertIn("完成：", output.getvalue())

    def test_upgrade_dry_run_reports_conflict_for_missing_installation(self):
        code = main(["--codex-home", str(self.home), "upgrade", "--dry-run"])
        self.assertEqual(code, 2)

    def test_verify_returns_one_for_missing_installation(self):
        self.assertEqual(main(["--codex-home", str(self.home), "verify"]), 1)

    def test_doctor_smoke_prints_three_explicit_verification_layers(self):
        doctor = DoctorReport(True, {"local": True, "codex": True}, True)
        smoke = SmokeReport(True)
        output = StringIO()
        with patch("model_economy_lib.cli.run_doctor", return_value=doctor), patch(
            "model_economy_lib.cli.run_smoke", return_value=smoke
        ), redirect_stdout(output):
            code = main(["--codex-home", str(self.home), "doctor", "--smoke"])

        self.assertEqual(code, 0)
        self.assertEqual(
            output.getvalue().splitlines()[-3:],
            [
                "Subagent 启动：通过",
                "角色身份：未验证（当前 Codex JSONL 不含 agent_type）",
                "模型身份：未验证",
            ],
        )

    def test_doctor_smoke_failure_keeps_identity_layers_unverified(self):
        doctor = DoctorReport(True, {"local": True, "codex": True}, True)
        smoke = SmokeReport(False)
        output = StringIO()
        with patch("model_economy_lib.cli.run_doctor", return_value=doctor), patch(
            "model_economy_lib.cli.run_smoke", return_value=smoke
        ), redirect_stdout(output):
            code = main(["--codex-home", str(self.home), "doctor", "--smoke"])

        self.assertEqual(code, 1)
        self.assertEqual(output.getvalue().splitlines()[-3:], [
            "Subagent 启动：失败",
            "角色身份：未验证（当前 Codex JSONL 不含 agent_type）",
            "模型身份：未验证",
        ])


if __name__ == "__main__":
    unittest.main()
