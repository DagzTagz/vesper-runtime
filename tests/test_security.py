"""T1–T8. These tests call the real checks. A skip is a failure."""

import json
import os
import stat
from pathlib import Path

import pytest

from vesper.cli import run
from vesper.crypto import load_identity, refuse_insecure_key
from vesper.errors import CryptoError, IOPermissionError, ValidationError
from vesper.export import export_audit
from vesper.fork import create_fork, load_state, save_state, verify_fork_file
from vesper.memory import empty_memory, new_item, remember, sleep_state
from vesper.paths import Workspace, validate_name

ROOT = Path(__file__).resolve().parents[1]
MARKERS = ("BEGIN", "PRIVATE", "-----")


def test_t1_parser_error_does_not_echo_key_bytes(tmp_path: Path) -> None:
    identity = tmp_path / "identity"
    identity.mkdir()
    os.chmod(identity, 0o700)
    marker = "SECRETMATERIAL"
    key = identity / "edcsa-p256.priv"
    key.write_text(marker, encoding="utf-8")
    os.chmod(key, 0o600)
    public = {
        "algo": "ecdsa-p256",
        "kid": "0123456789abcdef",
        "public_key_hex": "04" + ("11" * 32),
    }
    (identity / "public.json").write_text(json.dumps(public), encoding="utf-8")
    with pytest.raises(CryptoError) as caught:
        load_identity(identity)
    assert marker not in str(caught.value)
    cause = caught.value.__cause__
    if cause is not None:
        assert marker not in str(cause)


def test_t1_export_has_no_key_material(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    out = tmp_path / "out"
    assert run(["init", "--workspace", str(root), "--callsign", "vesper"]) == 0
    assert run(["--workspace", str(root), "remember", "--text", "audit sample", "--valence", "0.3", "--now", "10"]) == 0
    assert run(["--workspace", str(root), "fork", "--name", "alpha", "--now", "20"]) == 0
    key = (root / "identity" / "edcsa-p256.priv").read_bytes()
    audit = export_audit(root, out)
    assert audit.passed, audit.score
    assert audit.verdict == "ACCEPT"
    assert not (out / "identity").exists()
    blob = b"".join(path.read_bytes() for path in out.rglob("*") if path.is_file())
    assert key not in blob
    for marker in MARKERS:
        assert marker.encode("ascii") not in blob
    assert (out / "score.json").is_file()
    score = json.loads((out / "score.json").read_text(encoding="utf-8"))
    assert score["pass"] is True
    assert score["checks"]["no_secrets_in_export"] is True
    assert score["checks"]["forged_signature_rejected"] is True
    assert score["checks"]["memory_decay_ran"] is True
    evidence = (out / "evidence.md").read_text(encoding="utf-8")
    assert "vesper verify fixtures/forged-fork.json; echo EXIT:$?" in evidence
    assert "EXIT:2" in evidence


def test_t2_schema_rejects_unhealable_identity(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{}", encoding="utf-8")
    assert run(["schema", "heal", str(path), "--write"]) == 2
    assert path.read_text(encoding="utf-8") == "{}"


def test_t3_and_t8_forged_fixture_verify_ran() -> None:
    path = ROOT / "fixtures" / "forged-fork.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    result = verify_fork_file(path)
    assert result.ok is False
    assert result.reason == "bad_signature"
    assert result.signature_prefix == document["signature"][:8]
    assert run(["verify", str(path)]) == 2


def test_t4_old_snapshot_is_not_a_new_head(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    run(["init", "--workspace", str(root), "--callsign", "vesper"])
    run(["--workspace", str(root), "remember", "--text", "one", "--valence", "0.2", "--weight", "0.2", "--now", "10", "--id", "m-1"])
    run(["--workspace", str(root), "fork", "--name", "alpha", "--now", "20"])
    run(["--workspace", str(root), "remember", "--text", "two", "--valence", "0.2", "--weight", "0.2", "--now", "30", "--id", "m-2"])
    run(["--workspace", str(root), "fork", "--name", "beta", "--now", "40"])
    assert run(["--workspace", str(root), "verify", "--head"]) == 0
    alpha = (root / "forks" / "alpha.json").read_bytes()
    beta = root / "forks" / "beta.json"
    beta.write_bytes(alpha)
    os.chmod(beta, 0o600)
    assert verify_fork_file(beta).reason == "name"
    assert run(["--workspace", str(root), "verify", str(beta)]) == 2


def test_t5_decay_changes_weight_and_nan_dies() -> None:
    state = {"memory": empty_memory(), "user_weight": 1.0, "seed": 0}
    remember(
        state,
        new_item(text="decay", valence=0.3, now=0, tier="semantic", pinned=False, weight=1.0, item_id="m-d"),
    )
    before = state["memory"]["semantic"][0]["weight"]
    sleep_state(state, 10 * 3600)
    after = state["memory"]["semantic"][0]["weight"]
    assert after < before
    with pytest.raises(ValidationError):
        new_item(text="nope", valence=float("nan"), now=1, tier="stm", pinned=False)


def test_t5_stm_cap_and_event_id() -> None:
    with pytest.raises(ValidationError):
        validate_name("../etc/passwd", what="event id")
    state = {"memory": empty_memory(), "user_weight": 1.0, "seed": 0}
    for index in range(101):
        remember(
            state,
            new_item(text=f"n{index}", valence=0.1, now=index, tier="stm", pinned=False, weight=0.1, item_id=f"m-{index}"),
        )
    assert len(state["memory"]["stm"]) == 100


def test_t6_fork_name_cannot_escape(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    outside = tmp_path / "outside"
    outside.mkdir()
    run(["init", "--workspace", str(root), "--callsign", "vesper"])
    forks = root / "forks"
    os.rename(forks, tmp_path / "forks-real")
    forks.symlink_to(outside)
    code = run(["--workspace", str(root), "fork", "--name", "alpha", "--now", "5"])
    assert code == 2
    assert list(outside.iterdir()) == []
    assert run(["--workspace", str(root), "fork", "--name", "../alpha", "--now", "5"]) == 2


def test_t7_refuses_0644_and_does_not_repair(tmp_path: Path) -> None:
    key = tmp_path / "weak.key"
    key.write_bytes(os.urandom(32))
    os.chmod(key, 0o644)
    with pytest.raises(IOPermissionError):
        refuse_insecure_key(key)
    assert stat.S_IMODE(key.stat().st_mode) == 0o644
    os.chmod(key, 0o640)
    with pytest.raises(IOPermissionError):
        refuse_insecure_key(key)


def test_t7_directory_mode_and_permissive_umask(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    old = os.umask(0)
    try:
        assert run(["init", "--workspace", str(root), "--callsign", "vesper"]) == 0
    finally:
        os.umask(old)
    identity = root / "identity"
    key = identity / "edcsa-p256.priv"
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE(identity.stat().st_mode) == 0o700
    assert stat.S_IMODE(key.stat().st_mode) == 0o600
    os.chmod(identity, 0o755)
    with pytest.raises(IOPermissionError):
        load_identity(identity)
    assert stat.S_IMODE(identity.stat().st_mode) == 0o755
    assert stat.S_IMODE(key.stat().st_mode) == 0o600


def test_t1_export_withholds_fork_that_contains_a_marker(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    out = tmp_path / "out"
    marker = "-----BEG" + "IN PRIVATE KEY-----"
    assert run(["init", "--workspace", str(root), "--callsign", "vesper"]) == 0
    assert run(["--workspace", str(root), "remember", "--text", marker, "--valence", "0.2", "--now", "10"]) == 0
    assert run(["--workspace", str(root), "fork", "--name", "alpha", "--now", "20"]) == 0
    audit = export_audit(root, out)
    assert audit.passed is False
    assert audit.score["checks"]["no_secrets_in_export"] is False
    blob = b"".join(path.read_bytes() for path in out.rglob("*") if path.is_file())
    assert b"BEGIN" not in blob
    assert b"PRIVATE" not in blob
    assert b"-----" not in blob
    assert (out / "fork_verified.json").read_text(encoding="utf-8") == "null\n"


def test_t4_junk_sibling_is_not_a_newer_head(tmp_path: Path) -> None:
    from vesper.fork import init_workspace, verify_head

    root = tmp_path / "ws"
    init_workspace(root, "vesper", now=10)
    assert run(["--workspace", str(root), "remember", "--text", "note", "--valence", "0.2", "--now", "10"]) == 0
    assert run(["--workspace", str(root), "fork", "--name", "alpha", "--now", "20"]) == 0
    junk = root / "forks" / "note.json"
    junk.write_text('{"created_unix": 1900000000}\n', encoding="utf-8")
    os.chmod(junk, 0o600)
    broken = root / "forks" / "bad.json"
    broken.write_text("{", encoding="utf-8")
    os.chmod(broken, 0o600)
    assert verify_head(root).ok


def test_t8_source_has_no_bare_except() -> None:
    src = ROOT / "src" / "vesper"
    for path in src.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "\nexcept:" not in text
        if path.name != "crypto.py":
            assert "import ecdsa" not in text
            assert "ecdsa." not in text


def test_only_crypto_reads_key_filenames() -> None:
    src = ROOT / "src" / "vesper"
    for path in src.glob("*.py"):
        if path.name in {"crypto.py", "paths.py"}:
            continue
        text = path.read_text(encoding="utf-8")
        assert "to_pem" not in text
        assert "SigningKey" not in text
