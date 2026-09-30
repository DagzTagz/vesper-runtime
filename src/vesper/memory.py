"""Four-tier memory. Sleep is a pure function of (state, now, seed).

Order on sleep:
  1. Decay semantic weights by exp(-lambda * hours). lambda is 0.02 per hour.
  2. Drop semantic items with weight < 0.02 and valence < 0.4, unless pinned.
  3. Prune graph edges with weight < 0.05, unless pinned.
  4. Promote stm and semantic items to ltm when
     (weight * valence * user_weight) >= 0.45, or pinned is true.
  5. Compact ltm items that share an id. Keep the max weight.
     Equal weights break ties with SHA-256(seed | text | ts).

STM is append-only and capped at 100. On overflow the oldest (ts, id) is
dropped. LTM is not auto-deleted. Hours use the injected clock. now == ts
applies a factor of 1, so tests must move the clock to see decay.
Weights must be finite; they are then clamped into [0, 1].
"""

from __future__ import annotations

import hashlib
import math
from typing import Any

from vesper.errors import ValidationError
from vesper.paths import validate_name

STM_CAP = 100
DECAY_LAMBDA_PER_HOUR = 0.02
SEMANTIC_DROP_WEIGHT = 0.02
SEMANTIC_DROP_VALENCE = 0.4
GRAPH_PRUNE_WEIGHT = 0.05
LTM_PROMOTE_SCORE = 0.45
TEXT_MAX = 4096
USER_WEIGHT_DEFAULT = 1.0


def clamp_weight(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("weight is not a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValidationError("weight is not a finite number")
    if number < 0.0:
        number = 0.0
    elif number > 1.0:
        number = 1.0
    return round(number, 10)


def parse_valence(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("valence is not a finite number")
    number = float(value)
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        raise ValidationError("valence is outside [0, 1]")
    return number


def parse_user_weight(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("user_weight is not a finite number")
    number = float(value)
    if not math.isfinite(number) or number <= 0.0 or number > 2.0:
        raise ValidationError("user_weight must be in (0, 2]")
    return number


def _require_int(value: object, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{what} must be an integer")
    return value


def empty_memory() -> dict[str, list[dict[str, Any]]]:
    return {"stm": [], "semantic": [], "graph": [], "ltm": []}


def new_item(
    *,
    text: str,
    valence: float,
    now: int,
    tier: str,
    pinned: bool,
    weight: float = 1.0,
    item_id: str | None = None,
    existing: int = 0,
) -> dict[str, Any]:
    if tier not in {"stm", "semantic", "ltm"}:
        raise ValidationError("tier must be stm, semantic, or ltm")
    if not isinstance(text, str) or not text or len(text) > TEXT_MAX:
        raise ValidationError("text must be 1..4096 characters")
    valence = parse_valence(valence)
    weight = clamp_weight(weight)
    now = _require_int(now, "now")
    if item_id is None:
        digest = hashlib.sha256(f"{tier}|{now}|{text}|{existing}".encode("utf-8")).hexdigest()[:16]
        item_id = f"m-{digest}"
    validate_name(item_id, what="event id")
    return {
        "id": item_id,
        "ts": now,
        "text": text,
        "valence": valence,
        "weight": weight,
        "tier": tier,
        "pinned": bool(pinned),
    }


def _ids(state: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    memory = state["memory"]
    for tier in ("stm", "semantic", "ltm"):
        for item in memory[tier]:
            found.add(item["id"])
    for edge in memory["graph"]:
        found.add(edge["id"])
    return found


def remember(state: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    """Append a text item. STM drops the oldest item past the cap of 100."""
    if item["id"] in _ids(state):
        raise ValidationError("event id already exists")
    tier = item["tier"]
    state["memory"][tier].append(item)
    if tier == "stm":
        while len(state["memory"]["stm"]) > STM_CAP:
            stm = state["memory"]["stm"]
            index = min(range(len(stm)), key=lambda i: (stm[i]["ts"], stm[i]["id"]))
            del stm[index]
    return state


def add_edge(
    state: dict[str, Any],
    *,
    src: str,
    dst: str,
    rel: str,
    weight: float,
    now: int,
    pinned: bool = False,
    edge_id: str | None = None,
) -> dict[str, Any]:
    """Insert an undirected edge. src and dst are stored in sorted order."""
    src = validate_name(src, what="edge src")
    dst = validate_name(dst, what="edge dst")
    rel = validate_name(rel, what="edge rel")
    if src == dst:
        raise ValidationError("edge src and dst must differ")
    if src > dst:
        src, dst = dst, src
    weight = clamp_weight(weight)
    now = _require_int(now, "now")
    if edge_id is None:
        digest = hashlib.sha256(f"{src}|{dst}|{rel}|{now}".encode("utf-8")).hexdigest()[:16]
        edge_id = f"g-{digest}"
    edge_id = validate_name(edge_id, what="edge id")
    if edge_id in _ids(state):
        raise ValidationError("edge id already exists")
    state["memory"]["graph"].append(
        {
            "id": edge_id,
            "src": src,
            "dst": dst,
            "rel": rel,
            "weight": weight,
            "pinned": bool(pinned),
            "ts": now,
        }
    )
    return state


def _decay_lambda(state: dict[str, Any]) -> float:
    if "decay_lambda" not in state or state["decay_lambda"] is None:
        return DECAY_LAMBDA_PER_HOUR
    value = state["decay_lambda"]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("decay_lambda is not a finite number")
    number = float(value)
    if not math.isfinite(number) or number <= 0.0 or number > 1.0:
        raise ValidationError("decay_lambda must be in (0, 1]")
    return number


def _hours(now: int, then: int) -> float:
    if now < then:
        return 0.0
    return (now - then) / 3600.0


def _tie_key(seed: int, item: dict[str, Any]) -> str:
    raw = f"{seed}|{item.get('text', '')}|{item.get('ts', '')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sleep_state(state: dict[str, Any], now: int) -> dict[str, Any]:
    """Return the same state object after a deterministic consolidation."""
    now = _require_int(now, "now")
    lam = _decay_lambda(state)
    user_weight = parse_user_weight(state.get("user_weight", USER_WEIGHT_DEFAULT))
    state["user_weight"] = user_weight
    seed = state.get("seed", 0)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValidationError("seed must be an integer")
    memory = state["memory"]

    for item in memory["semantic"]:
        item["weight"] = clamp_weight(item["weight"])
        item["valence"] = parse_valence(item["valence"])
        base = item.get("last_decay_unix", item["ts"])
        base = _require_int(base, "last_decay_unix")
        if now < base:
            continue
        hours = _hours(now, base)
        item["weight"] = clamp_weight(item["weight"] * math.exp(-lam * hours))
        item["last_decay_unix"] = now

    memory["semantic"] = [
        item
        for item in memory["semantic"]
        if item.get("pinned") is True
        or not (
            item["weight"] < SEMANTIC_DROP_WEIGHT and item["valence"] < SEMANTIC_DROP_VALENCE
        )
    ]

    kept_edges = []
    for edge in memory["graph"]:
        edge["weight"] = clamp_weight(edge["weight"])
        if edge.get("pinned") is True or edge["weight"] >= GRAPH_PRUNE_WEIGHT:
            kept_edges.append(edge)
    memory["graph"] = sorted(kept_edges, key=lambda edge: (edge["src"], edge["dst"], edge["rel"], edge["id"]))

    promoted: list[dict[str, Any]] = []
    for tier in ("stm", "semantic"):
        stay: list[dict[str, Any]] = []
        for item in memory[tier]:
            item["weight"] = clamp_weight(item["weight"])
            item["valence"] = parse_valence(item["valence"])
            score = item["weight"] * item["valence"] * user_weight
            if item.get("pinned") is True or score >= LTM_PROMOTE_SCORE:
                item["tier"] = "ltm"
                promoted.append(item)
            else:
                stay.append(item)
        memory[tier] = stay
    promoted.sort(key=lambda item: item["id"])
    memory["ltm"].extend(promoted)
    memory["ltm"] = _compact_ltm(memory["ltm"], seed)
    state["last_sleep_unix"] = now
    return state


def _compact_ltm(items: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in items:
        item["weight"] = clamp_weight(item["weight"])
        current = grouped.get(item["id"])
        if current is None:
            grouped[item["id"]] = item
            continue
        if item["weight"] > current["weight"]:
            grouped[item["id"]] = item
            continue
        if item["weight"] < current["weight"]:
            continue
        if _tie_key(seed, item) > _tie_key(seed, current):
            grouped[item["id"]] = item
    return [grouped[key] for key in sorted(grouped)]
