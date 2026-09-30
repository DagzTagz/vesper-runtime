# Roadmap

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product.

**This runtime does not call the Grok API.** That stays true in later phases unless a maintainer changes this document and the README in the same release.

v0.1.0 is a Phase 1 MVP. It is experimental. It is not a finished product.

## Ships in v0.1.0

- Local workspace, identity directory `0700`, private key `0600`
- Four-tier memory with an injected clock
- Uni Schema v2 check, and heal-or-reject for the in-tree fixture
- ECDSA P-256 fork signatures, parent hash, and replay checks
- HMAC-SHA256 only when the `ecdsa` package does not import
- `vesper export --audit` with plan, evidence, critic, and score

## Not in this repo

These are product decisions, not a backlog in disguise.

- No user interface
- No embeddings and no vector index
- No network client, no telemetry, no crash report
- No model API and no Grok API call
- No wallet, no coin, no payment, no seed phrase
- No money-transmitter flow and no security offering
- No anonymity network, no traffic padding, no steganography
- No custom cipher and no unpublished cryptography
- No in-place key rotation command (the manual procedure is in [getting-started.md](getting-started.md))
- No multi-user access control

## Later, still local

A later version may add these if a skeptic can still audit the folder. None of them are promised by a date.

- A documented rotate that writes a new key beside the old one and signs a fork that names both kids, without ever chmod'ing a weak file
- Schema drafts beyond the minimal v2 fixture, still with reject-on-missing-identity
- Stronger parent-chain rules when two forks were signed by different kids
- A Dagz-Scaffold reader that consumes `score.json` without copying this kernel’s private keys

## How a phase changes

A phase change is a changelog entry, a test that fails if the new rule is skipped, and an export a person can read. Quitting with a green suite that never called `verify` on `fixtures/forged-fork.json` is not a phase change.
