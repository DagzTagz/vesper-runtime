# AGENTS.md

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product.

Humans start at [getting-started.md](getting-started.md). This file is for an agent in the tree.

You may author code under the operator’s account and terms. DagzTagz owns the repo. **This runtime does not call the Grok API.** Do not add a client that does. Do not phone home. Do not collect telemetry.

## Hard rules

- Python 3.11+. Standard library, plus optional `ecdsa` behind `src/vesper/crypto.py`.
- No numpy, no web framework, no cloud SDK, no extra packages.
- No network from tests or from the CLI.
- `crypto.py` is the only module that touches private key bytes.
- Do not weaken `0600` / `0700` checks to make a test pass. Do not chmod a weak key and continue.
- Do not log private keys. Do not write them world-readable. Do not embed a long-lived key in a test.
- Event ids and filenames: `[A-Za-z0-9._-]`, max 128, no `..`, no absolute path.
- Canonical JSON: UTF-8, `sort_keys=True`, separators `(',', ':')`, no NaN or Infinity.
- Red test first for each security rule, then the implementation that turns it green.
- Quit is not success. A green suite that never called `verify` on `fixtures/forged-fork.json`, never moved the decay clock, or never checked key mode is a failed task.

## Exit codes

`0` success. `1` usage. `2` validation or signature. `3` I/O or permissions.

`vesper verify PATH` for an ECDSA file must not require `./workspace` to exist. HMAC files do require the workspace key. Load it only after the file’s `algo` is `hmac-sha256`.

## Task 001

`tasks/001-heal-or-die.md` is the gate. `vesper export --audit` must actually run the checks. Do not hand-write `score.json`.

The audit folder must not contain PEM-shaped fragments. The operator grep pattern stays in the task file so the bundle does not match itself.

## What you do not ship

No wallet. No custom cipher. No steganography. No traffic obfuscation. No UI. No embeddings. No claim of HIPAA, SOC 2, certification, or “military-grade”.

Sibling repos stay as they are. Do not rewrite Dagz-Scaffold or dagztagz-hypothesis-engine to make this kernel pass.

## Done

Done means pytest is green, `vesper verify fixtures/forged-fork.json` exits 2, the private key is `0600` after init, the audit folder has no key material, and README plus LICENSE are present. Say which commands you ran. If a constraint fights convenience, keep the constraint and record a waiver in `critic.md`.
