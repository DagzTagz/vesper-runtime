"""Schema check and heal-or-reject."""

import json
from pathlib import Path

import pytest

from vesper.cli import run
from vesper.errors import ValidationError
from vesper.schema import check_document, heal, load_schema, read_json

ROOT = Path(__file__).resolve().parents[1]
DRIFTED = ROOT / "fixtures" / "drifted-state.json"


def test_schema_fixture_has_v2_shape() -> None:
    schema = load_schema()
    assert schema["type"] == "object"
    assert schema["required"] == ["universe_id", "schema_version", "character", "memory", "forks"]
    assert "memory_item" in schema["$defs"]


def test_drifted_fixture_fails_check() -> None:
    problems = check_document(read_json(DRIFTED))
    assert problems
    assert run(["schema", "check", str(DRIFTED)]) == 2


def test_heal_fills_defaults_and_keeps_unknown(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    original = json.loads(DRIFTED.read_text(encoding="utf-8"))
    target.write_text(DRIFTED.read_text(encoding="utf-8"), encoding="utf-8")
    assert run(["schema", "heal", str(target), "--write"]) == 0
    healed = json.loads(target.read_text(encoding="utf-8"))
    assert healed["character"]["id"] == original["character"]["id"]
    assert healed["builder_note"] == "preserve me"
    assert healed["memory"]["stm"][0]["tier"] == "stm"
    assert healed["memory"]["stm"][0]["pinned"] is False
    assert healed["memory"]["semantic"] == []
    assert healed["memory"]["graph"] == []
    assert healed["memory"]["ltm"] == []
    assert check_document(healed) == []


def test_heal_does_not_invent_character_id(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text(
        json.dumps(
            {
                "universe_id": "uni-x",
                "schema_version": "2",
                "character": {"callsign": "x", "straussian_level": 1},
                "memory": {"stm": [], "semantic": [], "graph": [], "ltm": []},
                "forks": [],
            }
        ),
        encoding="utf-8",
    )
    raw = path.read_text(encoding="utf-8")
    with pytest.raises(ValidationError, match="character.id"):
        heal(read_json(path))
    assert run(["schema", "heal", str(path), "--write"]) == 2
    assert path.read_text(encoding="utf-8") == raw


def test_wrong_identity_type_rejected() -> None:
    document = json.loads(DRIFTED.read_text(encoding="utf-8"))
    document["universe_id"] = 12
    with pytest.raises(ValidationError, match="universe_id"):
        heal(document)


def test_reserved_name_rejected() -> None:
    document = json.loads(DRIFTED.read_text(encoding="utf-8"))
    document["__proto__"] = "nope"
    with pytest.raises(ValidationError, match="reserved"):
        heal(document)


def test_non_finite_rejected() -> None:
    with pytest.raises(ValidationError, match="non-finite"):
        read_json_text = '{"universe_id": "u", "n": NaN}'
        from vesper.schema import loads_strict

        loads_strict(read_json_text)
