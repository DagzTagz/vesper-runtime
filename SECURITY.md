# Security Policy

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product.

vesper-runtime is a local development and provenance tool. It signs JSON with ECDSA P-256, or with HMAC-SHA256 if the `ecdsa` package cannot be imported. It is not a wallet, not a money transmitter, not a security offering, not an official scientific instrument, and not an anonymity system.

No bounty is offered.

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

The kernel is written against these failures.

| Id | Failure | What the code does |
|----|---------|--------------------|
| T1 | A private key lands in git, a log, `evidence.md`, or a world-readable file | Key bytes stay in `crypto.py`. Export refuses to copy `identity/`. Evidence omits output that contains PEM-shaped fragments. |
| T2 | Schema drift: missing fields, wrong types, unknown properties | `schema check` reports problems. `schema heal` fills documented structural defaults. It rejects a missing character id, universe id, schema version, or forks list. Unknown properties are kept. Reserved names `__proto__`, `constructor`, and `prototype` are rejected. |
| T3 | Fork forgery: wrong key, mutated body, detached signature | `verify` rebuilds the canonical body, checks the key id, and checks the signature. |
| T4 | A parent link breaks, or an old snapshot is replayed as the new head | `parent_hash` must match the parent file. The filename stem must match `name`. `created_unix` must not go backwards. An identical `state_hash` to the parent is a replay. |
| T5 | Memory poisoning: unbounded STM, NaN weights, path characters in ids | STM cap is 100. Non-finite weights are rejected. Ids are a single safe segment. |
| T6 | Paths escape the workspace | The workspace root is explicit. `..`, absolute paths, and symlinks that leave the root are rejected. |
| T7 | A process uses a mode `0644` private key | The key is opened with `O_NOFOLLOW`. Mode is `fstat` on that descriptor. Anything other than `0600` is refused and is not chmod'd into shape. The identity directory must be `0700`. |
| T8 | Tests are green while forged-signature or decay cases never ran | `vesper export` runs those checks and writes the commands into `evidence.md`. A suite that skipped them does not get `"pass": true`. |

## Keys

- Algorithm: ECDSA on NIST P-256 (`secp256r1`) via the PyPI package `ecdsa`, isolated in `src/vesper/crypto.py`.
- Signed bytes: UTF-8 JSON, `sort_keys=True`, separators `(',', ':')`, no NaN or Infinity. ECDSA signs the 32-byte SHA-256 digest with `sign_digest` and DER encoding. The stored signature is hex.
- Key id: first 16 hex characters of SHA-256 over the uncompressed public point (`0x04 || X || Y`). The truncation identifies a key. The signature is the check.
- On-disk name: `identity/edcsa-p256.priv`. Directory mode `0700`. File mode `0600`. `public.json` is `0644` and contains the kid, the algorithm, and the public point hex. It does not contain a PEM block.
- Fallback: if `import ecdsa` fails, the kernel writes `identity/hmac.key` and authenticates the canonical bytes with HMAC-SHA256. `public.json` then stores the kid only. HMAC verify loads that key from the workspace. ECDSA verify uses the public point inside the fork file.
- Tests generate keys in a temporary directory. pytest is set to keep none of those directories (`tmp_path_retention_policy = none`). Do not commit a key so a test can stay offline.
- A killed test run can still leave a key under `/tmp/pytest-of-*`. Shred the key file, then remove that tree, before you pack a release. Unlinking a name does not scrub freed disk blocks. This tool does not offer a free-space wipe.
- The tool never logs the private key. Parser errors must not echo key material.

HMAC-SHA256 and ECDSA P-256 are published algorithms. This project does not implement a custom cipher, steganography, or traffic obfuscation. There is no unpublished algorithm and no “military-grade” claim.

## Local policy

The CLI does not open a network connection. It does not send crashes or analytics. Privacy is the privacy of this Unix account and this disk. This document is not a HIPAA claim, a SOC 2 claim, or a certification.

`git` on the operator’s machine is the only network path, and only when a person runs git.

## Safe harbor

Research is welcome when you:

- Avoid privacy violations, destruction, and disruption beyond a local proof
- Do not use data that is not yours except as the smallest proof
- Do not use the finding except to report it
- Report through the private channels above

A public pull request that contains a live private key is not a report. Rotate that key. Then send the private advisory.
