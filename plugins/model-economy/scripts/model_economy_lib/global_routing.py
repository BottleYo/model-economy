"""Managed global AGENTS.md routing block."""

from dataclasses import dataclass
import os
from pathlib import Path
import re
import stat

from .filesystem import atomic_write
from .lifecycle import ChangeSet, ConflictError


START_MARKER = "<!-- model-economy:global-routing:start -->"
END_MARKER = "<!-- model-economy:global-routing:end -->"
_METADATA = re.compile(
    r"<!-- model-economy:global-routing:"
    r"origin=(missing|existing);separator-newlines=([0-2]) -->"
)

_RULE_LINES = (
    "## 默认开发路由",
    "",
    "- 在任何项目和新会话中，涉及软件开发、调试、重构、测试、代码审查或架构设计时，默认使用已安装的 Model Economy `cost-aware-development` skill。",
    "- 开始工作前先将任务分类为简单、标准或大型/高风险，并按照插件路由策略选择模型和角色。",
    "- 大型/高风险任务必须经过 strong architect 设计和 strong final reviewer 终审；具体实施优先使用 balanced/economy。",
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
    origin: str
    separator_newlines: int
    newline: str


def _newline_for(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _render_block(origin: str, separator_newlines: int, newline: str) -> str:
    metadata = (
        "<!-- model-economy:global-routing:"
        f"origin={origin};separator-newlines={separator_newlines} -->"
    )
    return newline.join((START_MARKER, metadata, *_RULE_LINES, END_MARKER)) + newline


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
    metadata_start = start + len(START_MARKER)
    if not text.startswith(newline, metadata_start):
        raise GlobalRoutingConflict("全局路由恢复元数据缺失")
    metadata_start += len(newline)
    metadata_end = text.find(newline, metadata_start)
    if metadata_end < 0:
        raise GlobalRoutingConflict("全局路由恢复元数据损坏")
    metadata = _METADATA.fullmatch(text[metadata_start:metadata_end])
    if metadata is None:
        raise GlobalRoutingConflict("全局路由恢复元数据损坏")

    end = end_marker_start + len(END_MARKER)
    if text.startswith(newline, end):
        end += len(newline)
    return _ManagedBlock(
        start=start,
        end=end,
        origin=metadata.group(1),
        separator_newlines=int(metadata.group(2)),
        newline=newline,
    )


def enable_text(text: str | None) -> str:
    """Return text containing the canonical managed routing block."""
    if text is not None:
        block = _managed_block(text)
        if block is not None:
            canonical = _render_block(block.origin, block.separator_newlines, block.newline)
            return text[:block.start] + canonical + text[block.end:]

    original = "" if text is None else text
    newline = _newline_for(original)
    if not original or original.endswith(newline * 2):
        separator_newlines = 0
    elif original.endswith(newline):
        separator_newlines = 1
    else:
        separator_newlines = 2
    origin = "missing" if text is None else "existing"
    return original + newline * separator_newlines + _render_block(
        origin, separator_newlines, newline
    )


def disable_text(text: str | None) -> str | None:
    """Remove only the managed routing block and restore its original prefix."""
    if text is None:
        return None
    block = _managed_block(text)
    if block is None:
        return text

    prefix = text[:block.start]
    separator = block.newline * block.separator_newlines
    if separator:
        if not prefix.endswith(separator):
            raise GlobalRoutingConflict("全局路由分隔元数据与文件内容不一致")
        prefix = prefix[: -len(separator)]
    restored = prefix + text[block.end:]
    if block.origin == "missing" and restored == "":
        return None
    return restored


def _read_text(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
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
        path.unlink()
        return ChangeSet(removed=[path])
    mode = None if os.name == "nt" else stat.S_IMODE(path.stat().st_mode)
    _write_text(path, updated, mode)
    return ChangeSet(updated=[path])
