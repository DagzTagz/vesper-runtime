# Security Policy

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API.

vesper-runtime is a local development and provenance tool. It signs JSON with ECDSA P-256, or with HMAC-SHA256 if the `ecdsa` package cannot be imported. You type commands in a terminal. The notes and the key stay in a folder you name.

This document is not legal advice. The license is the warranty text. You are responsible for the key and the files.

The tool is not a wallet, not a money transmitter, not a security offering, not an official scientific instrument, and not an anonymity system. A successful `verify` does not prove a legal identity.

There is no HIPAA claim, no SOC 2 claim, and no certification. Privacy is the privacy of this Unix account and this disk. The CLI does not open a network connection and does not send crashes or analytics. `git` on your machine is a network path only when you run git.

HMAC-SHA256 and ECDSA P-256 are published algorithms. This project does not implement a custom cipher, steganography, or traffic obfuscation. There is no unpublished algorithm.

No bounty is offered.

The work is provided **AS IS**, under Apache-2.0. There is no warranty of fitness for a particular purpose, no warranty of merchantability, and no warranty of non-infringement.

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x on `main` | Yes. Fixes land here. |
| Older snapshots and forks | Best effort. Report against current `main`. |

## Reporting

Use a private report. Do not open a public issue that contains a private key, a token, or a proof of concept that still works.

### Preferred: GitHub private vulnerability report

1. Open https://github.com/DagzTagz/vesper-runtime
2. Security → Advisories → Report a vulnerability
3. Direct link: https://github.com/DagzTagz/vesper-runtime/security/advisories/new

### If GitHub advisories are unavailable

Email **dagztagz369@proton.me**

Subject: `[SECURITY] vesper-runtime`

Say that a key was exposed. Do not attach the key. If you own the key, stop signing with it and init a new workspace. See [getting-started.md](getting-started.md).

Findings we have already reviewed, including dependency alerts that have no patched release, are written in [disclosurebulletins.md](disclosurebulletins.md). A bulletin is the public record of what we know and what we decided. It is not a substitute for the private report above.

## What to include

1. A one- or two-sentence summary
2. Who is affected
3. The file, command, or commit
4. Steps to reproduce on a local workspace
5. The smallest proof that shows the issue
6. How to reach you

## What we will do

- Acknowledge within 72 hours when the inbox is watched
- Triage and keep you posted on major changes
- Credit you if you want credit
- Not pursue legal action against good-faith research that follows this policy

Default coordinated-disclosure window: 90 days before a public write-up. We may publish sooner if people are signing with a bad key. Please do not post exploit details in a public issue first.

Out of scope: general bugs, style nits, theoretical issues with no local impact, and vulnerabilities that exist only in another project. Ordinary bugs can be a public issue.

## Threat model

These are the failures the program is written against. A plain version, including what you would see on the terminal, is in [docs/threat-model.md](docs/threat-model.md).

| Id | Failure | What the code does |
|----|---------|--------------------|
| T1 | A private key lands in git, a log, `evidence.md`, or a world-readable file | Key bytes stay in `crypto.py`. Export does not copy `identity/`. If a verified fork contains PEM-shaped text, `fork_verified.json` is replaced with JSON `null`, the scan line does not repeat the marker, and `pass` stays false. |
| T2 | Schema drift: missing fields, wrong types, unknown properties | `schema check` reports problems. `schema heal` fills documented structural defaults. It rejects a missing character id, universe id, schema version, or forks list. Unknown properties are kept. Reserved names `__proto__`, `constructor`, and `prototype` are rejected. |
| T3 | Fork forgery: wrong key, mutated body, detached signature | `verify` rebuilds the canonical body, checks the key id, and checks the signature. A kid that does not match the public point is reason `kid` before `bad_signature`. |
| T4 | A parent link breaks, or an old snapshot is replayed as the new head | `parent_hash` must match the parent file. The filename stem must match `name`. `created_unix` must not go backwards. An identical `state_hash` to the parent is a replay. `verify --head` ignores a sibling that does not verify. A sibling that verifies with a larger `created_unix` is a replay. JSON `true` is not a timestamp. |
| T5 | Memory poisoning: unbounded STM, NaN weights, path characters in ids | STM cap is 100. Non-finite weights are rejected. Ids are a single safe segment: `[A-Za-z0-9._-]`, length 1..128, no `..`. |
| T6 | Paths escape the workspace | The workspace root is explicit. `..`, absolute paths, and symlinks that leave the root are rejected. A symlinked workspace root is refused. |
| T7 | A process uses a mode `0644` private key, or a workspace directory other accounts can replace | The key is opened with `O_NOFOLLOW`. Mode is `fstat` on that descriptor. Anything other than `0600` is refused and is not chmod'd into shape. The identity directory must be `0700`. Init sets the workspace directory you named to `0700` and does not chmod its parents. `schema heal --write` keeps an existing mode that is a non-zero subset of `0644`. |
| T8 | Tests are green while forged-signature or decay cases never ran | `vesper export` runs those checks and writes the commands into `evidence.md`. A suite that skipped them does not get `"pass": true`. |

## Keys

- Algorithm: ECDSA on NIST P-256 (`secp256r1`) via the PyPI package `ecdsa`, isolated in `src/vesper/crypto.py`. This key is not a Bitcoin key. It only signs JSON.
- Signed bytes: UTF-8 JSON, `sort_keys=True`, separators `(',', ':')`, no NaN or Infinity. ECDSA signs the 32-byte SHA-256 digest with `sign_digest` and DER encoding. The stored signature is hex.
- Key id: first 16 hex characters of SHA-256 over the uncompressed public point (`0x04 || X || Y`). The truncation identifies a key. The signature is the check.
- On-disk name: `identity/edcsa-p256.priv`. The spelling `edcsa` is the v0.1 name. Do not rename it in this version. Directory mode `0700`. File mode `0600`. `public.json` is `0644` and contains the kid, the algorithm, and the public point hex. It does not contain a PEM block.
- Fallback: if `import ecdsa` fails, the kernel writes `identity/hmac.key` and authenticates the canonical bytes with HMAC-SHA256. `public.json` then stores the kid only. HMAC verify loads that key from the workspace. ECDSA verify uses the public point inside the fork file. Dry-run init prints the filename that matches this choice.
- Two secret files in one identity directory are refused. An existing identity directory is not overwritten.
- Tests generate keys in a temporary directory. pytest is set to keep none of those directories (`tmp_path_retention_policy = none`). Do not commit a key so a test can stay offline.
- A killed test run can still leave a key under `/tmp/pytest-of-*`. Shred the key file, then remove that tree, before you pack a release. `shred -u -n 1` overwrites the named file once and unlinks it. On an SSD, a copy-on-write disk, or some VM disks, that overwrite may not reach the old blocks. This tool does not wipe free space.
- The tool never logs the private key. Parser errors must not echo key material. The identity object's text form does not include key bytes.

## Local policy

The CLI does not open a network connection. It does not send crashes or analytics. Privacy is the privacy of this Unix account and this disk.

`git` on the operator’s machine is the only network path, and only when a person runs git.

## Safe harbor

Research is welcome when you:

- Avoid privacy violations, destruction, and disruption beyond a local proof
- Do not use data that is not yours except as the smallest proof
- Do not use the finding except to report it
- Report through the private channels above

A public pull request that contains a live private key is not a report. Stop using that key. Then send the private advisory.
