import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "model-economy" / "scripts"
PROFILES = ROOT / "plugins" / "model-economy" / "assets" / "profiles"
sys.path.insert(0, str(SCRIPTS))

from model_economy_lib.lifecycle import (  # noqa: E402
    ChangeSet,
    ConflictError,
    Context,
    install,
    plan_upgrade,
    uninstall,
    upgrade,
)
from model_economy_lib.config import MachineState, dump_state, load_state  # noqa: E402
from model_economy_lib.profiles import load_profile  # noqa: E402
from model_economy_lib.renderer import render_all_agents  # noqa: E402


def snapshot_tree(root: Path) -> dict[Path, bytes]:
    return {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.codex_home = Path(self.temporary_directory.name) / "codex-home"
        self.context = Context(
            codex_home=self.codex_home,
            plugin_root=ROOT / "plugins" / "model-economy",
            template_version="0.1.0",
        )
        self.profile = load_profile(PROFILES / "openai-56.toml")

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_dry_run_changes_nothing(self):
        install(self.context, self.profile)
        before = snapshot_tree(self.codex_home)

        plan = plan_upgrade(self.context)

        self.assertEqual(snapshot_tree(self.codex_home), before)
        self.assertIsInstance(plan, ChangeSet)
        self.assertEqual(len(plan.unchanged), 8)

    def test_current_upgrade_performs_zero_writes(self):
        install(self.context, self.profile)

        with patch("model_economy_lib.lifecycle.atomic_write") as write:
            result = upgrade(self.context)

        self.assertFalse(result.created or result.updated or result.removed)
        write.assert_not_called()

    def test_upgrade_updates_rendered_roles_and_hashes(self):
        install(self.context, self.profile)
        upgrade_context = Context(
            codex_home=self.codex_home,
            plugin_root=self.context.plugin_root,
            template_version="0.2.0",
        )
        rendered = render_all_agents(self.profile)
        rendered["model-economy-architect.toml"] += "# template upgrade\n"

        with patch("model_economy_lib.lifecycle.render_all_agents", return_value=rendered):
            result = upgrade(upgrade_context)

        architect = self.codex_home / "agents/model-economy-architect.toml"
        self.assertIn(architect, result.updated)
        self.assertNotIn(upgrade_context.config_path, result.updated)
        self.assertIn(upgrade_context.state_path, result.updated)
        self.assertIn(b"# template upgrade", architect.read_bytes())

    def test_upgrade_rejects_modified_role_without_writing_anything(self):
        install(self.context, self.profile)
        role = self.codex_home / "agents/model-economy-reviewer.toml"
        role.write_text(role.read_text(encoding="utf-8") + "\n# user change\n", encoding="utf-8")
        before = snapshot_tree(self.codex_home)

        with self.assertRaises(ConflictError):
            upgrade(self.context)

        self.assertEqual(snapshot_tree(self.codex_home), before)

    def test_upgrade_failure_restores_all_roles_config_and_state(self):
        install(self.context, self.profile)
        upgrade_context = Context(
            codex_home=self.codex_home,
            plugin_root=self.context.plugin_root,
            template_version="0.2.0",
        )
        before = snapshot_tree(self.codex_home)
        rendered = {
            name: content + "# upgraded\n"
            for name, content in render_all_agents(self.profile).items()
        }
        original_write = __import__(
            "model_economy_lib.lifecycle", fromlist=["atomic_write"]
        ).atomic_write

        def fail_while_writing_config(path: Path, content: bytes, **kwargs) -> None:
            if path == upgrade_context.state_path:
                raise OSError("simulated state write failure")
            original_write(path, content)

        with (
            patch("model_economy_lib.lifecycle.render_all_agents", return_value=rendered),
            patch("model_economy_lib.lifecycle.atomic_write", side_effect=fail_while_writing_config),
            self.assertRaises(OSError),
        ):
            upgrade(upgrade_context)

        self.assertEqual(snapshot_tree(self.codex_home), before)

    @unittest.skipIf(os.name == "nt", "POSIX mode is not available on Windows")
    def test_upgrade_failure_restores_original_file_mode(self):
        install(self.context, self.profile)
        role = self.codex_home / "agents/model-economy-architect.toml"
        role.chmod(0o640)
        rendered = {
            name: content + "# upgraded\n"
            for name, content in render_all_agents(self.profile).items()
        }
        original_write = __import__(
            "model_economy_lib.lifecycle", fromlist=["atomic_write"]
        ).atomic_write

        def fail_at_state(path: Path, content: bytes, **kwargs) -> None:
            if path == self.context.state_path:
                raise OSError("simulated state write failure")
            original_write(path, content, **kwargs)

        with (
            patch("model_economy_lib.lifecycle.render_all_agents", return_value=rendered),
            patch("model_economy_lib.lifecycle.atomic_write", side_effect=fail_at_state),
            self.assertRaises(OSError),
        ):
            upgrade(self.context, force=True)

        self.assertEqual(stat.S_IMODE(role.stat().st_mode), 0o640)

    def test_uninstall_with_modified_role_deletes_no_roles_without_force(self):
        install(self.context, self.profile)
        role = self.codex_home / "agents/model-economy-reviewer.toml"
        role.write_text(role.read_text(encoding="utf-8") + "\n# user change\n", encoding="utf-8")

        result = uninstall(self.context)

        self.assertTrue(role.exists())
        self.assertIn(role, result.conflicts)
        self.assertFalse(result.removed)
        self.assertTrue(self.context.config_path.exists())

    def test_purge_with_modified_role_deletes_nothing_without_force(self):
        install(self.context, self.profile)
        role = self.codex_home / "agents/model-economy-reviewer.toml"
        role.write_text(role.read_text(encoding="utf-8") + "\n# user change\n", encoding="utf-8")

        result = uninstall(self.context, purge=True)

        self.assertTrue(role.exists())
        self.assertIn(role, result.conflicts)
        self.assertNotIn(self.context.config_path, result.removed)
        self.assertTrue(self.context.config_path.exists())

    def test_tampering_config_cannot_authorize_role_deletion(self):
        install(self.context, self.profile)
        role = self.codex_home / "agents/model-economy-reviewer.toml"
        config_text = self.context.config_path.read_text(encoding="utf-8")
        self.context.config_path.write_text(
            config_text
            + '\n[managed_files]\n"model-economy-reviewer.toml" = "'
            + "0" * 64
            + '"\n',
            encoding="utf-8",
        )

        result = uninstall(self.context)

        self.assertTrue(role.exists())
        self.assertIn(self.context.config_path, result.conflicts)
        self.assertFalse(result.removed)

    def test_incomplete_state_record_fails_closed(self):
        install(self.context, self.profile)
        role = self.codex_home / "agents/model-economy-reviewer.toml"
        state = load_state(self.context.state_path)
        self.context.state_path.write_text(
            dump_state(MachineState(
                schema_version=state.schema_version,
                config_sha256=state.config_sha256,
                template_version=state.template_version,
                managed_files={},
                model_identity_verified=state.model_identity_verified,
            )),
            encoding="utf-8",
        )

        result = uninstall(self.context)

        self.assertTrue(role.exists())
        self.assertIn(role, result.conflicts)
        self.assertFalse(result.removed)

    def test_missing_state_fails_closed(self):
        install(self.context, self.profile)
        role = self.codex_home / "agents/model-economy-reviewer.toml"
        self.context.state_path.unlink()

        result = uninstall(self.context)

        self.assertTrue(role.exists())
        self.assertTrue(result.conflicts)
        self.assertFalse(result.removed)

    def test_malformed_state_fails_closed(self):
        install(self.context, self.profile)
        role = self.codex_home / "agents/model-economy-reviewer.toml"
        self.context.state_path.write_text("{not-json", encoding="utf-8")

        result = uninstall(self.context)

        self.assertTrue(role.exists())
        self.assertIn(self.context.state_path, result.conflicts)
        self.assertFalse(result.removed)

    def test_repeated_non_purge_uninstall_is_a_zero_write_noop(self):
        install(self.context, self.profile)
        uninstall(self.context)
        before = snapshot_tree(self.codex_home)

        with patch("model_economy_lib.lifecycle.atomic_write") as write:
            result = uninstall(self.context)

        self.assertEqual(snapshot_tree(self.codex_home), before)
        self.assertFalse(result.created or result.updated or result.removed)
        write.assert_not_called()

    def test_force_uninstall_removes_modified_roles_and_config(self):
        install(self.context, self.profile)
        role = self.codex_home / "agents/model-economy-reviewer.toml"
        role.write_text(role.read_text(encoding="utf-8") + "\n# user change\n", encoding="utf-8")

        result = uninstall(self.context, purge=True, force=True)

        self.assertIn(role, result.removed)
        self.assertFalse(role.exists())
        self.assertFalse(self.context.config_path.exists())
        self.assertFalse(self.context.state_path.exists())

    def test_force_uninstall_without_state_removes_fixed_role_names(self):
        install(self.context, self.profile)
        role = self.codex_home / "agents/model-economy-reviewer.toml"
        unrelated = self.codex_home / "agents/custom-role.toml"
        unrelated.write_text("keep", encoding="utf-8")
        self.context.state_path.unlink()

        result = uninstall(self.context, force=True)

        self.assertIn(role, result.removed)
        self.assertFalse(role.exists())
        self.assertTrue(unrelated.exists())
        self.assertTrue(self.context.config_path.exists())

    def test_force_purge_with_malformed_state_removes_fixed_roles_and_config(self):
        install(self.context, self.profile)
        role = self.codex_home / "agents/model-economy-reviewer.toml"
        self.context.state_path.write_text("{not-json", encoding="utf-8")

        result = uninstall(self.context, purge=True, force=True)

        self.assertIn(role, result.removed)
        self.assertFalse(role.exists())
        self.assertFalse(self.context.config_path.exists())
        self.assertFalse(self.context.state_path.exists())


if __name__ == "__main__":
    unittest.main()
