"""Safe local configuration and public profile import/export helpers."""

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import tomllib
from typing import Any

from .models import DEFAULT_REASONING, ROLES


class ConfigError(ValueError):
    """Raised when configuration or profile data is invalid."""


_MODEL_KEYS = frozenset(("strong", "balanced", "economy"))
_ROLE_NAMES = tuple(role.name for role in ROLES)
_ROLE_NAME_SET = frozenset(_ROLE_NAMES)
_EFFORTS = frozenset(("low", "medium", "high"))
_V1_REASONING = {
    "model-economy-architect": "high", "model-economy-final-reviewer": "high",
    "model-economy-implementer": "high", "model-economy-reviewer": "medium",
    "model-economy-explorer": "medium", "model-economy-batch-worker": "low",
}


@dataclass(frozen=True)
class LocalConfig:
    schema_version: int
    profile: str
    models: dict[str, str]
    role_models: dict[str, str] = field(default_factory=dict)
    reasoning: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_REASONING))


@dataclass(frozen=True)
class MachineState:
    schema_version: int
    config_sha256: str
    template_version: str
    managed_files: dict[str, str]
    model_identity_verified: bool = False


_V1_CONFIG_FIELDS = frozenset(("schema_version", "profile", "models"))
_V2_CONFIG_FIELDS = frozenset(("schema_version", "profile", "models", "role_models", "reasoning"))
_STATE_FIELDS = frozenset(("schema_version", "config_sha256", "template_version", "managed_files", "model_identity_verified"))
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def default_reasoning(*, legacy: bool = False) -> dict[str, str]:
    """Return a copy of the documented v1 or v2 role reasoning defaults."""
    return dict(_V1_REASONING if legacy else DEFAULT_REASONING)


def _parse(text: str) -> dict[str, Any]:
    try:
        data = tomllib.loads(text)
    except (tomllib.TOMLDecodeError, TypeError) as exc:
        raise ConfigError("invalid TOML") from exc
    if not isinstance(data, dict):
        raise ConfigError("configuration must be a TOML table")
    return data


def _check_fields(data: dict[str, Any], allowed: frozenset[str]) -> None:
    unknown = set(data) - allowed
    if unknown:
        raise ConfigError(f"unknown fields: {', '.join(sorted(unknown))}")


def _schema(data: dict[str, Any], allowed: frozenset[int] = frozenset((1, 2))) -> int:
    value = data.get("schema_version")
    if type(value) is not int or value not in allowed:
        expected = " or ".join(str(item) for item in sorted(allowed))
        raise ConfigError(f"schema_version must be {expected}")
    return value


def _string(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{field} must be a non-empty string")
    return value


def _model_identifier(value: Any) -> str:
    if not isinstance(value, str) or not value or not value.isprintable() or len(value) > 128:
        raise ConfigError("model identifiers must be printable strings of 1 to 128 characters")
    return value


def _models(value: Any, *, complete: bool) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ConfigError("models must be a TOML table")
    models: dict[str, str] = {}
    for key, model in value.items():
        if key not in _MODEL_KEYS:
            raise ConfigError("model keys must be one of: balanced, economy, strong")
        models[key] = _model_identifier(model)
    if complete and models and set(models) != _MODEL_KEYS:
        raise ConfigError("models must be empty or define balanced, economy, and strong")
    return models


def _role_models(value: Any, models: dict[str, str]) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError("role_models must be a TOML table")
    if value and set(models) != _MODEL_KEYS:
        raise ConfigError("role_models requires an explicit complete models mapping")
    result: dict[str, str] = {}
    for role, model in value.items():
        if role not in _ROLE_NAME_SET:
            raise ConfigError("role_models keys must name one of the six built-in roles")
        result[role] = _model_identifier(model)
    return result


def _reasoning(value: Any, *, require_complete: bool, fallback: dict[str, str] | None = None) -> dict[str, str]:
    if value is None and fallback is not None:
        return dict(fallback)
    if not isinstance(value, dict):
        raise ConfigError("reasoning must be a TOML table")
    if require_complete and set(value) != _ROLE_NAME_SET:
        raise ConfigError("reasoning must define every built-in role exactly once")
    result: dict[str, str] = {}
    for role, effort in value.items():
        if role not in _ROLE_NAME_SET:
            raise ConfigError("reasoning keys must name one of the six built-in roles")
        if effort not in _EFFORTS:
            raise ConfigError("reasoning values must be one of: low, medium, high")
        result[role] = effort
    return result


def _string_map(value: Any, field: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ConfigError(f"{field} must be a TOML table")
    if any(not isinstance(key, str) or not key for key in value):
        raise ConfigError(f"{field} keys must be non-empty strings")
    if any(not isinstance(item, str) for item in value.values()):
        raise ConfigError(f"{field} values must be strings")
    return dict(value)


def _sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ConfigError(f"{field} must be a lowercase SHA-256 hash")
    return value


def _sha256_map(value: Any, field: str) -> dict[str, str]:
    values = _string_map(value, field)
    for key, item in values.items():
        _sha256(item, f"{field}.{key}")
    return values


def _parse_state(text: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ConfigError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    try:
        data = json.loads(text, object_pairs_hook=reject_duplicates, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ConfigError("invalid state JSON") from exc
    if not isinstance(data, dict):
        raise ConfigError("state must be a JSON object")
    return data


def load_config_text(text: str) -> LocalConfig:
    data = _parse(text)
    schema_version = _schema(data)
    _check_fields(data, _V1_CONFIG_FIELDS if schema_version == 1 else _V2_CONFIG_FIELDS)
    profile = _string(data, "profile")
    models = _models(data.get("models"), complete=schema_version == 2)
    if schema_version == 1:
        return LocalConfig(1, profile, models, {}, default_reasoning(legacy=True))
    return LocalConfig(2, profile, models, _role_models(data.get("role_models"), models), _reasoning(data.get("reasoning"), require_complete=True))


def load_config(path: Path) -> LocalConfig:
    try:
        return load_config_text(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read config: {path}") from exc


def load_state_text(text: str) -> MachineState:
    data = _parse_state(text)
    _check_fields(data, _STATE_FIELDS)
    if set(data) != _STATE_FIELDS:
        missing = _STATE_FIELDS - set(data)
        raise ConfigError(f"missing state fields: {', '.join(sorted(missing))}")
    _schema(data, frozenset((1,)))
    return MachineState(1, _sha256(data["config_sha256"], "config_sha256"), _string(data, "template_version"), _sha256_map(data["managed_files"], "managed_files"), _state_verified(data["model_identity_verified"]))


def load_state(path: Path) -> MachineState:
    try:
        return load_state_text(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read state: {path}") from exc


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _dump_map(name: str, values: dict[str, str]) -> list[str]:
    return [f"[{name}]", *[f"{_toml_string(key)} = {_toml_string(values[key])}" for key in sorted(values)]]


def _validate_config(config: LocalConfig) -> None:
    if not isinstance(config, LocalConfig):
        raise ConfigError("config must be a LocalConfig")
    if config.schema_version not in (1, 2):
        raise ConfigError("schema_version must be 1 or 2")
    _string({"profile": config.profile}, "profile")
    models = _models(config.models, complete=config.schema_version == 2)
    _role_models(config.role_models, models)
    _reasoning(config.reasoning, require_complete=True)


def _state_verified(value: Any) -> bool:
    if not isinstance(value, bool):
        raise ConfigError("model_identity_verified must be a boolean")
    return value


def _validate_state(state: MachineState) -> None:
    if not isinstance(state, MachineState):
        raise ConfigError("state must be a MachineState")
    if state.schema_version != 1:
        raise ConfigError("schema_version must be 1")
    _sha256(state.config_sha256, "config_sha256")
    _string({"template_version": state.template_version}, "template_version")
    _sha256_map(state.managed_files, "managed_files")
    _state_verified(state.model_identity_verified)


def dump_config(config: LocalConfig) -> str:
    """Serialize all managed configuration as schema v2, including v1 upgrades."""
    _validate_config(config)
    lines = ["schema_version = 2", f"profile = {_toml_string(config.profile)}", *_dump_map("models", config.models)]
    if config.role_models:
        lines.extend(_dump_map("role_models", config.role_models))
    lines.extend(_dump_map("reasoning", config.reasoning))
    return "\n".join(lines) + "\n"


def dump_state(state: MachineState) -> str:
    _validate_state(state)
    return json.dumps({"schema_version": state.schema_version, "config_sha256": state.config_sha256, "template_version": state.template_version, "managed_files": dict(sorted(state.managed_files.items())), "model_identity_verified": state.model_identity_verified}, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def export_profile(config: LocalConfig, path: Path) -> None:
    _validate_config(config)
    try:
        path.write_text(dump_config(config), encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot write profile: {path}") from exc


def import_profile_config_text(text: str) -> LocalConfig:
    """Import only public v1/v2 profile fields; no local state is accepted."""
    return load_config_text(text)


def import_profile_config(path: Path) -> LocalConfig:
    try:
        return import_profile_config_text(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read profile: {path}") from exc


def import_profile_text(text: str) -> tuple[str, dict[str, str]]:
    """Compatibility helper for callers that only need capability mappings."""
    config = import_profile_config_text(text)
    return config.profile, config.models


def import_profile(path: Path) -> tuple[str, dict[str, str]]:
    config = import_profile_config(path)
    return config.profile, config.models
