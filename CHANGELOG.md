# Changelog

All notable changes to **vesper-runtime** are documented here.

This project is early and iterative. It is not a finished product. Versions follow [Semantic Versioning](https://semver.org/) while pre-1.0. `0.x` may break.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

---

## [0.1.0] — 2026-09-30 — Phase 1 MVP

First public slice. Local only. No model API.

### Added

- Workspace init with an identity directory at mode `0700` and a private key at mode `0600`.
- ECDSA P-256 signatures over SHA-256 of canonical JSON. HMAC-SHA256 is the fallback when the `ecdsa` package does not import.
- Four-tier memory: STM cap 100, semantic decay (`lambda` 0.02 per hour), graph prune, LTM promotion. `sleep` takes an injected `--now`.
- Uni Schema v2 check and heal. Heal fills documented structural defaults. It does not invent a character id.
- `vesper fork` and `vesper verify`, including parent hash checks and a refusal of a file whose name does not match the signed name.
- `vesper export --audit` writes `plan.md`, `evidence.md`, `critic.md`, `score.json`, `state_hash.txt`, and `fork_verified.json`.
- Task `tasks/001-heal-or-die.md` and `examples/passing-audit/`.
- Tests for forged signatures, weak key modes, decay, and path traversal.

### Notes

- The on-disk ECDSA key filename is `identity/edcsa-p256.priv` (the v0.1 layout name).
- `vesper verify PATH` loads a workspace key only when the file's `algo` is `hmac-sha256`. ECDSA verification uses the public point inside the fork.
- Identity files and audit files are opened with `O_NOFOLLOW`. A symlink is refused. Modes are set with `fchmod` on that descriptor.
- The key id is the first 16 hex characters of SHA-256 over the uncompressed public point. That is an identifier. The signature is the check.
- This release is not a wallet, not a money transmitter, and not an anonymity system.
- Getting started states the AS IS warranty, the roles this tool does not fill, and how to create, back up, and destroy a workspace key.
