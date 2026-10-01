"""Workspace init and signed forks.

A fork file is a JSON object. Every field except `signature` is the signed
body. parent_hash is SHA-256 of the parent's canonical signed body.
state_hash is SHA-256 of the canonical state object inside the body.
The filename stem must equal `name`. An older snapshot copied onto a newer
head name fails that check.
"""

from __future__ import annotations

import copy
import hmac
import json
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vesper import crypto as crypto_mod
from vesper.crypto import (
    Identity,
    canonical_bytes,
    generate_identity,
    load_identity,
    public_kid_matches,
    sha256_hex,
    verify_signature,
)
from vesper.errors import CryptoError, IOPermissionError, ValidationError
from vesper.memory import empty_memory, parse_user_weight
from vesper.paths import (
    ECDSA_KEY_FILENAME,
    FORKS_DIRNAME,
    HMAC_KEY_FILENAME,
    IDENTITY_DIRNAME,
    STATE_FILENAME,
    Workspace,
    assert_mode,
    create_private_dir,
    prepare_workspace_dirs,
    slugify_callsign,
    validate_name,
)
from vesper.schema import loads_strict

FORK_SCHEMA_ID = "dagztagz.uni.fork.v2"
FORK_SCHEMA_VERSION = "2"
_REQUIRED = (
    "algo",
    "created_unix",
    "kid",
    "memory_root",
    "name",
    "parent_hash",
    "parent_id",
    "schema_id",
    "schema_version",
    "state",
    "state_hash",
)


@dataclass
class VerifyResult:
    ok: bool
    reason: str
    waivers: list[dict[str, str]] = field(default_factory=list)
    document: dict[str, Any] | None = None
    content_hash: str = ""
    signature_prefix: str = ""


def initial_state(callsign: str, now: int, user_weight: float) -> dict[str, Any]:
    slug = slugify_callsign(callsign)
    return {
        "universe_id": f"uni-{slug}",
        "schema_version": "2",
        "character": {
            "id": f"char-{slug}",
            "callsign": callsign,
            "straussian_level": 1,
        },
        "memory": empty_memory(),
        "forks": [],
        "fork_index": {},
        "head": None,
        "user_weight": user_weight,
        "seed": 0,
        "last_sleep_unix": None,
        "created_unix": now,
    }


def init_workspace(
    root: Path,
    callsign: str,
    *,
    dry_run: bool = False,
    now: int | None = None,
    user_weight: float = 1.0,
) -> None:
    user_weight = parse_user_weight(user_weight)
    slugify_callsign(callsign)
    stamp = int(time.time()) if now is None else now
    if isinstance(stamp, bool) or not isinstance(stamp, int):
        raise ValidationError("now must be an integer")
    if any(part == ".." for part in Path(root).parts):
        raise ValidationError("workspace path rejects '..'")
    identity_dir = Path(root) / IDENTITY_DIRNAME
    if dry_run:
        key_name = HMAC_KEY_FILENAME if not crypto_mod.ecdsa_available() else ECDSA_KEY_FILENAME
        print(f"dry-run: would create {identity_dir} mode 0700")
        print(f"dry-run: would write {identity_dir / key_name} mode 0600")
        print(f"dry-run: would write {identity_dir / 'public.json'} mode 0644")
        print(f"dry-run: would write {Path(root) / STATE_FILENAME} mode 0600")
        print(f"dry-run: would create {Path(root) / FORKS_DIRNAME} mode 0700")
        return
    ws = prepare_workspace_dirs(Path(root))
    identity = ws.sub(IDENTITY_DIRNAME)
    if identity.exists() or identity.is_symlink():
        raise IOPermissionError("identity already exists")
    generate_identity(identity)
    forks = ws.sub(FORKS_DIRNAME)
    create_private_dir(forks)
    _write_regular(
        ws.sub(STATE_FILENAME),
        _pretty(initial_state(callsign, stamp, user_weight)),
        0o600,
    )


def load_state(ws: Workspace) -> dict[str, Any]:
    path = ws.sub(STATE_FILENAME)
    if path.is_symlink() or not path.is_file():
        raise IOPermissionError("state file is missing")
    document = loads_strict(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValidationError("state file is not an object")
    if not isinstance(document.get("memory"), dict):
        raise ValidationError("state memory is missing")
    return document


def save_state(ws: Workspace, state: dict[str, Any]) -> None:
    _write_regular(ws.sub(STATE_FILENAME), _pretty(state), 0o600)


def create_fork(
    root: Path,
    name: str,
    *,
    dry_run: bool = False,
    now: int | None = None,
) -> Path | None:
    name = validate_name(name, what="fork name")
    ws = Workspace(Path(root))
    ws.require_dir()
    identity = load_identity(ws.sub(IDENTITY_DIRNAME))
    state = load_state(ws)
    stamp = int(time.time()) if now is None else now
    if isinstance(stamp, bool) or not isinstance(stamp, int):
        raise ValidationError("now must be an integer")
    parent_id = state.get("head")
    parent_hash: str | None = None
    if parent_id is not None:
        if not isinstance(parent_id, str):
            raise ValidationError("head is not a name")
        parent_path = _fork_path(ws, parent_id)
        parent = verify_fork_file(parent_path, identity=identity, allow_orphan=False)
        if not parent.ok or parent.document is None:
            raise CryptoError(parent.reason or "parent_hash")
        parent_hash = parent.content_hash
        if stamp < int(parent.document["created_unix"]):
            raise ValidationError("fork clock is earlier than its parent")
    snapshot = copy.deepcopy(state)
    forks = list(snapshot.get("forks") or [])
    if name in forks:
        raise ValidationError("fork name already exists")
    forks.append(name)
    snapshot["forks"] = forks
    snapshot["head"] = name
    body = _body(
        identity=identity,
        name=name,
        parent_id=parent_id if isinstance(parent_id, str) else None,
        parent_hash=parent_hash,
        state=snapshot,
        created_unix=stamp,
    )
    target = _fork_path(ws, name)
    if dry_run:
        parent_label = parent_id if parent_id else "none"
        print(f"dry-run: would sign fork {name} parent {parent_label}")
        print(f"dry-run: would write {target} mode 0600")
        return None
    signature = identity.sign_canonical(body)
    document = dict(body)
    document["signature"] = signature
    _write_regular(target, _pretty(document), 0o600)
    content_hash = sha256_hex(canonical_bytes(body))
    disk = copy.deepcopy(snapshot)
    index = dict(disk.get("fork_index") or {})
    index[name] = content_hash
    disk["fork_index"] = index
    save_state(ws, disk)
    return target


def verify_fork_file(
    path: Path,
    *,
    identity: Identity | None = None,
    allow_orphan: bool = False,
    _seen: set[str] | None = None,
) -> VerifyResult:
    if ".." in Path(path).parts:
        return VerifyResult(False, "name")
    if path.is_symlink() or not path.is_file():
        return VerifyResult(False, "parent_missing")
    try:
        parsed = loads_strict(path.read_text(encoding="utf-8"))
    except (ValidationError, IOPermissionError, OSError):
        return VerifyResult(False, "canonical")
    if not isinstance(parsed, dict):
        return VerifyResult(False, "canonical")
    signature = parsed.get("signature")
    prefix = signature[:8] if isinstance(signature, str) else ""
    if not isinstance(signature, str) or not signature or len(signature) % 2:
        return VerifyResult(False, "bad_signature", signature_prefix=prefix)
    body = {key: value for key, value in parsed.items() if key != "signature"}
    for key in _REQUIRED:
        if key not in body:
            return VerifyResult(False, "canonical", signature_prefix=prefix)
    if body.get("schema_id") != FORK_SCHEMA_ID:
        return VerifyResult(False, "schema_id", signature_prefix=prefix)
    if body.get("schema_version") != FORK_SCHEMA_VERSION:
        return VerifyResult(False, "schema_id", signature_prefix=prefix)
    try:
        name = validate_name(body.get("name"), what="fork name")
    except ValidationError:
        return VerifyResult(False, "name", signature_prefix=prefix)
    if path.stem != name:
        return VerifyResult(False, "name", signature_prefix=prefix)
    state = body.get("state")
    if not isinstance(state, dict) or not isinstance(state.get("memory"), dict):
        return VerifyResult(False, "state_hash", signature_prefix=prefix)
    if not _digest_eq(body.get("state_hash"), sha256_hex(canonical_bytes(state))):
        return VerifyResult(False, "state_hash", signature_prefix=prefix)
    if not _digest_eq(body.get("memory_root"), sha256_hex(canonical_bytes(state["memory"]))):
        return VerifyResult(False, "state_hash", signature_prefix=prefix)
    created = body.get("created_unix")
    if isinstance(created, bool) or not isinstance(created, int):
        return VerifyResult(False, "canonical", signature_prefix=prefix)
    algo = body.get("algo")
    try:
        _verify_sig(algo, body, signature, identity)
    except CryptoError as exc:
        reason = "kid" if str(exc) == "kid" else "bad_signature"
        return VerifyResult(False, reason, signature_prefix=prefix)
    content_hash = sha256_hex(canonical_bytes(body))
    parent_id = body.get("parent_id")
    parent_hash = body.get("parent_hash")
    waivers: list[dict[str, str]] = []
    if parent_id is None and parent_hash is None:
        chain_ok = True
    elif isinstance(parent_id, str) and isinstance(parent_hash, str):
        chain_ok, chain_reason, waivers = _check_parent(
            path=path,
            name=name,
            parent_id=parent_id,
            parent_hash=parent_hash,
            created=created,
            state_hash=str(body["state_hash"]),
            identity=identity,
            allow_orphan=allow_orphan,
            seen=_seen or set(),
        )
        if not chain_ok:
            return VerifyResult(False, chain_reason, signature_prefix=prefix)
    else:
        return VerifyResult(False, "parent_hash", signature_prefix=prefix)
    return VerifyResult(True, "ok", waivers, parsed, content_hash, prefix)


def verify_head(root: Path, *, allow_orphan: bool = False) -> VerifyResult:
    ws = Workspace(Path(root))
    ws.require_dir()
    identity = load_identity(ws.sub(IDENTITY_DIRNAME))
    state = load_state(ws)
    head = state.get("head")
    if not isinstance(head, str):
        return VerifyResult(False, "no_head")
    try:
        validate_name(head, what="head")
    except ValidationError:
        return VerifyResult(False, "name")
    result = verify_fork_file(
        _fork_path(ws, head),
        identity=identity,
        allow_orphan=allow_orphan,
    )
    if not result.ok or result.document is None:
        return result
    index = state.get("fork_index") or {}
    recorded = index.get(head) if isinstance(index, dict) else None
    if not _digest_eq(recorded, result.content_hash):
        return VerifyResult(False, "replay", signature_prefix=result.signature_prefix)
    head_ts = int(result.document["created_unix"])
    forks = ws.sub(FORKS_DIRNAME)
    for entry in sorted(forks.iterdir()):
        if not entry.is_file() or entry.suffix != ".json" or entry.is_symlink():
            continue
        try:
            validate_name(entry.stem, what="fork name")
        except ValidationError:
            return VerifyResult(False, "name")
        if entry.stem == head:
            continue
        try:
            other = verify_fork_file(entry, identity=identity, allow_orphan=allow_orphan)
        except (ValidationError, CryptoError, IOPermissionError, OSError):
            return VerifyResult(False, "canonical", signature_prefix=result.signature_prefix)
        if not other.ok or other.document is None:
            continue
        other_ts = other.document.get("created_unix")
        if isinstance(other_ts, bool) or not isinstance(other_ts, int):
            continue
        if other_ts > head_ts:
            return VerifyResult(False, "replay", signature_prefix=result.signature_prefix)
    return result


def _check_parent(
    *,
    path: Path,
    name: str,
    parent_id: str,
    parent_hash: str,
    created: int,
    state_hash: str,
    identity: Identity | None,
    allow_orphan: bool,
    seen: set[str],
) -> tuple[bool, str, list[dict[str, str]]]:
    try:
        validate_name(parent_id, what="parent id")
    except ValidationError:
        return False, "parent_hash", []
    if parent_id == name or parent_id in seen:
        return False, "cycle", []
    parent_path = path.parent / f"{parent_id}.json"
    if parent_path.is_symlink():
        return False, "parent_hash", []
    if not parent_path.is_file():
        if not allow_orphan:
            return False, "parent_missing", []
        return True, "ok", [
            {
                "id": "orphan-parent",
                "reason": "parent file is missing and --allow-orphan was set",
            }
        ]
    seen = set(seen)
    seen.add(name)
    parent = verify_fork_file(parent_path, identity=identity, allow_orphan=allow_orphan, _seen=seen)
    if not parent.ok or parent.document is None:
        return False, parent.reason, []
    if not _digest_eq(parent.content_hash, parent_hash):
        return False, "parent_hash", []
    parent_created = parent.document.get("created_unix")
    if not isinstance(parent_created, int) or created < parent_created:
        return False, "replay", []
    if _digest_eq(parent.document.get("state_hash"), state_hash):
        return False, "replay", []
    return True, "ok", list(parent.waivers)


def _verify_sig(algo: object, body: dict[str, Any], signature: str, identity: Identity | None) -> None:
    if algo == "ecdsa-p256":
        public_hex = body.get("public_key_hex")
        if not isinstance(public_hex, str) or not isinstance(body.get("kid"), str):
            raise CryptoError("kid")
        if not public_kid_matches(public_hex, body["kid"]):
            raise CryptoError("kid")
        verify_signature(
            algo="ecdsa-p256",
            body=body,
            signature_hex=signature,
            public_key_hex=public_hex,
            hmac_key=None,
        )
        return
    if algo == "hmac-sha256":
        if identity is None or identity.algo != "hmac-sha256":
            raise CryptoError("bad_signature")
        if not isinstance(body.get("kid"), str) or not _digest_eq(identity.kid, body["kid"]):
            raise CryptoError("kid")
        identity.verify_canonical(body, signature)
        return
    raise CryptoError("bad_signature")


def _body(
    *,
    identity: Identity,
    name: str,
    parent_id: str | None,
    parent_hash: str | None,
    state: dict[str, Any],
    created_unix: int,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "algo": identity.algo,
        "created_unix": created_unix,
        "kid": identity.kid,
        "memory_root": sha256_hex(canonical_bytes(state["memory"])),
        "name": name,
        "parent_hash": parent_hash,
        "parent_id": parent_id,
        "schema_id": FORK_SCHEMA_ID,
        "schema_version": FORK_SCHEMA_VERSION,
        "state": state,
        "state_hash": sha256_hex(canonical_bytes(state)),
    }
    if identity.algo == "ecdsa-p256":
        body["public_key_hex"] = identity.public_key_hex
    else:
        body["hmac_kid"] = identity.kid
    return body


def _fork_path(ws: Workspace, name: str) -> Path:
    validate_name(name, what="fork name")
    filename = f"{name}.json"
    if len(filename) > 128 or ".." in filename:
        raise ValidationError("fork filename is not allowed")
    directory = ws.sub(FORKS_DIRNAME)
    return directory / filename


def _digest_eq(left: object, right: object) -> bool:
    if not isinstance(left, str) or not isinstance(right, str):
        return False
    if len(left) != len(right):
        return False
    return hmac.compare_digest(left, right)


def _pretty(document: dict[str, Any]) -> bytes:
    # Round-trip through canonical bytes first so NaN cannot be written.
    parsed = json.loads(canonical_bytes(document))
    text = json.dumps(parsed, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
    return (text + "\n").encode("utf-8")


def _write_regular(path: Path, data: bytes, mode: int) -> None:
    if path.is_symlink():
        raise ValidationError("symlink rejected")
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir():
        raise IOPermissionError("destination directory is missing")
    fd, tmp_name = tempfile.mkstemp(dir=parent, prefix=".vesper-", suffix=".tmp")
    try:
        os.write(fd, data)
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp_name, path)
    assert_mode(path, mode, directory=False)
