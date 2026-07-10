"""Small filesystem primitives used by the lifecycle operations."""

import hashlib
import os
from pathlib import Path
import tempfile
from typing import Mapping


def resolve_codex_home(env: Mapping[str, str]) -> Path:
    return Path(env.get("CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def atomic_write(path: Path, content: bytes, *, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None and os.name != "nt":
            os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
