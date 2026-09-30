# Contributing to vesper-runtime

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product.

This is a community repository under the DagzTagz name. DagzTagz owns it. Grok Build may draft a patch under the contributor’s own account and terms. Humans review the patch. The runtime does not call the Grok API.

You do not need to be a cryptographer to help. A clear bug report, a doc fix, and a careful reading of `evidence.md` all count.

## Before you start

1. Read [README.md](README.md) and [getting-started.md](getting-started.md).
2. Read [SECURITY.md](SECURITY.md) before you touch keys or `crypto.py`.
3. Read [ROADMAP.md](ROADMAP.md) so a patch does not add a wallet, a network client, or a model call.

Small fixes can be a pull request. A new signature scheme, a new dependency, or a license change needs an issue first.

Security reports go through [SECURITY.md](SECURITY.md). Do not file them as public issues.

## Ground rules

- Prefer a short patch that keeps the threat model over a convenient bypass.
- Do not weaken the `0600` / `0700` checks so a test can pass. Do not chmod a weak key and continue.
- Do not add a dependency other than `ecdsa`. The standard library is the default. No numpy, no web framework, no cloud SDK.
- `src/vesper/crypto.py` is the only module that reads or writes private key bytes.
- Tests use `tempfile` (pytest’s `tmp_path`) and an injected `now`. Do not `sleep` for decay.
- Test keys are generated at test time and destroyed with the temp directory. Do not commit a private key, a `.env`, or `workspace/`.
- No GPL-incompatible copyleft.
- Do not vendor the `ecdsa` package. Notice it in [NOTICE](NOTICE).
- Apache-2.0. Copyright DagzTagz contributors. The work is AS IS.

## Setup

```bash
git clone https://github.com/DagzTagz/vesper-runtime.git
cd vesper-runtime
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
```

What good looks like: pytest exits 0.

Work on a branch. Fork if you do not have write access.

## Tests that must stay honest

A change to schema, memory, forks, or keys needs a test that would fail if the check were deleted.

In particular:

- `fixtures/forged-fork.json` must be passed to `verify` and must exit 2
- Decay must move a weight when `now` is later than `ts`, and must not move it when `now == ts`
- A mode `0644` key must be refused and left at `0644`
- A name containing `..` must be rejected

`vesper export --audit` on a real workspace is the bundle a reviewer can read. Do not hand-edit `score.json` to flip `"pass"` to true.

## Pull requests

One concern per PR. Say what changed, why, and the command you ran.

Commit subjects, present tense:

```text
fix: refuse a private key that is not mode 0600
docs: describe identity rotation in getting-started
```

Signed commits are welcome. They are not required for a first patch. Maintainers on this machine sign with their own key. An agent session that cannot unlock a signing key should leave the commit for a human, or say that the commit is unsigned.

If an AI tool wrote part of the diff, say so in the PR. You still own the explanation. Do not paste private keys into a hosted model.

## Bugs and ideas

Include what you ran, what you expected, what happened, the OS, and the Python version. Redact paths that contain a home directory if you want to. Never paste a private key.

Feature requests should name the problem first. If the idea needs a network call or a new cryptographic primitive, it is out of scope for this repo.

## Conduct

Be kind. Stay on the patch. No harassment. Credit other people’s work. Maintainer scope decisions are about the kernel, not about the person.
