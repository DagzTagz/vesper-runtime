"""An item's tier is its list; load_state refuses a disagreement (audit F11)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from vesper.cli import run
from vesper.errors import ValidationError
from vesper.fork import init_workspace, load_state
from vesper.paths import Workspace


def _edit_state(root: Path, edit) -> None:
    path = root / "state.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    edit(state)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def _item(tier: str) -> dict:
    return {"id": "m-x", "ts": 1, "text": "t", "valence": 0.5, "weight": 1.0, "tier": tier, "pinned": False}


def test_tier_mismatch_is_refused_on_load(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "ws"
    init_workspace(root, "nova", now=1)
    _edit_state(root, lambda s: s["memory"]["stm"].append(_item("ltm")))
    with pytest.raises(ValidationError, match="tier does not match its list"):
        load_state(Workspace(root))
    # Before the fix, remember/sleep/fork carried the inconsistent item on.
    assert run(["--workspace", str(root), "sleep", "--now", "100"]) == 2
    assert "tier does not match" in capsys.readouterr().err


def test_missing_tier_field_is_still_accepted(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    init_workspace(root, "nova", now=1)

    def add(state: dict) -> None:
        item = _item("semantic")
        del item["tier"]
        state["memory"]["semantic"].append(item)

    _edit_state(root, add)
    assert load_state(Workspace(root))["memory"]["semantic"][0]["id"] == "m-x"


def test_promotion_keeps_tier_and_list_in_step(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    init_workspace(root, "nova", now=1)
    assert run(["--workspace", str(root), "remember", "--text", "hot", "--valence", "0.9", "--weight", "0.9", "--now", "2", "--pin"]) == 0
    assert run(["--workspace", str(root), "sleep", "--now", "3"]) == 0
    state = load_state(Workspace(root))
    for tier in ("stm", "semantic", "ltm"):
        assert all(item["tier"] == tier for item in state["memory"][tier])
