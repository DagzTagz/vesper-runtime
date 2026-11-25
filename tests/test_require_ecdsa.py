"""Residual item S15: no silent HMAC fallback when `ecdsa` is missing."""

from __future__ import annotations

from pathlib import Path

import pytest

from vesper import crypto
from vesper.cli import run
from vesper.crypto import HmacIdentity, generate_identity, load_identity
from vesper.errors import CryptoError
from vesper.fork import create_fork, init_workspace, verify_fork_file


@pytest.fixture
def no_ecdsa(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    monkeypatch.setattr(crypto, "ecdsa_available", lambda: False)
    monkeypatch.delenv(crypto.INSECURE_HMAC_ENV, raising=False)
    return monkeypatch


def _hmac_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """An HMAC workspace made by an older vesper (or with the opt-in) plus one fork."""
    monkeypatch.setattr(crypto, "ecdsa_available", lambda: False)
    monkeypatch.setenv(crypto.INSECURE_HMAC_ENV, "1")
    root = tmp_path / "ws"
    init_workspace(root, "old-hmac", now=5)
    fork = create_fork(root, "alpha", now=6)
    assert fork is not None
    monkeypatch.delenv(crypto.INSECURE_HMAC_ENV)
    return root, fork


def test_generate_refuses_without_ecdsa(tmp_path: Path, no_ecdsa) -> None:
    with pytest.raises(CryptoError, match="ecdsa"):
        generate_identity(tmp_path / "identity")
    assert not (tmp_path / "identity").exists()


def test_only_exact_opt_in_value_counts(tmp_path: Path, no_ecdsa) -> None:
    for value in ("", "0", "true", "yes", "1 "):
        no_ecdsa.setenv(crypto.INSECURE_HMAC_ENV, value)
        with pytest.raises(CryptoError):
            generate_identity(tmp_path / f"identity-{len(value)}")


def test_cli_init_refuses_and_writes_nothing(
    tmp_path: Path, no_ecdsa, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "ws"
    assert run(["init", "--workspace", str(root), "--callsign", "v"]) == 2
    err = capsys.readouterr().err
    assert "pip install" in err and crypto.INSECURE_HMAC_ENV in err
    assert not root.exists()


def test_cli_dry_run_init_refuses(tmp_path: Path, no_ecdsa, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "ws"
    assert run(["--dry-run", "init", "--workspace", str(root), "--callsign", "v"]) == 2
    assert "would write" not in capsys.readouterr().out
    assert not root.exists()


def test_opt_in_warns_loudly(tmp_path: Path, no_ecdsa, capsys: pytest.CaptureFixture[str]) -> None:
    no_ecdsa.setenv(crypto.INSECURE_HMAC_ENV, "1")
    made = generate_identity(tmp_path / "identity")
    assert isinstance(made, HmacIdentity)
    assert "WARNING" in capsys.readouterr().err


def test_existing_hmac_workspace_is_verify_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root, fork = _hmac_workspace(tmp_path, monkeypatch)
    identity = load_identity(root / "identity")
    assert isinstance(identity, HmacIdentity)
    # Old forks still verify, from the API and the CLI.
    assert verify_fork_file(fork, identity=identity).ok
    assert run(["--workspace", str(root), "verify", str(fork)]) == 0
    # New signatures are refused, before anything is written.
    forks_before = sorted((root / "forks").iterdir())
    with pytest.raises(CryptoError, match="refuses to sign"):
        create_fork(root, "beta", now=7)
    assert sorted((root / "forks").iterdir()) == forks_before
    assert not (root / ".fork-pending.json").exists()
    with pytest.raises(CryptoError):
        identity.sign_canonical({"a": 1})
    capsys.readouterr()
    assert run(["--workspace", str(root), "fork", "--name", "gamma"]) == 2
    assert "refuses to sign" in capsys.readouterr().err


def test_existing_hmac_workspace_signs_with_opt_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _fork = _hmac_workspace(tmp_path, monkeypatch)
    monkeypatch.setenv(crypto.INSECURE_HMAC_ENV, "1")
    capsys.readouterr()
    assert create_fork(root, "beta", now=7) is not None
    assert "WARNING" in capsys.readouterr().err


def test_ecdsa_path_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if not crypto._load_ecdsa():
        pytest.skip("ecdsa is not installed")
    monkeypatch.delenv(crypto.INSECURE_HMAC_ENV, raising=False)
    root = tmp_path / "ws"
    init_workspace(root, "ecdsa-user", now=5)
    assert (root / "identity" / "edcsa-p256.priv").is_file()
    assert create_fork(root, "alpha", now=6) is not None
