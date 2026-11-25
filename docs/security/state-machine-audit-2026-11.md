# State-machine audit, November 2026: vesper-runtime

This page is the vesper-runtime part of the full disclosure for the November 2026 implicit-state-machine audit of the DagzTagz repositories.

- The complete report, with every finding and how each was reproduced, is in [Dagz-Scaffold/docs/audits/2026-11-state-machine-audit.md](https://github.com/DagzTagz/Dagz-Scaffold/blob/main/docs/audits/2026-11-state-machine-audit.md).
- The same report holds the remediation status for all 13 findings across the four repositories.
- The audited commit is [`5b775d7`](https://github.com/DagzTagz/vesper-runtime/tree/5b775d7115c5e81ebd7a98d12e1115be87e49c3b).
- All fixes below merged on `main` on 2026-11-24 in [vesper-runtime#1](https://github.com/DagzTagz/vesper-runtime/pull/1) (merge commit [`e241040`](https://github.com/DagzTagz/vesper-runtime/commit/e24104020be997b48ed12db9fe1fecb52663ae90)).
- [DB-002](../../disclosurebulletins.md#db-002--interrupted-fork-and-init-left-the-workspace-stuck) is the bulletin record for the two Med findings.

None of these findings let anyone forge a fork, read a key, or bypass `verify`. The two Med findings could leave a workspace stuck after a crash or a failed write. The Low findings let invalid states be written down without any observed failure.

| Finding | Priority | What was wrong | Fix |
|---|---|---|---|
| F4 | Med | Writing a fork took two separate file writes with no lock between them. A failure between the writes made `verify --head` report `replay` until the next fork. Two concurrent writers could lose an update. **Reproduced.** | [`0fcca7c`](https://github.com/DagzTagz/vesper-runtime/commit/0fcca7c) |
| F5 | Med | An I/O error during `vesper init` left a half-built workspace. `init` refused to run again, and every other command failed on it. **Reproduced.** | [`cbc2575`](https://github.com/DagzTagz/vesper-runtime/commit/cbc2575) |
| F7 | Low | `VerifyResult` could hold `ok=True` with no document. Rejection reasons were free strings. | [`f549ca6`](https://github.com/DagzTagz/vesper-runtime/commit/f549ca6) |
| F11 | Low | Each memory item stored its tier twice. The copies were only reconciled by `schema heal`, never when state was loaded. | [`f74d3de`](https://github.com/DagzTagz/vesper-runtime/commit/f74d3de) |
| F12 | Low | `Identity` kept the algorithm as a string next to two nullable keys, so the name and the key could disagree. | [`39dd62c`](https://github.com/DagzTagz/vesper-runtime/commit/39dd62c) |
| (side bug) | Low | If an atomic write failed, its temp file was left in the workspace. | [`0c64b83`](https://github.com/DagzTagz/vesper-runtime/commit/0c64b83) |
| (side bug) | Low | `export.py` spelled the key filenames out by hand instead of using the constants in `vesper.paths`. | [`d8acc48`](https://github.com/DagzTagz/vesper-runtime/commit/d8acc48) |

## What changed

- **F4**
  - `fork`, `remember`, `link` and `sleep` take an exclusive `flock` on `<workspace>/.lock` for the whole read-modify-write.
  - `fork` writes a journal, `.fork-pending.json`, before it writes the fork file, and removes the journal after `state.json` is committed.
  - The next `fork`, `remember`, `link`, `sleep`, `verify --head` or `export` finishes an interrupted fork, or discards it, and says which on stderr.
  - The rule is to commit only when the fork file verifies, matches the journal's hash, and its parent is the current head.
- **F5**
  - `init` writes `.init-in-progress` first and removes it last.
  - The workspace is classified as absent, partial, ready or foreign.
  - A partial workspace can be finished with `vesper init --resume`.
  - `init` never deletes a half-written `identity/`. If it cannot be loaded, the message asks you to move it aside.
  - `init` now also refuses a `state.json` that has no `identity/` next to it.
- **F7**
  - `VerifyResult` is now `Verified | Rejected`, and `Reject` is a StrEnum.
  - The printed reasons and exit codes are unchanged.
  - `.ok`, `.reason` and `.waivers` still exist on both classes.
- **F11**
  - Every load checks each item's `tier` against the list it sits in.
  - A missing `tier` is accepted. A mismatched one is refused, and the error points to `schema heal`.
  - The contract for writers outside this program is documented in [docs/memory.md](../memory.md#writers-outside-this-program).
- **F12**
  - `Identity` is now `EcdsaIdentity | HmacIdentity`. Each class carries exactly one key.

## Compatibility

Existing forks, keys and workspaces keep working, with these exceptions:

- `load_state` now refuses an item whose `tier` disagrees with its list. Run `vesper schema heal --write` once to fix it.
- `init` refuses a foreign `state.json`, and a partial workspace unless `--resume` is passed.
- Code that builds `Identity(...)` or `VerifyResult(...)` directly must use the new classes. The CLI does not.
- Workspaces can now contain `.lock`, `.fork-pending.json` and `.init-in-progress`. See [docs/workspace.md](../workspace.md).

## Follow-up, 2026-11-25: residual items from the shared-compute review

**Status: Merged.** Silent HMAC fallback: [vesper-runtime#3](https://github.com/DagzTagz/vesper-runtime/pull/3), merge [`b89579c`](https://github.com/DagzTagz/vesper-runtime/commit/b89579c4fb785ab2d3f0b58809b02fd272c82581) (fix [`9bfbafd`](https://github.com/DagzTagz/vesper-runtime/commit/9bfbafd3f0083b4a5f746cde4d0779d0d2f74198)). One account, one key: [vesper-runtime#4](https://github.com/DagzTagz/vesper-runtime/pull/4), merge [`d216686`](https://github.com/DagzTagz/vesper-runtime/commit/d21668654f577cd44ca3cc6cf5c2bf387cefa583) (fix [`3d8de1e`](https://github.com/DagzTagz/vesper-runtime/commit/3d8de1ee141fb38f104200856c046322abf8f618)).

| Item | What was left | Change |
|---|---|---|
| Silent HMAC fallback | If `ecdsa` did not import, `init` made a shared-secret HMAC key without saying so. Anyone who can verify with it can forge. | `init` refuses without `ecdsa` unless `VESPER_INSECURE_ALLOW_HMAC_FALLBACK=1`. Existing HMAC workspaces are verify-only. See [docs/forks.md](../forks.md#moving-off-an-hmac-key). |
| One account, one key | Agents that run under the same operating-system account can all read `identity/` and sign as that workspace. The `0700`/`0600` modes do not separate them. | Documented in [docs/threat-model.md](../threat-model.md), with a how-to for one account and one key per agent. |

**Breaking:** a machine without `ecdsa` can no longer create or sign with a vesper key unless `VESPER_INSECURE_ALLOW_HMAC_FALLBACK=1` is set.

