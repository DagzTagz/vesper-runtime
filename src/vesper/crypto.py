"""Document signatures. This is the only module that reads or writes key bytes.

Canonical bytes are UTF-8 JSON with sort_keys=True, separators=(",", ":"),
and allow_nan=False. The digest is SHA-256 of those bytes.

ECDSA P-256 (secp256r1), when the `ecdsa` package imports:
  sign the 32-byte digest with SigningKey.sign_digest, DER-encoded, hex.
  kid is the first 16 hex characters of SHA-256 over the uncompressed
  public point (0x04 || X || Y). Truncation is an identifier, not a proof.
  The signature is the proof.

HMAC-SHA256 fallback, only when `ecdsa` does not import:
  HMAC over the canonical bytes (the bytes, not the raw digest alone).
  The key file is identity/hmac.key. public.json stores the kid only.

Key files are opened with O_NOFOLLOW. Mode is checked with fstat on that
same descriptor. A mode other than 0600 is refused and is not repaired.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vesper.errors import CryptoError, IOPermissionError, ValidationError
from vesper.paths import (
    ECDSA_KEY_FILENAME,
    HMAC_KEY_FILENAME,
    PUBLIC_FILENAME,
    assert_mode,
    create_private_dir,
)

_ECDSA: dict[str, Any] | None | bool = None


def ecdsa_available() -> bool:
    """True when the optional ecdsa package imported."""
    return _load_ecdsa() is not None


def _load_ecdsa() -> dict[str, Any] | None:
    global _ECDSA
    if _ECDSA is False:
        return None
    if isinstance(_ECDSA, dict):
        return _ECDSA
    try:
        from ecdsa import NIST256p, SigningKey, VerifyingKey
        from ecdsa.keys import BadSignatureError
        from ecdsa.util import sigdecode_der, sigencode_der
    except ImportError:
        _ECDSA = False
        return None
    _ECDSA = {
        "NIST256p": NIST256p,
        "SigningKey": SigningKey,
        "VerifyingKey": VerifyingKey,
        "BadSignatureError": BadSignatureError,
        "sigdecode_der": sigdecode_der,
        "sigencode_der": sigencode_der,
    }
    return _ECDSA


def canonical_bytes(obj: object) -> bytes:
    """UTF-8 canonical JSON. Rejects NaN and Infinity."""
    try:
        text = json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValidationError("value is not canonical JSON") from exc
    return text.encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_digest(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


@dataclass
class Identity:
    """Loaded identity. Private bytes stay on this object."""

    algo: str
    kid: str
    public_key_hex: str | None
    public_doc: dict[str, Any]
    _ecdsa_key: object | None
    _hmac_key: bytes | None

    def verify_canonical(self, body: dict[str, Any], signature_hex: str) -> None:
        """Check a signature with this identity. Key bytes stay in this module."""
        verify_signature(
            algo=self.algo,
            body=body,
            signature_hex=signature_hex,
            public_key_hex=self.public_key_hex,
            hmac_key=self._hmac_key,
        )

    def sign_canonical(self, body: dict[str, Any]) -> str:
        raw = canonical_bytes(body)
        if self.algo == "ecdsa-p256":
            backend = _load_ecdsa()
            if backend is None or self._ecdsa_key is None:
                raise CryptoError("ECDSA backend is not available")
            signature = self._ecdsa_key.sign_digest(  # type: ignore[attr-defined]
                sha256_digest(raw),
                sigencode=backend["sigencode_der"],
            )
            return signature.hex()
        if self.algo == "hmac-sha256":
            if self._hmac_key is None:
                raise CryptoError("HMAC key is not loaded")
            return hmac.new(self._hmac_key, raw, hashlib.sha256).hexdigest()
        raise CryptoError("unknown signature algorithm")


def _kid_from_uncompressed(point: bytes) -> str:
    return sha256_hex(point)[:16]


def _public_doc_is_clean(doc: dict[str, Any]) -> None:
    blob = json.dumps(doc, sort_keys=True)
    if "BEGIN" in blob or "PRIVATE" in blob or "-----" in blob:
        raise CryptoError("public identity file contains secret-shaped text")


def _read_regular_nofollow(path: Path, limit: int) -> bytes:
    """Read a regular file without following a symlink."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        raise IOPermissionError("cannot open identity file") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise IOPermissionError("identity file is not a regular file")
        if info.st_size > limit:
            raise IOPermissionError("identity file is too large")
        return os.read(fd, info.st_size)
    finally:
        os.close(fd)


def _read_secret(path: Path) -> bytes:
    """Read a regular file whose permission bits are exactly 0600."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        raise IOPermissionError("cannot open key file") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise IOPermissionError("key is not a regular file")
        if stat.S_IMODE(info.st_mode) != 0o600:
            raise IOPermissionError("refusing key that is not mode 0600")
        if info.st_size <= 0 or info.st_size > 16384:
            raise IOPermissionError("key file size is not usable")
        return os.read(fd, info.st_size)
    finally:
        os.close(fd)


def _write_secret(path: Path, data: bytes) -> None:
    """Create a new 0600 file. Do not overwrite. Do not follow a symlink."""
    if path.exists() or path.is_symlink():
        raise IOPermissionError("refusing to overwrite a key file")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except OSError as exc:
        raise IOPermissionError("cannot create key file") from exc
    try:
        os.write(fd, data)
        os.fchmod(fd, 0o600)
        info = os.fstat(fd)
        if stat.S_IMODE(info.st_mode) != 0o600:
            raise IOPermissionError("key mode is not 0600 after write")
    except Exception:
        os.close(fd)
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    else:
        os.close(fd)
    # Re-open and fstat so a mode change after the write is not ignored.
    _read_secret(path)


def _write_public(path: Path, doc: dict[str, Any]) -> None:
    _public_doc_is_clean(doc)
    text = json.dumps(doc, sort_keys=True, indent=2) + "\n"
    if path.exists() or path.is_symlink():
        raise IOPermissionError("refusing to overwrite public identity")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    except OSError as exc:
        raise IOPermissionError("cannot create public identity") from exc
    try:
        os.write(fd, text.encode("utf-8"))
        os.fchmod(fd, 0o644)
    finally:
        os.close(fd)


def _parse_ecdsa_private(pem: bytes) -> tuple[object, str, str]:
    backend = _load_ecdsa()
    if backend is None:
        raise CryptoError("ECDSA backend is not available")
    try:
        key = backend["SigningKey"].from_pem(pem)
    except Exception as exc:
        raise CryptoError("key file could not be parsed") from exc
    if key.curve != backend["NIST256p"]:
        raise CryptoError("key curve is not P-256")
    verifying = key.get_verifying_key()
    uncompressed = b"\x04" + verifying.to_string()
    kid = _kid_from_uncompressed(uncompressed)
    return key, kid, uncompressed.hex()


def _public_key_kid(public_key_hex: str) -> str:
    try:
        raw = bytes.fromhex(public_key_hex)
    except ValueError as exc:
        raise CryptoError("public key hex is malformed") from exc
    if len(raw) != 65 or raw[0] != 0x04:
        raise CryptoError("public key is not an uncompressed P-256 point")
    return _kid_from_uncompressed(raw)


def generate_identity(identity_dir: Path) -> Identity:
    """Create identity_dir at 0700 and a new key at 0600."""
    create_private_dir(identity_dir)
    if ecdsa_available():
        backend = _load_ecdsa()
        assert backend is not None
        key = backend["SigningKey"].generate(curve=backend["NIST256p"])
        pem = key.to_pem()
        _write_secret(identity_dir / ECDSA_KEY_FILENAME, pem)
        verifying = key.get_verifying_key()
        uncompressed = b"\x04" + verifying.to_string()
        kid = _kid_from_uncompressed(uncompressed)
        public = {
            "algo": "ecdsa-p256",
            "curve": "secp256r1",
            "kid": kid,
            "public_key_hex": uncompressed.hex(),
        }
        _write_public(identity_dir / PUBLIC_FILENAME, public)
        return Identity("ecdsa-p256", kid, uncompressed.hex(), public, key, None)

    key_bytes = os.urandom(32)
    _write_secret(identity_dir / HMAC_KEY_FILENAME, key_bytes)
    kid = sha256_hex(key_bytes)[:16]
    public = {"algo": "hmac-sha256", "hmac_kid": kid, "kid": kid}
    _write_public(identity_dir / PUBLIC_FILENAME, public)
    return Identity("hmac-sha256", kid, None, public, None, key_bytes)


def refuse_insecure_key(path: Path) -> None:
    """Read a key file. A mode other than 0600 raises and does not repair it."""
    _read_secret(path)


def load_identity(identity_dir: Path) -> Identity:
    """Load a key. Refuse a directory that is not 0700 or a key that is not 0600."""
    assert_mode(identity_dir, 0o700, directory=True)
    public_path = identity_dir / PUBLIC_FILENAME
    if public_path.is_symlink() or not public_path.is_file():
        raise IOPermissionError("public identity file is missing")
    try:
        public = json.loads(_read_regular_nofollow(public_path, 65536).decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CryptoError("public identity file is not JSON") from exc
    if not isinstance(public, dict):
        raise CryptoError("public identity file is not an object")
    _public_doc_is_clean(public)
    algo = public.get("algo")
    ecdsa_path = identity_dir / ECDSA_KEY_FILENAME
    hmac_path = identity_dir / HMAC_KEY_FILENAME
    if ecdsa_path.exists() and hmac_path.exists():
        raise IOPermissionError("identity directory has two key files")
    if algo == "ecdsa-p256":
        pem = _read_secret(ecdsa_path)
        key, kid, public_hex = _parse_ecdsa_private(pem)
        if public.get("kid") != kid or public.get("public_key_hex") != public_hex:
            raise CryptoError("public identity does not match the key file")
        if _public_key_kid(public_hex) != kid:
            raise CryptoError("kid does not match the public key")
        return Identity(algo, kid, public_hex, public, key, None)
    if algo == "hmac-sha256":
        raw = _read_secret(hmac_path)
        kid = sha256_hex(raw)[:16]
        if public.get("kid") != kid or public.get("hmac_kid") != kid:
            raise CryptoError("public identity does not match the key file")
        return Identity(algo, kid, None, public, None, raw)
    raise CryptoError("unknown identity algorithm")


def public_kid_matches(public_key_hex: str, kid: str) -> bool:
    """True when kid is the documented truncation of SHA-256(uncompressed point)."""
    try:
        derived = _public_key_kid(public_key_hex)
    except CryptoError:
        return False
    if len(derived) != len(kid):
        return False
    return hmac.compare_digest(derived, kid)


def verify_signature(
    *,
    algo: str,
    body: dict[str, Any],
    signature_hex: str,
    public_key_hex: str | None,
    hmac_key: bytes | None,
) -> None:
    """Raise CryptoError('bad_signature') when the signature does not match."""
    raw = canonical_bytes(body)
    try:
        signature = bytes.fromhex(signature_hex)
    except ValueError as exc:
        raise CryptoError("bad_signature") from exc
    if algo == "ecdsa-p256":
        if not public_key_hex:
            raise CryptoError("public key is missing")
        _public_key_kid(public_key_hex)
        backend = _load_ecdsa()
        if backend is None:
            raise CryptoError("ECDSA backend is not available")
        point = bytes.fromhex(public_key_hex)[1:]
        try:
            verifying = backend["VerifyingKey"].from_string(point, curve=backend["NIST256p"])
            verifying.verify_digest(signature, sha256_digest(raw), sigdecode=backend["sigdecode_der"])
        except backend["BadSignatureError"] as exc:
            raise CryptoError("bad_signature") from exc
        except Exception as exc:
            raise CryptoError("bad_signature") from exc
        return
    if algo == "hmac-sha256":
        if hmac_key is None:
            raise CryptoError("HMAC key is not loaded")
        expected = hmac.new(hmac_key, raw, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, signature):
            raise CryptoError("bad_signature")
        return
    raise CryptoError("unknown signature algorithm")
