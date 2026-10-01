"""Sign, verify, parent chain, and forged fixtures."""

import json
import os
from pathlib import Path

import pytest

from vesper.cli import run
from vesper.crypto import canonical_bytes, load_identity, sha256_hex
from vesper.fork import create_fork, init_workspace, load_state, save_state, verify_fork_file, verify_head
from vesper.memory import new_item, remember
from vesper.paths import Workspace

ROOT = Path(__file__).resolve().parents[1]


def _init(tmp_path: Path, callsign: str = "vesper") -> Path:
    root = tmp_path / "ws"
    assert run(["init", "--workspace", str(root), "--callsign", callsign]) == 0
    return root


def test_canonical_bytes_and_nan() -> None:
    assert canonical_bytes({"b": 1, "a": 2}) == b'{"a":2,"b":1}'
    from vesper.errors import ValidationError

    with pytest.raises(ValidationError):
        canonical_bytes({"x": float("nan")})


def test_roundtrip_and_mutation(tmp_path: Path) -> None:
    root = _init(tmp_path)
    ws = Workspace(root)
    state = load_state(ws)
    remember(state, new_item(text="hello", valence=0.3, now=10, tier="stm", pinned=False, weight=0.2, item_id="m-1"))
    save_state(ws, state)
    path = create_fork(root, "alpha", now=20)
    assert path is not None
    result = verify_fork_file(path)
    assert result.ok
    assert result.reason == "ok"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["created_unix"] = 99
    path.write_text(json.dumps(document), encoding="utf-8")
    os.chmod(path, 0o600)
    mutated = verify_fork_file(path)
    assert not mutated.ok
    assert mutated.reason == "bad_signature"


def test_parent_chain_and_replay(tmp_path: Path) -> None:
    root = _init(tmp_path)
    ws = Workspace(root)
    state = load_state(ws)
    remember(state, new_item(text="one", valence=0.2, now=10, tier="stm", pinned=False, weight=0.2, item_id="m-1"))
    save_state(ws, state)
    alpha = create_fork(root, "alpha", now=20)
    state = load_state(ws)
    remember(state, new_item(text="two", valence=0.2, now=30, tier="stm", pinned=False, weight=0.2, item_id="m-2"))
    save_state(ws, state)
    beta = create_fork(root, "beta", now=40)
    assert alpha is not None and beta is not None
    assert verify_head(root).ok
    alpha_bytes = alpha.read_bytes()
    copied = root / "forks" / "copied.json"
    copied.write_bytes(alpha_bytes)
    os.chmod(copied, 0o600)
    assert verify_fork_file(copied).reason == "name"
    identity = load_identity(root / "identity")
    document = json.loads(beta.read_text(encoding="utf-8"))
    body = {key: value for key, value in document.items() if key != "signature"}
    body["parent_hash"] = "0" * 64
    lied = dict(body)
    lied["signature"] = identity.sign_canonical(body)
    beta.write_text(json.dumps(lied), encoding="utf-8")
    os.chmod(beta, 0o600)
    assert verify_fork_file(beta, identity=identity).reason == "parent_hash"


def test_missing_parent_and_orphan_waiver(tmp_path: Path) -> None:
    root = _init(tmp_path)
    from vesper.fork import _body

    identity = load_identity(root / "identity")
    body = _body(
        identity=identity,
        name="orphan",
        parent_id="no-such-parent",
        parent_hash="ab" * 32,
        state=load_state(Workspace(root)),
        created_unix=50,
    )
    document = dict(body)
    document["signature"] = identity.sign_canonical(body)
    path = root / "forks" / "orphan.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    os.chmod(path, 0o600)
    assert verify_fork_file(path, identity=identity).reason == "parent_missing"
    waived = verify_fork_file(path, identity=identity, allow_orphan=True)
    assert waived.ok
    assert waived.waivers[0]["id"] == "orphan-parent"
    assert run(["--workspace", str(root), "verify", str(path)]) == 2
    assert run(["--workspace", str(root), "verify", str(path), "--allow-orphan"]) == 0


def test_forged_fixture_is_actually_verified() -> None:
    path = ROOT / "fixtures" / "forged-fork.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    result = verify_fork_file(path)
    assert result.reason == "bad_signature"
    assert result.signature_prefix == document["signature"][:8]
    assert document["state_hash"] == sha256_hex(canonical_bytes(document["state"]))
    assert run(["verify", str(path)]) == 2


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    assert run(["--dry-run", "init", "--workspace", str(root), "--callsign", "vesper"]) == 0
    assert not root.exists()


def test_hmac_fallback_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import vesper.crypto as crypto

    monkeypatch.setattr(crypto, "ecdsa_available", lambda: False)
    root = tmp_path / "ws"
    init_workspace(root, "hmac-user", now=5)
    assert (root / "identity" / "hmac.key").is_file()
    assert not (root / "identity" / "edcsa-p256.priv").exists()
    ws = Workspace(root)
    state = load_state(ws)
    remember(state, new_item(text="local", valence=0.4, now=5, tier="stm", pinned=False, weight=0.3, item_id="m-h"))
    save_state(ws, state)
    path = create_fork(root, "alpha", now=6)
    assert path is not None
    identity = load_identity(root / "identity")
    assert verify_fork_file(path, identity=identity).ok
    public = (root / "identity" / "public.json").read_text(encoding="utf-8")
    assert "BEGIN" not in public
    key = (root / "identity" / "hmac.key").read_bytes()
    assert key not in public.encode("utf-8")
    assert run(["--workspace", str(root), "verify", str(path)]) == 0
    assert run(["--workspace", str(tmp_path / "missing"), "verify", str(path)]) == 3
    assert key not in repr(identity).encode("utf-8")


def test_hmac_dry_run_names_hmac_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import vesper.crypto as crypto

    monkeypatch.setattr(crypto, "ecdsa_available", lambda: False)
    root = tmp_path / "ws"
    assert run(["--dry-run", "init", "--workspace", str(root), "--callsign", "hmac-user"]) == 0
    text = capsys.readouterr().out
    assert "hmac.key" in text
    assert "edcsa-p256.priv" not in text
    assert not root.exists()
