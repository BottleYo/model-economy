import json
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
from model_economy_lib.config import MachineState, dump_state, load_config, load_state  # noqa: E402
from model_economy_lib.filesystem import sha256_bytes  # noqa: E402
from model_economy_lib.models import Profile, ROLES  # noqa: E402
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

    def install_v1_fixture(self) -> None:
        legacy_reasoning = {
            "model-economy-architect": "high",
            "model-economy-final-reviewer": "high",
            "model-economy-implementer": "high",
            "model-economy-reviewer": "medium",
            "model-economy-explorer": "medium",
            "model-economy-batch-worker": "low",
        }
        profile = Profile("openai-56", False, self.profile.models, reasoning=legacy_reasoning)
        roles = render_all_agents(profile)
        self.context.agents_dir.mkdir(parents=True)
        for name, content in roles.items():
            (self.context.agents_dir / name).write_text(content, encoding="utf-8")
        config = (
            'schema_version = 1\nprofile = "openai-56"\n[models]\n'
            'strong = "gpt-5.6-sol"\nbalanced = "gpt-5.6-terra"\neconomy = "gpt-5.6-luna"\n'
        ).encode("utf-8")
        self.context.config_path.parent.mkdir(parents=True)
        self.context.config_path.write_bytes(config)
        state = MachineState(
            schema_version=1,
            config_sha256=sha256_bytes(config),
            template_version=self.context.template_version,
            managed_files={name: sha256_bytes((self.context.agents_dir / name).read_bytes()) for name in roles},
        )
        self.context.state_path.write_text(dump_state(state), encoding="utf-8")

    def managed_snapshot_with_metadata(self) -> dict[Path, tuple[bytes, int | None, int]]:
        paths = (*self.context.agents_dir.glob("model-economy-*.toml"), self.context.config_path, self.context.state_path)
        return {
            path: (
                path.read_bytes(),
                None if os.name == "nt" else stat.S_IMODE(path.stat().st_mode),
                path.stat().st_mtime_ns,
            )
            for path in paths
        }

    def test_dry_run_changes_nothing(self):
        install(self.context, self.profile)
        before = snapshot_tree(self.codex_home)

        plan = plan_upgrade(self.context)

        self.assertEqual(snapshot_tree(self.codex_home), before)
        self.assertIsInstance(plan, ChangeSet)
        self.assertEqual(len(plan.unchanged), 8)

    def test_v1_dry_run_is_zero_write_and_creates_no_backup(self):
        self.install_v1_fixture()
        before = snapshot_tree(self.codex_home)

        plan = plan_upgrade(self.context)

        self.assertEqual(plan.migration_from_schema, 1)
        self.assertEqual(plan.migration_to_schema, 2)
        self.assertIsNone(plan.backup_path)
        self.assertEqual(snapshot_tree(self.codex_home), before)
        self.assertFalse(self.context.backups_dir.exists())

    def test_v1_install_and_force_require_upgrade_without_writing_or_backup(self):
        self.install_v1_fixture()
        before = self.managed_snapshot_with_metadata()

        for force in (False, True):
            with self.subTest(force=force), self.assertRaisesRegex(ConflictError, "请先运行 upgrade"):
                install(self.context, self.profile, force=force)
            self.assertEqual(self.managed_snapshot_with_metadata(), before)
            self.assertFalse(list(self.context.backups_dir.glob("upgrade-*")))

    def test_v1_force_install_rejects_missing_or_malformed_state_when_roles_remain(self):
        for state_case in ("missing", "malformed"):
            with self.subTest(state_case=state_case):
                with tempfile.TemporaryDirectory() as directory:
                    home = Path(directory) / "codex-home"
                    context = Context(home, ROOT / "plugins" / "model-economy", "0.1.0")
                    original_context, self.context = self.context, context
                    original_home, self.codex_home = self.codex_home, home
                    try:
                        self.install_v1_fixture()
                    finally:
                        self.context, self.codex_home = original_context, original_home
                    if state_case == "missing":
                        context.state_path.unlink()
                    else:
                        context.state_path.write_bytes(b"{not-json")
                    paths = (*context.agents_dir.glob("model-economy-*.toml"), context.config_path, context.state_path)
                    before = {
                        path: (path.read_bytes(), None if os.name == "nt" else stat.S_IMODE(path.stat().st_mode), path.stat().st_mtime_ns)
                        for path in paths
                        if path.exists()
                    }

                    with self.assertRaisesRegex(ConflictError, "请先运行 upgrade"):
                        install(context, self.profile, force=True)

                    self.assertEqual(
                        before,
                        {
                            path: (path.read_bytes(), None if os.name == "nt" else stat.S_IMODE(path.stat().st_mode), path.stat().st_mtime_ns)
                            for path in before
                        },
                    )
                    if state_case == "missing":
                        self.assertFalse(context.state_path.exists())
                    else:
                        self.assertEqual(context.state_path.read_bytes(), b"{not-json")
                    self.assertFalse(list(context.backups_dir.glob("upgrade-*")))

    def test_explicit_v1_reconfigure_writes_v2_without_claiming_it_is_an_upgrade(self):
        self.install_v1_fixture()

        result = install(self.context, self.profile, reconfigure_v1=True)

        self.assertEqual(load_config(self.context.config_path).schema_version, 2)
        self.assertFalse(result.upgrade_required)
        self.assertIsNone(result.backup_path)

    def test_force_operations_reject_hardlinked_config_or_role_without_writing_or_deleting(self):
        for relative in (Path("model-economy/config.toml"), Path("agents/model-economy-reviewer.toml")):
            with self.subTest(relative=relative):
                with tempfile.TemporaryDirectory() as directory:
                    home = Path(directory) / "codex-home"
                    context = Context(home, ROOT / "plugins" / "model-economy", "0.1.0")
                    install(context, self.profile)
                    target = home / relative
                    peer = Path(directory) / f"peer-{relative.name}"
                    os.link(target, peer)
                    managed = (*context.agents_dir.glob("model-economy-*.toml"), context.config_path, context.state_path)
                    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in managed}

                    with self.assertRaises(ConflictError):
                        install(context, self.profile, force=True)
                    with self.assertRaises(ConflictError):
                        upgrade(context, force=True)
                    result = uninstall(context, purge=True, force=True)

                    self.assertTrue(result.conflicts)
                    self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before})
                    self.assertTrue(target.exists())
                    self.assertTrue(peer.exists())
                    self.assertFalse(list(context.backups_dir.glob("upgrade-*")))

    def test_v1_upgrade_rejects_symlinked_intermediate_agents_directory_without_backup(self):
        self.install_v1_fixture()
        outside = Path(self.temporary_directory.name) / "outside-agents"
        self.context.agents_dir.rename(outside)
        self.context.agents_dir.symlink_to(outside, target_is_directory=True)
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (self.context.config_path, self.context.state_path, *outside.glob("model-economy-*.toml"))}

        with self.assertRaises(ConflictError):
            upgrade(self.context, force=True)

        self.assertEqual(
            before,
            {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before},
        )
        self.assertFalse(list(self.context.backups_dir.glob("upgrade-*")))

    def test_v1_upgrade_rejects_symlinked_backups_directory_without_writing_outside(self):
        self.install_v1_fixture()
        outside = Path(self.temporary_directory.name) / "outside-backups"
        outside.mkdir()
        self.context.backups_dir.symlink_to(outside, target_is_directory=True)
        before = self.managed_snapshot_with_metadata()

        for force in (False, True):
            with self.subTest(force=force), self.assertRaises(ConflictError):
                upgrade(self.context, force=force)
            self.assertEqual(self.managed_snapshot_with_metadata(), before)
            self.assertFalse(any(outside.iterdir()))

    def test_v1_upgrade_preserves_effective_reasoning_and_creates_scoped_backup(self):
        self.install_v1_fixture()
        before = snapshot_tree(self.codex_home)
        role = self.context.agents_dir / "model-economy-implementer.toml"
        role.chmod(0o640)
        original_mode = stat.S_IMODE(role.stat().st_mode)
        # Windows 不提供完整 POSIX 权限位；迁移前后核对实际值，备份按契约记录 null。
        if os.name != "nt":
            self.assertEqual(original_mode, 0o640)

        result = upgrade(self.context)

        self.assertEqual(load_config(self.context.config_path).schema_version, 2)
        self.assertEqual(load_config(self.context.config_path).reasoning["model-economy-implementer"], "high")
        self.assertEqual(load_config(self.context.config_path).reasoning["model-economy-explorer"], "medium")
        self.assertEqual(stat.S_IMODE(role.stat().st_mode), original_mode)
        self.assertIsNotNone(result.backup_path)
        assert result.backup_path is not None
        manifest = json.loads((result.backup_path / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["files"]), {"config.toml", "state.json", *{f"agents/{item.name}.toml" for item in ROLES}})
        self.assertEqual((result.backup_path / "config.toml").read_bytes(), before[Path("model-economy/config.toml")])
        expected_backup_mode = None if os.name == "nt" else original_mode
        self.assertEqual(manifest["files"]["agents/model-economy-implementer.toml"]["mode"], expected_backup_mode)

    def test_repeated_v1_upgrade_is_zero_write_after_migration(self):
        self.install_v1_fixture()
        upgrade(self.context)
        with patch("model_economy_lib.lifecycle.atomic_write") as write:
            result = upgrade(self.context)
        self.assertFalse(result.created or result.updated or result.removed)
        self.assertIsNone(result.backup_path)
        write.assert_not_called()

    def test_v1_backup_failure_leaves_the_managed_installation_unchanged(self):
        self.install_v1_fixture()
        managed = {path: path.read_bytes() for path in (*self.context.agents_dir.glob("model-economy-*.toml"), self.context.config_path, self.context.state_path)}
        original_write = __import__("model_economy_lib.lifecycle", fromlist=["atomic_write"]).atomic_write

        def fail_backup_write(path: Path, content: bytes, **kwargs) -> None:
            if self.context.backups_dir in path.parents:
                raise OSError("simulated backup failure")
            original_write(path, content, **kwargs)

        with patch("model_economy_lib.lifecycle.atomic_write", side_effect=fail_backup_write), self.assertRaises(OSError):
            upgrade(self.context)

        self.assertEqual(managed, {path: path.read_bytes() for path in managed})
        self.assertFalse(list(self.context.backups_dir.glob("upgrade-*")))

    @unittest.skipIf(os.name == "nt", "POSIX mode is not available on Windows")
    def test_v1_write_failure_restores_original_bytes_and_permissions_and_keeps_backup(self):
        self.install_v1_fixture()
        self.context.config_path.chmod(0o640)
        before = {path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) for path in (*self.context.agents_dir.glob("model-economy-*.toml"), self.context.config_path, self.context.state_path)}
        original_write = __import__("model_economy_lib.lifecycle", fromlist=["atomic_write"]).atomic_write

        def fail_main_state(path: Path, content: bytes, **kwargs) -> None:
            if path == self.context.state_path:
                raise OSError("simulated main state failure")
            original_write(path, content, **kwargs)

        with patch("model_economy_lib.lifecycle.atomic_write", side_effect=fail_main_state), self.assertRaises(OSError):
            upgrade(self.context)

        self.assertEqual(
            before,
            {path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) for path in before},
        )
        self.assertTrue(list(self.context.backups_dir.glob("upgrade-*")))

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
