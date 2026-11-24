"""A fork commit is journalled, locked, and recoverable (audit F4)."""

from __future__ import annotations

import fcntl
import os
from pathlib import Path

import pytest

from vesper import fork
from vesper.cli import run
from vesper.fork import (
    PendingFork,
    create_fork,
    init_workspace,
    load_state,
    recover_pending,
    verify_head,
    workspace_lock,
)
from vesper.paths import LOCK_FILENAME, PENDING_FORK_FILENAME, Workspace


def _workspace(tmp_path: Path) -> tuple[Path, Workspace]:
    root = tmp_path / "ws"
    init_workspace(root, "nova", now=1)
    create_fork(root, "alpha", now=10)
    assert verify_head(root).ok
    return root, Workspace(root)


def test_state_write_failure_is_recovered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # The audit reproduction: save_state raised after forks/beta.json was
    # published, and verify --head then reported "replay" indefinitely.
    root, ws = _workspace(tmp_path)
    with monkeypatch.context() as patch:

        def boom(ws_: Workspace, state: dict) -> None:
            raise OSError("disk full")

        patch.setattr(fork, "save_state", boom)
        with pytest.raises(OSError):
            create_fork(root, "beta", now=20)
    assert (root / "forks" / "beta.json").is_file()
    assert (root / PENDING_FORK_FILENAME).is_file()

    assert run(["--workspace", str(root), "verify", "--head"]) == 0
    captured = capsys.readouterr()
    assert "verify ok" in captured.out
    assert "interrupted fork committed" in captured.err
    state = load_state(ws)
    assert state["head"] == "beta"
    assert state["forks"] == ["alpha", "beta"]
    assert not (root / PENDING_FORK_FILENAME).exists()
    assert create_fork(root, "gamma", now=30) is not None
    assert verify_head(root).ok


def test_failure_before_fork_file_is_rolled_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, ws = _workspace(tmp_path)
    real = fork._write_regular

    def boom(path: Path, data: bytes, mode: int) -> None:
        if path.name == "beta.json":
            raise OSError("disk full")
        real(path, data, mode)

    with monkeypatch.context() as patch:
        patch.setattr(fork, "_write_regular", boom)
        with pytest.raises(OSError):
            create_fork(root, "beta", now=20)
    assert (root / PENDING_FORK_FILENAME).is_file()
    with workspace_lock(ws):
        assert recover_pending(ws) is PendingFork.DISCARDED
    assert load_state(ws)["head"] == "alpha"
    assert not (root / "forks" / "beta.json").exists()
    assert verify_head(root).ok
    assert create_fork(root, "beta", now=20) is not None


def test_recovery_runs_before_the_next_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, ws = _workspace(tmp_path)
    with monkeypatch.context() as patch:
        patch.setattr(fork, "save_state", lambda ws_, state: (_ for _ in ()).throw(OSError("x")))
        with pytest.raises(OSError):
            create_fork(root, "beta", now=20)
    assert run(["--workspace", str(root), "remember", "--text", "t", "--valence", "0.2", "--now", "30"]) == 0
    state = load_state(ws)
    assert state["head"] == "beta"
    assert len(state["memory"]["stm"]) == 1
    assert verify_head(root).ok


def _lock_is_held(root: Path) -> bool:
    fd = os.open(root / LOCK_FILENAME, os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return True
    finally:
        os.close(fd)
    return False


def test_fork_and_state_writes_hold_the_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, ws = _workspace(tmp_path)
    seen: list[bool] = []
    real = fork.save_state

    def probe(ws_: Workspace, state: dict) -> None:
        seen.append(_lock_is_held(root))
        real(ws_, state)

    monkeypatch.setattr(fork, "save_state", probe)
    monkeypatch.setattr("vesper.cli.save_state", probe)
    create_fork(root, "beta", now=20)
    assert run(["--workspace", str(root), "remember", "--text", "t", "--valence", "0.2", "--now", "30"]) == 0
    assert run(["--workspace", str(root), "sleep", "--now", "40"]) == 0
    assert seen == [True, True, True]
    assert not _lock_is_held(root)


def test_dry_run_fork_takes_no_lock(tmp_path: Path) -> None:
    root, _ = _workspace(tmp_path)
    (root / LOCK_FILENAME).unlink()
    assert create_fork(root, "beta", dry_run=True, now=20) is None
    assert not (root / LOCK_FILENAME).exists()
