import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import BytesIO, StringIO, TextIOWrapper
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "model-economy" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from model_economy_lib.cli import main  # noqa: E402
from model_economy_lib.config import MachineState, dump_state, load_state  # noqa: E402
from model_economy_lib.doctor import DoctorReport, SmokeReport  # noqa: E402
from model_economy_lib.filesystem import sha256_bytes  # noqa: E402
from model_economy_lib.global_routing import END_MARKER, START_MARKER  # noqa: E402
from model_economy_lib.models import ROLES  # noqa: E402
from model_economy_lib.usage import (  # noqa: E402
    ModelTotal,
    TokenTotals,
    UsageError as UsageDataError,
    UsageSummary,
)


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

    def test_install_does_not_fail_when_console_cannot_encode_chinese(self):
        output = TextIOWrapper(BytesIO(), encoding="cp1252")
        with patch("sys.stdout", output):
            code = main(["--codex-home", str(self.home), "install", "--profile", "inherited"])

        self.assertEqual(code, 0)

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

    def test_install_applies_role_model_and_reasoning_overrides(self):
        code = main(
            [
                "--codex-home", str(self.home), "install", "--profile", "openai-56",
                "--role-model", "model-economy-implementer=implementation-model",
                "--reasoning", "model-economy-implementer=low",
            ]
        )
        self.assertEqual(code, 0)
        rendered = (self.home / "agents" / "model-economy-implementer.toml").read_text(encoding="utf-8")
        self.assertIn('model = "implementation-model"', rendered)
        self.assertIn('model_reasoning_effort = "low"', rendered)

    def test_role_override_rejects_duplicate_role_keys(self):
        code = main(
            [
                "--codex-home", str(self.home), "install", "--profile", "openai-56",
                "--reasoning", "model-economy-implementer=low",
                "--reasoning", "model-economy-implementer=medium",
            ]
        )
        self.assertEqual(code, 64)

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

    def test_v1_upgrade_preview_and_backup_path_are_reported(self):
        self.assertEqual(main(["--codex-home", str(self.home), "install", "--profile", "openai-56"]), 0)
        config = (
            'schema_version = 1\nprofile = "openai-56"\n[models]\n'
            'strong = "gpt-5.6-sol"\nbalanced = "gpt-5.6-terra"\neconomy = "gpt-5.6-luna"\n'
        ).encode("utf-8")
        config_path = self.home / "model-economy" / "config.toml"
        config_path.write_bytes(config)
        for name, old, new in (
            ("model-economy-implementer.toml", 'model_reasoning_effort = "medium"', 'model_reasoning_effort = "high"'),
            ("model-economy-explorer.toml", 'model_reasoning_effort = "low"', 'model_reasoning_effort = "medium"'),
        ):
            path = self.home / "agents" / name
            path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
        state_path = self.home / "model-economy" / "state.json"
        state = load_state(state_path)
        state_path.write_text(dump_state(MachineState(
            schema_version=1,
            config_sha256=sha256_bytes(config),
            template_version=state.template_version,
            managed_files={path.name: sha256_bytes(path.read_bytes()) for path in (self.home / "agents").glob("model-economy-*.toml")},
            model_identity_verified=state.model_identity_verified,
        )), encoding="utf-8")

        dry_output = StringIO()
        with redirect_stdout(dry_output):
            self.assertEqual(main(["--codex-home", str(self.home), "upgrade", "--dry-run"]), 0)
        self.assertIn("升级预览：schema v1 → v2", dry_output.getvalue())
        self.assertIn("模型映射：保留 explicit", dry_output.getvalue())
        self.assertIn("角色模型覆盖：保留 0 项", dry_output.getvalue())
        self.assertIn("model-economy-implementer high → high", dry_output.getvalue())
        self.assertIn("迁移备份：不会创建（dry-run）", dry_output.getvalue())

        upgrade_output = StringIO()
        with redirect_stdout(upgrade_output):
            self.assertEqual(main(["--codex-home", str(self.home), "upgrade"]), 0)
        self.assertIn("迁移备份：", upgrade_output.getvalue())
        self.assertNotIn("不会创建", upgrade_output.getvalue())

    def test_upgrade_dry_run_reports_conflict_for_missing_installation(self):
        code = main(["--codex-home", str(self.home), "upgrade", "--dry-run"])
        self.assertEqual(code, 2)

    def test_upgrade_dry_run_force_previews_conflict_override_without_writing(self):
        self.assertEqual(main(["--codex-home", str(self.home), "install", "--profile", "inherited"]), 0)
        role = self.home / "agents" / "model-economy-reviewer.toml"
        role.write_text(role.read_text(encoding="utf-8") + "\n# local change\n", encoding="utf-8")
        before = role.read_bytes()

        code = main(["--codex-home", str(self.home), "upgrade", "--dry-run", "--force"])

        self.assertEqual(code, 0)
        self.assertEqual(role.read_bytes(), before)

    def test_verify_returns_one_for_missing_installation(self):
        self.assertEqual(main(["--codex-home", str(self.home), "verify"]), 1)

    def test_status_json_reports_core_without_installation(self):
        output = StringIO()
        with redirect_stdout(output):
            code = main(["--codex-home", str(self.home), "status", "--format", "json"])

        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["status_schema_version"], 1)
        self.assertEqual(payload["plugin_version"], "0.7.0")
        self.assertEqual(payload["mode"], "core")
        self.assertEqual(payload["identity_verification"], {"model": False, "role": False})

    def test_status_json_is_emitted_for_degraded_state(self):
        role = self.home / "agents" / "model-economy-reviewer.toml"
        role.parent.mkdir(parents=True)
        role.write_text("sandbox_mode = \"read-only\"\n", encoding="utf-8")
        output = StringIO()

        with redirect_stdout(output):
            code = main(["--codex-home", str(self.home), "status", "--format", "json"])

        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())["mode"], "degraded")

    def test_enable_global_routing_uses_explicit_codex_home(self):
        code = main(["--codex-home", str(self.home), "enable-global-routing"])

        target = self.home / "AGENTS.md"
        self.assertEqual(code, 0)
        self.assertIn(START_MARKER, target.read_text(encoding="utf-8"))
        self.assertFalse((self.default_home / ".codex" / "AGENTS.md").exists())

    def test_repeated_enable_global_routing_performs_zero_writes(self):
        self.assertEqual(main(["--codex-home", str(self.home), "enable-global-routing"]), 0)

        with patch("model_economy_lib.global_routing.atomic_write") as write:
            code = main(["--codex-home", str(self.home), "enable-global-routing"])

        self.assertEqual(code, 0)
        write.assert_not_called()

    def test_disable_global_routing_restores_existing_agents_file(self):
        target = self.home / "AGENTS.md"
        target.parent.mkdir(parents=True)
        original = "# Existing\n\nKeep this rule.\n"
        target.write_text(original, encoding="utf-8")
        self.assertEqual(main(["--codex-home", str(self.home), "enable-global-routing"]), 0)

        code = main(["--codex-home", str(self.home), "disable-global-routing"])

        self.assertEqual(code, 0)
        self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_disable_global_routing_leaves_empty_file_created_by_plugin(self):
        self.assertEqual(main(["--codex-home", str(self.home), "enable-global-routing"]), 0)

        code = main(["--codex-home", str(self.home), "disable-global-routing"])

        self.assertEqual(code, 0)
        self.assertEqual((self.home / "AGENTS.md").read_bytes(), b"")

    def test_global_routing_with_malformed_markers_returns_conflict_without_writing(self):
        target = self.home / "AGENTS.md"
        target.parent.mkdir(parents=True)
        target.write_text(START_MARKER + "\n损坏的未闭合块", encoding="utf-8")
        before = target.read_bytes()

        code = main(["--codex-home", str(self.home), "enable-global-routing"])

        self.assertEqual(code, 2)
        self.assertEqual(target.read_bytes(), before)

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

    def usage_summary(self, project=None):
        return UsageSummary(
            project=project,
            range_days=7,
            tokens=TokenTotals(
                input=12000,
                output=345,
                cache_read=9000,
                cache_creation=None,
                total=12345,
            ),
            estimated_cost=12.34,
            currency="USD",
            models=(ModelTotal("balanced-model", 12345, 12.34),),
        )

    def test_usage_json_is_stable_and_hides_project_parent(self):
        project = Path(self.temporary_directory.name) / "private-parent" / "project-name"
        output = StringIO()
        with patch("model_economy_lib.cli.discover_codexbar", return_value=Path("/bin/tool")), patch(
            "model_economy_lib.cli.check_codexbar_version", return_value=(0, 41, 0)
        ), patch("model_economy_lib.cli.fetch_usage", return_value={"provider": "codex"}), patch(
            "model_economy_lib.cli.summarize_usage",
            return_value=self.usage_summary("project-name"),
        ) as summarize, redirect_stdout(output):
            code = main(
                [
                    "usage",
                    "--project",
                    str(project),
                    "--days",
                    "7",
                    "--format",
                    "json",
                    "--codexbar-bin",
                    "/bin/tool",
                ]
            )

        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["usage_schema_version"], 1)
        self.assertEqual(payload["project"], "project-name")
        self.assertNotIn(str(project.parent), output.getvalue())
        summarize.assert_called_once_with(
            {"provider": "codex"}, project=project, days=7
        )

    def test_usage_text_marks_cost_and_role_attribution_limits(self):
        output = StringIO()
        with patch("model_economy_lib.cli.discover_codexbar", return_value=Path("/bin/tool")), patch(
            "model_economy_lib.cli.check_codexbar_version", return_value=(0, 41, 0)
        ), patch("model_economy_lib.cli.fetch_usage", return_value=[]), patch(
            "model_economy_lib.cli.summarize_usage", return_value=self.usage_summary()
        ), redirect_stdout(output):
            code = main(["usage", "--days", "7"])

        self.assertEqual(code, 0)
        self.assertIn("来源：CodexBar（本地统计，成本为估算）", output.getvalue())
        self.assertIn("总 token：12,345", output.getvalue())
        self.assertIn("估算成本：USD 12.34", output.getvalue())
        self.assertIn("角色归因：不可用", output.getvalue())

    def test_usage_text_preserves_missing_values(self):
        summary = UsageSummary(
            project=None,
            range_days=30,
            tokens=TokenTotals(None, None, None, None, None),
            estimated_cost=None,
            currency=None,
            models=(),
        )
        output = StringIO()
        with patch("model_economy_lib.cli.discover_codexbar", return_value=Path("/bin/tool")), patch(
            "model_economy_lib.cli.check_codexbar_version", return_value=(0, 41, 0)
        ), patch("model_economy_lib.cli.fetch_usage", return_value=[]), patch(
            "model_economy_lib.cli.summarize_usage", return_value=summary
        ), redirect_stdout(output):
            code = main(["usage"])

        self.assertEqual(code, 0)
        self.assertIn("总 token：不可用", output.getvalue())
        self.assertIn("估算成本：不可用", output.getvalue())

    def test_usage_days_out_of_range_returns_parameter_error(self):
        for value in ("0", "366", "not-a-number"):
            with self.subTest(value=value):
                self.assertEqual(main(["usage", "--days", value]), 64)

    def test_usage_dependency_failure_does_not_affect_other_commands(self):
        with patch(
            "model_economy_lib.cli.discover_codexbar",
            side_effect=UsageDataError("未找到 CodexBar"),
        ):
            self.assertEqual(main(["usage"]), 1)

        self.assertEqual(main(["--codex-home", str(self.home), "verify", "--quiet"]), 1)


if __name__ == "__main__":
    unittest.main()
