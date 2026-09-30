# vesper-runtime

Local-first universe kernel for DagzTagz Uni: persistent memory, schema heal-or-reject, and signed forks.

**Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product.** Sister to [dagztagz-hypothesis-engine](https://github.com/DagzTagz/dagztagz-hypothesis-engine) and [Dagz-Scaffold](https://github.com/DagzTagz/Dagz-Scaffold). DagzTagz owns this repo. Grok Build may author code under the operator’s own account and terms. **This runtime does not call the Grok API.**

> **Current Status:** **v0.1.0** · **Phase 1 MVP** · experimental · **not a finished product**

---

## Vision

A character here is machine state: a callsign, four tiers of memory, and a chain of signed snapshots. The builder owns that slice. The kernel keeps it on disk between sessions, refuses a document that has lost its identity, and signs each fork so a later reader can see whether the bytes still match the key that produced them.

## What problem this solves

Agents forget. Files drift. A green test run can hide a check that never ran.

This kernel is the small local counterweight:

- **Persistence.** Short-term notes, semantic items, graph edges, and long-term memory survive the process.
- **Schema drift.** A Uni Schema v2 document is checked. Missing structural fields can be filled from documented defaults. A missing character id is rejected.
- **Forged forks.** Each fork carries an ECDSA P-256 signature over a canonical JSON body, plus the parent hash. A wrong key, a mutated field, or a detached signature fails `verify`.
- **False completion.** `vesper export` writes a folder. The score is true only when the forged fixture was rejected, decay actually moved a weight, and the key mode was checked.

## What ships today

Phase 1 is a Python CLI and a library.

- `vesper init`, `remember`, `link`, `sleep`, `fork`, `verify`, `schema`, `export`
- Four-tier memory with an injected clock
- JSON Schema subset loader for the in-tree Uni Schema v2 fixture
- ECDSA P-256 signatures (HMAC-SHA256 only if the `ecdsa` package cannot be imported)
- An audit folder: `plan.md`, `evidence.md`, `critic.md`, `score.json`

What does not ship:

- No UI
- No embeddings
- No network client
- No model API
- Not a wallet, not a money transmitter, not a security offering, not an official scientific instrument, and not an anonymity system

## How it works

1. **init** creates a workspace, a mode `0700` identity directory, and a mode `0600` private key.
2. **remember** appends an item. Short-term memory keeps the newest 100 and drops the oldest.
3. **sleep** decays semantic weights, prunes weak graph edges, and promotes strong or pinned items into long-term memory.
4. **fork** writes `forks/<name>.json` signed over the canonical body.
5. **verify** checks the signature, the schema id, the state hash, and the parent hash.
6. **export** writes an audit folder a person can read without opening the chat.

## Getting Started

Full walk: **[getting-started.md](getting-started.md)**. Dry path first. Nothing below calls a model.

```bash
git clone https://github.com/DagzTagz/vesper-runtime.git
cd vesper-runtime
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
vesper --help
```

Success means pytest finishes with no failures, and `vesper --help` prints the command list and exits 0. Both stay on this machine.

## Disclosures

- **Not malware.** The install does not open a socket. The CLI does not phone home, does not send crash reports, and does not collect telemetry.
- **Keys stay on disk** unless a person copies them. The tool refuses a private key that is not mode `0600`. It does not print the key.
- **Not an official xAI product.** “Powered by Grok” in the DagzTagz sense means Grok Build may have been the pair programmer, on the operator’s account. This process does not call `api.x.ai`.
- **Local policy only.** There is no HIPAA claim, no SOC 2 claim, and no “compliance certified” claim. Local files are as private as the account and the disk.
- **Standard signatures only.** SHA-256, HMAC-SHA256, and ECDSA P-256 (`secp256r1`). No custom cipher. No unpublished algorithm.

## Who this is for

Builders on the Ubuntu privacy VM who already use Grok Build with Dagz-Scaffold and dagztagz-hypothesis-engine, and who want a local state file they can sign and audit. If you want a chat UI or a hosted agent, this is the wrong tree.

## Docs map

| If you want to… | Read |
|-----------------|------|
| Install and run locally | [getting-started.md](getting-started.md) |
| Threat model and key handling | [SECURITY.md](SECURITY.md) |
| Version history | [CHANGELOG.md](CHANGELOG.md) |
| What we will and will not build | [ROADMAP.md](ROADMAP.md) |
| Send a patch | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Agent rules | [AGENTS.md](AGENTS.md) |

## Tree overview

`src/vesper/` is the kernel. `crypto.py` is the only module that reads or writes key bytes. `fixtures/` holds the schema, a drifted state, and a forged fork that `verify` must reject. `tasks/001-heal-or-die.md` is the Phase 1 gate. `examples/passing-audit/` is a bundle produced by `vesper export`. `tests/` uses temporary directories and an injected clock.

## Roadmap

Phase 1 is the CLI above. Later phases stay local. See [ROADMAP.md](ROADMAP.md). We are not building a wallet, a network service, or a UI in this repo.

## Contributing

Small fixes can be a pull request. Security reports go through [SECURITY.md](SECURITY.md), not a public issue. Rules: [CONTRIBUTING.md](CONTRIBUTING.md).

## Development & Attribution

This is an open community effort under the DagzTagz name.

**Grok as pair programmer.** Grok Build may draft code, tests, and docs. That work runs under the operator’s own account and terms. Humans review it. DagzTagz owns the repository. The runtime itself does not call the Grok API, and a dry `pytest` does not spend model credit. Live Grok Build use, if a person chooses it later, is that person’s bill.

**Not an official collaboration.** There is no xAI or SpaceXAI endorsement, partnership, or sponsorship.

## License

Apache License 2.0. Copyright DagzTagz contributors. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

The work is provided **AS IS**. There is no warranty of fitness for a particular purpose, no warranty of merchantability, and no warranty of non-infringement.

## Please remember

Prefer the dry path until you mean to create a key. Do not commit `workspace/`, private keys, or live audit folders that contain personal notes. Read `evidence.md` yourself.

**Leave folders a skeptic can audit.**
