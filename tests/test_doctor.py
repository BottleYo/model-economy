import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "model-economy" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from model_economy_lib.doctor import (  # noqa: E402
    find_codex,
    run_doctor,
    run_smoke,
    verify_installation,
)
from model_economy_lib.lifecycle import Context, install  # noqa: E402
from model_economy_lib.models import Profile  # noqa: E402
from model_economy_lib.profiles import load_profile  # noqa: E402


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.home = Path(self.temporary_directory.name) / "codex-home"
        self.plugin_root = ROOT / "plugins" / "model-economy"
        self.context = Context(self.home, self.plugin_root, "0.1.0")
        install(self.context, load_profile(self.plugin_root / "assets" / "profiles" / "inherited.toml"))

    def test_find_codex_prefers_argument_then_environment_then_path(self):
        with patch("model_economy_lib.doctor.shutil.which", return_value="path-codex"):
            self.assertEqual(find_codex("argument-codex", {"CODEX_BIN": "environment-codex"}), "argument-codex")
            self.assertEqual(find_codex(None, {"CODEX_BIN": "environment-codex"}), "environment-codex")
            self.assertEqual(find_codex(None, {}), "path-codex")

    def test_doctor_reports_missing_codex_as_environment_failure(self):
        with patch("model_economy_lib.doctor.find_codex", return_value=None):
            report = run_doctor(self.context)
        self.assertFalse(report.ok)
        self.assertFalse(report.codex_available)
        self.assertFalse(report.model_identity_verified)

    def test_doctor_runs_bounded_version_check_with_explicit_home(self):
        completed = CompletedProcess(["codex"], 0, stdout="codex-cli 0.144.6\n", stderr="")
        with patch("model_economy_lib.doctor.find_codex", return_value="codex"), patch(
            "model_economy_lib.doctor._is_executable", return_value=True
        ), patch(
            "model_economy_lib.doctor.subprocess.run", return_value=completed
        ) as run:
            report = run_doctor(self.context)
        self.assertTrue(report.ok)
        self.assertEqual(run.call_args.args[0], ["codex", "--version"])
        self.assertEqual(run.call_args.kwargs["env"]["CODEX_HOME"], str(self.home))
        self.assertEqual(run.call_args.kwargs["timeout"], 10)

    def test_doctor_rejects_empty_or_unrelated_version_output(self):
        for output in ("", "0.144.6", "another-cli 0.144.6"):
            completed = CompletedProcess(["codex"], 0, stdout=output, stderr="")
            with self.subTest(output=output), patch(
                "model_economy_lib.doctor.find_codex", return_value="codex"
            ), patch("model_economy_lib.doctor._is_executable", return_value=True), patch(
                "model_economy_lib.doctor.subprocess.run", return_value=completed
            ):
                report = run_doctor(self.context)
            self.assertFalse(report.checks["codex"])

    def test_doctor_does_not_mark_an_unexecutable_path_available(self):
        with patch("model_economy_lib.doctor.find_codex", return_value="/missing/codex"):
            report = run_doctor(self.context)
        self.assertFalse(report.codex_available)
        self.assertFalse(report.checks["codex"])

    def test_verification_rejects_a_role_that_no_longer_matches_state(self):
        role = self.home / "agents" / "model-economy-explorer.toml"
        role.write_text(role.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
        with patch("model_economy_lib.doctor.find_codex", return_value=None):
            report = run_doctor(self.context)
        self.assertFalse(report.ok)
        self.assertFalse(report.checks["role_hashes"])

    def test_verification_rejects_installed_template_version_drift(self):
        newer_context = Context(self.home, self.plugin_root, "0.2.0")

        report = verify_installation(newer_context)

        self.assertFalse(report.ok)
        self.assertFalse(report.checks["template_version"])

    def test_verification_rejects_symlinked_artifact_before_loading_it(self):
        outside = Path(self.temporary_directory.name) / "outside-config.toml"
        outside.write_text('schema_version = 1\nprofile = "outside"\n', encoding="utf-8")
        self.context.config_path.unlink()
        try:
            self.context.config_path.symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"symlinks are unavailable: {exc}")

        with patch(
            "model_economy_lib.doctor.load_config",
            side_effect=AssertionError("unsafe artifact must not be loaded"),
        ):
            report = verify_installation(self.context)

        self.assertFalse(report.ok)
        self.assertFalse(report.checks["artifact_safety"])

    def test_verification_checks_rendered_role_models_against_config_mapping(self):
        install(
            self.context,
            Profile(
                "custom",
                False,
                {"strong": "strong", "balanced": "balanced", "economy": "economy"},
            ),
        )
        role = self.home / "agents" / "model-economy-explorer.toml"
        role.write_text(
            role.read_text(encoding="utf-8").replace('model = "economy"', 'model = "wrong"'),
            encoding="utf-8",
        )
        with patch("model_economy_lib.doctor.find_codex", return_value=None):
            report = run_doctor(self.context)
        self.assertFalse(report.checks["model_mapping"])

    def test_doctor_reports_a_codex_timeout_as_failure(self):
        with patch("model_economy_lib.doctor.find_codex", return_value="codex"), patch(
            "model_economy_lib.doctor.subprocess.run",
            side_effect=TimeoutExpired(["codex", "--version"], 10),
        ):
            report = run_doctor(self.context)
        self.assertFalse(report.ok)
        self.assertFalse(report.checks["codex"])

    def test_smoke_accepts_completed_spawn_event_and_requires_turn_completion(self):
        completed = CompletedProcess(
            ["codex"],
            0,
            stdout=(
                '{"type":"thread.started"}\n'
                '{"type":"item.completed","item":{"type":"collab_tool_call",'
                '"tool":"spawn_agent","status":"completed",'
                '"receiver_thread_ids":["thread-1"],'
                '"agents_states":{"thread-1":{"status":"completed","message":"done"}}}}\n'
                '{"type":"item.updated","item":{"type":"collab_tool_call",'
                '"tool":"spawn_agent","status":"completed",'
                '"receiver_thread_ids":["thread-2"],'
                '"agents_states":{"thread-2":{"status":"completed","message":"done"}}}}\n'
                '{"type":"turn.completed","assistant":"I used gpt-fake"}\n'
            ),
            stderr="",
        )
        with patch("model_economy_lib.doctor.find_codex", return_value="codex"), patch(
            "model_economy_lib.doctor._is_executable", return_value=True
        ), patch(
            "model_economy_lib.doctor.subprocess.run", return_value=completed
        ) as run:
            report = run_smoke(self.context)
        self.assertTrue(report.subagent_started)
        self.assertFalse(report.agent_type_verified)
        self.assertFalse(report.model_identity_verified)
        self.assertIn("--ephemeral", run.call_args.args[0])
        self.assertIn("--json", run.call_args.args[0])
        self.assertIn("--skip-git-repo-check", run.call_args.args[0])
        self.assertEqual(run.call_args.args[0][run.call_args.args[0].index("-s") + 1], "read-only")
        self.assertNotIn("--agent", run.call_args.args[0])

    def test_smoke_rejects_turn_completion_and_assistant_role_claim_without_spawn_event(self):
        completed = CompletedProcess(
            ["codex"],
            0,
            stdout='{"type":"turn.completed","message":"spawned model-economy-explorer"}\n',
            stderr="",
        )
        with patch("model_economy_lib.doctor.find_codex", return_value="codex"), patch(
            "model_economy_lib.doctor._is_executable", return_value=True
        ), patch(
            "model_economy_lib.doctor.subprocess.run", return_value=completed
        ):
            report = run_smoke(self.context)
        self.assertFalse(report.subagent_started)
        self.assertFalse(report.agent_type_verified)
        self.assertFalse(report.model_identity_verified)

    def test_smoke_rejects_missing_turn_completion(self):
        stdout = (
            '{"type":"item.updated","item":{"type":"collab_tool_call",'
            '"tool":"spawn_agent","status":"completed",'
            '"receiver_thread_ids":["thread-1"],'
            '"agents_states":{"thread-1":{"status":"completed","message":"done"}}}}\n'
        )
        completed = CompletedProcess(["codex"], 0, stdout=stdout, stderr="")
        with patch("model_economy_lib.doctor.find_codex", return_value="codex"), patch(
            "model_economy_lib.doctor._is_executable", return_value=True
        ), patch("model_economy_lib.doctor.subprocess.run", return_value=completed):
            report = run_smoke(self.context)
        self.assertFalse(report.subagent_started)

    def test_smoke_rejects_non_schema_spawn_events(self):
        outputs = (
            '{"type":"item.completed","item":{"type":"collab_tool_call",'
            '"tool":"spawn_agent","status":"running",'
            '"receiver_thread_ids":["thread-1"],'
            '"agents_states":{"thread-1":{"status":"completed","message":"done"}}}}\n'
            '{"type":"turn.completed"}\n',
            '{"type":"item.completed","item":{"type":"collab_tool_call",'
            '"tool":"spawn_backup","status":"completed",'
            '"receiver_thread_ids":["thread-1"],'
            '"agents_states":{"thread-1":{"status":"completed","message":"done"}}}}\n'
            '{"type":"turn.completed"}\n',
            '{"type":"item.completed","item":{"type":"collab_tool_call",'
            '"tool":"spawn_agent","status":"completed",'
            '"receiver_thread_ids":[],"agents_states":{}}}\n'
            '{"type":"turn.completed"}\n',
            '{"type":"item.completed","item":{"type":"collab_tool_call",'
            '"tool":"spawn_agent","status":"completed",'
            '"receiver_thread_ids":["thread-1"],'
            '"agents_states":{"thread-1":{"status":"running","message":"working"}}}}\n'
            '{"type":"turn.completed"}\n',
        )
        for stdout in outputs:
            completed = CompletedProcess(["codex"], 0, stdout=stdout, stderr="")
            with self.subTest(stdout=stdout), patch(
                "model_economy_lib.doctor.find_codex", return_value="codex"
            ), patch("model_economy_lib.doctor._is_executable", return_value=True), patch(
                "model_economy_lib.doctor.subprocess.run", return_value=completed
            ):
                report = run_smoke(self.context)
            self.assertFalse(report.subagent_started)

    def test_smoke_rejects_completed_state_for_an_unrelated_thread(self):
        stdout = (
            '{"type":"item.completed","item":{"type":"collab_tool_call",'
            '"tool":"spawn_agent","status":"completed",'
            '"receiver_thread_ids":["receiver-thread"],'
            '"agents_states":{'
            '"receiver-thread":{"status":"running","message":"working"},'
            '"other-thread":{"status":"completed","message":"done"}}}}\n'
            '{"type":"turn.completed"}\n'
        )
        completed = CompletedProcess(["codex"], 0, stdout=stdout, stderr="")
        with patch("model_economy_lib.doctor.find_codex", return_value="codex"), patch(
            "model_economy_lib.doctor._is_executable", return_value=True
        ), patch("model_economy_lib.doctor.subprocess.run", return_value=completed):
            report = run_smoke(self.context)
        self.assertFalse(report.subagent_started)

    def test_smoke_rejects_turn_completion_before_a_qualifying_spawn(self):
        stdout = (
            '{"type":"turn.completed"}\n'
            '{"type":"item.completed","item":{"type":"collab_tool_call",'
            '"tool":"spawn_agent","status":"completed",'
            '"receiver_thread_ids":["thread-1"],'
            '"agents_states":{"thread-1":{"status":"completed","message":"done"}}}}\n'
        )
        completed = CompletedProcess(["codex"], 0, stdout=stdout, stderr="")
        with patch("model_economy_lib.doctor.find_codex", return_value="codex"), patch(
            "model_economy_lib.doctor._is_executable", return_value=True
        ), patch("model_economy_lib.doctor.subprocess.run", return_value=completed):
            report = run_smoke(self.context)
        self.assertFalse(report.subagent_started)

    def test_smoke_command_options_are_supported_by_current_codex_when_available(self):
        executable = os.environ.get("CODEX_BIN") or shutil.which("codex")
        if executable is None:
            self.skipTest("CODEX_BIN and codex are unavailable")
        try:
            completed = subprocess.run(
                [executable, "exec", "--help"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.skipTest(f"Codex is unavailable: {exc}")
        if completed.returncode != 0:
            self.skipTest("Codex exec --help is unavailable")
        for option in ("--ephemeral", "--json", "--skip-git-repo-check", "-s, --sandbox"):
            self.assertIn(option, completed.stdout)

    def test_doctor_source_never_scans_session_or_database_artifacts(self):
        source = (SCRIPTS / "model_economy_lib" / "doctor.py").read_text(encoding="utf-8").lower()
        self.assertNotIn('[codex_bin, "doctor", "--json"]', source)
        self.assertNotIn("auth.json", source)
        self.assertNotIn("history.jsonl", source)
        self.assertNotIn("sqlite", source)
        self.assertNotIn("rollout", source)


if __name__ == "__main__":
    unittest.main()
