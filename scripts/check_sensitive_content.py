#!/usr/bin/env python3
"""Reject private material before this repository is published."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable, Sequence


IGNORED_DIRS = {".git", "__pycache__", ".venv", ".superpowers"}
TEXT_SUFFIXES = {".py", ".md", ".toml", ".json", ".yml", ".yaml", ".txt"}


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    rule: str


RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private_key",
        re.compile(
            r"-----BEGIN "
            r"(?:(?:ENCRYPTED|OPENSSH|EC|RSA|DSA) |PGP )?"
            r"PRIVATE KEY(?: BLOCK)?-----"
        ),
    ),
    (
        "api_key_assignment",
        re.compile(
            r"\b(?:[a-z][a-z0-9_]*?(?:api[_-]?key|token|secret|password)|api[_-]?key)\b"
            r"\s*[:=]\s*(?:[\"'][^\"']+[\"']|[^\s#\"']+)",
            re.IGNORECASE,
        ),
    ),
    (
        "macos_absolute_path",
        re.compile(r"/" r"Users/" r"[^/\s]+/"),
    ),
    (
        "windows_absolute_path",
        re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+\\"),
    ),
    ("private_project", re.compile(r"stock[-_]studio", re.IGNORECASE)),
    ("persona_name", re.compile(r"N[O]RA")),
    (
        "investment_keyword",
        re.compile(
            r"(?:\u4e2a\u4eba)?\u6301\u4ed3|\u80a1\u7968|\u8bc1\u5238|\u671f\u6743|"
            r"\u4e70\u5165|\u5356\u51fa|\u4ea4\u6613\u8bb0\u5f55|\u6295\u8d44\u7ec4\u5408"
        ),
    ),
)


def scan_text(path: Path, text: str) -> list[Finding]:
    """Return rule-only findings for every matching line in text."""
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in RULES:
            if pattern.search(line):
                findings.append(Finding(path, line_number, rule))
    return findings


def scan(root: Path) -> list[Finding]:
    """Scan public text files in the working tree, excluding generated state."""
    findings: list[Finding] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(scan_text(path.relative_to(root), text))
    return findings


def _git_output(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stdout if completed.returncode == 0 else ""


def _reachable_revisions(root: Path) -> Iterable[str]:
    return (revision for revision in _git_output(root, "rev-list", "--all").splitlines() if revision)


def _tree_entries(root: Path, revision: str) -> Iterable[tuple[str, str]]:
    output = _git_output(root, "ls-tree", "-r", "-z", revision)
    for entry in output.split("\0"):
        metadata, separator, path = entry.partition("\t")
        parts = metadata.split()
        if separator and len(parts) == 3 and parts[1] == "blob":
            yield parts[2], path


def scan_git(root: Path) -> list[Finding]:
    """Scan reachable Git metadata, paths, messages, and text blobs without echoing them."""
    findings: list[Finding] = []
    scanned_blobs: set[str] = set()
    for revision in _reachable_revisions(root):
        git_path = Path(".git") / "commits" / revision
        author = _git_output(root, "show", "-s", "--format=%ae", revision).strip()
        if author and not author.endswith("@users.noreply.github.com"):
            findings.append(Finding(git_path, 1, "git_author_email"))
        committer = _git_output(root, "show", "-s", "--format=%ce", revision).strip()
        if committer and not committer.endswith("@users.noreply.github.com"):
            findings.append(Finding(git_path, 1, "git_committer_email"))

        message = _git_output(root, "show", "-s", "--format=%B", revision)
        findings.extend(scan_text(git_path / "message", message))
        for blob, path in _tree_entries(root, revision):
            findings.extend(scan_text(git_path / "paths", path))
            if blob in scanned_blobs:
                continue
            scanned_blobs.add(blob)
            content = _git_output(root, "cat-file", "blob", blob)
            if "\0" not in content:
                findings.extend(scan_text(git_path / "blobs" / blob, content))
    return findings


def format_findings(findings: Sequence[Finding]) -> str:
    """Render findings without including the matching source text."""
    return "\n".join(
        f"{finding.path.as_posix()}:{finding.line}: {finding.rule}"
        for finding in findings
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0] if args else ".").resolve()
    if not root.is_dir():
        print("扫描目标必须是目录。", file=sys.stderr)
        return 2

    findings = [*scan(root), *scan_git(root)]
    if findings:
        print(format_findings(findings))
        return 1
    print("敏感内容检查：通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
