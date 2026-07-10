"""Transactional installation of Model Economy agent definitions."""

from dataclasses import dataclass, field
from pathlib import Path

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


@dataclass
class ChangeSet:
    created: list[Path] = field(default_factory=list)
    updated: list[Path] = field(default_factory=list)
    removed: list[Path] = field(default_factory=list)
    unchanged: list[Path] = field(default_factory=list)
    conflicts: list[Path] = field(default_factory=list)


def _read_config(path: Path) -> LocalConfig | None:
    if not path.exists():
        return None
    try:
        return load_config(path)
    except ConfigError:
        return None


def _read_state(path: Path) -> MachineState | None:
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


def _restore(path: Path, original: bytes | None) -> None:
    if original is None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return
    _write_path(path, original)


def _apply_transaction(operations: list[tuple[Path, bytes | None]]) -> None:
    originals = {path: path.read_bytes() if path.exists() else None for path, _ in operations}
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
    if state is None:
        if context.state_path.exists():
            return [context.state_path]
        conflicts: list[Path] = []
        if context.config_path.exists():
            conflicts.append(context.config_path)
        conflicts.extend(path for path in roles.values() if path.exists())
        return conflicts

    conflicts: list[Path] = []
    if config is None or not context.config_path.exists():
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
            if path.exists():
                conflicts.append(path)
            continue
        if not path.exists() or sha256_bytes(path.read_bytes()) != expected_hash:
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
        schema_version=1,
        profile=profile.name,
        models=dict(profile.models),
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
    context: Context, profile: Profile, force: bool
) -> tuple[ChangeSet, list[tuple[Path, bytes | None]]]:
    current_config = _read_config(context.config_path)
    current_state = _read_state(context.state_path)
    changes = ChangeSet()
    changes.conflicts.extend(_ownership_conflicts(context, current_config, current_state))
    if changes.conflicts and not force:
        return changes, []
    if force:
        changes.conflicts.clear()

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
    if changes.conflicts:
        paths = ", ".join(str(path) for path in changes.conflicts)
        raise ConflictError(f"unmanaged paths: {paths}")


def install(context: Context, profile: Profile, force: bool = False) -> ChangeSet:
    """Install roles after checking the complete, state-backed ownership record."""
    changes, writes = _prepare_install(context, profile, force)
    _raise_for_conflicts(changes)
    _apply_transaction(writes)
    return changes


def _prepare_upgrade(
    context: Context, force: bool
) -> tuple[ChangeSet, list[tuple[Path, bytes | None]]]:
    current_config = _read_config(context.config_path)
    if current_config is None:
        return ChangeSet(conflicts=[context.config_path]), []
    profile = Profile(
        name=current_config.profile,
        inherit_model=not current_config.models,
        models=current_config.models,
    )
    return _prepare_install(context, profile, force)


def plan_upgrade(context: Context) -> ChangeSet:
    """Return the upgrade changes without writing to the filesystem."""
    changes, _ = _prepare_upgrade(context, force=False)
    return changes


def upgrade(context: Context, force: bool = False) -> ChangeSet:
    """Upgrade files only after state and file integrity checks succeed."""
    changes, writes = _prepare_upgrade(context, force)
    _raise_for_conflicts(changes)
    _apply_transaction(writes)
    return changes


def _force_uninstall_operations(context: Context, purge: bool) -> tuple[ChangeSet, list[tuple[Path, bytes | None]]]:
    changes = ChangeSet()
    operations: list[tuple[Path, bytes | None]] = []
    for path in _role_paths(context).values():
        if path.exists():
            changes.removed.append(path)
            operations.append((path, None))
    if purge and context.config_path.exists():
        changes.removed.append(context.config_path)
        operations.append((context.config_path, None))
    if context.state_path.exists():
        changes.removed.append(context.state_path)
        operations.append((context.state_path, None))
    return changes, operations


def uninstall(context: Context, purge: bool = False, force: bool = False) -> ChangeSet:
    """Remove roles only when the complete state record still matches them."""
    current_config = _read_config(context.config_path)
    current_state = _read_state(context.state_path)
    if force:
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
