"""VerifyResult is a closed union: Verified | Rejected (audit F7)."""

from __future__ import annotations

import dataclasses
import typing
from pathlib import Path

import pytest

from vesper.fork import (
    Reject,
    Rejected,
    Verified,
    VerifyResult,
    create_fork,
    init_workspace,
    verify_fork_file,
    verify_head,
)

ROOT = Path(__file__).resolve().parents[1]


def test_union_members() -> None:
    assert set(typing.get_args(VerifyResult)) == {Verified, Rejected}


def test_verified_always_has_a_document(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    init_workspace(root, "nova", now=1)
    path = create_fork(root, "alpha", now=5)
    assert path is not None
    result = verify_fork_file(path)
    assert isinstance(result, Verified)
    assert result.ok and result.reason == "ok"
    assert result.document["name"] == "alpha"
    assert len(result.content_hash) == 64
    assert isinstance(verify_head(root), Verified)


def test_rejected_has_a_typed_reason_and_no_document() -> None:
    result = verify_fork_file(ROOT / "fixtures" / "forged-fork.json")
    assert isinstance(result, Rejected)
    assert not result.ok
    assert isinstance(result.reason, Reject)
    assert result.reason == "bad_signature"
    assert not hasattr(result, "document")
    assert result.waivers == ()


def test_results_are_immutable(tmp_path: Path) -> None:
    rejected = Rejected(Reject.NAME)
    with pytest.raises(dataclasses.FrozenInstanceError):
        rejected.reason = Reject.REPLAY  # type: ignore[misc]


def test_every_reason_is_a_plain_string() -> None:
    # The CLI prints the reason; the strings must stay the same.
    assert [r.value for r in Reject] == [
        "name",
        "parent_missing",
        "canonical",
        "bad_signature",
        "schema_id",
        "state_hash",
        "kid",
        "parent_hash",
        "cycle",
        "replay",
        "no_head",
    ]
