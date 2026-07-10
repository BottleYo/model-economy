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

from model_economy_lib.config import LocalConfig, dump_config, load_config, load_state  # noqa: E402
from model_economy_lib.filesystem import sha256_bytes  # noqa: E402
from model_economy_lib.lifecycle import ConflictError, Context, install  # noqa: E402
from model_economy_lib.profiles import load_profile  # noqa: E402


class InstallTests(unittest.TestCase):
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

    def test_install_writes_only_owned_paths(self):
        result = install(self.context, self.profile)

        self.assertEqual(len(result.created), 8)
        self.assertTrue((self.codex_home / "agents/model-economy-architect.toml").is_file())
        self.assertTrue(self.context.config_path.is_file())
        self.assertFalse((self.codex_home / "config.toml").exists())
        self.assertTrue(self.context.state_path.is_file())
        state = load_state(self.context.state_path)
        self.assertEqual(len(state.managed_files), 6)
        self.assertEqual(state.config_sha256, sha256_bytes(self.context.config_path.read_bytes()))

    def test_state_file_is_private_on_posix(self):
        if os.name == "nt":
            self.skipTest("Windows does not provide POSIX mode semantics")

        install(self.context, self.profile)

        self.assertEqual(stat.S_IMODE(self.context.state_path.stat().st_mode), 0o600)

    def test_second_install_is_noop(self):
        install(self.context, self.profile)

        result = install(self.context, self.profile)

        self.assertFalse(result.created or result.updated or result.removed)
        self.assertEqual(len(result.unchanged), 8)

    def test_preexisting_valid_user_config_is_not_overwritten_without_state(self):
        self.context.config_path.parent.mkdir(parents=True)
        self.context.config_path.write_text(
            dump_config(load_config_text_fixture()), encoding="utf-8"
        )
        before = self.context.config_path.read_bytes()

        with self.assertRaises(ConflictError):
            install(self.context, self.profile)

        self.assertEqual(self.context.config_path.read_bytes(), before)
        self.assertFalse(self.context.state_path.exists())
        self.assertFalse(any(self.context.agents_dir.glob("model-economy-*.toml")))

    def test_config_hash_mismatch_rejects_install_before_any_write(self):
        install(self.context, self.profile)
        self.context.config_path.write_bytes(self.context.config_path.read_bytes() + b"\n")
        before = {
            path.relative_to(self.codex_home): path.read_bytes()
            for path in self.codex_home.rglob("*")
            if path.is_file()
        }

        with self.assertRaises(ConflictError):
            install(self.context, self.profile)

        after = {
            path.relative_to(self.codex_home): path.read_bytes()
            for path in self.codex_home.rglob("*")
            if path.is_file()
        }
        self.assertEqual(after, before)

    def test_unmanaged_collision_is_rejected_before_any_write(self):
        path = self.codex_home / "agents/model-economy-reviewer.toml"
        path.parent.mkdir(parents=True)
        path.write_text("user content", encoding="utf-8")

        with self.assertRaises(ConflictError):
            install(self.context, self.profile)

        self.assertEqual(path.read_text(encoding="utf-8"), "user content")
        self.assertFalse((self.codex_home / "agents/model-economy-architect.toml").exists())
        self.assertFalse(self.context.config_path.exists())

    def test_force_overwrites_unmanaged_collision(self):
        path = self.codex_home / "agents/model-economy-architect.toml"
        path.parent.mkdir(parents=True)
        path.write_text("user content", encoding="utf-8")

        result = install(self.context, self.profile, force=True)

        self.assertIn(path, result.updated)
        self.assertNotEqual(path.read_text(encoding="utf-8"), "user content")

    def test_write_failure_rolls_back_roles_config_and_state(self):
        original_write = __import__("model_economy_lib.lifecycle", fromlist=["atomic_write"]).atomic_write
        writes = 0

        def fail_while_writing_config(path: Path, content: bytes, **kwargs) -> None:
            nonlocal writes
            writes += 1
            if path == self.context.state_path:
                raise OSError("simulated state write failure")
            original_write(path, content)

        with patch(
            "model_economy_lib.lifecycle.atomic_write", side_effect=fail_while_writing_config
        ):
            with self.assertRaises(OSError):
                install(self.context, self.profile)

        self.assertEqual(writes, 8)
        self.assertFalse(self.context.config_path.exists())
        self.assertFalse(self.context.state_path.exists())
        self.assertFalse(any(self.context.agents_dir.glob("model-economy-*.toml")))

    def test_install_writes_config_and_state_after_roles(self):
        original_write = __import__(
            "model_economy_lib.lifecycle", fromlist=["atomic_write"]
        ).atomic_write
        paths: list[Path] = []

        def record_write(path: Path, content: bytes, **kwargs) -> None:
            paths.append(path)
            original_write(path, content)

        with patch("model_economy_lib.lifecycle.atomic_write", side_effect=record_write):
            install(self.context, self.profile)

        self.assertEqual(paths[-2:], [self.context.config_path, self.context.state_path])

    def test_resolve_codex_home_uses_windows_safe_environment_path(self):
        from model_economy_lib.filesystem import resolve_codex_home

        path = resolve_codex_home({"CODEX_HOME": str(self.codex_home)})

        self.assertEqual(path, self.codex_home.resolve())
        self.assertNotIn("/Users", str(path))

    def test_atomic_write_uses_replace_for_windows_safe_replacement(self):
        from model_economy_lib.filesystem import atomic_write

        path = self.codex_home / "model-economy" / "config.toml"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"old")

        with patch("model_economy_lib.filesystem.os.replace", wraps=os.replace) as replace:
            atomic_write(path, b"new")

        replace.assert_called_once()
        self.assertEqual(Path(replace.call_args.args[1]), path)
        self.assertEqual(path.read_bytes(), b"new")

    def test_atomic_write_cleans_temporary_file_when_replace_fails(self):
        from model_economy_lib.filesystem import atomic_write

        path = self.codex_home / "model-economy" / "config.toml"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"old")

        with patch("model_economy_lib.filesystem.os.replace", side_effect=OSError("replace failed")):
            with self.assertRaises(OSError):
                atomic_write(path, b"new")

        self.assertEqual(path.read_bytes(), b"old")
        self.assertFalse(list(path.parent.glob(f".{path.name}.*")))


if __name__ == "__main__":
    unittest.main()


def load_config_text_fixture():
    return LocalConfig(
        schema_version=1,
        profile="user-owned",
        models={"strong": "s", "balanced": "b", "economy": "e"},
    )
