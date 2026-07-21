"""Static installation diagnostics and a minimal read-only Codex smoke check."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import stat
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


@dataclass(frozen=True)
class StatusReport:
    """Read-only summary of the optional six-role enhancement."""

    plugin_version: str
    mode: str
    enhancement_state: str
    role_files_expected: int
    role_files_present: int
    role_hashes_match: bool | None
    model_mapping_status: str
    installed_template_version: str | None
    template_current: bool | None
    exit_code: int


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


def _status_artifact_exists(path: Path) -> bool:
    """Treat even a broken symlink as an enhancement trace without following it."""
    return path.exists() or path.is_symlink()


def _status_artifact_is_safe(path: Path, codex_home: Path) -> bool:
    """Allow status to read only regular, singly linked managed artifacts."""
    if path != codex_home and codex_home not in path.parents:
        return False
    current = path
    while True:
        if current.is_symlink():
            return False
        if current == codex_home:
            break
        current = current.parent
    try:
        metadata = path.stat()
    except OSError:
        return False
    return stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1


def status_to_dict(report: StatusReport) -> dict[str, object]:
    """Return the stable public status schema."""
    return {
        "status_schema_version": 1,
        "plugin_version": report.plugin_version,
        "mode": report.mode,
        "enhancement": {
            "state": report.enhancement_state,
            "role_files": {
                "expected": report.role_files_expected,
                "present": report.role_files_present,
                "hashes_match": report.role_hashes_match,
            },
            "model_mapping": {"status": report.model_mapping_status},
            "template_version": {
                "bundled": report.plugin_version,
                "installed": report.installed_template_version,
                "current": report.template_current,
            },
        },
        "identity_verification": {"role": False, "model": False},
    }


def inspect_status(context: Context) -> StatusReport:
    """Infer core, enhanced, or degraded mode from managed local artifacts only."""
    role_paths = {f"{role.name}.toml": context.agents_dir / f"{role.name}.toml" for role in ROLES}
    present = sum(_status_artifact_exists(path) for path in role_paths.values())
    traced_paths = (*role_paths.values(), context.config_path, context.state_path)
    traces_exist = any(_status_artifact_exists(path) for path in traced_paths)
    base = {
        "plugin_version": context.template_version,
        "role_files_expected": len(role_paths),
        "role_files_present": present,
    }

    if not traces_exist:
        return StatusReport(
            **base,
            mode="core",
            enhancement_state="absent",
            role_hashes_match=None,
            model_mapping_status="not_installed",
            installed_template_version=None,
            template_current=None,
            exit_code=0,
        )

    unsafe_artifacts = any(
        _status_artifact_exists(path)
        and not _status_artifact_is_safe(path, context.codex_home)
        for path in traced_paths
    )
    if unsafe_artifacts:
        return StatusReport(
            **base,
            mode="degraded",
            enhancement_state="conflict",
            role_hashes_match=False,
            model_mapping_status="invalid",
            installed_template_version=None,
            template_current=None,
            exit_code=2,
        )

    try:
        config = load_config(context.config_path)
        state = load_state(context.state_path)
    except ConfigError:
        return StatusReport(
            **base,
            mode="degraded",
            enhancement_state="incomplete",
            role_hashes_match=None,
            model_mapping_status="invalid",
            installed_template_version=None,
            template_current=None,
            exit_code=1,
        )

    recorded_names = set(state.managed_files)
    expected_names = set(role_paths)
    try:
        config_hash_matches = sha256_bytes(context.config_path.read_bytes()) == state.config_sha256
        invalid_names = bool(recorded_names - expected_names)
        unowned_roles = any(
            path.is_file() and filename not in recorded_names
            for filename, path in role_paths.items()
        )
        recorded_missing = any(
            filename in recorded_names and not path.is_file()
            for filename, path in role_paths.items()
        )
        recorded_changed = any(
            filename in recorded_names
            and path.is_file()
            and sha256_bytes(path.read_bytes()) != state.managed_files[filename]
            for filename, path in role_paths.items()
        )
    except OSError:
        return StatusReport(
            **base,
            mode="degraded",
            enhancement_state="incomplete",
            role_hashes_match=None,
            model_mapping_status="invalid",
            installed_template_version=state.template_version,
            template_current=state.template_version == context.template_version,
            exit_code=1,
        )
    hashes_match = not (invalid_names or unowned_roles or recorded_missing or recorded_changed)

    if not state.managed_files and present == 0 and config_hash_matches:
        return StatusReport(
            **base,
            mode="core",
            enhancement_state="absent",
            role_hashes_match=None,
            model_mapping_status="not_installed",
            installed_template_version=state.template_version,
            template_current=state.template_version == context.template_version,
            exit_code=0,
        )

    if not config_hash_matches or invalid_names or unowned_roles or recorded_changed:
        return StatusReport(
            **base,
            mode="degraded",
            enhancement_state="conflict",
            role_hashes_match=False,
            model_mapping_status="mismatch" if config.models else "inherited",
            installed_template_version=state.template_version,
            template_current=state.template_version == context.template_version,
            exit_code=2,
        )

    mapping_status = (
        "inherited"
        if not config.models
        else "explicit"
        if set(config.models) == {"strong", "balanced", "economy"}
        else "invalid"
    )
    if present == len(role_paths) and not _role_models_match(config.models, role_paths):
        mapping_status = "mismatch"

    if recorded_names != expected_names or recorded_missing or present != len(role_paths):
        return StatusReport(
            **base,
            mode="degraded",
            enhancement_state="incomplete",
            role_hashes_match=hashes_match,
            model_mapping_status=mapping_status,
            installed_template_version=state.template_version,
            template_current=state.template_version == context.template_version,
            exit_code=1,
        )

    if mapping_status in {"invalid", "mismatch"}:
        return StatusReport(
            **base,
            mode="degraded",
            enhancement_state="incomplete",
            role_hashes_match=hashes_match,
            model_mapping_status=mapping_status,
            installed_template_version=state.template_version,
            template_current=state.template_version == context.template_version,
            exit_code=1,
        )

    if state.template_version != context.template_version:
        return StatusReport(
            **base,
            mode="degraded",
            enhancement_state="outdated",
            role_hashes_match=hashes_match,
            model_mapping_status=mapping_status,
            installed_template_version=state.template_version,
            template_current=False,
            exit_code=1,
        )

    return StatusReport(
        **base,
        mode="enhanced",
        enhancement_state="healthy",
        role_hashes_match=hashes_match,
        model_mapping_status=mapping_status,
        installed_template_version=state.template_version,
        template_current=True,
        exit_code=0,
    )


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
