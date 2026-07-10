"""Safe local configuration and public profile import/export helpers."""

from dataclasses import dataclass
import json
from pathlib import Path
import re
import tomllib
from typing import Any


class ConfigError(ValueError):
    """Raised when configuration or profile data is invalid."""


@dataclass(frozen=True)
class LocalConfig:
    schema_version: int
    profile: str
    models: dict[str, str]


@dataclass(frozen=True)
class MachineState:
    schema_version: int
    config_sha256: str
    template_version: str
    managed_files: dict[str, str]
    model_identity_verified: bool = False


_LOCAL_FIELDS = frozenset(
    (
        "schema_version",
        "profile",
        "models",
    )
)
_PUBLIC_FIELDS = frozenset(("schema_version", "profile", "models"))
_STATE_FIELDS = frozenset(
    ("schema_version", "config_sha256", "template_version", "managed_files", "model_identity_verified")
)
_MODEL_KEYS = frozenset(("strong", "balanced", "economy"))
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


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


def _require_schema_version(data: dict[str, Any]) -> None:
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ConfigError("schema_version must be 1")


def _string(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{field} must be a non-empty string")
    return value


def _models(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ConfigError("models must be a TOML table")
    models: dict[str, str] = {}
    for key, model in value.items():
        if key not in _MODEL_KEYS:
            raise ConfigError("model keys must be one of: balanced, economy, strong")
        if not isinstance(model, str) or not model or not model.isprintable() or len(model) > 128:
            raise ConfigError("model identifiers must be printable strings of 1 to 128 characters")
        models[key] = model
    return models


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
        data = json.loads(
            text,
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ConfigError("invalid state JSON") from exc
    if not isinstance(data, dict):
        raise ConfigError("state must be a JSON object")
    return data


def load_config_text(text: str) -> LocalConfig:
    data = _parse(text)
    _check_fields(data, _LOCAL_FIELDS)
    _require_schema_version(data)
    profile = _string(data, "profile")
    models = _models(data.get("models"))
    return LocalConfig(1, profile, models)


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
    _require_schema_version(data)
    return MachineState(
        schema_version=1,
        config_sha256=_sha256(data["config_sha256"], "config_sha256"),
        template_version=_string(data, "template_version"),
        managed_files=_sha256_map(data["managed_files"], "managed_files"),
        model_identity_verified=_state_verified(data["model_identity_verified"]),
    )


def load_state(path: Path) -> MachineState:
    try:
        return load_state_text(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read state: {path}") from exc


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _dump_map(name: str, values: dict[str, str]) -> list[str]:
    lines = [f"[{name}]"]
    lines.extend(f"{_toml_string(key)} = {_toml_string(values[key])}" for key in sorted(values))
    return lines


def _validate_config(config: LocalConfig) -> None:
    if not isinstance(config, LocalConfig):
        raise ConfigError("config must be a LocalConfig")
    if config.schema_version != 1:
        raise ConfigError("schema_version must be 1")
    _string({"profile": config.profile}, "profile")
    _models(config.models)


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
    _validate_config(config)
    lines = [
        "schema_version = 1",
        f"profile = {_toml_string(config.profile)}",
        *_dump_map("models", config.models),
    ]
    return "\n".join(lines) + "\n"


def dump_state(state: MachineState) -> str:
    _validate_state(state)
    return json.dumps(
        {
            "schema_version": state.schema_version,
            "config_sha256": state.config_sha256,
            "template_version": state.template_version,
            "managed_files": dict(sorted(state.managed_files.items())),
            "model_identity_verified": state.model_identity_verified,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def export_profile(config: LocalConfig, path: Path) -> None:
    _validate_config(config)
    lines = [
        "schema_version = 1",
        f"profile = {_toml_string(config.profile)}",
        *_dump_map("models", config.models),
    ]
    try:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot write profile: {path}") from exc


def import_profile_text(text: str) -> tuple[str, dict[str, str]]:
    data = _parse(text)
    _check_fields(data, _PUBLIC_FIELDS)
    _require_schema_version(data)
    return _string(data, "profile"), _models(data.get("models"))


def import_profile(path: Path) -> tuple[str, dict[str, str]]:
    try:
        return import_profile_text(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read profile: {path}") from exc
