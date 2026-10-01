# Changelog

All notable changes to **vesper-runtime** are documented here.

The package version in this tree is still 0.1.0. The README status line stays **v0.1.0 experimental**. The unreleased notes below are the working tree after the published 0.1.0 commit.

This project is early and iterative. It is not a finished product. Versions follow [Semantic Versioning](https://semver.org/) while pre-1.0. `0.x` may break.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

The roles this tool does not fill are in [getting-started.md](getting-started.md#what-this-tool-is-not).

---

## [Unreleased]

### Fixed

- `schema heal --write` keeps an existing mode that is a non-zero subset of `0644`. A `0600` notes file stays `0600`. A new file, or a wider mode, is written as `0644`.
- `vesper init` sets the workspace directory you named to mode `0700`, including a directory that already existed. Parent directories are left alone. A symlinked workspace root is refused.
- If an audit scan finds PEM-shaped text, `fork_verified.json` is rewritten as JSON `null`, the scan line does not repeat the marker, and `pass` stays false.
- `verify --head` ignores a sibling file that does not verify. A sibling that verifies and has a larger integer `created_unix` is still `replay`. JSON `true` is not treated as a timestamp. A crash that leaves a newer signed fork beside a stale head still returns `replay`.
- The identity object's text form does not include key bytes.
- Dry-run init prints `identity/hmac.key` when the `ecdsa` package did not import, and `identity/edcsa-p256.priv` otherwise.

### Docs

- 2026-09-30: rewrote the human guides and added [docs/glossary.md](docs/glossary.md), [docs/commands.md](docs/commands.md), [docs/workspace.md](docs/workspace.md), [docs/schema.md](docs/schema.md), [docs/memory.md](docs/memory.md), [docs/forks.md](docs/forks.md), [docs/audit-export.md](docs/audit-export.md), [docs/threat-model.md](docs/threat-model.md), and [docs/faq.md](docs/faq.md).
- 2026-09-30: added [disclosurebulletins.md](disclosurebulletins.md). The first entry records the `python-ecdsa` P-256 timing advisory, GHSA-wj6h-64fc-37mp, which has no patched release.
- 2026-09-30: rewrote [docs/audit-export.md](docs/audit-export.md) so each exported file, plan promise, critic heading, and score check is explained in plain language.
- 2026-09-30: rewrote [docs/commands.md](docs/commands.md) so each command, flag, and verify result is explained in plain language.

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
- Getting started states the AS IS warranty, the roles this tool does not fill, and how to create, back up, and destroy a workspace key.
