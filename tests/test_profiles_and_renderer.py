import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "model-economy" / "scripts"
PROFILES = ROOT / "plugins" / "model-economy" / "assets" / "profiles"
sys.path.insert(0, str(SCRIPTS))

from model_economy_lib.profiles import load_profile
from model_economy_lib.models import Profile, ROLES
from model_economy_lib.renderer import render_agent, render_all_agents


class RendererTests(unittest.TestCase):
    def test_openai_profile_maps_three_capabilities(self):
        profile = load_profile(PROFILES / "openai-56.toml")
        self.assertEqual(profile.models["strong"], "gpt-5.6-sol")
        self.assertEqual(profile.models["balanced"], "gpt-5.6-terra")
        self.assertEqual(profile.models["economy"], "gpt-5.6-luna")

    def test_inherited_profile_omits_model(self):
        profile = load_profile(PROFILES / "inherited.toml")
        rendered = render_all_agents(profile)["model-economy-architect.toml"]
        self.assertNotIn("\nmodel =", rendered)
        self.assertIn('sandbox_mode = "read-only"', rendered)

    def test_strong_roles_are_read_only(self):
        rendered = render_all_agents(load_profile(PROFILES / "openai-56.toml"))
        for name in ("model-economy-architect.toml", "model-economy-final-reviewer.toml"):
            self.assertIn('sandbox_mode = "read-only"', rendered[name])
            self.assertIn('model = "gpt-5.6-sol"', rendered[name])

    def test_render_agent_rejects_strong_role_with_writable_sandbox(self):
        role = next(role for role in ROLES if role.capability == "strong")
        invalid_role = role.__class__(
            name=role.name,
            capability="strong",
            reasoning_effort=role.reasoning_effort,
            sandbox_mode="workspace-write",
            description=role.description,
            developer_instructions=role.developer_instructions,
        )
        with self.assertRaises(ValueError):
            render_agent(invalid_role, load_profile(PROFILES / "openai-56.toml"))

    def test_render_all_agents_has_exactly_six_roles_and_limits(self):
        expected_names = {
            "model-economy-architect.toml",
            "model-economy-final-reviewer.toml",
            "model-economy-implementer.toml",
            "model-economy-reviewer.toml",
            "model-economy-explorer.toml",
            "model-economy-batch-worker.toml",
        }
        rendered = render_all_agents(load_profile(PROFILES / "openai-56.toml"))
        self.assertEqual(set(rendered), expected_names)
        self.assertEqual(len(rendered), 6)
        for name, contents in rendered.items():
            with self.subTest(name=name):
                document = tomllib.loads(contents)
                self.assertEqual(document["agents"]["max_threads"], 3)
                self.assertEqual(document["agents"]["max_depth"], 1)

    def test_both_profiles_render_twelve_parseable_outputs_and_inherited_has_no_model(self):
        for profile_name in ("openai-56.toml", "inherited.toml"):
            with self.subTest(profile_name=profile_name):
                rendered = render_all_agents(load_profile(PROFILES / profile_name))
                self.assertEqual(len(rendered), 6)
                for role_name, contents in rendered.items():
                    with self.subTest(role_name=role_name):
                        document = tomllib.loads(contents)
                        if profile_name == "inherited.toml":
                            self.assertNotIn("model", document)

    def test_special_model_strings_round_trip_without_placeholders(self):
        special_models = {
            "strong": 'model "strong" \\ path\nnext',
            "balanced": "balanced\tvalue",
            "economy": "经济模型",
        }
        profile = Profile(name="special", inherit_model=False, models=special_models)
        for role_name, contents in render_all_agents(profile).items():
            with self.subTest(role_name=role_name):
                document = tomllib.loads(contents)
                self.assertEqual(document["model"], special_models[next(
                    role.capability for role in ROLES if f"{role.name}.toml" == role_name
                )])
                self.assertNotIn("{{", contents)
                self.assertNotIn("}}", contents)

    def test_profile_rejects_invalid_model_configurations(self):
        invalid_profiles = (
            'name = "unknown"\ninherit_model = false\n[models]\nstrong = "a"\nbalanced = "b"\neconomy = "c"\nother = "d"\n',
            'name = "empty"\ninherit_model = false\n[models]\nstrong = ""\nbalanced = "b"\neconomy = "c"\n',
            'name = "inherited"\ninherit_model = true\n[models]\nstrong = "a"\n',
            'name = "incomplete"\ninherit_model = false\n[models]\nstrong = "a"\nbalanced = "b"\n',
        )
        for contents in invalid_profiles:
            with self.subTest(contents=contents), tempfile.NamedTemporaryFile(mode="w", suffix=".toml") as handle:
                handle.write(contents)
                handle.flush()
                with self.assertRaises(ValueError):
                    load_profile(Path(handle.name))


if __name__ == "__main__":
    unittest.main()
