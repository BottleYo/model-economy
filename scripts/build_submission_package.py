#!/usr/bin/env python3
"""构建可重复生成的 Skills-only 官方目录提交包。"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLUGIN_ROOT = ROOT / "plugins" / "model-economy"
PLUGIN_MANIFEST = Path(".codex-plugin/plugin.json")
ALLOWED_ROOTS = frozenset({".codex-plugin", "assets", "scripts", "skills"})
EXCLUDED_PREFIXES = ("assets/screenshots/",)
EXCLUDED_NAMES = frozenset({".DS_Store", ".app.json", ".mcp.json"})
UNSUPPORTED_MANIFEST_FIELDS = ("apps", "mcpServers")
ARCHIVE_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def submission_manifest(manifest: dict[str, object]) -> dict[str, object]:
    """Return the skills-only manifest while rejecting app or MCP components."""
    for field in UNSUPPORTED_MANIFEST_FIELDS:
        if field in manifest:
            raise ValueError(f"Skills-only 提交不支持 manifest 字段：{field}")

    result = deepcopy(manifest)
    interface = result.get("interface")
    if isinstance(interface, dict):
        interface.pop("screenshots", None)
    return result


def _load_manifest(plugin_root: Path) -> dict[str, object]:
    path = plugin_root / PLUGIN_MANIFEST
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取插件 manifest：{path}") from exc
    if not isinstance(document, dict):
        raise ValueError("插件 manifest 根节点必须是对象")
    return document


def _included_files(plugin_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in plugin_root.rglob("*"):
        relative = path.relative_to(plugin_root)
        relative_text = relative.as_posix()
        if path.is_symlink():
            raise ValueError(f"提交包不接受符号链接：{relative_text}")
        if not path.is_file():
            continue
        if relative.parts[0] not in ALLOWED_ROOTS:
            continue
        if relative.parts[0] == ".codex-plugin" and relative != PLUGIN_MANIFEST:
            continue
        if path.name in EXCLUDED_NAMES or "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        if any(relative_text.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            continue
        files.append(relative)
    return sorted(files, key=lambda item: item.as_posix())


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, ARCHIVE_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def build_package(plugin_root: Path, output: Path) -> Path:
    """Build a deterministic ZIP containing one normalized plugin root."""
    plugin_root = plugin_root.resolve()
    output = output.resolve()
    if output.suffix.lower() != ".zip":
        raise ValueError("输出文件必须使用 .zip 扩展名")
    if not (plugin_root / "skills").is_dir():
        raise ValueError("Skills-only 提交必须包含 skills/ 目录")
    if plugin_root == output or plugin_root in output.parents:
        raise ValueError("输出 ZIP 必须位于插件根目录之外")

    manifest = submission_manifest(_load_manifest(plugin_root))
    if manifest.get("name") != plugin_root.name:
        raise ValueError("插件目录名必须与 manifest name 一致")
    files = _included_files(plugin_root)
    if PLUGIN_MANIFEST not in files:
        raise ValueError("提交包缺少 .codex-plugin/plugin.json")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".zip", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for relative in files:
                archive_name = f"{plugin_root.name}/{relative.as_posix()}"
                if relative == PLUGIN_MANIFEST:
                    content = (
                        json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
                    )
                else:
                    content = (plugin_root / relative).read_bytes()
                archive.writestr(_zip_info(archive_name), content, compresslevel=9)
        temporary_path.replace(output)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建 Model Economy Skills-only 提交 ZIP")
    parser.add_argument("--plugin-root", type=Path, default=DEFAULT_PLUGIN_ROOT)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = build_package(args.plugin_root, args.output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
