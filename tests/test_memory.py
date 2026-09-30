"""Four-tier memory. Clocks are injected. Nothing sleeps for real."""

import copy
import math

import pytest

from vesper.errors import ValidationError
from vesper.memory import (
    DECAY_LAMBDA_PER_HOUR,
    STM_CAP,
    add_edge,
    clamp_weight,
    empty_memory,
    new_item,
    remember,
    sleep_state,
)


def _state(seed: int = 0, user_weight: float = 1.0) -> dict:
    return {"memory": empty_memory(), "user_weight": user_weight, "seed": seed}


def test_stm_drops_oldest_at_cap() -> None:
    state = _state()
    first = None
    for index in range(STM_CAP + 1):
        item = new_item(
            text=f"n{index}",
            valence=0.1,
            now=index,
            tier="stm",
            pinned=False,
            weight=0.1,
            item_id=f"m-{index}",
        )
        if index == 0:
            first = item["id"]
        remember(state, item)
    assert len(state["memory"]["stm"]) == STM_CAP
    assert first not in {item["id"] for item in state["memory"]["stm"]}
    assert state["memory"]["stm"][-1]["id"] == f"m-{STM_CAP}"


def test_nan_weight_rejected() -> None:
    with pytest.raises(ValidationError, match="finite"):
        clamp_weight(float("nan"))
    with pytest.raises(ValidationError, match="finite"):
        clamp_weight(float("inf"))


def test_weight_clamped_into_unit_interval() -> None:
    assert clamp_weight(1.4) == 1.0
    assert clamp_weight(-0.2) == 0.0


def test_decay_requires_elapsed_time() -> None:
    state = _state()
    remember(
        state,
        new_item(text="keep", valence=0.3, now=1_000, tier="semantic", pinned=False, weight=1.0, item_id="m-1"),
    )
    same = copy.deepcopy(state)
    sleep_state(same, 1_000)
    assert same["memory"]["semantic"][0]["weight"] == 1.0
    moved = copy.deepcopy(state)
    sleep_state(moved, 1_000 + 10 * 3600)
    expected = round(math.exp(-DECAY_LAMBDA_PER_HOUR * 10), 10)
    assert moved["memory"]["semantic"][0]["weight"] == expected
    assert expected < 1.0


def test_semantic_drop_and_pin() -> None:
    state = _state()
    remember(
        state,
        new_item(text="fade", valence=0.3, now=0, tier="semantic", pinned=False, weight=0.03, item_id="m-fade"),
    )
    remember(
        state,
        new_item(text="stay", valence=0.3, now=0, tier="semantic", pinned=True, weight=0.03, item_id="m-pin"),
    )
    sleep_state(state, 100 * 3600)
    ids = {item["id"] for item in state["memory"]["semantic"]}
    assert "m-fade" not in ids
    assert "m-pin" not in ids
    assert "m-pin" in {item["id"] for item in state["memory"]["ltm"]}


def test_graph_prune_keeps_pins() -> None:
    state = _state()
    add_edge(state, src="b", dst="a", rel="knows", weight=0.04, now=1, edge_id="g-low")
    add_edge(state, src="a", dst="c", rel="knows", weight=0.04, now=1, pinned=True, edge_id="g-pin")
    add_edge(state, src="c", dst="b", rel="knows", weight=0.2, now=1, edge_id="g-ok")
    assert state["memory"]["graph"][0]["src"] == "a"
    sleep_state(state, 2)
    ids = {edge["id"] for edge in state["memory"]["graph"]}
    assert ids == {"g-pin", "g-ok"}


def test_ltm_promotion_and_no_autodelete() -> None:
    state = _state()
    remember(
        state,
        new_item(text="hot", valence=0.8, now=1, tier="stm", pinned=False, weight=0.8, item_id="m-hot"),
    )
    remember(
        state,
        new_item(text="cold", valence=0.2, now=1, tier="stm", pinned=False, weight=0.2, item_id="m-cold"),
    )
    state["memory"]["ltm"].append(
        {
            "id": "m-old",
            "ts": 1,
            "text": "archive",
            "valence": 0.1,
            "weight": 0.01,
            "tier": "ltm",
            "pinned": False,
        }
    )
    sleep_state(state, 1)
    ltm = {item["id"] for item in state["memory"]["ltm"]}
    stm = {item["id"] for item in state["memory"]["stm"]}
    assert "m-hot" in ltm
    assert "m-cold" in stm
    assert "m-old" in ltm


def test_user_weight_bounds() -> None:
    from vesper.memory import parse_user_weight

    assert parse_user_weight(2) == 2.0
    with pytest.raises(ValidationError):
        parse_user_weight(0)
    with pytest.raises(ValidationError):
        parse_user_weight(2.1)


def test_ltm_duplicate_is_deterministic() -> None:
    def snap(seed: int) -> dict:
        state = _state(seed=seed)
        state["memory"]["ltm"] = [
            {"id": "m-dup", "ts": 1, "text": "left", "valence": 0.5, "weight": 0.5, "tier": "ltm", "pinned": False},
            {"id": "m-dup", "ts": 2, "text": "right", "valence": 0.5, "weight": 0.5, "tier": "ltm", "pinned": False},
        ]
        return state

    winners = set()
    for seed in range(30):
        a = snap(seed)
        b = snap(seed)
        sleep_state(a, 5)
        sleep_state(b, 5)
        assert a["memory"]["ltm"] == b["memory"]["ltm"]
        assert len(a["memory"]["ltm"]) == 1
        winners.add(a["memory"]["ltm"][0]["text"])
    assert winners == {"left", "right"}


def test_event_id_traversal_rejected() -> None:
    state = _state()
    with pytest.raises(ValidationError):
        new_item(text="x", valence=0.2, now=1, tier="stm", pinned=False, item_id="../x")
    with pytest.raises(ValidationError):
        add_edge(state, src="../a", dst="b", rel="knows", weight=0.2, now=1)
