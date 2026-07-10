from pathlib import Path
import tomllib

from .models import Capability, Profile


_CAPABILITIES: frozenset[str] = frozenset(("strong", "balanced", "economy"))


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
    if any(not isinstance(model, str) or not model for model in raw_models.values()):
        raise ValueError("model names must be non-empty strings")

    models: dict[Capability, str] = {
        capability: raw_models[capability] for capability in _CAPABILITIES if capability in raw_models
    }
    return Profile(name=name, inherit_model=inherit_model, models=models)
