"""Output files that appear under their final name only when the command succeeded."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from .errors import DecontamError


def require_new(path: str) -> None:
    """Refuse to overwrite an existing file."""
    if os.path.exists(path):
        raise DecontamError(f"output exists: {path}")


@contextmanager
def replace_on_success(path: str) -> Iterator[str]:
    """Yield a temporary path.  It is renamed to `path` when the block ends normally and
    removed when the block raises.  The caller closes the file before the block ends."""
    temporary = path + ".tmp"
    try:
        yield temporary
    except BaseException:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise
    os.replace(temporary, path)
