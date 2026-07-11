import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "model-economy" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from model_economy_lib.usage import (  # noqa: E402
    UsageError,
    _run_process,
    check_codexbar_version,
    discover_codexbar,
    fetch_usage,
    summarize_usage,
    usage_to_dict,
)


def fixture_payload(project_path: Path) -> list[dict[str, object]]:
    return [
        {
            "provider": "codex",
            "historyDays": 7,
            "currencyCode": "USD",
            "account": "must-not-leak",
            "unknown": "must-not-leak",
            "daily": [
                {
                    "date": "2026-07-10",
                    "inputTokens": 100,
                    "outputTokens": 10,
                    "cacheReadTokens": 40,
                    "totalTokens": 110,
                    "totalCost": 1.25,
                    "modelBreakdowns": [
                        {"modelName": "strong-model", "totalTokens": 80, "cost": 1.0}
                    ],
                },
                {
                    "date": "2026-07-11",
                    "inputTokens": 200,
                    "outputTokens": 20,
                    "cacheReadTokens": 60,
                    "totalTokens": 220,
                    "totalCost": 2.5,
                    "modelBreakdowns": [
                        {"modelName": "strong-model", "totalTokens": 120, "cost": 2.0},
                        {"modelName": "efficient-model", "totalTokens": 100, "cost": 0.5},
                    ],
                },
            ],
            "projects": [
                {
                    "name": "/private/upstream-name-must-not-leak",
                    "path": str(project_path),
                    "modelBreakdowns": [
                        {
                            "modelName": "efficient-model",
                            "totalTokens": 55,
                            "cost": 0.75,
                        }
                    ],
                    "daily": [
                        {
                            "date": "2026-07-11",
                            "inputTokens": 50,
                            "outputTokens": 5,
                            "cacheReadTokens": 20,
                            "totalTokens": 55,
                            "totalCost": 0.75,
                        }
                    ],
                },
                {
                    "name": "other-project",
                    "path": "/private/must-not-leak",
                    "daily": [],
                },
            ],
        }
    ]


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)

    def executable(self, name: str) -> Path:
        path = self.root / name
        path.write_text("placeholder", encoding="utf-8")
        path.chmod(0o700)
        return path

    def test_discovery_prefers_explicit_then_environment_then_path(self):
        explicit = self.executable("explicit")
        environment = self.executable("environment")
        path_binary = self.executable("path-binary")

        result = discover_codexbar(
            explicit=explicit,
            env={"CODEXBAR_BIN": str(environment)},
            which=lambda name: str(path_binary) if name == "codexbar" else None,
            platform="darwin",
            macos_candidates=(),
        )

        self.assertEqual(result, explicit.resolve())

    def test_discovery_uses_environment_path_and_macos_helper_in_order(self):
        environment = self.executable("environment")
        helper = self.executable("CodexBarCLI")

        self.assertEqual(
            discover_codexbar(
                explicit=None,
                env={"CODEXBAR_BIN": str(environment)},
                which=lambda _name: None,
                platform="darwin",
                macos_candidates=(helper,),
            ),
            environment.resolve(),
        )
        self.assertEqual(
            discover_codexbar(
                explicit=None,
                env={},
                which=lambda _name: None,
                platform="darwin",
                macos_candidates=(helper,),
            ),
            helper.resolve(),
        )

    def test_windows_requires_an_explicit_or_environment_binary(self):
        path_binary = self.executable("codexbar")

        with self.assertRaisesRegex(UsageError, "未找到 CodexBar"):
            discover_codexbar(
                explicit=None,
                env={},
                which=lambda _name: str(path_binary),
                platform="win32",
                macos_candidates=(),
            )

    def test_discovery_rejects_missing_or_unexecutable_paths(self):
        missing = self.root / "missing"
        unexecutable = self.root / "unexecutable"
        unexecutable.write_text("x", encoding="utf-8")
        unexecutable.chmod(0o600)

        for candidate in (missing, unexecutable):
            with self.subTest(candidate=candidate), self.assertRaises(UsageError):
                discover_codexbar(
                    explicit=candidate,
                    env={},
                    which=lambda _name: None,
                    platform="linux",
                    macos_candidates=(),
                )

    def test_version_requires_codexbar_041_or_newer(self):
        binary = self.executable("codexbar")

        with patch(
            "model_economy_lib.usage._run_process", return_value="CodexBar 0.41.0\n"
        ) as run:
            self.assertEqual(check_codexbar_version(binary), (0, 41, 0))
        run.assert_called_once_with([str(binary), "--version"], timeout_seconds=10)

        with patch(
            "model_economy_lib.usage._run_process", return_value="CodexBar 0.40.9\n"
        ), self.assertRaisesRegex(UsageError, "0.41.0"):
            check_codexbar_version(binary)

    def test_fetch_usage_passes_calendar_window_and_project_grouping(self):
        binary = self.executable("codexbar")
        raw = json.dumps(fixture_payload(self.root / "example-project"))

        with patch("model_economy_lib.usage._run_process", return_value=raw) as run:
            payload = fetch_usage(binary, days=7)

        self.assertIsInstance(payload, list)
        run.assert_called_once_with(
            [
                str(binary),
                "cost",
                "--provider",
                "codex",
                "--format",
                "json",
                "--days",
                "7",
                "--group-by",
                "project",
            ],
            timeout_seconds=30,
        )

    def test_fetch_usage_rejects_duplicate_keys_depth_and_record_limits(self):
        binary = self.executable("codexbar")
        deeply_nested: dict[str, object] = {}
        cursor = deeply_nested
        for _index in range(34):
            child: dict[str, object] = {}
            cursor["child"] = child
            cursor = child
        samples = (
            '[{"provider":"codex","provider":"codex"}]',
            json.dumps(deeply_nested),
            json.dumps([{}] * 20_001),
        )

        for raw in samples:
            with self.subTest(size=len(raw)), patch(
                "model_economy_lib.usage._run_process", return_value=raw
            ), self.assertRaises(UsageError):
                fetch_usage(binary, days=7)

    def test_summarize_provider_totals_and_models(self):
        project = self.root / "example-project"
        summary = summarize_usage(fixture_payload(project), days=7)

        self.assertIsNone(summary.project)
        self.assertEqual(summary.range_days, 7)
        self.assertEqual(summary.tokens.input, 300)
        self.assertEqual(summary.tokens.output, 30)
        self.assertEqual(summary.tokens.cache_read, 100)
        self.assertIsNone(summary.tokens.cache_creation)
        self.assertEqual(summary.tokens.total, 330)
        self.assertEqual(summary.estimated_cost, 3.75)
        self.assertEqual(summary.currency, "USD")
        self.assertEqual(
            [(model.name, model.total_tokens, model.estimated_cost) for model in summary.models],
            [
                ("strong-model", 200, 3.0),
                ("efficient-model", 100, 0.5),
            ],
        )

    def test_summarize_project_hides_absolute_path(self):
        project = self.root / "example-project"
        summary = summarize_usage(fixture_payload(project), project=project, days=7)
        public = usage_to_dict(summary)
        encoded = json.dumps(public, ensure_ascii=False)

        self.assertEqual(summary.project, "example-project")
        self.assertEqual(summary.tokens.total, 55)
        self.assertEqual(
            [(model.name, model.total_tokens, model.estimated_cost) for model in summary.models],
            [("efficient-model", 55, 0.75)],
        )
        self.assertEqual(public["usage_schema_version"], 1)
        self.assertNotIn(str(self.root), encoded)
        self.assertNotIn("must-not-leak", encoded)
        self.assertFalse(public["role_attribution"]["available"])

    def test_missing_metric_in_any_daily_row_makes_aggregate_unavailable(self):
        project = self.root / "example-project"
        payload = fixture_payload(project)
        del payload[0]["daily"][1]["cacheReadTokens"]

        summary = summarize_usage(payload, days=7)

        self.assertIsNone(summary.tokens.cache_read)
        self.assertEqual(summary.tokens.total, 330)

    def test_missing_daily_model_breakdown_does_not_publish_partial_models(self):
        payload = fixture_payload(self.root / "example-project")
        del payload[0]["daily"][1]["modelBreakdowns"]

        summary = summarize_usage(payload, days=7)

        self.assertEqual(summary.models, ())

    def test_missing_currency_hides_all_costs(self):
        payload = fixture_payload(self.root / "example-project")
        del payload[0]["currencyCode"]

        summary = summarize_usage(payload, days=7)

        self.assertIsNone(summary.estimated_cost)
        self.assertTrue(summary.models)
        self.assertTrue(all(model.estimated_cost is None for model in summary.models))

    def test_history_window_must_match_requested_days(self):
        payload = fixture_payload(self.root / "example-project")

        with self.assertRaisesRegex(UsageError, "时间范围"):
            summarize_usage(payload, days=30)

    def test_invalid_project_does_not_expose_candidate_paths(self):
        payload = fixture_payload(self.root / "example-project")

        with self.assertRaisesRegex(UsageError, "未找到项目") as caught:
            summarize_usage(payload, project=self.root / "missing", days=7)

        self.assertNotIn(str(self.root), str(caught.exception))

    def test_process_errors_are_fixed_and_do_not_include_sensitive_output(self):
        binary = self.executable("codexbar")
        with patch(
            "model_economy_lib.usage._run_process",
            side_effect=UsageError("CodexBar 执行失败"),
        ), self.assertRaisesRegex(UsageError, "CodexBar 执行失败") as caught:
            fetch_usage(binary, days=7)

        self.assertNotIn(str(self.root), str(caught.exception))

    def test_process_runner_enforces_output_and_timeout_bounds(self):
        with patch("model_economy_lib.usage.MAX_OUTPUT_BYTES", 32), self.assertRaisesRegex(
            UsageError, "安全上限"
        ):
            _run_process(
                [sys.executable, "-c", "import sys; sys.stdout.write('x' * 64)"],
                timeout_seconds=5,
            )

        with self.assertRaisesRegex(UsageError, "超时"):
            _run_process(
                [sys.executable, "-c", "import time; time.sleep(2)"],
                timeout_seconds=0,
            )


if __name__ == "__main__":
    unittest.main()
