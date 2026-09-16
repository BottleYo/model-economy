from pathlib import Path
import tomllib

from .config import default_reasoning
from .models import Capability, Profile, ROLES


_CAPABILITIES: frozenset[str] = frozenset(("strong", "balanced", "economy"))
_ROLE_NAMES: frozenset[str] = frozenset(role.name for role in ROLES)
_EFFORTS: frozenset[str] = frozenset(("low", "medium", "high"))


def _model_name(value: object) -> str:
    if not isinstance(value, str) or not value or not value.isprintable() or len(value) > 128:
        raise ValueError("model names must be printable strings of 1 to 128 characters")
    return value


def load_profile(path: Path) -> Profile:
    """Load and validate a model profile from a TOML file."""
    with path.open("rb") as profile_file:
        data = tomllib.load(profile_file)

    name = data.get("name")
    inherit_model = data.get("inherit_model")
    if not isinstance(name, str) or not name:
        raise ValueError("profile name must be a non-empty string")
    if not isinstance(inherit_model, bool):
        raise ValueError("inherit_model must be a boolean")

    raw_models = data.get("models", {})
    if not isinstance(raw_models, dict):
        raise ValueError("models must be a TOML table")
    unknown = set(raw_models) - _CAPABILITIES
    if unknown:
        raise ValueError(f"unknown capabilities: {', '.join(sorted(unknown))}")
    if inherit_model and raw_models:
        raise ValueError("inherited profiles cannot define models")
    if not inherit_model and set(raw_models) != _CAPABILITIES:
        raise ValueError("non-inherited profiles must define every capability")
    models: dict[Capability, str] = {
        capability: _model_name(raw_models[capability])
        for capability in _CAPABILITIES
        if capability in raw_models
    }

    raw_role_models = data.get("role_models", {})
    if not isinstance(raw_role_models, dict):
        raise ValueError("role_models must be a TOML table")
    if raw_role_models and (inherit_model or set(models) != _CAPABILITIES):
        raise ValueError("role_models requires explicit complete models")
    if set(raw_role_models) - _ROLE_NAMES:
        raise ValueError("role_models must name only built-in roles")
    role_models = {role: _model_name(model) for role, model in raw_role_models.items()}

    raw_reasoning = data.get("reasoning")
    if raw_reasoning is None:
        reasoning = default_reasoning()
    else:
        if not isinstance(raw_reasoning, dict) or set(raw_reasoning) != _ROLE_NAMES:
            raise ValueError("reasoning must define every built-in role")
        if any(effort not in _EFFORTS for effort in raw_reasoning.values()):
            raise ValueError("reasoning values must be low, medium, or high")
        reasoning = dict(raw_reasoning)

    return Profile(name=name, inherit_model=inherit_model, models=models, role_models=role_models, reasoning=reasoning)
