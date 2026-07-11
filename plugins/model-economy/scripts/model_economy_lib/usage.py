"""Safe adapter for CodexBar's public cost JSON output."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence


MINIMUM_CODEXBAR_VERSION = (0, 41, 0)
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 20_000


class UsageError(ValueError):
    """Raised when usage data cannot be obtained or trusted."""


@dataclass(frozen=True)
class TokenTotals:
    input: int | None
    output: int | None
    cache_read: int | None
    cache_creation: int | None
    total: int | None


@dataclass(frozen=True)
class ModelTotal:
    name: str
    total_tokens: int | None
    estimated_cost: float | None


@dataclass(frozen=True)
class UsageSummary:
    project: str | None
    range_days: int
    tokens: TokenTotals
    estimated_cost: float | None
    currency: str | None
    models: tuple[ModelTotal, ...]


def _is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def discover_codexbar(
    explicit: Path | None,
    env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    platform: str = sys.platform,
    macos_candidates: Sequence[Path] | None = None,
) -> Path:
    """Resolve a trusted-by-the-user CodexBar CLI location."""
    environment = os.environ if env is None else env
    direct = explicit or (
        Path(environment["CODEXBAR_BIN"]) if environment.get("CODEXBAR_BIN") else None
    )
    if direct is not None:
        candidate = direct.expanduser().resolve()
        if not _is_executable(candidate):
            raise UsageError("CodexBar 路径不存在或不可执行")
        return candidate

    if platform == "win32":
        raise UsageError("未找到 CodexBar；Windows 需要显式指定兼容 CLI")

    for name in ("codexbar", "CodexBarCLI"):
        located = which(name)
        if located:
            candidate = Path(located).expanduser().resolve()
            if _is_executable(candidate):
                return candidate

    if platform == "darwin":
        candidates = macos_candidates
        if candidates is None:
            candidates = (
                Path("/Applications/CodexBar.app/Contents/Helpers/CodexBarCLI"),
                Path.home() / "Applications/CodexBar.app/Contents/Helpers/CodexBarCLI",
            )
        for raw in candidates:
            candidate = raw.expanduser().resolve()
            if _is_executable(candidate):
                return candidate

    raise UsageError("未找到 CodexBar；请安装或使用 --codexbar-bin")


def _stop_process(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _run_process(command: Sequence[str], timeout_seconds: int) -> str:
    """Run one direct child while bounding stdout on disk and in memory."""
    started = time.monotonic()
    with tempfile.TemporaryFile() as stdout:
        try:
            process = subprocess.Popen(
                list(command),
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=subprocess.DEVNULL,
                shell=False,
            )
        except OSError as exc:
            raise UsageError("CodexBar 无法启动") from exc

        try:
            while process.poll() is None:
                if os.fstat(stdout.fileno()).st_size > MAX_OUTPUT_BYTES:
                    _stop_process(process)
                    raise UsageError("CodexBar 输出超过安全上限")
                if time.monotonic() - started > timeout_seconds:
                    _stop_process(process)
                    raise UsageError("CodexBar 执行超时")
                time.sleep(0.02)
            if process.returncode != 0:
                raise UsageError("CodexBar 执行失败")
            size = os.fstat(stdout.fileno()).st_size
            if size > MAX_OUTPUT_BYTES:
                raise UsageError("CodexBar 输出超过安全上限")
            stdout.seek(0)
            return stdout.read(MAX_OUTPUT_BYTES + 1).decode("utf-8", errors="replace")
        finally:
            _stop_process(process)


def check_codexbar_version(binary: Path) -> tuple[int, ...]:
    raw = _run_process([str(binary), "--version"], timeout_seconds=10)
    match = re.search(r"\bCodexBar\s+(\d+)\.(\d+)\.(\d+)\b", raw)
    if match is None:
        raise UsageError("无法识别 CodexBar 版本")
    version = tuple(int(part) for part in match.groups())
    if version < MINIMUM_CODEXBAR_VERSION:
        raise UsageError("CodexBar 版本过低；需要 0.41.0 或更高版本")
    return version


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise UsageError("CodexBar JSON 包含重复字段")
        result[key] = value
    return result


def _validate_tree(value: Any, depth: int = 0, nodes: list[int] | None = None) -> None:
    if nodes is None:
        nodes = [0]
    nodes[0] += 1
    if nodes[0] > MAX_JSON_NODES:
        raise UsageError("CodexBar JSON 记录过多")
    if depth > MAX_JSON_DEPTH:
        raise UsageError("CodexBar JSON 嵌套过深")
    if isinstance(value, dict):
        for child in value.values():
            _validate_tree(child, depth + 1, nodes)
    elif isinstance(value, list):
        for child in value:
            _validate_tree(child, depth + 1, nodes)


def fetch_usage(binary: Path, days: int, timeout_seconds: int = 30) -> object:
    if not 1 <= days <= 365:
        raise UsageError("天数必须在 1 到 365 之间")
    command = [
        str(binary),
        "cost",
        "--provider",
        "codex",
        "--format",
        "json",
        "--days",
        str(days),
        "--group-by",
        "project",
    ]
    raw = _run_process(command, timeout_seconds=timeout_seconds)
    if len(raw.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise UsageError("CodexBar 输出超过安全上限")
    try:
        payload = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except UsageError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise UsageError("CodexBar 返回了无效 JSON") from exc
    _validate_tree(payload)
    return payload


def _provider(payload: object) -> dict[str, Any]:
    candidates = payload if isinstance(payload, list) else [payload]
    matches = [
        item
        for item in candidates
        if isinstance(item, dict) and item.get("provider") == "codex"
    ]
    if len(matches) != 1:
        raise UsageError("CodexBar 返回的 Codex provider 不唯一")
    return matches[0]


def _nonnegative_int(value: object) -> int | None:
    if type(value) is not int or value < 0:
        return None
    return value


def _nonnegative_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    if result < 0 or not math.isfinite(result):
        return None
    return result


def _complete_sum(entries: Sequence[dict[str, Any]], key: str, number: str) -> int | float | None:
    parsed: list[int | float] = []
    converter = _nonnegative_int if number == "int" else _nonnegative_float
    for entry in entries:
        value = converter(entry.get(key))
        if value is None:
            return None
        parsed.append(value)
    return sum(parsed) if parsed else None


def _daily_entries(
    provider: dict[str, Any], project: Path | None
) -> tuple[str | None, list[dict[str, Any]], list[dict[str, Any]] | None]:
    if project is None:
        daily = provider.get("daily")
        if not isinstance(daily, list) or not all(isinstance(item, dict) for item in daily):
            raise UsageError("CodexBar 缺少日用量数据")
        return None, daily, None

    wanted = project.expanduser().resolve()
    projects = provider.get("projects")
    if not isinstance(projects, list):
        raise UsageError("CodexBar 缺少项目用量数据")
    matches: list[dict[str, Any]] = []
    for item in projects:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            continue
        try:
            candidate = Path(item["path"]).expanduser().resolve()
        except (OSError, ValueError):
            continue
        if candidate == wanted:
            matches.append(item)
    if len(matches) != 1:
        raise UsageError("未找到项目用量或项目结果不唯一")
    daily = matches[0].get("daily")
    if not isinstance(daily, list) or not all(isinstance(item, dict) for item in daily):
        raise UsageError("CodexBar 缺少项目日用量数据")
    project_models = matches[0].get("modelBreakdowns")
    if project_models is not None and (
        not isinstance(project_models, list)
        or not all(isinstance(item, dict) for item in project_models)
    ):
        raise UsageError("CodexBar 项目模型明细格式无效")
    return wanted.name, daily, project_models


def _model_totals(
    entries: Sequence[dict[str, Any]],
    explicit_breakdowns: list[dict[str, Any]] | None,
    costs_available: bool,
) -> tuple[ModelTotal, ...]:
    totals: dict[str, dict[str, int | float | None]] = {}
    if explicit_breakdowns is None:
        if any(not isinstance(entry.get("modelBreakdowns"), list) for entry in entries):
            return ()
        breakdown_groups = [entry["modelBreakdowns"] for entry in entries]
    else:
        breakdown_groups = [explicit_breakdowns]

    for breakdowns in breakdown_groups:
        for breakdown in breakdowns:
            if not isinstance(breakdown, dict):
                raise UsageError("CodexBar 模型明细格式无效")
            name = breakdown.get("modelName")
            if not isinstance(name, str) or not name.strip():
                raise UsageError("CodexBar 模型名称无效")
            current = totals.setdefault(name, {"tokens": 0, "cost": 0.0})
            tokens = _nonnegative_int(breakdown.get("totalTokens"))
            cost = _nonnegative_float(breakdown.get("cost")) if costs_available else None
            current["tokens"] = (
                None if tokens is None or current["tokens"] is None else int(current["tokens"]) + tokens
            )
            current["cost"] = (
                None if cost is None or current["cost"] is None else float(current["cost"]) + cost
            )
    result = [
        ModelTotal(name, values["tokens"], values["cost"])
        for name, values in totals.items()
    ]
    return tuple(
        sorted(
            result,
            key=lambda item: (
                -(item.estimated_cost if item.estimated_cost is not None else -1),
                item.name,
            ),
        )
    )


def summarize_usage(
    payload: object,
    project: Path | None = None,
    days: int = 30,
) -> UsageSummary:
    provider = _provider(payload)
    if _nonnegative_int(provider.get("historyDays")) != days:
        raise UsageError("CodexBar 返回的时间范围与请求不一致")
    public_project, entries, project_models = _daily_entries(provider, project)
    currency_raw = provider.get("currencyCode")
    currency = currency_raw.strip().upper() if isinstance(currency_raw, str) else None
    if not currency:
        currency = None
    cost = _complete_sum(entries, "totalCost", "float") if currency else None
    return UsageSummary(
        project=public_project,
        range_days=days,
        tokens=TokenTotals(
            input=_complete_sum(entries, "inputTokens", "int"),
            output=_complete_sum(entries, "outputTokens", "int"),
            cache_read=_complete_sum(entries, "cacheReadTokens", "int"),
            cache_creation=_complete_sum(entries, "cacheCreationTokens", "int"),
            total=_complete_sum(entries, "totalTokens", "int"),
        ),
        estimated_cost=cost,
        currency=currency,
        models=_model_totals(entries, project_models, costs_available=currency is not None),
    )


def usage_to_dict(summary: UsageSummary) -> dict[str, Any]:
    return {
        "usage_schema_version": 1,
        "source": "codexbar",
        "cost_is_estimate": True,
        "project": summary.project,
        "range_days": summary.range_days,
        "tokens": {
            "input": summary.tokens.input,
            "output": summary.tokens.output,
            "cache_read": summary.tokens.cache_read,
            "cache_creation": summary.tokens.cache_creation,
            "total": summary.tokens.total,
        },
        "estimated_cost": {
            "amount": summary.estimated_cost,
            "currency": summary.currency,
        },
        "models": [
            {
                "name": model.name,
                "total_tokens": model.total_tokens,
                "estimated_cost": model.estimated_cost,
            }
            for model in summary.models
        ],
        "role_attribution": {
            "available": False,
            "reason": "Codex telemetry does not expose verified Model Economy role identity",
        },
    }
