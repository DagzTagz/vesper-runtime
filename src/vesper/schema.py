"""Uni Schema v2 loader, checker, and heal-or-reject.

Heal may fill documented structural defaults. It does not invent character
ids, callsigns, universe ids, schema versions, memory text, or keys.
Required identity fields with the wrong type are a hard reject.
Unknown properties are kept, except a short reserved-name list.
"""

from __future__ import annotations

import json
import math
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

from vesper.errors import IOPermissionError, ValidationError

RESERVED_NAMES = frozenset({"__proto__", "constructor", "prototype"})
MEMORY_LISTS = ("stm", "semantic", "graph", "ltm")
ITEM_LISTS = ("stm", "semantic", "ltm")

# Defaults heal is allowed to add. Identity fields are not in this set.
HEAL_DEFAULTS = (
    "memory.stm/semantic/graph/ltm = [] when the memory object exists but a list is missing",
    "memory item pinned = false when the field is absent",
    "memory item tier = the list name when tier is absent",
    "user_weight = 1.0 when absent",
    "seed = 0 when absent",
    "finite weight is clamped into [0, 1] when present",
)


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        fixture = parent / "fixtures" / "dagztagz-uni-schema-v2.json"
        if fixture.is_file() and (parent / "pyproject.toml").is_file():
            return parent
    raise IOPermissionError("schema fixture is not in the source tree")


def default_schema_path() -> Path:
    return repo_root() / "fixtures" / "dagztagz-uni-schema-v2.json"


def read_json(path: Path) -> Any:
    """Load JSON. Reject NaN, Infinity, and symlink paths."""
    if ".." in path.parts:
        raise ValidationError("path traversal rejected")
    if path.is_symlink():
        raise ValidationError("symlink rejected")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise IOPermissionError(f"cannot read {path.name}") from exc
    return loads_strict(text)


def loads_strict(text: str) -> Any:
    def _reject(name: str) -> None:
        raise ValidationError(f"non-finite number {name}")

    try:
        return json.loads(text, parse_constant=_reject)
    except ValidationError:
        raise
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON: {exc.msg}") from exc


def load_schema(path: Path | None = None) -> dict[str, Any]:
    schema = read_json(path or default_schema_path())
    if not isinstance(schema, dict):
        raise ValidationError("schema is not an object")
    if schema.get("title") is None or schema.get("type") != "object":
        raise ValidationError("schema is not Uni Schema v2")
    return schema


def _type_ok(expected: str, instance: object) -> bool:
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        if isinstance(instance, bool) or not isinstance(instance, (int, float)):
            return False
        return isinstance(instance, int) or math.isfinite(instance)
    return False


def _resolve_ref(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if ref is None:
        return schema
    if not isinstance(ref, str) or not ref.startswith("#/"):
        raise ValidationError("unsupported schema $ref")
    node: object = root
    for part in ref[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            raise ValidationError("unresolved schema $ref")
        node = node[part]
    if not isinstance(node, dict):
        raise ValidationError("schema $ref is not an object")
    return node


def validate(schema: dict[str, Any], instance: object, root: dict[str, Any] | None = None, path: str = "$") -> list[str]:
    """Return a list of human-readable errors. Empty means the instance matches."""
    root = schema if root is None else root
    schema = _resolve_ref(schema, root)
    errors: list[str] = []
    expected = schema.get("type")
    if isinstance(expected, str) and not _type_ok(expected, instance):
        return [f"{path}: expected {expected}"]
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value is not in the enum")
    if "minLength" in schema and isinstance(instance, str) and len(instance) < int(schema["minLength"]):
        errors.append(f"{path}: shorter than minLength")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if isinstance(instance, float) and not math.isfinite(instance):
            errors.append(f"{path}: non-finite")
        else:
            if "minimum" in schema and instance < schema["minimum"]:
                errors.append(f"{path}: below minimum")
            if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
                errors.append(f"{path}: not above exclusiveMinimum")
            if "maximum" in schema and instance > schema["maximum"]:
                errors.append(f"{path}: above maximum")
    if expected == "object":
        if not isinstance(instance, dict):
            return errors
        props = schema.get("properties") or {}
        required = schema.get("required") or []
        additional = schema.get("additionalProperties", True)
        for key in required:
            if key not in instance:
                errors.append(f"{path}.{key}: required")
        for key, value in instance.items():
            if key in RESERVED_NAMES:
                errors.append(f"{path}.{key}: reserved name")
                continue
            if key in props:
                errors.extend(validate(props[key], value, root, f"{path}.{key}"))
            elif additional is False:
                errors.append(f"{path}.{key}: unknown property")
            elif isinstance(additional, dict):
                errors.extend(validate(additional, value, root, f"{path}.{key}"))
    if expected == "array" and isinstance(instance, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for index, value in enumerate(instance):
                errors.extend(validate(items, value, root, f"{path}[{index}]"))
    return errors


def _require_identity(doc: dict[str, Any]) -> None:
    universe = doc.get("universe_id")
    if not isinstance(universe, str) or not universe:
        raise ValidationError("required identity field universe_id is absent or wrong type")
    version = doc.get("schema_version")
    if not isinstance(version, str) or not version:
        raise ValidationError("required field schema_version is absent or wrong type")
    character = doc.get("character")
    if not isinstance(character, dict):
        raise ValidationError("required identity field character is absent or wrong type")
    if not isinstance(character.get("id"), str) or not character.get("id"):
        raise ValidationError("required identity field character.id is absent or wrong type")
    if not isinstance(character.get("callsign"), str) or character.get("callsign") == "":
        raise ValidationError("required identity field character.callsign is absent or wrong type")
    level = character.get("straussian_level", None)
    if "straussian_level" not in character or not _finite_number(level):
        raise ValidationError("required field character.straussian_level is absent or wrong type")


def _finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return isinstance(value, int) or math.isfinite(value)


def _clamp_weight(value: object) -> float:
    if not _finite_number(value):
        raise ValidationError("weight is missing or not a finite number")
    number = float(value)  # type: ignore[arg-type]
    if number < 0.0:
        number = 0.0
    elif number > 1.0:
        number = 1.0
    return round(number, 10)


def _check_item_types(item: dict[str, Any]) -> None:
    if not isinstance(item.get("id"), str) or not item.get("id"):
        raise ValidationError("memory item id is absent or wrong type")
    if not _finite_number(item.get("ts")):
        raise ValidationError("memory item ts is absent or wrong type")
    if not isinstance(item.get("text"), str):
        raise ValidationError("memory item text is absent or wrong type")
    valence = item.get("valence")
    if not _finite_number(valence) or not 0.0 <= float(valence) <= 1.0:  # type: ignore[arg-type]
        raise ValidationError("memory item valence is absent or out of range")
    item["weight"] = _clamp_weight(item.get("weight"))
    if item.get("tier") not in ITEM_LISTS:
        raise ValidationError("memory item tier is absent or wrong type")
    if not isinstance(item.get("pinned"), bool):
        raise ValidationError("memory item pinned is absent or wrong type")


def _reject_reserved(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in RESERVED_NAMES:
                raise ValidationError(f"reserved name {key}")
            _reject_reserved(child)
    elif isinstance(value, list):
        for child in value:
            _reject_reserved(child)


def heal(document: object, schema: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a healed document or raise ValidationError. Does not write."""
    if not isinstance(document, dict):
        raise ValidationError("state must be a JSON object")
    try:
        doc = json.loads(json.dumps(document, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ValidationError("non-finite number") from exc
    _reject_reserved(doc)
    _require_identity(doc)
    memory = doc.get("memory")
    if not isinstance(memory, dict):
        raise ValidationError("required field memory is absent or wrong type")
    if "forks" not in doc or not isinstance(doc.get("forks"), list):
        raise ValidationError("required field forks is absent or wrong type")
    for tier in MEMORY_LISTS:
        if tier not in memory:
            memory[tier] = []
        if not isinstance(memory[tier], list):
            raise ValidationError(f"memory.{tier} has the wrong type")
    for tier in ITEM_LISTS:
        for item in memory[tier]:
            if not isinstance(item, dict):
                raise ValidationError("memory item has the wrong type")
            if "tier" not in item:
                item["tier"] = tier
            elif item.get("tier") != tier:
                raise ValidationError("memory item tier does not match its list")
            if "pinned" not in item:
                item["pinned"] = False
            _check_item_types(item)
    for edge in memory["graph"]:
        if not isinstance(edge, dict):
            raise ValidationError("graph edge has the wrong type")
        if "pinned" not in edge:
            edge["pinned"] = False
        for field in ("id", "src", "dst", "rel"):
            if not isinstance(edge.get(field), str) or not edge.get(field):
                raise ValidationError(f"graph edge {field} is absent or wrong type")
        edge["weight"] = _clamp_weight(edge.get("weight"))
    if "user_weight" not in doc:
        doc["user_weight"] = 1.0
    elif not _finite_number(doc["user_weight"]) or not 0.0 < float(doc["user_weight"]) <= 2.0:
        raise ValidationError("user_weight is out of range")
    if "seed" not in doc:
        doc["seed"] = 0
    elif isinstance(doc["seed"], bool) or not isinstance(doc["seed"], int):
        raise ValidationError("seed has the wrong type")
    schema = schema or load_schema()
    problems = validate(schema, doc)
    if problems:
        raise ValidationError("; ".join(problems))
    return doc


def check_document(document: object, schema: dict[str, Any] | None = None) -> list[str]:
    schema = schema or load_schema()
    if not isinstance(document, dict):
        return ["$: expected object"]
    try:
        _reject_reserved(document)
    except ValidationError as exc:
        return [str(exc)]
    return validate(schema, document)


def _write_mode(path: Path) -> int:
    """Keep a private mode. A new file, or a looser one, stays 0644."""
    default = 0o644
    if not path.exists():
        return default
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        return default
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return default
        current = stat.S_IMODE(info.st_mode)
    finally:
        os.close(fd)
    if current == 0 or current & ~0o644:
        return default
    return current


def write_json_atomic(path: Path, document: dict[str, Any]) -> None:
    """Replace a regular file. Refuse a symlink so the write cannot leave the named path."""
    if ".." in path.parts:
        raise ValidationError("path traversal rejected")
    if path.is_symlink():
        raise ValidationError("symlink rejected")
    parent = path.parent
    if not parent.is_dir():
        raise IOPermissionError("destination directory is missing")
    mode = _write_mode(path)
    payload = json.dumps(document, sort_keys=True, indent=2, allow_nan=False, ensure_ascii=False) + "\n"
    fd, tmp_name = tempfile.mkstemp(dir=parent, prefix=".vesper-", suffix=".tmp")
    try:
        os.write(fd, payload.encode("utf-8"))
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp_name, path)
