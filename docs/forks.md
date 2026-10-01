# Forks

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API. The roles this tool does not fill are in [getting-started.md](../getting-started.md#what-this-tool-is-not).

A fork is a snapshot of your notes plus a signature. The file is `forks/<name>.json`, and it is mode `0600`, so only your user can read it. The `signature` field is the stamp. Every other field is the signed body. `vesper verify` rebuilds that body and checks the stamp. A match means the body still agrees with the key that signed it. It does not prove a legal identity, and it does not prove that the note is true.

This key is not a Bitcoin key. It uses NIST P-256, a different curve, and it only signs JSON.

## What gets signed

The file you open in an editor is pretty-printed, with sorted keys, an indent of two spaces, and a final newline. The signature does not cover those spaces. It covers the canonical form of the body. Canonical JSON is one standard spelling of the same data: UTF-8, keys sorted, separators `(",", ":")`, and `NaN` and `Infinity` rejected. Non-ASCII text is kept as itself.

`state_hash` is the hex SHA-256 of the canonical `state` object. `memory_root` is the hex SHA-256 of the canonical `state.memory` object. `parent_hash` is the hex SHA-256 of the parent's canonical body, which is the parent object with `signature` removed. The notes inside the snapshot already include this fork as `head`, because the program updates that field before it signs.

| Field | What it holds |
|-------|----------------|
| `algo` | `ecdsa-p256` on a normal install. `hmac-sha256` only when the `ecdsa` package did not import. |
| `created_unix` | A whole number of seconds. This is the clock used for the snapshot. |
| `kid` | The short key id. For ECDSA it is the first 16 hex characters of SHA-256 over the uncompressed public point. That point is byte `0x04`, then X, then Y. The short id names the key. The signature is the check. |
| `memory_root` | The fingerprint of `state.memory`, as defined above. |
| `name` | The snapshot name. The filename stem must be this same string. |
| `parent_id` | The previous snapshot's name, or JSON `null` on the first snapshot. |
| `parent_hash` | The fingerprint of the previous signed body, or JSON `null` on the first snapshot. |
| `schema_id` | Always `dagztagz.uni.fork.v2`. |
| `schema_version` | Always the string `"2"`. |
| `state` | The notes file at the moment of the snapshot. |
| `state_hash` | The fingerprint of `state`, as defined above. |
| `public_key_hex` | Present for ECDSA only. It is the uncompressed public point, written as hex. |
| `hmac_kid` | Present for HMAC only. It is set to the same value as `kid`. |
| `signature` | The stamp. This field is not part of the signed body. |

## How the stamp is made

| | ECDSA, the normal case | HMAC, the fallback |
|--|------------------------|--------------------|
| When it is used | The `ecdsa` package imports. | `import ecdsa` fails. |
| What is signed | SHA-256 of the canonical body. The 32-byte digest is signed with `SigningKey.sign_digest`, DER-encoded with `sigencode_der`, and stored as hex. | HMAC-SHA256 of the canonical bytes themselves, stored as hex. The bare digest is not what HMAC covers. |
| What verify needs | The public point in `public_key_hex`. The workspace and the private key are not required. | The secret file `identity/hmac.key` in the workspace. The program loads that file only after it reads `algo` and sees `hmac-sha256`. |
| A mismatched key id | Reason `kid`, before the stamp is treated as `bad_signature`. | Reason `kid` when the workspace key's id does not match `kid`. A missing workspace key is `bad_signature`. |

## The parent link

The first snapshot sets both `parent_id` and `parent_hash` to JSON `null`. That pair is the start of the chain. The two fields are required to be present. Omitting either one makes the file fail as `canonical`.

| Parent fields | Result |
|---------------|--------|
| Both JSON `null` | The snapshot is accepted as the start of a chain. |
| One is a string and the other is `null`, or either one has another type | Reason `parent_hash`. |
| Both are strings | The previous file must be the sibling `<parent_id>.json`. Its content fingerprint must equal `parent_hash`. |
| The parent id is not a legal name, or the parent path is a shortcut | Reason `parent_hash`. |
| The parent file is absent | Reason `parent_missing`, unless `--allow-orphan` is set. |
| `created_unix` is earlier than the parent's time | Reason `replay`. An equal time is allowed. |
| `state_hash` is identical to the parent's `state_hash` | Reason `replay`, even when the clock moved forward. |
| The parent name repeats one already visited, or it equals this file's own name | Reason `cycle`. |

`--allow-orphan` applies only when the parent file is absent. Verify then succeeds and records waiver id `orphan-parent`, with the reason `parent file is missing and --allow-orphan was set`. Do not use the flag to hide a missing parent. A parent file that exists is still checked in full.

At the moment you run `vesper fork`, a clock earlier than the parent is rejected before a file is written. The message is `fork clock is earlier than its parent`, and the exit code is `2`. That is a different report from a later `verify` that returns `replay`.

## The filename

The filename stem must equal the signed `name`. `forks/alpha.json` verifies only when `name` is `alpha`. A copy named `copied.json` returns `name`, even when every byte of the body is intact.

A legal name is one segment of `[A-Za-z0-9._-]`, from 1 to 128 characters, with no `..`. The written filename is `name.json`, and that filename must also be at most 128 characters. A name of 124 characters or more is rejected when you create the fork, because `name.json` would be longer than 128. A name of 123 characters is the longest name that fits.

`fork_verified.json` in an audit folder keeps that filename on purpose. Verifying that path returns `name`. Copy the bytes to `<signed-name>.json`, or verify `workspace/forks/<signed-name>.json`. The sample in `examples/passing-audit/` is named `alpha` inside the JSON. A copy named `alpha.json` verifies as `ok`. The path `fork_verified.json` does not.

## What `verify` checks, in order

`vesper verify PATH` stops at the first failing reason. Exit `0` and the text `verify ok` mean the reason `ok`.

| Order | Check | Failure reason |
|-------|--------|----------------|
| 1 | The path must not contain `..`. | `name` |
| 2 | The path must be a real file. A shortcut or a missing file fails here. | `parent_missing` |
| 3 | The file must be readable JSON, and the top value must be an object. | `canonical` |
| 4 | `signature` must be a non-empty hex string with an even number of characters. | `bad_signature` |
| 5 | Every field in the table above must be present, except `public_key_hex`, `hmac_kid`, and `signature`. | `canonical` |
| 6 | `schema_id` must be `dagztagz.uni.fork.v2`, and `schema_version` must be `"2"`. | `schema_id` |
| 7 | `name` must be a legal name, and the filename stem must equal it. | `name` |
| 8 | `state` must be an object with a `memory` object. `state_hash` and `memory_root` must match the canonical fingerprints. | `state_hash` |
| 9 | `created_unix` must be an integer. JSON `true` and `false` are rejected here, because a boolean is not a timestamp. | `canonical` |
| 10 | The key id is checked, then the stamp is checked. | `kid`, then `bad_signature` |
| 11 | The parent pair is checked, using the parent table above. | `parent_hash`, `parent_missing`, `replay`, or `cycle` |

## What `verify --head` adds

`--head` opens the workspace, reads `head` from `state.json`, and verifies `forks/<head>.json`. If `head` is missing or is not a string, the reason is `no_head`. If that string is not a legal name, the reason is `name`.

`state.json` keeps a `fork_index` entry for the head. That entry must equal the content fingerprint of the signed body. A mismatch is `replay`.

The command then looks at every other `forks/*.json`.

| Sibling file | Result |
|--------------|--------|
| Not a regular `.json` file, or a shortcut | Ignored. |
| Filename stem is not a legal name | The head check fails with `name`. |
| Verifies, and its `created_unix` is a non-boolean integer greater than the head | `replay`. |
| Does not verify, including broken JSON and a timestamp that is not an integer | Ignored. |
| Opening it raises `ValidationError`, `CryptoError`, `IOPermissionError`, or `OSError` | The head check fails with `canonical`. |

A crash can write the new fork file and stop before `state.json` records it. The new file is then a newer signed sibling of a stale head, and `verify --head` returns `replay`. This version does not repair that window. Both files are still on disk. Read them, then sign a newer head when you mean to move forward.

## Commands

```bash
vesper --workspace ./workspace fork --name alpha
vesper --workspace ./workspace verify --head
vesper verify workspace/forks/alpha.json
vesper verify fixtures/forged-fork.json; echo EXIT:$?
```

What good looks like: the first three commands exit `0`. The fork command prints the path of `workspace/forks/alpha.json`. Both verify commands print `verify ok`. The forged sample prints `vesper: bad_signature` and `EXIT:2`. That exit is the success condition for the sample.

What failure means: any other reason on a fork you just signed means the file or the workspace changed after the write. Exit `0` on the forged sample means a bad stamp was accepted. Treat that as a bug.
