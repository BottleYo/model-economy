import json
from pathlib import Path

from .models import Profile, ROLES, RoleSpec


_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "assets" / "agent-templates"


def _toml_string(value: str) -> str:
    """Encode a value as a TOML basic string using JSON's compatible escapes."""
    return json.dumps(value, ensure_ascii=False)


def render_agent(role: RoleSpec, profile: Profile) -> str:
    """Render a single agent definition using the template for its role."""
    if role.capability == "strong" and role.sandbox_mode != "read-only":
        raise ValueError("strong capability requires read-only sandbox")

    template_name = role.name.removeprefix("model-economy-")
    template = (_TEMPLATE_DIR / f"{template_name}.toml.tpl").read_text(encoding="utf-8")
    model_line = ""
    if not profile.inherit_model:
        model_line = f"model = {_toml_string(profile.models[role.capability])}\n"

    replacements = {
        "name": _toml_string(role.name),
        "description": _toml_string(role.description),
        "developer_instructions": _toml_string(role.developer_instructions),
        "model_line": model_line,
        "reasoning_effort": _toml_string(role.reasoning_effort),
        "sandbox_mode": _toml_string(role.sandbox_mode),
    }
    for key, value in replacements.items():
        template = template.replace(f"{{{{{key}}}}}", value)
    return template


def render_all_agents(profile: Profile) -> dict[str, str]:
    """Render every built-in role, keyed by its target TOML filename."""
    return {f"{role.name}.toml": render_agent(role, profile) for role in ROLES}
