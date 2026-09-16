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
            schema_version=2,
            profile="custom",
            models={"strong": "s", "balanced": "b", "economy": "e"},
            role_models={"model-economy-implementer": "implementation"},
            reasoning={
                "model-economy-architect": "high",
                "model-economy-final-reviewer": "high",
                "model-economy-implementer": "medium",
                "model-economy-reviewer": "medium",
                "model-economy-explorer": "low",
                "model-economy-batch-worker": "low",
            },
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
            'schema_version = 2\n'
            'profile = "custom"\n'
            '[models]\n'
            'strong = "s"\n'
            'balanced = "b"\n'
            'economy = "e"\n'
            '[role_models]\n'
            'model-economy-implementer = "implementation"\n'
            '[reasoning]\n'
            'model-economy-architect = "high"\n'
            'model-economy-final-reviewer = "high"\n'
            'model-economy-implementer = "medium"\n'
            'model-economy-reviewer = "medium"\n'
            'model-economy-explorer = "low"\n'
            'model-economy-batch-worker = "low"\n'
        )
        self.assertEqual(load_config_text(text), self.make_config())

    def test_v1_loads_with_legacy_reasoning_but_new_writes_are_v2(self):
        legacy = (
            'schema_version = 1\n'
            'profile = "custom"\n'
            '[models]\n'
            'strong = "s"\n'
            'balanced = "b"\n'
            'economy = "e"\n'
        )
        config = load_config_text(legacy)
        self.assertEqual(config.schema_version, 1)
        self.assertEqual(config.role_models, {})
        self.assertEqual(config.reasoning["model-economy-implementer"], "high")
        self.assertEqual(config.reasoning["model-economy-explorer"], "medium")
        self.assertIn("schema_version = 2", dump_config(config))

    def test_v2_requires_complete_reasoning_and_rejects_inherited_role_model_override(self):
        partial_reasoning = (
            'schema_version = 2\nprofile = "custom"\n[models]\nstrong = "s"\nbalanced = "b"\neconomy = "e"\n'
            '[reasoning]\nmodel-economy-architect = "high"\n'
        )
        inherited_with_override = (
            'schema_version = 2\nprofile = "inherited"\n[models]\n'
            '[role_models]\nmodel-economy-implementer = "implementation"\n'
            '[reasoning]\n'
            'model-economy-architect = "high"\nmodel-economy-final-reviewer = "high"\n'
            'model-economy-implementer = "medium"\nmodel-economy-reviewer = "medium"\n'
            'model-economy-explorer = "low"\nmodel-economy-batch-worker = "low"\n'
        )
        with self.assertRaises(ConfigError):
            load_config_text(partial_reasoning)
        with self.assertRaises(ConfigError):
            load_config_text(inherited_with_override)

    def test_v2_rejects_unknown_role_models_and_invalid_effort(self):
        common = (
            'schema_version = 2\nprofile = "custom"\n[models]\nstrong = "s"\nbalanced = "b"\neconomy = "e"\n'
            '[reasoning]\nmodel-economy-architect = "high"\nmodel-economy-final-reviewer = "high"\n'
            'model-economy-implementer = "medium"\nmodel-economy-reviewer = "medium"\n'
            'model-economy-explorer = "low"\nmodel-economy-batch-worker = "low"\n'
        )
        with self.assertRaises(ConfigError):
            load_config_text(common + '[role_models]\nunknown = "model"\n')
        with self.assertRaises(ConfigError):
            load_config_text(common.replace('model-economy-explorer = "low"', 'model-economy-explorer = "xhigh"'))

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
                        schema_version=2,
                        profile="custom",
                        models={"strong": value, "balanced": "b", "economy": "e"},
                        role_models={},
                        reasoning=self.make_config().reasoning,
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
