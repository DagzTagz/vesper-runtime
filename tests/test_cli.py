"""CLI exit codes and the init → remember → sleep → fork → verify path."""

import json
import stat
from pathlib import Path

import pytest

from vesper.cli import run
from vesper.fork import load_state
from vesper.paths import Workspace

ROOT = Path(__file__).resolve().parents[1]


def test_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as caught:
        run(["--help"])
    assert caught.value.code == 0


def test_usage_exit_one() -> None:
    assert run([]) == 1
    assert run(["remember"]) == 1
    assert run(["nope"]) == 1


def test_schema_and_forged_exit_codes() -> None:
    drifted = ROOT / "fixtures" / "drifted-state.json"
    forged = ROOT / "fixtures" / "forged-fork.json"
    assert run(["schema", "check", str(drifted)]) == 2
    assert run(["verify", str(forged)]) == 2


def test_operator_path(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    assert run(["init", "--workspace", str(root), "--callsign", "Vesper"]) == 0
    key = root / "identity" / "edcsa-p256.priv"
    assert stat.S_IMODE(key.stat().st_mode) == 0o600
    assert stat.S_IMODE((root / "identity").stat().st_mode) == 0o700
    public = json.loads((root / "identity" / "public.json").read_text(encoding="utf-8"))
    assert public["algo"] == "ecdsa-p256"
    assert "BEGIN" not in json.dumps(public)
    assert run(
        [
            "--workspace",
            str(root),
            "remember",
            "--text",
            "first session",
            "--valence",
            "0.3",
            "--tier",
            "semantic",
            "--weight",
            "1.0",
            "--now",
            "0",
            "--id",
            "m-1",
        ]
    ) == 0
    assert run(["--workspace", str(root), "sleep", "--now", "36000"]) == 0
    state = load_state(Workspace(root))
    assert state["memory"]["semantic"][0]["weight"] < 1.0
    assert run(["--workspace", str(root), "fork", "--name", "alpha", "--now", "36001"]) == 0
    assert run(["--workspace", str(root), "verify", "--head"]) == 0
    fork_path = root / "forks" / "alpha.json"
    assert run(["verify", str(fork_path)]) == 0
    assert run(["--workspace", str(root), "fork", "--name", "../beta"]) == 2


def test_link_and_memory_export(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "ws"
    assert run(["init", "--workspace", str(root), "--callsign", "vesper"]) == 0
    assert run(
        ["--workspace", str(root), "link", "--src", "b", "--dst", "a", "--rel", "knows", "--weight", "0.2", "--now", "3"]
    ) == 0
    assert run(["--workspace", str(root), "memory", "export"]) == 0
    captured = capsys.readouterr()
    start = captured.out.find('\n{')
    assert start != -1
    document = json.loads(captured.out[start + 1:])
    assert document["graph"][0]["src"] == "a"
    assert document["graph"][0]["dst"] == "b"
