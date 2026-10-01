# Forks

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API. The full list of roles it does not fill is in [getting-started.md](../getting-started.md#what-this-tool-is-not).

A fork is a snapshot plus a signature. The file is `forks/<name>.json`. The signature is the `signature` field. Every other field is the signed body. Later, `vesper verify` rebuilds that body and checks the stamp. A match means the body still agrees with the key. It does not prove a legal identity, and it does not prove the note is true.

This key is not a Bitcoin key. It uses NIST P-256, a different curve, and it only signs JSON.

## Canonical JSON, hash, and stamp

The signed bytes are UTF-8 JSON with keys sorted, separators `(",", ":")`, and `NaN` and `Infinity` rejected (`ensure_ascii` is false, so non-ASCII text stays as itself). The file you open in an editor is pretty-printed. The stamp covers the canonical bytes, not the indentation.

`state_hash` is the hex SHA-256 of the canonical `state` object. `memory_root` is the hex SHA-256 of the canonical `state.memory` object. `parent_hash` is the hex SHA-256 of the parent's canonical signed body (the parent object without its `signature` field).

When the `ecdsa` package imports, the algorithm is `ecdsa-p256`. The program hashes the canonical body with SHA-256, signs that 32-byte digest with `SigningKey.sign_digest`, DER-encodes the signature (`sigencode_der`), and stores the DER bytes as hex. The public point in the body is the uncompressed form: byte `0x04`, then X, then Y, written as hex in `public_key_hex`.

The kid is the first 16 hex characters of SHA-256 over that uncompressed point. The truncation identifies the key. The signature is the check. If `kid` does not match `public_key_hex`, `verify` returns `kid` before it returns `bad_signature`.

When `ecdsa` does not import, the algorithm is `hmac-sha256`. HMAC-SHA256 covers the canonical bytes themselves, not the bare digest. The body stores `hmac_kid` set to the same kid. There is no `public_key_hex`.

The fork schema id is `dagztagz.uni.fork.v2`. The schema version is the string `"2"`.

The signed body always includes `algo`, `created_unix`, `kid`, `memory_root`, `name`, `parent_hash`, `parent_id`, `schema_id`, `schema_version`, `state`, and `state_hash`. ECDSA adds `public_key_hex`. HMAC adds `hmac_kid`. `signature` is outside the body.

## Parent link

A first snapshot sets `parent_id` and `parent_hash` to JSON `null`. That pair is the start of the chain.

If one of those two fields is a string and the other is null, `verify` returns `parent_hash`.

If both are strings, the parent file must be the sibling `<parent_id>.json`. Its content hash must equal `parent_hash`. `created_unix` must be an integer greater than or equal to the parent's `created_unix`. JSON `true` is rejected as `canonical`, because a boolean is not accepted as the timestamp. An equal `state_hash` on parent and child is `replay`, even when the clock moved.

The parent chain remembers names it has already visited. A repeated name, or a parent id equal to this file's own name, is `cycle`.

`--allow-orphan` applies only when the parent file is absent. Verify then succeeds with waiver id `orphan-parent`. Do not use that flag to hide a missing parent. A parent file that exists is still checked.

## Filename

The stem of the filename must equal the signed `name`. `forks/alpha.json` verifies only when `name` is `alpha`. A copy named `copied.json` returns `name`, even if every byte of the body is intact. Names are one segment of `[A-Za-z0-9._-]`, length 1..128, with no `..`. The written filename is `name.json`, and that filename must be at most 128 characters. A name of 124 characters or more is rejected at write time, because `name.json` would be longer than 128. A name of 123 characters is the longest that fits.

`fork_verified.json` in an audit folder keeps that filename. Verifying that path returns `name`. Copy it to `<signed-name>.json`, or verify `workspace/forks/<signed-name>.json`. The sample in `examples/passing-audit/` is named `alpha` inside the JSON. A copy named `alpha.json` verifies as `ok`. The path `fork_verified.json` does not.

## What verify checks, in order

`vesper verify PATH` returns the first failing reason. Exit 0 and the text `verify ok` mean reason `ok`.

1. The path must not contain `..`. A symlink or a missing file is `parent_missing`. Unreadable JSON is `canonical`.
2. `signature` must be a non-empty even-length hex string. Otherwise `bad_signature`.
3. The required body fields must be present. Otherwise `canonical`.
4. `schema_id` and `schema_version` must match. Otherwise `schema_id`.
5. `name` must be a safe segment, and the filename stem must equal it. Otherwise `name`.
6. `state_hash` and `memory_root` must match the canonical state. Otherwise `state_hash`.
7. `created_unix` must be an integer and not a boolean. Otherwise `canonical`.
8. The kid is checked against the public point (ECDSA) or against the loaded HMAC kid. A mismatch is `kid`. The stamp is then checked. A bad stamp is `bad_signature`.
9. The parent pair is checked, as above. Reasons are `parent_hash`, `parent_missing`, `replay`, or `cycle`.

ECDSA verify uses `public_key_hex` inside the file. It does not open the workspace and it does not need the private key. HMAC verify needs the workspace. The CLI reads `algo` first and loads `identity/hmac.key` only when `algo` is `hmac-sha256`.

## `verify --head`

`--head` loads the workspace, reads `state.json`'s `head`, and verifies `forks/<head>.json`. The `fork_index` entry for that name must equal the content hash of the signed body. A mismatch is `replay`.

It then looks at every other `forks/*.json`. A sibling that returns a failed verification is ignored, including junk JSON and a non-integer `created_unix`. A sibling that verifies, and whose `created_unix` is a non-boolean integer greater than the head, is `replay`. If opening that sibling raises `ValidationError`, `CryptoError`, `IOPermissionError`, or `OSError`, `verify --head` returns `canonical` instead of skipping it.

A crash can write the new fork file and die before `state.json` records it. The new file is then a newer signed sibling of a stale head. `verify --head` returns `replay`. v0.1 does not repair that window. You still have both files. Sign a newer head when you mean to move forward, after you have read them.

`no_head` means `state.json` has no snapshot name yet.

## Commands

```bash
vesper --workspace ./workspace fork --name alpha
vesper --workspace ./workspace verify --head
vesper verify workspace/forks/alpha.json
vesper verify fixtures/forged-fork.json; echo EXIT:$?
```

What good looks like: the first three commands exit 0. The fork command prints the path. Both verify commands print `verify ok`. The forged fixture prints `vesper: bad_signature` and `EXIT:2`. That exit is the success condition for the fixture.

What failure means: any other reason on a fork you just signed means the file or the workspace changed after the write. Exit 0 on the forged fixture means a bad stamp was accepted. Treat that as a bug.
