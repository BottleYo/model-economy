"""Managed global AGENTS.md routing block."""

from dataclasses import dataclass
import os
from pathlib import Path
import stat

from .filesystem import atomic_write
from .lifecycle import ChangeSet, ConflictError


START_MARKER = "<!-- model-economy:global-routing:start -->"
END_MARKER = "<!-- model-economy:global-routing:end -->"

_RULE_LINES = (
    "## 默认开发路由",
    "",
    "- 在任何项目和新会话中，涉及软件开发、调试、重构、测试、代码审查或架构设计时，默认使用已安装的 Model Economy `cost-aware-development` skill。",
    "- 开始工作前先将任务分类为简单、标准或大型/高风险，并按照插件路由策略选择模型和角色。",
    "- 大型/高风险任务必须经过 strong architect 设计和 strong final reviewer 终审；具体实施优先使用 balanced/economy。",
    "- Model Economy 默认使用原生轻量质量门；安装、启用或发现 Superpowers 不构成启用其完整工作流的授权。",
    "- 只有用户在当前任务中明确要求“完整 Superpowers”、“full Superpowers”或“Superpowers strict mode”时才交出本次流程编排权；此时 Model Economy 只提供模型与成本建议，不得启动自己的角色或追加质量流程。",
    "- 单项测试先行、系统化调试或完成前验证请求不等于完整 Superpowers 授权；strict 交权不跨任务保存。",
    "- 非软件开发任务不启用 Model Economy。",
    "- 项目自身的 `AGENTS.md` 可以覆盖本规则。",
    "- 不自动运行 `doctor --smoke`，不为验证模型身份额外消耗额度。",
)


class GlobalRoutingConflict(ConflictError):
    """Raised when the managed markers cannot be interpreted safely."""


@dataclass(frozen=True)
class _ManagedBlock:
    start: int
    end: int
    newline: str


def _newline_for(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _render_block(newline: str) -> str:
    return newline.join((START_MARKER, *_RULE_LINES, END_MARKER))


def _managed_block(text: str) -> _ManagedBlock | None:
    start_count = text.count(START_MARKER)
    end_count = text.count(END_MARKER)
    if start_count == 0 and end_count == 0:
        return None
    if start_count != 1 or end_count != 1:
        raise GlobalRoutingConflict("全局路由标记缺失或重复")

    start = text.index(START_MARKER)
    end_marker_start = text.index(END_MARKER)
    if end_marker_start < start:
        raise GlobalRoutingConflict("全局路由标记顺序错误")

    newline = _newline_for(text[start:end_marker_start])
    end = end_marker_start + len(END_MARKER)
    return _ManagedBlock(start=start, end=end, newline=newline)


def enable_text(text: str | None) -> str:
    """Return text containing the canonical managed routing block."""
    if text is not None:
        block = _managed_block(text)
        if block is not None:
            canonical = _render_block(block.newline)
            return text[:block.start] + canonical + text[block.end:]

    original = "" if text is None else text
    newline = _newline_for(original)
    return original + _render_block(newline) + newline


def disable_text(text: str | None) -> str | None:
    """Remove only the managed routing block and restore its original prefix."""
    if text is None:
        return None
    block = _managed_block(text)
    if block is None:
        return text

    suffix = text[block.end:]
    if suffix == block.newline:
        suffix = ""
    return text[:block.start] + suffix


def _read_text(path: Path) -> str | None:
    if path.is_symlink():
        raise GlobalRoutingConflict("全局 AGENTS.md 不能是符号链接")
    if not path.exists():
        return None
    if path.stat().st_nlink > 1:
        raise GlobalRoutingConflict("全局 AGENTS.md 不能是多硬链接文件")
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GlobalRoutingConflict("全局 AGENTS.md 不是有效 UTF-8 文本") from exc


def _write_text(path: Path, text: str, original_mode: int | None) -> None:
    atomic_write(path, text.encode("utf-8"), mode=original_mode)


def enable_global_routing(path: Path) -> ChangeSet:
    """Create or refresh the managed global routing block."""
    original = _read_text(path)
    updated = enable_text(original)
    if updated == original:
        return ChangeSet(unchanged=[path])
    mode = None
    if path.exists() and os.name != "nt":
        mode = stat.S_IMODE(path.stat().st_mode)
    _write_text(path, updated, mode)
    if original is None:
        return ChangeSet(created=[path])
    return ChangeSet(updated=[path])


def disable_global_routing(path: Path) -> ChangeSet:
    """Remove only the managed global routing block."""
    original = _read_text(path)
    updated = disable_text(original)
    if updated == original:
        return ChangeSet(unchanged=[path])
    if updated is None:
        return ChangeSet(unchanged=[path])
    mode = None if os.name == "nt" else stat.S_IMODE(path.stat().st_mode)
    _write_text(path, updated, mode)
    return ChangeSet(updated=[path])
