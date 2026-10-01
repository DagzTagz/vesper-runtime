# AGENTS.md

Unofficial DagzTagz project. This runtime does not call the Grok API. Humans start at [getting-started.md](getting-started.md). Roles the tool does not fill: [that page](getting-started.md#what-this-tool-is-not).

You may author code under the operator’s account and terms. DagzTagz owns the repo. Do not add a client that calls the Grok API. Do not phone home. Do not collect telemetry.

## Hard rules

- Python 3.11+. Standard library plus the `ecdsa` dependency, imported only inside `src/vesper/crypto.py`. If that import fails, HMAC is the fallback.
- No numpy, no web framework, no cloud SDK, no extra packages.
- No network from tests or from the CLI.
- `crypto.py` is the only module that touches private key bytes.
- Do not weaken `0600` / `0700` checks to make a test pass. Do not chmod a weak key and continue.
- Init sets the named workspace directory to `0700`. Do not chmod parent directories.
- `schema heal --write` keeps a non-zero mode that is a subset of `0644`. Do not force `0600` files to `0644`.
- If an audit scan hits PEM-shaped text, withhold the fork bytes, keep `pass` false, and do not write the marker into the scan line.
- Do not log private keys. Do not write them world-readable. Do not embed a long-lived key in a test. Do not rename `identity/edcsa-p256.priv` in v0.1.
- Event ids and filenames: `[A-Za-z0-9._-]`, max 128, no `..`, no absolute path. The fork filename stem must equal the signed `name`. Do not weaken that check so `fork_verified.json` verifies in place.
- Canonical JSON: UTF-8, `sort_keys=True`, separators `(',', ':')`, no NaN or Infinity.
- Red test first for each security rule, then the implementation that turns it green.
- Quit is not success. A green suite that never called `verify` on `fixtures/forged-fork.json`, never moved the decay clock, or never checked key mode is a failed task.

## Exit codes

`0` success. `1` usage. `2` validation or signature. `3` I/O or permissions.

`vesper verify PATH` for an ECDSA file must not require `./workspace` to exist. HMAC files do require the workspace key. Load it only after the file’s `algo` is `hmac-sha256`.

## Task 001

`tasks/001-heal-or-die.md` is the gate. `vesper export --audit` must actually run the checks. Do not hand-write `score.json`.

The audit folder must not contain PEM-shaped fragments. The operator grep pattern stays in the task file so the bundle does not match itself.

## Do not ship

No wallet. No custom cipher. No steganography. No traffic obfuscation. No UI. No embeddings. No HIPAA, SOC 2, certification, or “military-grade” claim.

Do not rewrite Dagz-Scaffold or dagztagz-hypothesis-engine to make this kernel pass.

## Done

Done means pytest is green, `vesper verify fixtures/forged-fork.json` exits 2, the private key is `0600` after init, the workspace directory is `0700`, the audit folder has no key material, and README plus LICENSE are present. Say which commands you ran. If a constraint fights convenience, keep the constraint and record a waiver in `critic.md`.
