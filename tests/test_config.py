import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "model-economy" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from model_economy_lib.config import (  # noqa: E402
    ConfigError,
    LocalConfig,
    MachineState,
    dump_config,
    dump_state,
    export_profile,
    import_profile,
    import_profile_text,
    load_config,
    load_config_text,
    load_state,
    load_state_text,
)


class ConfigTests(unittest.TestCase):
    def make_config(self) -> LocalConfig:
        return LocalConfig(
            schema_version=1,
            profile="custom",
            models={"strong": "s", "balanced": "b", "economy": "e"},
        )

    def make_state(self) -> MachineState:
        return MachineState(
            schema_version=1,
            config_sha256="a" * 64,
            template_version="0.1.0",
            managed_files={"model-economy-architect.toml": "b" * 64},
            model_identity_verified=True,
        )

    def test_config_round_trip_contains_only_user_configuration(self):
        config = self.make_config()
        self.assertEqual(load_config_text(dump_config(config)), config)
        self.assertNotIn("managed_files", dump_config(config))
        self.assertNotIn("template_version", dump_config(config))
        self.assertNotIn("model_identity_verified", dump_config(config))

    def test_machine_state_round_trip_is_strict_json(self):
        state = self.make_state()
        self.assertEqual(load_state_text(dump_state(state)), state)
        with self.assertRaises(ConfigError):
            load_state_text('{"schema_version": 1, "schema_version": 1}')
        with self.assertRaises(ConfigError):
            load_state_text('{"schema_version": 1, "extra": true}')

    def test_load_config_rejects_unknown_fields(self):
        with self.assertRaises(ConfigError):
            load_config_text('schema_version = 1\nprofile = "custom"\nextra = true\n')

    def test_import_rejects_private_fields(self):
        with self.assertRaisesRegex(ConfigError, "unknown fields: account"):
            import_profile_text(
                'schema_version = 1\n'
                'profile = "custom"\n'
                'account = "private"\n'
                '[models]\n'
                'strong = "s"\n'
            )

    def test_import_rejects_unknown_model_keys(self):
        for key in ("account", "\\u0000"):
            with self.subTest(key=repr(key)), self.assertRaises(ConfigError):
                import_profile_text(
                    'schema_version = 1\n'
                    'profile = "custom"\n'
                    '[models]\n'
                    f'"{key}" = "value"\n'
                )

    def test_load_rejects_unknown_model_keys(self):
        for key in ("account", "\\u0000"):
            with self.subTest(key=repr(key)), self.assertRaises(ConfigError):
                load_config_text(
                    'schema_version = 1\n'
                    'profile = "custom"\n'
                    '[models]\n'
                    f'"{key}" = "value"\n'
                )

    def test_import_profile_accepts_only_export_fields(self):
        text = 'schema_version = 1\nprofile = "custom"\n[models]\nstrong = "s"\n'
        self.assertEqual(import_profile_text(text), ("custom", {"strong": "s"}))

    def test_import_rejects_malformed_toml(self):
        with self.assertRaises(ConfigError):
            import_profile_text('profile = "custom"\n[models\n')

    def test_complete_valid_config_loads(self):
        text = (
            'schema_version = 1\n'
            'profile = "custom"\n'
            '[models]\n'
            'strong = "s"\n'
            'balanced = "b"\n'
            'economy = "e"\n'
        )
        self.assertEqual(load_config_text(text), self.make_config())

    def test_config_rejects_legacy_machine_state_fields(self):
        with self.assertRaises(ConfigError):
            load_config_text(
                'schema_version = 1\n'
                'profile = "custom"\n'
                'template_version = "0.1.0"\n'
                'model_identity_verified = true\n'
                '[models]\n'
                'strong = "s"\n'
            )

    def test_model_names_must_be_printable_nonempty_and_at_most_128_chars(self):
        invalid_values = {
            "empty": "",
            "too_long": "x" * 129,
            "newline": "model\nname",
            "nul": "model\x00name",
        }
        for case, value in invalid_values.items():
            with self.subTest(case=case), self.assertRaises(ConfigError):
                dump_config(
                    LocalConfig(
                        schema_version=1,
                        profile="custom",
                        models={"strong": value, "balanced": "b", "economy": "e"},
                    )
                )

    def test_export_profile_uses_a_strict_public_whitelist(self):
        config = self.make_config()
        text = dump_config(config)
        self.assertNotIn("managed_files", export_text := self.export_to_text(config))
        self.assertNotIn("model_identity_verified", export_text)
        self.assertEqual(import_profile_text(export_text), ("custom", config.models))
        self.assertNotIn("managed_files", text)

    def export_to_text(self, config: LocalConfig) -> str:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.toml"
            export_profile(config, path)
            return path.read_text(encoding="utf-8")

    def test_file_apis_round_trip(self):
        config = self.make_config()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(dump_config(config), encoding="utf-8")
            self.assertEqual(load_config(path), config)
            state_path = Path(directory) / "state.json"
            state_path.write_text(dump_state(self.make_state()), encoding="utf-8")
            self.assertEqual(load_state(state_path), self.make_state())
            profile_path = Path(directory) / "profile.toml"
            export_profile(config, profile_path)
            self.assertEqual(import_profile(profile_path), ("custom", config.models))


if __name__ == "__main__":
    unittest.main()
