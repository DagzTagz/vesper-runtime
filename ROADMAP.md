# Roadmap

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API. The full list of roles it does not fill is in [getting-started.md](getting-started.md#what-this-tool-is-not).

v0.1.0 is experimental. It is a first slice you can run on Ubuntu. It is not a finished product.

## Phase 1 — a folder you can check

This is what v0.1.0 ships. Each line is here because a later reader needs it.

- A workspace directory at mode `0700`, an identity directory at mode `0700`, and a private key at mode `0600`. You can see who is allowed to read the notes.
- Four trays of notes, and `sleep`, so a long list does not grow without a rule. The clock can be injected with `--now`, so a test does not wait on the wall clock.
- Uni Schema v2 check and heal. A file that has lost its identity is refused. A file that is only missing lists can be filled.
- ECDSA P-256 snapshots, a parent hash, and replay checks. You can see whether a file still matches the key that stamped it.
- HMAC-SHA256 only when the `ecdsa` package does not import, so the program still has one stamp to check.
- `vesper export --audit`, so a reviewer can read the checks without the chat and without the private key.

## Out of this repository

These are choices about what the program is. They are not a hidden backlog.

- No user interface. The terminal transcript is the thing you can copy into a review.
- No embeddings and no vector index. v0.1 ranks notes with the sleep rules, which you can recompute.
- No network client, no telemetry, and no crash report. The program does not talk to the internet.
- No model API and no Grok API call. Editing the repo in Grok Build is your account. Running `vesper` is not.
- No wallet, no coin, no payment, and no seed phrase. The key only signs JSON. People should not treat it as money.
- No money-transmitter flow and no security offering. The project does not hold customer funds.
- No anonymity network, no traffic padding, and no steganography. Local files are as private as the account and the disk.
- No custom cipher and no unpublished cryptography. A reviewer can look up P-256 and HMAC-SHA256.
- No in-place key rotation command. The manual steps are in [getting-started.md](getting-started.md). A rotate that chmod'd a weak file would hide a mistake.
- No multi-user access control. Modes `0700` and `0600` are the whole sharing story in v0.1.

## Later, still on your computer

A later version may add these. None of them has a date.

- A documented rotate that writes a new key beside the old one and signs a snapshot naming both kids. You could retire a key without chmod'ing a weak file, and old snapshots would still name the key that signed them.
- Schema drafts past the small v2 fixture, still refusing a file with no identity. More fields can be added without the program guessing who the notes belong to.
- Clearer parent-chain rules when two snapshots were signed by different kids. A reviewer could see a key change instead of treating it as a bad stamp.
- A Dagz-Scaffold reader that consumes `score.json` without copying this program's private keys. The audit folder would stay the handoff.

## How a phase changes

A phase change is a changelog entry, a test that fails if the new rule is skipped, and an export a person can read. A green suite that never called `verify` on `fixtures/forged-fork.json` is not a phase change.
