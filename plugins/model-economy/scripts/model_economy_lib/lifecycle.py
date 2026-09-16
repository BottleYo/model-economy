"""Transactional installation of Model Economy agent definitions."""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import tomllib

from .config import (
    ConfigError,
    LocalConfig,
    MachineState,
    dump_config,
    dump_state,
    load_config,
    load_state,
)
from .filesystem import atomic_write, sha256_bytes
from .models import Profile, ROLES
from .renderer import render_all_agents


class ConflictError(RuntimeError):
    """Raised when an operation would overwrite an unmanaged file."""


@dataclass(frozen=True)
class Context:
    codex_home: Path
    plugin_root: Path
    template_version: str

    @property
    def agents_dir(self) -> Path:
        return self.codex_home / "agents"

    @property
    def config_path(self) -> Path:
        return self.codex_home / "model-economy" / "config.toml"

    @property
    def state_path(self) -> Path:
        return self.codex_home / "model-economy" / "state.json"

    @property
    def backups_dir(self) -> Path:
        return self.codex_home / "model-economy" / "backups"


@dataclass
class ChangeSet:
    created: list[Path] = field(default_factory=list)
    updated: list[Path] = field(default_factory=list)
    removed: list[Path] = field(default_factory=list)
    unchanged: list[Path] = field(default_factory=list)
    conflicts: list[Path] = field(default_factory=list)
    migration_from_schema: int | None = None
    migration_to_schema: int | None = None
    backup_path: Path | None = None
    migration_models: str | None = None
    migration_role_models: int | None = None
    migration_reasoning: dict[str, str] = field(default_factory=dict)
    upgrade_required: bool = False


@dataclass(frozen=True)
class _OriginalFile:
    content: bytes | None
    mode: int | None


def _artifact_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _is_safe_artifact(context: Context, path: Path) -> bool:
    """Reject links and multiply linked files before any managed-file read/write."""
    if path != context.codex_home and context.codex_home not in path.parents:
        return False
    current = path
    while current != context.codex_home:
        if current.is_symlink():
            return False
        current = current.parent
    if not _artifact_exists(path):
        return True
    try:
        metadata = path.lstat()
    except OSError:
        return False
    return stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1


def _unsafe_managed_paths(context: Context) -> list[Path]:
    paths = (*_role_paths(context).values(), context.config_path, context.state_path)
    return [path for path in paths if not _is_safe_artifact(context, path)]


def _read_config(context: Context) -> LocalConfig | None:
    path = context.config_path
    if not _is_safe_artifact(context, path):
        return None
    if not path.exists():
        return None
    try:
        return load_config(path)
    except ConfigError:
        return None


def _read_state(context: Context) -> MachineState | None:
    path = context.state_path
    if not _is_safe_artifact(context, path):
        return None
    if not path.exists():
        return None
    try:
        return load_state(path)
    except ConfigError:
        return None


def _write_path(path: Path, content: bytes) -> None:
    if path.name == "state.json":
        atomic_write(path, content, mode=0o600)
    else:
        atomic_write(path, content)


def _role_paths(context: Context) -> dict[str, Path]:
    return {f"{role.name}.toml": context.agents_dir / f"{role.name}.toml" for role in ROLES}


def _snapshot(path: Path) -> _OriginalFile:
    if not path.exists():
        return _OriginalFile(None, None)
    mode = None if os.name == "nt" else stat.S_IMODE(path.stat().st_mode)
    return _OriginalFile(path.read_bytes(), mode)


def _restore(path: Path, original: _OriginalFile) -> None:
    if original.content is None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return
    atomic_write(path, original.content, mode=original.mode)


def _apply_transaction(operations: list[tuple[Path, bytes | None]]) -> None:
    originals = {path: _snapshot(path) for path, _ in operations}
    completed: list[Path] = []
    try:
        for path, content in operations:
            if content is None:
                path.unlink()
            else:
                _write_path(path, content)
            completed.append(path)
    except Exception:
        for path in reversed(completed):
            _restore(path, originals[path])
        raise


def _ownership_conflicts(
    context: Context, config: LocalConfig | None, state: MachineState | None
) -> list[Path]:
    # state.json is trusted local package metadata, not an anti-tamper token;
    # missing, malformed, or incomplete records fail closed as conflicts.
    roles = _role_paths(context)
    unsafe = _unsafe_managed_paths(context)
    if unsafe:
        return unsafe
    if state is None:
        if _artifact_exists(context.state_path):
            return [context.state_path]
        conflicts: list[Path] = []
        if _artifact_exists(context.config_path):
            conflicts.append(context.config_path)
        conflicts.extend(path for path in roles.values() if _artifact_exists(path))
        return conflicts

    conflicts: list[Path] = []
    if config is None or not _artifact_exists(context.config_path):
        conflicts.append(context.config_path)
    elif sha256_bytes(context.config_path.read_bytes()) != state.config_sha256:
        conflicts.append(context.config_path)

    recorded_names = set(state.managed_files)
    allowed_names = set(roles)
    if not recorded_names <= allowed_names:
        conflicts.append(context.state_path)

    for filename, path in roles.items():
        expected_hash = state.managed_files.get(filename)
        if expected_hash is None:
            if _artifact_exists(path):
                conflicts.append(path)
            continue
        if not _artifact_exists(path) or sha256_bytes(path.read_bytes()) != expected_hash:
            conflicts.append(path)
    return conflicts


def _desired_installation(
    context: Context,
    profile: Profile,
    current_config: LocalConfig | None,
    current_state: MachineState | None,
) -> list[tuple[Path, bytes]]:
    agent_contents = {
        context.agents_dir / name: text.encode("utf-8")
        for name, text in render_all_agents(profile).items()
    }
    config = LocalConfig(
        schema_version=2,
        profile=profile.name,
        models=dict(profile.models),
        role_models=dict(profile.role_models),
        reasoning=dict(profile.reasoning),
    )
    config_content = dump_config(config).encode("utf-8")
    state = MachineState(
        schema_version=1,
        config_sha256=sha256_bytes(config_content),
        template_version=context.template_version,
        managed_files={path.name: sha256_bytes(content) for path, content in agent_contents.items()},
        model_identity_verified=(current_state.model_identity_verified if current_state else False),
    )
    return [
        *agent_contents.items(),
        (context.config_path, config_content),
        (context.state_path, dump_state(state).encode("utf-8")),
    ]


def _prepare_install(
    context: Context, profile: Profile, force: bool, *, reconfigure_v1: bool = False
) -> tuple[ChangeSet, list[tuple[Path, bytes | None]]]:
    current_config = _read_config(context)
    current_state = _read_state(context)
    changes = ChangeSet()
    changes.conflicts.extend(_ownership_conflicts(context, current_config, current_state))
    if changes.conflicts and not force:
        return changes, []
    if force:
        unsafe = set(_unsafe_managed_paths(context))
        changes.conflicts[:] = [path for path in changes.conflicts if path in unsafe]
        if changes.conflicts:
            return changes, []
    v1_traces = _artifact_exists(context.state_path) or any(
        _artifact_exists(path) for path in _role_paths(context).values()
    )
    if current_config is not None and current_config.schema_version == 1 and v1_traces and not reconfigure_v1:
        changes.upgrade_required = True
        return changes, []

    writes: list[tuple[Path, bytes | None]] = []
    for path, content in _desired_installation(context, profile, current_config, current_state):
        existing = path.read_bytes() if path.exists() else None
        if existing is None:
            changes.created.append(path)
            writes.append((path, content))
        elif existing == content:
            changes.unchanged.append(path)
        else:
            changes.updated.append(path)
            writes.append((path, content))
    return changes, writes


def _raise_for_conflicts(changes: ChangeSet) -> None:
    if changes.upgrade_required:
        raise ConflictError("受管理安装仍为 schema v1；请先运行 upgrade")
    if changes.conflicts:
        paths = ", ".join(str(path) for path in changes.conflicts)
        raise ConflictError(f"unmanaged paths: {paths}")


def install(
    context: Context, profile: Profile, force: bool = False, *, reconfigure_v1: bool = False
) -> ChangeSet:
    """Install roles after checking the complete, state-backed ownership record."""
    changes, writes = _prepare_install(context, profile, force, reconfigure_v1=reconfigure_v1)
    _raise_for_conflicts(changes)
    _apply_transaction(writes)
    return changes


def _prepare_upgrade(
    context: Context, force: bool
) -> tuple[ChangeSet, list[tuple[Path, bytes | None]]]:
    current_config = _read_config(context)
    if current_config is None:
        return ChangeSet(conflicts=[context.config_path]), []
    current_state = _read_state(context)
    conflicts = _ownership_conflicts(context, current_config, current_state)
    if conflicts:
        if current_config.schema_version == 1 or not force:
            return ChangeSet(conflicts=conflicts), []
        unsafe = set(_unsafe_managed_paths(context))
        if any(path in unsafe for path in conflicts):
            return ChangeSet(conflicts=conflicts), []
    if current_config.models and set(current_config.models) != {"strong", "balanced", "economy"}:
        return ChangeSet(conflicts=[context.config_path]), []
    reasoning = dict(current_config.reasoning)
    if current_config.schema_version == 1:
        for role in ROLES:
            try:
                document = tomllib.loads(_role_paths(context)[f"{role.name}.toml"].read_text(encoding="utf-8"))
            except (OSError, tomllib.TOMLDecodeError) as exc:
                return ChangeSet(conflicts=[_role_paths(context)[f"{role.name}.toml"]]), []
            effort = document.get("model_reasoning_effort")
            if document.get("name") != role.name or not isinstance(effort, str) or effort not in {"low", "medium", "high"}:
                return ChangeSet(conflicts=[_role_paths(context)[f"{role.name}.toml"]]), []
            reasoning[role.name] = effort
    profile = Profile(
        name=current_config.profile,
        inherit_model=not current_config.models,
        models=current_config.models,
        role_models=current_config.role_models,
        reasoning=reasoning,
    )
    changes, writes = _prepare_install(context, profile, force, reconfigure_v1=True)
    if current_config.schema_version == 1:
        changes.migration_from_schema = 1
        changes.migration_to_schema = 2
        changes.migration_models = "inherited" if not current_config.models else "explicit"
        changes.migration_role_models = 0
        changes.migration_reasoning = dict(reasoning)
    return changes, writes


def plan_upgrade(context: Context, force: bool = False) -> ChangeSet:
    """Return the upgrade changes without writing to the filesystem."""
    changes, _ = _prepare_upgrade(context, force)
    return changes


def _managed_paths(context: Context) -> dict[str, Path]:
    return {
        "config.toml": context.config_path,
        "state.json": context.state_path,
        **{f"agents/{name}": path for name, path in _role_paths(context).items()},
    }


def _backup_migration(
    context: Context, operations: list[tuple[Path, bytes | None]]
) -> Path:
    """Store exactly the eight managed inputs before a v1-to-v2 write begins."""
    managed = _managed_paths(context)
    if any(not _is_safe_artifact(context, path) or not _artifact_exists(path) for path in managed.values()):
        raise ConflictError("unsafe managed artifact prevents migration backup")
    parent = context.backups_dir
    if parent.exists() and (parent.is_symlink() or not parent.is_dir()):
        raise ConflictError("unsafe backups directory")
    if parent.parent.is_symlink():
        raise ConflictError("unsafe model-economy directory")
    parent.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix="upgrade-", dir=parent))
    desired = {path: content for path, content in operations}
    manifest: dict[str, object] = {"schema_version": 1, "migration": "v1-to-v2", "files": {}}
    try:
        for relative, source in managed.items():
            original = _snapshot(source)
            if original.content is None:
                raise ConflictError("missing managed artifact prevents migration backup")
            target = backup / relative
            atomic_write(target, original.content, mode=original.mode)
            after = desired.get(source, original.content)
            if after is None:
                raise ConflictError("migration cannot remove managed artifacts")
            manifest["files"][relative] = {
                "sha256": sha256_bytes(original.content),
                "mode": original.mode,
                "post_migration_sha256": sha256_bytes(after),
            }
        atomic_write(backup / "manifest.json", json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n", mode=0o600)
    except Exception:
        shutil.rmtree(backup, ignore_errors=True)
        raise
    return backup


def upgrade(context: Context, force: bool = False) -> ChangeSet:
    """Upgrade files only after state and file integrity checks succeed."""
    changes, writes = _prepare_upgrade(context, force)
    _raise_for_conflicts(changes)
    if changes.migration_from_schema == 1:
        changes.backup_path = _backup_migration(context, writes)
    _apply_transaction(writes)
    return changes


def _force_uninstall_operations(context: Context, purge: bool) -> tuple[ChangeSet, list[tuple[Path, bytes | None]]]:
    changes = ChangeSet()
    operations: list[tuple[Path, bytes | None]] = []
    for path in _role_paths(context).values():
        if _artifact_exists(path):
            changes.removed.append(path)
            operations.append((path, None))
    if purge and _artifact_exists(context.config_path):
        changes.removed.append(context.config_path)
        operations.append((context.config_path, None))
    if _artifact_exists(context.state_path):
        changes.removed.append(context.state_path)
        operations.append((context.state_path, None))
    return changes, operations


def uninstall(context: Context, purge: bool = False, force: bool = False) -> ChangeSet:
    """Remove roles only when the complete state record still matches them."""
    current_config = _read_config(context)
    current_state = _read_state(context)
    if force:
        unsafe = _unsafe_managed_paths(context)
        if unsafe:
            return ChangeSet(conflicts=unsafe)
        changes, operations = _force_uninstall_operations(context, purge)
        _apply_transaction(operations)
        return changes

    changes = ChangeSet()
    changes.conflicts.extend(_ownership_conflicts(context, current_config, current_state))
    if changes.conflicts:
        return changes
    if current_state is None or current_config is None:
        return changes

    if purge:
        operations: list[tuple[Path, bytes | None]] = []
        for filename in current_state.managed_files:
            path = _role_paths(context)[filename]
            changes.removed.append(path)
            operations.append((path, None))
        changes.removed.extend((context.config_path, context.state_path))
        operations.extend(((context.config_path, None), (context.state_path, None)))
    else:
        if not current_state.managed_files:
            changes.unchanged.extend((context.config_path, context.state_path))
            return changes
        operations = []
        for filename in current_state.managed_files:
            path = _role_paths(context)[filename]
            changes.removed.append(path)
            operations.append((path, None))
        empty_state = MachineState(
            schema_version=1,
            config_sha256=sha256_bytes(context.config_path.read_bytes()),
            template_version=current_state.template_version,
            managed_files={},
            model_identity_verified=current_state.model_identity_verified,
        )
        changes.updated.append(context.state_path)
        operations.append((context.state_path, dump_state(empty_state).encode("utf-8")))

    _apply_transaction(operations)
    return changes
