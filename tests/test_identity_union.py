"""Identity is EcdsaIdentity | HmacIdentity; the algorithm is the type (audit F12)."""

from __future__ import annotations

import typing
from pathlib import Path

import pytest

from vesper import crypto
from vesper.crypto import EcdsaIdentity, HmacIdentity, Identity, generate_identity, load_identity
from vesper.errors import CryptoError


def test_union_members() -> None:
    assert set(typing.get_args(Identity)) == {EcdsaIdentity, HmacIdentity}


def test_ecdsa_identity_round_trip(tmp_path: Path) -> None:
    made = generate_identity(tmp_path / "identity")
    assert isinstance(made, EcdsaIdentity)
    loaded = load_identity(tmp_path / "identity")
    assert isinstance(loaded, EcdsaIdentity)
    assert loaded.algo == "ecdsa-p256" and loaded.kid == made.kid
    body = {"a": 1}
    loaded.verify_canonical(body, made.sign_canonical(body))
    with pytest.raises(CryptoError):
        loaded.verify_canonical({"a": 2}, made.sign_canonical(body))
    assert "_key=" not in repr(loaded)


def test_hmac_identity_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(crypto, "ecdsa_available", lambda: False)
    made = generate_identity(tmp_path / "identity")
    assert isinstance(made, HmacIdentity)
    assert made.public_key_hex is None
    loaded = load_identity(tmp_path / "identity")
    assert isinstance(loaded, HmacIdentity)
    body = {"a": 1}
    loaded.verify_canonical(body, made.sign_canonical(body))
    assert "_key=" not in repr(loaded)


def test_impossible_identities_cannot_be_built() -> None:
    # Before: Identity("ecdsa-p256", kid, hex, doc, None, None) was accepted and
    # only failed later inside sign_canonical.
    with pytest.raises(TypeError):
        EcdsaIdentity("kid", "04", {})  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        HmacIdentity("kid", {}, b"k", object())  # type: ignore[call-arg]
