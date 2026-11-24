"""Workspace init is an explicit, resumable state machine (audit F5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vesper import fork
from vesper.cli import run
from vesper.crypto import load_identity
from vesper.errors import IOPermissionError
from vesper.fork import WorkspaceState, classify_workspace, init_workspace, load_state
from vesper.paths import INIT_MARKER_FILENAME, Workspace


def _fail_state_write(monkeypatch: pytest.MonkeyPatch) -> None:
    real = fork._write_regular

    def boom(path: Path, data: bytes, mode: int) -> None:
        if path.name == "state.json":
            raise OSError("disk full")
        real(path, data, mode)

    monkeypatch.setattr(fork, "_write_regular", boom)


def test_failed_init_is_partial_and_resumable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "ws"
    assert classify_workspace(root) is WorkspaceState.ABSENT
    with monkeypatch.context() as patch:
        _fail_state_write(patch)
        with pytest.raises(OSError):
            init_workspace(root, "nova", now=1)
    assert classify_workspace(root) is WorkspaceState.PARTIAL
    kid = load_identity(root / "identity").kid

    # The audit reproduction: init refused and every command failed for good.
    assert run(["init", "--workspace", str(root), "--callsign", "nova"]) == 3
    assert "vesper init --resume" in capsys.readouterr().err
    with pytest.raises(IOPermissionError, match="--resume"):
        load_state(Workspace(root))

    assert run(["init", "--workspace", str(root), "--callsign", "nova", "--resume"]) == 0
    assert classify_workspace(root) is WorkspaceState.READY
    assert not (root / INIT_MARKER_FILENAME).exists()
    assert load_identity(root / "identity").kid == kid
    assert load_state(Workspace(root))["head"] is None
    assert run(["--workspace", str(root), "fork", "--name", "alpha", "--now", "5"]) == 0


def test_identity_failure_is_partial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "ws"

    def boom(identity_dir: Path) -> None:
        identity_dir.mkdir(mode=0o700)
        raise OSError("disk full")

    with monkeypatch.context() as patch:
        patch.setattr(fork, "generate_identity", boom)
        with pytest.raises(OSError):
            init_workspace(root, "nova", now=1)
    assert classify_workspace(root) is WorkspaceState.PARTIAL
    # A half-written identity is never reused or deleted automatically.
    with pytest.raises(IOPermissionError, match="identity/ is incomplete"):
        init_workspace(root, "nova", now=1, resume=True)
    (root / "identity").rmdir()
    init_workspace(root, "nova", now=1, resume=True)
    assert classify_workspace(root) is WorkspaceState.READY


def test_stray_state_json_is_not_overwritten(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    stray = root / "state.json"
    stray.write_text('{"keep": true}\n', encoding="utf-8")
    assert classify_workspace(root) is WorkspaceState.FOREIGN
    for resume in (False, True):
        with pytest.raises(IOPermissionError, match="refusing to overwrite"):
            init_workspace(root, "nova", now=1, resume=resume)
    assert json.loads(stray.read_text(encoding="utf-8")) == {"keep": True}
    assert not (root / "identity").exists()


def test_ready_workspace_refuses_init_and_resume(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    init_workspace(root, "nova", now=1)
    assert classify_workspace(root) is WorkspaceState.READY
    for resume in (False, True):
        with pytest.raises(IOPermissionError, match="identity already exists"):
            init_workspace(root, "nova", now=1, resume=resume)
