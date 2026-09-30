"""Workspace jail and filename rules.

Every identity, state, and fork path is resolved under an explicit root.
Names are a single path segment: letters, digits, dot, underscore, hyphen.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from vesper.errors import IOPermissionError, ValidationError

# One segment. ".." is rejected separately so it cannot pass as a name.
NAME_RE_MAX = 128
_ALLOWED = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-")

IDENTITY_DIRNAME = "identity"
STATE_FILENAME = "state.json"
FORKS_DIRNAME = "forks"
PUBLIC_FILENAME = "public.json"

# On-disk private key name from the v0.1 layout contract.
ECDSA_KEY_FILENAME = "edcsa-p256.priv"
HMAC_KEY_FILENAME = "hmac.key"


def validate_name(name: object, *, what: str = "name") -> str:
    """Accept a single safe path segment. Reject traversal and odd types."""
    if not isinstance(name, str):
        raise ValidationError(f"{what} must be a string")
    if not name or len(name) > NAME_RE_MAX:
        raise ValidationError(f"{what} must be 1..{NAME_RE_MAX} characters")
    if name in {".", ".."} or ".." in name:
        raise ValidationError(f"{what} rejects '..'")
    if name.startswith("/") or name.startswith("\\"):
        raise ValidationError(f"{what} rejects an absolute path")
    if "/" in name or "\\" in name or "\x00" in name:
        raise ValidationError(f"{what} rejects a path separator")
    if any(ch not in _ALLOWED for ch in name):
        raise ValidationError(f"{what} has characters outside [A-Za-z0-9._-]")
    return name


def slugify_callsign(callsign: str) -> str:
    """Turn a callsign into a filename-safe id. Does not invent a random id."""
    if not isinstance(callsign, str) or not callsign.strip():
        raise ValidationError("callsign is empty")
    if len(callsign) > 64:
        raise ValidationError("callsign is longer than 64 characters")
    if "\x00" in callsign or "/" in callsign or "\\" in callsign or ".." in callsign:
        raise ValidationError("callsign rejects path characters")
    pieces: list[str] = []
    for ch in callsign.lower():
        if ch.isascii() and ch.isalnum():
            pieces.append(ch)
        elif ch in {" ", "-", "_"}:
            pieces.append("-")
        else:
            raise ValidationError("callsign has characters the kernel will not store")
    slug = "".join(pieces).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return validate_name(slug, what="callsign slug")


class Workspace:
    """A resolved directory. Joins refuse to leave it."""

    def __init__(self, root: Path) -> None:
        if not isinstance(root, Path):
            root = Path(root)
        if any(part == ".." for part in root.parts):
            # Path('foo/../../etc') is caught before resolve escapes.
            raise ValidationError("workspace path rejects '..'")
        if root.is_symlink():
            raise IOPermissionError("workspace root is a symlink")
        self.root = root.resolve()

    def require_dir(self) -> None:
        if not self.root.is_dir():
            raise IOPermissionError(f"workspace does not exist: {self.root}")
        if self.root.is_symlink():
            raise IOPermissionError("workspace root is a symlink")

    def sub(self, *parts: str) -> Path:
        """Join safe segments. Existing symlinks that leave the root fail."""
        current = self.root
        for part in parts:
            validate_name(part, what="path segment")
            current = current / part
            if current.is_symlink():
                target = current.resolve()
                if not _is_inside(self.root, target):
                    raise ValidationError("symlink escapes the workspace")
        if current.exists() or current.is_symlink():
            resolved = current.resolve()
            if not _is_inside(self.root, resolved):
                raise ValidationError("path escapes the workspace")
        return current


def _is_inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def assert_mode(path: Path, required: int, *, directory: bool) -> None:
    """Check permission bits on an open descriptor, not a prior stat."""
    flags = os.O_RDONLY | os.O_NOFOLLOW
    if directory:
        flags |= os.O_DIRECTORY
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise IOPermissionError(f"cannot open {path.name} to check mode") from exc
    try:
        info = os.fstat(fd)
        if directory and not stat.S_ISDIR(info.st_mode):
            raise IOPermissionError(f"{path.name} is not a directory")
        if not directory and not stat.S_ISREG(info.st_mode):
            raise IOPermissionError(f"{path.name} is not a regular file")
        actual = stat.S_IMODE(info.st_mode)
        if actual != required:
            kind = "directory" if directory else "file"
            raise IOPermissionError(
                f"{path.name} is mode {actual:04o}; {kind} must be {required:04o}"
            )
    finally:
        os.close(fd)


def fchmod_nofollow(path: Path, mode: int, *, directory: bool) -> None:
    """Set mode through the opened inode. Do not follow a symlink."""
    flags = os.O_RDONLY | os.O_NOFOLLOW
    if directory:
        flags |= os.O_DIRECTORY
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise IOPermissionError(f"cannot open {path.name}") from exc
    try:
        os.fchmod(fd, mode)
        info = os.fstat(fd)
        if directory and not stat.S_ISDIR(info.st_mode):
            raise IOPermissionError(f"{path.name} is not a directory")
        if not directory and not stat.S_ISREG(info.st_mode):
            raise IOPermissionError(f"{path.name} is not a regular file")
        actual = stat.S_IMODE(info.st_mode)
        if actual != mode:
            raise IOPermissionError(f"{path.name} is mode {actual:04o}; must be {mode:04o}")
    finally:
        os.close(fd)


def write_nofollow(path: Path, data: bytes, mode: int) -> None:
    """Create or replace a regular file. A symlink is refused, not followed."""
    if path.is_symlink():
        raise IOPermissionError("refusing to write through a symlink")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, mode)
    except OSError as exc:
        raise IOPermissionError("cannot write file") from exc
    try:
        os.write(fd, data)
        os.fchmod(fd, mode)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != mode:
            raise IOPermissionError("file mode is not the requested mode")
        os.fsync(fd)
    finally:
        os.close(fd)


def create_private_dir(path: Path) -> None:
    """Create a directory at mode 0700. Refuse to reuse one. Do not follow a symlink."""
    if path.exists() or path.is_symlink():
        raise IOPermissionError(f"refusing to reuse {path.name}")
    os.mkdir(path, 0o700)
    fchmod_nofollow(path, 0o700, directory=True)


def prepare_workspace_dirs(root: Path) -> Workspace:
    """Create the workspace root if needed. Do not follow a symlinked root."""
    if any(part == ".." for part in Path(root).parts):
        raise ValidationError("workspace path rejects '..'")
    if root.is_symlink():
        raise IOPermissionError("workspace root is a symlink")
    root.mkdir(parents=True, exist_ok=True)
    ws = Workspace(root)
    ws.require_dir()
    return ws
