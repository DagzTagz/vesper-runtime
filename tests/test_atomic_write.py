"""fork._write_regular leaves no temp file behind when it fails."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from vesper import fork


def test_failed_write_removes_temp_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "state.json"

    def boom(fd: int, mode: int) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(fork.os, "fchmod", boom)
    with pytest.raises(OSError):
        fork._write_regular(target, b"{}\n", 0o600)
    assert sorted(os.listdir(tmp_path)) == []


def test_failed_rename_removes_temp_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "state.json"

    def boom(src: str, dst: object) -> None:
        raise OSError("rename failed")

    monkeypatch.setattr(fork.os, "replace", boom)
    with pytest.raises(OSError):
        fork._write_regular(target, b"{}\n", 0o600)
    assert sorted(os.listdir(tmp_path)) == []
