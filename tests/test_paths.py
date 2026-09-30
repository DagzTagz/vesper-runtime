"""T6: names and joins stay inside the workspace."""

from pathlib import Path

import pytest

from vesper.errors import IOPermissionError, ValidationError
from vesper.paths import Workspace, prepare_workspace_dirs, validate_name, write_nofollow


@pytest.mark.parametrize(
    "name",
    ["../etc/passwd", "/etc/passwd", "..", ".", "a/b", "a\\b", "a..b", "", "x" * 129, "has space"],
)
def test_rejects_unsafe_names(name: str) -> None:
    with pytest.raises(ValidationError):
        validate_name(name, what="event id")


def test_accepts_plain_name() -> None:
    assert validate_name("fork-1.alpha") == "fork-1.alpha"


def test_join_stays_inside(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    path = ws.sub("forks", "alpha.json")
    assert path.parent == tmp_path / "forks"
    assert path.name == "alpha.json"


def test_absolute_segment_rejected(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    with pytest.raises(ValidationError):
        ws.sub("/etc")


def test_symlink_escape_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "ws"
    root.mkdir()
    (root / "forks").symlink_to(outside)
    ws = Workspace(root)
    with pytest.raises(ValidationError):
        ws.sub("forks")


def test_workspace_dotdot_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        prepare_workspace_dirs(tmp_path / "ws" / ".." / "elsewhere")


def test_write_nofollow_does_not_follow_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.write_bytes(b"keep")
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(IOPermissionError):
        write_nofollow(link, b"nope", 0o600)
    assert target.read_bytes() == b"keep"


def test_symlinked_root_rejected(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(IOPermissionError):
        Workspace(link)
