"""Static installation diagnostics and a minimal read-only Codex smoke check."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
from typing import Mapping

from .config import ConfigError, load_config, load_state
from .filesystem import sha256_bytes
from .lifecycle import Context
from .models import ROLES


@dataclass(frozen=True)
class VerificationReport:
    ok: bool
    checks: dict[str, bool]


@dataclass(frozen=True)
class DoctorReport:
    ok: bool
    checks: dict[str, bool]
    codex_available: bool
    model_identity_verified: bool = False


@dataclass(frozen=True)
class SmokeReport:
    subagent_started: bool
    agent_type_verified: bool = False
    model_identity_verified: bool = False


def find_codex(codex_bin: str | None, env: Mapping[str, str] | None = None) -> str | None:
    """Find Codex using the documented explicit-to-implicit precedence."""
    if codex_bin:
        return codex_bin
    environment = os.environ if env is None else env
    return environment.get("CODEX_BIN") or shutil.which("codex")


def _is_executable(executable: str) -> bool:
    """Return whether an executable path or command can be launched."""
    path = Path(executable).expanduser()
    if path.parent != Path("."):
        return path.is_file() and os.access(path, os.X_OK)
    resolved = shutil.which(executable)
    return resolved is not None and os.access(resolved, os.X_OK)


def _codex_environment(context: Context, env: Mapping[str, str] | None) -> dict[str, str]:
    environment = dict(os.environ if env is None else env)
    environment["CODEX_HOME"] = str(context.codex_home)
    return environment


def _directory_is_accessible(codex_home: Path) -> bool:
    candidate = codex_home if codex_home.exists() else codex_home.parent
    return candidate.is_dir() and os.access(candidate, os.R_OK | os.W_OK | os.X_OK)


def _role_models_match(config_models: dict[str, str], role_paths: dict[str, Path]) -> bool:
    expected_capabilities = {role.name: role.capability for role in ROLES}
    try:
        for filename, path in role_paths.items():
            document = tomllib.loads(path.read_text(encoding="utf-8"))
            expected = config_models.get(expected_capabilities[filename.removesuffix(".toml")])
            if expected is None:
                if "model" in document:
                    return False
            elif document.get("model") != expected:
                return False
    except (OSError, tomllib.TOMLDecodeError):
        return False
    return True


def verify_installation(context: Context) -> VerificationReport:
    """Check local files only; this deliberately performs no Codex invocation."""
    checks = {
        "python": sys.version_info >= (3, 11),
        "directory": _directory_is_accessible(context.codex_home),
        "roles": False,
        "role_hashes": False,
        "config_hash": False,
        "model_mapping": False,
        "template_version": False,
    }
    try:
        config = load_config(context.config_path)
        state = load_state(context.state_path)
    except ConfigError:
        return VerificationReport(False, checks)

    role_paths = {f"{role.name}.toml": context.agents_dir / f"{role.name}.toml" for role in ROLES}
    checks["roles"] = all(path.is_file() for path in role_paths.values())
    checks["role_hashes"] = checks["roles"] and set(state.managed_files) == set(role_paths) and all(
        sha256_bytes(path.read_bytes()) == state.managed_files[filename]
        for filename, path in role_paths.items()
    )
    checks["config_hash"] = (
        sha256_bytes(context.config_path.read_bytes()) == state.config_sha256
    )
    checks["model_mapping"] = set(config.models) in (set(), {"strong", "balanced", "economy"}) and (
        _role_models_match(config.models, role_paths)
    )
    checks["template_version"] = state.template_version == context.template_version
    return VerificationReport(all(checks.values()), checks)


def _run_codex_doctor(
    codex_bin: str, context: Context, env: Mapping[str, str] | None = None
) -> bool:
    try:
        completed = subprocess.run(
            [codex_bin, "doctor", "--json"],
            env=_codex_environment(context, env),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if completed.returncode != 0:
        return False
    try:
        document = json.loads(completed.stdout)
    except (TypeError, json.JSONDecodeError):
        return False
    return isinstance(document, dict)


def run_doctor(
    context: Context,
    codex_bin: str | None = None,
    env: Mapping[str, str] | None = None,
) -> DoctorReport:
    """Combine local verification with Codex's supported diagnostic command."""
    local = verify_installation(context)
    executable = find_codex(codex_bin, env)
    codex_available = executable is not None and _is_executable(executable)
    codex_ok = codex_available and _run_codex_doctor(executable, context, env)
    checks = {**local.checks, "codex": codex_ok}
    return DoctorReport(
        ok=all(checks.values()),
        checks=checks,
        codex_available=codex_available,
    )


def _has_completed_subagent_spawn(stdout: str) -> bool:
    spawn_seen = False
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "turn.completed":
            if spawn_seen:
                return True
            continue
        if event.get("type") not in {"item.completed", "item.updated"}:
            continue
        item = event.get("item")
        if not isinstance(item, dict):
            continue
        if item.get("type") != "collab_tool_call":
            continue
        if item.get("tool") != "spawn_agent" or item.get("status") != "completed":
            continue
        receiver_thread_ids = item.get("receiver_thread_ids")
        if not isinstance(receiver_thread_ids, list) or not receiver_thread_ids:
            continue
        agents_states = item.get("agents_states")
        if not isinstance(agents_states, dict) or not any(
            isinstance(agents_states.get(thread_id), dict)
            and agents_states[thread_id].get("status") == "completed"
            for thread_id in receiver_thread_ids
        ):
            continue
        spawn_seen = True
    return False


def run_smoke(
    context: Context,
    codex_bin: str | None = None,
    env: Mapping[str, str] | None = None,
) -> SmokeReport:
    """Ask the root agent to spawn a subagent and inspect structured events only."""
    executable = find_codex(codex_bin, env)
    if executable is None or not _is_executable(executable):
        return SmokeReport(False)
    try:
        completed = subprocess.run(
            [
                executable,
                "exec",
                "--ephemeral",
                "--json",
                "--skip-git-repo-check",
                "-s",
                "read-only",
                "仅进行只读检查。必须使用 spawn_agent 启动一个 subagent；完成后仅回复 SMOKE_SUBAGENT_STARTED。",
            ],
            env=_codex_environment(context, env),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return SmokeReport(False)
    return SmokeReport(
        completed.returncode == 0 and _has_completed_subagent_spawn(completed.stdout)
    )
