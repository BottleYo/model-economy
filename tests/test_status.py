import tempfile
import unittest
import inspect
from pathlib import Path
from unittest.mock import patch


from tests.test_doctor import SCRIPTS  # keeps the test import path identical across platforms

import sys

sys.path.insert(0, str(SCRIPTS))

from model_economy_lib.doctor import inspect_status, status_to_dict  # noqa: E402
from model_economy_lib.lifecycle import Context, install, uninstall  # noqa: E402
from model_economy_lib.models import Profile, ROLES  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins/model-economy"


class StatusTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name) / "codex-home"
        self.context = Context(self.home, PLUGIN_ROOT, "0.6.0-rc.1")

    def test_empty_home_is_core_without_creating_files(self):
        report = inspect_status(self.context)

        self.assertEqual(report.mode, "core")
        self.assertEqual(report.enhancement_state, "absent")
        self.assertEqual(report.exit_code, 0)
        self.assertEqual(report.role_files_present, 0)
        self.assertFalse(self.home.exists())

    def test_healthy_inherited_install_is_enhanced(self):
        install(self.context, Profile("inherited", True, {}))

        report = inspect_status(self.context)
        payload = status_to_dict(report)

        self.assertEqual(report.mode, "enhanced")
        self.assertEqual(report.enhancement_state, "healthy")
        self.assertEqual(report.model_mapping_status, "inherited")
        self.assertEqual(report.role_files_present, len(ROLES))
        self.assertTrue(report.role_hashes_match)
        self.assertEqual(payload["status_schema_version"], 1)
        self.assertEqual(payload["identity_verification"], {"role": False, "model": False})

    def test_healthy_explicit_mapping_is_enhanced(self):
        models = {"strong": "s", "balanced": "b", "economy": "e"}
        install(self.context, Profile("custom", False, models))

        self.assertEqual(inspect_status(self.context).model_mapping_status, "explicit")

    def test_normal_non_purge_uninstall_returns_to_core(self):
        install(self.context, Profile("inherited", True, {}))
        uninstall(self.context)

        report = inspect_status(self.context)

        self.assertEqual(report.mode, "core")
        self.assertEqual(report.enhancement_state, "absent")
        self.assertEqual(report.model_mapping_status, "not_installed")

    def test_missing_managed_role_is_degraded_incomplete(self):
        install(self.context, Profile("inherited", True, {}))
        (self.home / "agents" / "model-economy-reviewer.toml").unlink()

        report = inspect_status(self.context)

        self.assertEqual(report.mode, "degraded")
        self.assertEqual(report.enhancement_state, "incomplete")
        self.assertEqual(report.exit_code, 1)

    def test_changed_managed_role_is_conflict(self):
        install(self.context, Profile("inherited", True, {}))
        role = self.home / "agents" / "model-economy-reviewer.toml"
        role.write_text(role.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")

        report = inspect_status(self.context)

        self.assertEqual(report.mode, "degraded")
        self.assertEqual(report.enhancement_state, "conflict")
        self.assertEqual(report.exit_code, 2)

    def test_old_template_is_degraded_outdated(self):
        old_context = Context(self.home, PLUGIN_ROOT, "0.5.1")
        install(old_context, Profile("inherited", True, {}))

        report = inspect_status(self.context)

        self.assertEqual(report.mode, "degraded")
        self.assertEqual(report.enhancement_state, "outdated")
        self.assertEqual(report.exit_code, 1)

    def test_partial_unmanaged_role_is_never_treated_as_core(self):
        role = self.home / "agents" / "model-economy-reviewer.toml"
        role.parent.mkdir(parents=True)
        role.write_text("sandbox_mode = \"read-only\"\n", encoding="utf-8")

        report = inspect_status(self.context)

        self.assertEqual(report.mode, "degraded")
        self.assertEqual(report.enhancement_state, "incomplete")
        self.assertEqual(report.exit_code, 1)

    def test_status_rejects_role_symlink_without_reading_target(self):
        target = self.home.parent / "session.json"
        target.write_text('{"secret": true}', encoding="utf-8")
        role = self.home / "agents" / "model-economy-reviewer.toml"
        role.parent.mkdir(parents=True)
        try:
            role.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("当前平台不允许创建符号链接")

        with patch.object(Path, "read_bytes", side_effect=AssertionError("不得读取链接目标")):
            report = inspect_status(self.context)

        self.assertEqual(report.mode, "degraded")
        self.assertEqual(report.enhancement_state, "conflict")
        self.assertEqual(report.exit_code, 2)

    def test_status_rejects_config_symlink_without_loading_it(self):
        target = self.home.parent / "auth.json"
        target.write_text('{"token": "redacted"}', encoding="utf-8")
        self.context.config_path.parent.mkdir(parents=True)
        try:
            self.context.config_path.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("当前平台不允许创建符号链接")

        with patch("model_economy_lib.doctor.load_config") as load_config:
            report = inspect_status(self.context)

        load_config.assert_not_called()
        self.assertEqual(report.enhancement_state, "conflict")
        self.assertEqual(report.exit_code, 2)

    def test_status_rejects_hardlinked_state_without_loading_it(self):
        target = self.home.parent / "session.json"
        target.write_text('{"secret": true}', encoding="utf-8")
        self.context.state_path.parent.mkdir(parents=True)
        self.context.state_path.hardlink_to(target)

        with patch("model_economy_lib.doctor.load_state") as load_state:
            report = inspect_status(self.context)

        load_state.assert_not_called()
        self.assertEqual(report.enhancement_state, "conflict")
        self.assertEqual(report.exit_code, 2)

    def test_status_rejects_symlinked_agents_directory_without_reading_target(self):
        external_agents = self.home.parent / "external-agents"
        external_agents.mkdir()
        (external_agents / "model-economy-reviewer.toml").write_text(
            'sandbox_mode = "read-only"\n', encoding="utf-8"
        )
        self.home.mkdir()
        try:
            (self.home / "agents").symlink_to(external_agents, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("当前平台不允许创建目录符号链接")

        with patch.object(Path, "read_bytes", side_effect=AssertionError("不得读取链接目录")):
            report = inspect_status(self.context)

        self.assertEqual(report.enhancement_state, "conflict")
        self.assertEqual(report.exit_code, 2)

    def test_status_rejects_symlinked_config_directory_without_loading_it(self):
        external_config = self.home.parent / "external-config"
        external_config.mkdir()
        (external_config / "config.toml").write_text("profile = 'inherited'\n", encoding="utf-8")
        self.home.mkdir()
        try:
            (self.home / "model-economy").symlink_to(external_config, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("当前平台不允许创建目录符号链接")

        with patch("model_economy_lib.doctor.load_config") as load_config:
            report = inspect_status(self.context)

        load_config.assert_not_called()
        self.assertEqual(report.enhancement_state, "conflict")
        self.assertEqual(report.exit_code, 2)

    def test_status_never_starts_a_subprocess(self):
        with patch("model_economy_lib.doctor.subprocess.run") as run:
            inspect_status(self.context)

        run.assert_not_called()

    def test_status_source_is_bounded_to_declared_artifacts(self):
        source = inspect.getsource(inspect_status)
        for prohibited in ("subprocess", "os.environ", "rglob", "glob(", "iterdir"):
            self.assertNotIn(prohibited, source)

    def test_public_identity_fields_ignore_legacy_state_flag(self):
        import json

        install(self.context, Profile("inherited", True, {}))
        state = json.loads(self.context.state_path.read_text(encoding="utf-8"))
        state["model_identity_verified"] = True
        self.context.state_path.write_text(json.dumps(state), encoding="utf-8")

        payload = status_to_dict(inspect_status(self.context))

        self.assertEqual(payload["identity_verification"], {"role": False, "model": False})


if __name__ == "__main__":
    unittest.main()
